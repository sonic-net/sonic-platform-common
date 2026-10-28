"""
Select the CDB target of an NVIDIA CPO device before each CDB command, and
serialize the CDB commands of each module.

The laser source (ELS) has no CDB of its own: its commands go through the CDB
of its optical engine (OE). xcvrd and cpoutil send commands to that CDB at the
same time, so each command, with its target selection and the reading of its
reply, holds a lock of the module, shared by its OE and its ELS.
"""

import contextlib
import fcntl
import functools
import os
import threading
import time

# Lower page 00h, byte 26: Module Global Controls.
CDB_TARGET_SELECT_OFFSET = 26
CDB_TARGET_SELECT_MASK = 0x01

CDB_TARGET_OE = 0
CDB_TARGET_ELS = 1

# Seconds between two attempts to take a CDB lock held by another process,
# when waiting at most a given time for it.
_CDB_LOCK_RETRY_INTERVAL = 0.05


class CdbLock:
    """
    The CDB lock of one module.

    An flock() on a file keeps the other processes out, and an RLock the
    other threads of this process. It is reentrant, since a firmware
    operation, the CDB target selection, a command and the reading of its
    reply hold it in turn; only the outermost hold takes the flock. A holder
    that dies releases it.

    `with lock:` waits for the holder. hold(timeout) waits at most timeout
    seconds and raises RuntimeError after: a firmware operation, which holds
    the lock for long, uses it so that another one fails instead of waiting,
    while it still waits for a single command of another user.
    """

    def __init__(self, path):
        self._path = path
        self._rlock = threading.RLock()
        self._depth = 0
        self._fd = None

    def _acquire(self, timeout=None):
        """Take the lock, waiting at most timeout seconds (None: no limit); return False on timeout."""
        deadline = None if timeout is None else time.monotonic() + timeout
        if not self._rlock.acquire(timeout=-1 if timeout is None else timeout):
            return False
        try:
            if self._depth == 0:
                fd = os.open(self._path, os.O_RDWR | os.O_CREAT, 0o644)
                try:
                    if deadline is None:
                        fcntl.flock(fd, fcntl.LOCK_EX)
                    else:
                        while True:
                            try:
                                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                                break
                            except BlockingIOError:
                                if time.monotonic() >= deadline:
                                    os.close(fd)
                                    self._rlock.release()
                                    return False
                                time.sleep(_CDB_LOCK_RETRY_INTERVAL)
                except BaseException:
                    os.close(fd)
                    raise
                self._fd = fd
            self._depth += 1
        except BaseException:
            self._rlock.release()
            raise
        return True

    def _release(self):
        self._depth -= 1
        if self._depth == 0:
            # Closing the file releases the flock.
            os.close(self._fd)
            self._fd = None
        self._rlock.release()

    def __enter__(self):
        self._acquire()
        return self

    def __exit__(self, *exc_info):
        self._release()
        return False

    @contextlib.contextmanager
    def hold(self, timeout):
        """
        Hold the lock, waiting at most timeout seconds for it

        Raises:
            RuntimeError: Another user held the lock for timeout seconds
        """
        if not self._acquire(timeout):
            raise RuntimeError('The CDB of the module is busy: another firmware operation is in progress')
        try:
            yield
        finally:
            self._release()


class _NoCdbLock:
    """The lock of a device that names no lock file: it does nothing."""

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def hold(self, timeout):
        return contextlib.nullcontext()


_cdb_locks = {}
_cdb_locks_guard = threading.Lock()


def _get_cdb_lock(path):
    """Return the one CdbLock of this process for a lock file."""
    with _cdb_locks_guard:
        lock = _cdb_locks.get(path)
        if lock is None:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            lock = _cdb_locks[path] = CdbLock(path)
        return lock


def get_module_cdb_lock(device):
    """
    Return the CDB lock of the module of an NVIDIA CPO platform device.

    The lock is the file cdb<sdk_index>.lock in the CDB_LOCK_DIR of the
    device, so the OE and the ELS of a module share it. A device without them
    gets a lock that does nothing.

    Returns:
        A CdbLock, or a lock that does nothing
    """
    lock_dir = getattr(device, 'CDB_LOCK_DIR', None)
    sdk_index = getattr(device, 'sdk_index', None)
    if not isinstance(lock_dir, str) or not isinstance(sdk_index, int):
        return _NoCdbLock()
    return _get_cdb_lock(os.path.join(lock_dir, 'cdb{}.lock'.format(sdk_index)))


class CdbTargetHandler:
    """
    A CDB handler that selects the CDB target before each method call.

    The target is one register for the whole module, so the selection and
    the call hold the CDB lock of the module together.
    """

    def __init__(self, handler, select_target, lock=contextlib.nullcontext):
        self._handler = handler
        self._select_target = select_target
        self._lock = lock

    def __getattr__(self, name):
        attr = getattr(self._handler, name)
        if not callable(attr):
            return attr

        @functools.wraps(attr)
        def call(*args, **kwargs):
            with self._lock():
                if not self._select_target():
                    raise RuntimeError('Failed to select the CDB target')
                return attr(*args, **kwargs)
        setattr(self, name, call)
        return call


class NvidiaCpoCdbTargetMixin:
    """
    Select CDB_TARGET for every CDB command of the API's CDB handlers, under
    the CDB lock of the module.

    Mix it in ahead of the API classes that own the CDB handlers, so that its
    handler accessors take precedence.
    """

    CDB_TARGET = CDB_TARGET_OE

    def cdb_lock(self):
        """
        Hold the CDB of the module, so that no other process or thread sends
        it a command meanwhile. Reentrant.

        It is the lock of the platform device that reads the EEPROM: see
        get_module_cdb_lock().

        Returns:
            A context manager
        """
        return get_module_cdb_lock(getattr(self.xcvr_eeprom.reader, '__self__', None))

    def _select_cdb_target(self):
        """Point the CDB at CDB_TARGET; return False if the EEPROM access failed."""
        raw = self.xcvr_eeprom.reader(CDB_TARGET_SELECT_OFFSET, 1)
        if not raw:
            return False
        control = raw[0]
        if control & CDB_TARGET_SELECT_MASK == self.CDB_TARGET:
            return True
        control = (control & ~CDB_TARGET_SELECT_MASK) | self.CDB_TARGET
        return bool(self.xcvr_eeprom.writer(CDB_TARGET_SELECT_OFFSET, 1, bytearray([control])))

    def _create_cdb_fw_handler(self):
        # Creating the firmware handler sends CDB commands.
        with self.cdb_lock():
            if not self._select_cdb_target():
                return None
            handler = super()._create_cdb_fw_handler()
        if handler is None:
            return None
        return CdbTargetHandler(handler, self._select_cdb_target, self.cdb_lock)

    @property
    def cdb_handler(self):
        handler = super().cdb_handler
        if handler is None:
            return None
        return CdbTargetHandler(handler, self._select_cdb_target, self.cdb_lock)
