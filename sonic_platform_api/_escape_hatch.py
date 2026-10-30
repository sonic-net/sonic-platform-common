"""The bodies the generator cannot derive.

Hand-written, and deliberately small: everything here is declared in
`facade.pyi` as an `EscapeHatch` with a reason, so a body that appears without
a matching declaration is a body somebody should have generated.
"""

import signal
import sys
import threading
from typing import Any, Callable, Optional


def _call(fn: Any, default: Any = None) -> Any:
    """The same not-implemented handling the generated facade uses.

    Duplicated rather than imported: facade.py imports this module, so taking
    it the other way would be a cycle, and a five-line helper is a smaller
    price than a deferred import in every method here.
    """
    if fn is None:
        return default
    try:
        r = fn()
    except NotImplementedError:
        return default
    if r is None or r is NotImplementedError:
        return default
    return r

# Where a platform's thermal policy lives.  thermalctld:1435 spells the same
# path; it is a platform artefact rather than daemon configuration, which is
# why the facade owns it once instead of each daemon passing it in.
POLICY_FILE: str = '/usr/share/sonic/platform/thermal_policy.json'


# Where a platform declares the sensors it exposes through sysfs rather than
# through a driver object.  sensormond:516 reads the same file.
SENSORS_YAML = 'sensors.yaml'

# The seven status strings ChassisBase.get_change_event documents, named.  A
# value not in here is passed through as-is: vendors are not limited to these,
# and a facade that dropped an eighth would hide the one event somebody needed.
CHANGE_EVENT_KINDS = {
    '0': 'removed',
    '1': 'inserted',
    '2': 'i2c_stuck',
    '3': 'bad_eeprom',
    '4': 'unsupported_cable',
    '5': 'high_temperature',
    '6': 'bad_cable',
}


# -- shutdown ---------------------------------------------------------------
#
# A vendor may install SIGTERM/SIGINT handlers while its chassis is built, so
# that its readiness waits abort when the daemon is told to stop: mlnx's
# `utils.watch_shutdown_signals()` (chassis.py:151) sets an event that ends the
# 300 s wait in `ThermalUpdater.start()` on SPC1, then chains to whatever
# handler was installed before it -- and when that is `SIG_DFL` it re-raises
# the signal, `signal.signal(signum, SIG_DFL); os.kill(os.getpid(), signum)`.
#
# In a Python daemon the previous handler is the daemon's own, so the chain is
# harmless and the wait ends.  In a Rust daemon the daemon owns the signals
# (the bridge resets the interpreter's table and puts the process's
# dispositions back), so the vendor's handler would never run -- and if it
# did, the previous handler it captured would be `SIG_DFL` and it would kill
# the process mid-shutdown.  So the bridge arms the table with a no-op before
# the chassis is built, keeps whatever the vendor installed on top of it, and
# `notify_shutdown()` runs that: the event is set, the chain ends in the
# no-op, and the daemon carries on with its own shutdown.

_SHUTDOWN_SIGNALS = ('SIGTERM', 'SIGINT')

# signum -> the vendor's handler, the first one kept.  Process-wide: the
# vendor's state is (mlnx installs its handlers once per process), and the
# Rust daemons open the platform on more than one thread.
_shutdown_handlers: dict[int, Callable[..., Any]] = {}
# Held for good by the first `notify_shutdown()`: a lock rather than a flag so
# that two threads cannot both get past the check.
_shutdown_notified = threading.Lock()
# Between `arm_shutdown_capture()` and `disarm_shutdown_capture()`: the
# daemon's handlers are out of the way, so a signal that arrives is the
# daemon's, and is kept for the bridge to raise again.
_capturing = False
_deferred_signals: list[int] = []


def _ignore_shutdown_signal(signum: int, frame: Any) -> None:
    """What a vendor's shutdown handler chains to, and what runs for a signal
    nobody else claimed while the chassis is built.  Never installed for
    longer than that; the shutdown `notify_shutdown()` hands on is not one to
    keep."""
    if _capturing and not _shutdown_notified.locked():
        _deferred_signals.append(signum)


def arm_shutdown_capture() -> bool:
    """Before the vendor's chassis is built: give a handler installed during
    the build a harmless previous handler to chain to.

    False off the main thread, where `signal.signal()` raises -- and where a
    vendor's installer has the same guard, so there is nothing to capture.
    """
    global _capturing
    for name in _SHUTDOWN_SIGNALS:
        signum = getattr(signal, name, None)
        if signum is None:
            continue
        try:
            signal.signal(signum, _ignore_shutdown_signal)
        except (ValueError, OSError):
            return False
    _capturing = True
    return True


def capture_shutdown_handlers() -> None:
    """After the build: keep what the vendor installed over the no-op.  The
    first handler kept for a signal stays -- a later build finds the vendor's
    installer already done, and the no-op still in place."""
    for name in _SHUTDOWN_SIGNALS:
        signum = getattr(signal, name, None)
        if signum is None or signum in _shutdown_handlers:
            continue
        handler = signal.getsignal(signum)
        if callable(handler) and handler is not _ignore_shutdown_signal:
            _shutdown_handlers[signum] = handler


def disarm_shutdown_capture() -> list[int]:
    """Once the interpreter's table is reset: the signals that arrived while
    the chassis was built, in order, for the bridge to raise again when the
    daemon's handlers are back.  Without that a SIGTERM sent during start-up
    would be lost to the daemon."""
    global _capturing
    _capturing = False
    taken = list(_deferred_signals)
    del _deferred_signals[:]
    return taken


def notify_shutdown() -> None:
    """Run the vendor's shutdown handler as the signal would have: SIGTERM's,
    or SIGINT's if it kept only that.  Once per process, and never raising --
    a handler that fails must not stop the daemon stopping."""
    if not _shutdown_notified.acquire(blocking=False):
        return
    for name in _SHUTDOWN_SIGNALS:
        signum = getattr(signal, name, None)
        handler = _shutdown_handlers.get(signum) if signum is not None else None
        if handler is None:
            continue
        try:
            handler(signum, None)
        except BaseException as e:  # SystemExit and KeyboardInterrupt too
            sys.stderr.write('vendor shutdown handler for %s failed: %r\n' % (name, e))
        return


class EscapeHatches(object):
    """The hatch bodies, and what they keep between calls.

    One per facade, holding the chassis.  The thermal manager, the EEPROM,
    the parsed sensors.yaml, the sensors built from it and the Pcie and
    storage objects are kept once found, as the Python daemons keep theirs.
    """

    def __init__(self, chassis: Any) -> None:
        self._chassis = chassis
        self._manager: Any = None
        self._loaded = False
        self._sensors_data: Any = None
        self._sensors_built: dict[str, Any] = {}
        self._eeprom: Any = None
        self._pcie: Any = None
        self._pcie_tried = False
        self._storage: Any = None
        self._storage_tried = False

    # -- thermal manager ----------------------------------------------------
    #
    # `ChassisBase.get_thermal_manager()` returns a *class*, not an instance,
    # and all twelve of its methods are `@classmethod` over process-global
    # state.  Two of them -- `init_thermal_algorithm` and `run_policy` -- take
    # the chassis back as an argument, and the Python policy engine then calls
    # back through it into the platform API.
    #
    # Holding the chassis here is what keeps that entirely inside Python.  The
    # Rust side sees four calls that take no arguments, so the bridge never
    # re-enters Python from Rust from Python, and the thermal policy plugin
    # ecosystem stays where it is.

    def _get(self) -> Any:
        """The thermal manager class, or None on a platform without one.

        Three ways to not have one, and a platform uses all three: the chassis
        has no such method, the method raises, or it hands back None.
        """
        if self._manager is None:
            fn = getattr(self._chassis, 'get_thermal_manager', None)
            if fn is None:
                return None
            try:
                self._manager = fn()
            except NotImplementedError:
                return None
        return self._manager

    def tm_initialize(self) -> None:
        """Start-up, in the order `ThermalControlDaemon.__init__` does it.

        `load()` and `init_thermal_algorithm()` belong with `initialize()`:
        a manager that has been initialised but not loaded has no policies,
        and `run_policy` on it is a no-op that looks like a working one.

        Unlike the other `tm_*` calls, this one lets a `NotImplementedError`
        from `get_thermal_manager()` through.  thermalctld asks for the manager
        inside the same `try` as `initialize()`, and its `except
        NotImplementedError` logs "Thermal manager is not supported on this
        platform"; swallowing it here would leave a daemon over this facade
        unable to say the same.  Every later call treats that platform as one
        without a manager, as thermalctld does.
        """
        if self._manager is None:
            fn = getattr(self._chassis, 'get_thermal_manager', None)
            if fn is not None:
                self._manager = fn()
        mgr = self._manager
        if mgr is None:
            return
        mgr.initialize()
        mgr.load(POLICY_FILE)
        mgr.init_thermal_algorithm(self._chassis)
        self._loaded = True

    def tm_run_policy(self) -> None:
        """One policy round.

        Skipped rather than raised when nothing was loaded: a platform whose
        fan policy lives in firmware ships a `thermal_policy.json` with no
        policies in it, and that is not an error.
        """
        mgr = self._get()
        if mgr is None or not self._loaded:
            return
        mgr.run_policy(self._chassis)

    def tm_get_interval(self) -> Optional[float]:
        """How often `tm_run_policy` should run, in seconds.

        None when the platform has no manager -- the caller then keeps its own
        polling interval rather than adopting one that does not exist.
        """
        mgr = self._get()
        if mgr is None:
            return None
        try:
            interval = mgr.get_interval()
        except NotImplementedError:
            return None
        # ThermalManagerBase declares this as int; vendors return float. The
        # facade publishes seconds, so it is a float either way.
        return None if interval is None else float(interval)

    def tm_deinitialize(self) -> None:
        """Shutdown.  `stop()` then `deinitialize()`, as thermalctld does at
        :1526 and :1506 respectively."""
        mgr = self._get()
        if mgr is None:
            return
        try:
            mgr.stop()
        except NotImplementedError:
            pass
        mgr.deinitialize()
        self._loaded = False

    def tm_stop(self) -> None:
        """`stop()` alone: what thermalctld's signal handler does the moment
        SIGTERM arrives (thermalctld:1610-1612), before `deinit()`."""
        mgr = self._get()
        if mgr is None:
            return
        try:
            mgr.stop()
        except NotImplementedError:
            pass

    # -- shutdown -------------------------------------------------------------

    def notify_shutdown(self) -> None:
        """See the module-level `notify_shutdown()`: the handlers it runs are
        the process's, not this facade's."""
        notify_shutdown()

    # -- system EEPROM ------------------------------------------------------

    def _eeprom_obj(self) -> Any:
        """The chassis' EEPROM object, or None on a platform without one.

        Cached like the thermal manager: `get_eeprom()` opens a device on some
        platforms, and syseepromd asks once a minute forever.
        """
        if self._eeprom is None:
            fn = getattr(self._chassis, 'get_eeprom', None)
            if fn is None:
                return None
            try:
                self._eeprom = fn()
            except NotImplementedError:
                return None
        return self._eeprom

    def eeprom_update_db(self) -> str:
        """`read_eeprom()` then `update_eeprom_db()`, as syseepromd:85-96 does.

        The two belong together: `update_eeprom_db` takes the bytes the first
        call returns, and nothing else in the surface wants them, so handing a
        raw EEPROM image across the language boundary would buy nothing.

        A platform that cannot read it answers 'read_failed' rather than
        raising, and one that read it and could not write the table
        'update_failed': syseepromd logs which half it was -- its
        ERR_FAILED_EEPROM and ERR_FAILED_UPDATE_DB -- and leaves the table
        alone until the next cycle.
        """
        eeprom = self._eeprom_obj()
        if eeprom is None:
            return 'read_failed'
        try:
            data = eeprom.read_eeprom()
        except (NotImplementedError, AttributeError):
            return 'read_failed'
        if data is None:
            return 'read_failed'
        try:
            # Python's own contract: 0 is success, anything else is failure.
            failed = eeprom.update_eeprom_db(data)
        except (NotImplementedError, AttributeError):
            return 'update_failed'
        return 'update_failed' if failed else 'updated'

    # -- sensors.yaml -------------------------------------------------------
    #
    # `SensorFs.factory(sensor_cls, data)` takes a *class* as its first
    # argument, which no declaration can express.  What it produces is an
    # ordinary list of sensor objects, so the stub declares these as flatten
    # sources with a `provider=` and the rows come out with the same columns,
    # in the same order, as every other sensor.

    def _sensors_yaml(self) -> Any:
        """The platform's sensors.yaml, or an empty mapping.

        Read once. A platform without the file is the common case, not an
        error -- sensormond:512-526 swallows every failure here for exactly
        that reason, and a facade that shouted instead would shout on most
        platforms.  A file whose root is not a mapping is as good as none:
        sensormond's `'voltage_sensors' in sensors_data` finds no key in a
        list or a scalar, or raises into that same `except`, and the
        chassis' own sensors are collected all the same.
        """
        if self._sensors_data is not None:
            return self._sensors_data
        self._sensors_data = {}
        try:
            import os

            import yaml
            from sonic_py_common import device_info

            platform_path, _hwsku = device_info.get_paths_to_platform_and_hwsku_dirs()
            with open(os.path.join(platform_path, SENSORS_YAML)) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                self._sensors_data = data
        except Exception:
            pass
        return self._sensors_data

    def _sensors_fs(self, key: str, cls_name: str) -> Any:
        """The sensors.yaml sensors of one kind, built once.

        sensormond builds its list once and polls the same objects every
        cycle (sensormond:521-523), and the objects remember: `SensorFs` seeds
        its recorded minimum and maximum from the reading it was built with
        and moves them as readings come in.  Rebuilt per call, they recorded
        nothing but the current value.  A malformed entry is also warned about
        once, by the factory, rather than every cycle.
        """
        if key in self._sensors_built:
            return self._sensors_built[key]
        built: Any = []
        data = self._sensors_yaml().get(key)
        if data:
            try:
                from sonic_platform_base import sensor_fs

                cls = getattr(sensor_fs, cls_name)
                # The class is passed to its own factory; that is the signature.
                built = cls.factory(cls, data)
            except Exception:
                built = []
        self._sensors_built[key] = built
        return built

    def voltage_sensors_from_yaml(self) -> Any:
        return self._sensors_fs('voltage_sensors', 'VoltageSensorFs')

    def current_sensors_from_yaml(self) -> Any:
        return self._sensors_fs('current_sensors', 'CurrentSensorFs')

    # -- PCIe ---------------------------------------------------------------
    #
    # pcied is the one daemon that does not reach the platform through the
    # chassis.  It builds its own object -- the vendor's `sonic_platform.pcie
    # .Pcie` if there is one, the base `PcieUtil` otherwise -- and the
    # two-step import with a fallback is what makes this a hatch rather than a
    # declaration (`pcied:47-69`).

    def _pcie_util(self) -> Any:
        """The platform's Pcie object, or None.

        Built once.  A platform with neither module is not an error here: the
        rows come back empty and pcied publishes no verdict.  The Python daemon
        raises out of its constructor instead, and a restart cannot bring a
        module back, so either way nothing is checked.
        """
        if self._pcie_tried:
            return self._pcie
        self._pcie_tried = True
        try:
            from sonic_py_common import device_info

            platform_path, _hwsku = device_info.get_paths_to_platform_and_hwsku_dirs()
        except Exception:
            return None
        try:
            from sonic_platform.pcie import Pcie

            self._pcie = Pcie(platform_path)
        except Exception:
            try:
                from sonic_platform_base.sonic_pcie.pcie_common import PcieUtil

                # In this repo but untyped, as every platform base class is.
                self._pcie = PcieUtil(platform_path)  # type: ignore[no-untyped-call]
            except Exception:
                self._pcie = None
        return self._pcie

    def get_pcie_devices(self) -> Any:
        """`get_pcie_check()`, with the yaml's hex strings parsed.

        `result` is `'Passed'` or `'Failed'`; anything else counts as not
        found, because the only two a caller can act on are those.

        A platform without a pcie.yaml answers with `sys.exit()`:
        `PcieUtil.load_config_file` prints two lines to stdout and raises
        SystemExit, on every call.  The Python daemon lets it end the process,
        quietly and with 0, so supervisord leaves it down.  Here it is the
        empty parts list it means, and the object is dropped, so the next call
        does not print the same two lines a minute later, and the one after
        that, for the life of the switch.
        """
        from .facade import PcieDevice

        util = self._pcie_util()
        if util is None:
            return []
        try:
            answer = util.get_pcie_check()
        except (NotImplementedError, AttributeError):
            return []
        except SystemExit:
            self._pcie = None
            return []
        rows = []
        for item in answer or []:
            try:
                rows.append(PcieDevice(
                    name=str(item.get('name', '')),
                    bus=int(str(item['bus']), 16),
                    dev=int(str(item['dev']), 16),
                    fn=int(str(item['fn']), 16),
                    present=item.get('result') == 'Passed',
                ))
            except (KeyError, TypeError, ValueError):
                # One malformed entry in pcie.yaml does not invalidate the
                # rest of the parts list.
                continue
        return rows

    def get_pcie_aer_stats(self, bus: int, dev: int, func: int) -> Any:
        """`get_pcie_aer_stats()`, flattened out of its three severities."""
        from .facade import PcieAerStat

        util = self._pcie_util()
        if util is None:
            return []
        try:
            answer = util.get_pcie_aer_stats(bus=bus, dev=dev, func=func)
        except (NotImplementedError, AttributeError):
            return []
        rows = []
        for severity, fields in (answer or {}).items():
            for field, value in (fields or {}).items():
                rows.append(PcieAerStat(
                    severity=str(severity), field=str(field), value=str(value),
                ))
        return rows

    # -- storage ------------------------------------------------------------
    #
    # stormond is the other daemon that does not go through the chassis.  Its
    # object walks /sys/block and picks a utility class per disk; the readings
    # are only current after `fetch_parse_info` has run for that disk, which is
    # why this is one method and not eleven columns.

    def _storage_devices(self) -> Any:
        """The `StorageDevices` composition object, or None."""
        if self._storage_tried:
            return self._storage
        self._storage_tried = True
        try:
            from sonic_platform_base.sonic_storage.storage_devices import StorageDevices

            # In this repo but untyped, as every platform base class is.
            self._storage = StorageDevices()  # type: ignore[no-untyped-call]
        except Exception:
            self._storage = None
        return self._storage

    def get_storage_devices(self) -> Any:
        """Every disk, refreshed.

        One disk that cannot be read does not cost the others: stormond reads
        each disk in its own `try`, twice -- its model and serial once at
        start-up (`stormond:311-332`), and the rest every cycle, starting with
        `fetch_parse_info` (`stormond:335-393`) -- and catches whatever is
        raised, logging `str(ex)`.  So does this, pass for pass: an exception
        is the disk's `static_error` or `error`, the readings of that pass are
        'N/A', and the other disks are read as if nothing had happened.
        """
        from .facade import StorageDeviceInfo

        devices = self._storage_devices()
        if devices is None:
            return []

        def _count(v: Any) -> Any:
            """A counter the daemon does arithmetic on, or None.  The getter
            answered; this is only whether its answer is a number."""
            if isinstance(v, bool):
                return None
            try:
                return int(v)
            except (TypeError, ValueError):
                return None

        import os

        try:
            from sonic_platform_base.sonic_storage.storage_devices import BLKDEV_BASE_PATH
        except Exception:
            # Only where that module will not import, which is where the
            # devices came from somewhere else -- stormond itself would not
            # have started.  Its value.
            BLKDEV_BASE_PATH = '/dev'

        rows = []
        for name, obj in sorted(getattr(devices, 'devices', {}).items()):
            row = StorageDeviceInfo(
                name=name, available=obj is not None,
                model='N/A', serial='N/A', firmware='N/A', health='N/A',
                temperature='N/A', disk_io_reads='N/A', disk_io_writes='N/A',
                reserved_blocks='N/A', fs_io_reads=None, fs_io_writes=None,
                static_error=None, error=None,
            )
            rows.append(row)
            if obj is None:
                # A disk the switch has and no utility class handles.  Carried
                # rather than dropped; the daemon has a line to say about it.
                continue
            try:
                model = str(obj.get_model())
                serial = str(obj.get_serial())
                row.model, row.serial = model, serial
            except Exception as e:
                row.static_error = str(e)
            try:
                obj.fetch_parse_info(os.path.join(BLKDEV_BASE_PATH, name))
                # In stormond's order, every one read before the row changes:
                # a pass that fails part way publishes nothing of it.
                firmware = str(obj.get_firmware())
                health = str(obj.get_health())
                temperature = str(obj.get_temperature())
                fs_io_reads = _count(obj.get_fs_io_reads())
                fs_io_writes = _count(obj.get_fs_io_writes())
                disk_io_reads = str(obj.get_disk_io_reads())
                disk_io_writes = str(obj.get_disk_io_writes())
                reserved_blocks = str(obj.get_reserved_blocks())
            except Exception as e:
                row.error = str(e)
                continue
            row.firmware, row.health, row.temperature = firmware, health, temperature
            row.fs_io_reads, row.fs_io_writes = fs_io_reads, fs_io_writes
            row.disk_io_reads, row.disk_io_writes = disk_io_reads, disk_io_writes
            row.reserved_blocks = reserved_blocks
        return rows

    # -- change events ------------------------------------------------------

    def get_change_event(self, timeout_ms: int) -> Any:
        """Flatten what `ChassisBase.get_change_event` answered.

        `{'fan': {'0': '0'}, 'sfp': {'11': '0'}}` becomes two rows.  The outer
        key is the device type and the inner key is the device id; the nesting
        carries nothing a row cannot.

        `ok` is carried rather than raised on.  It reads like a success flag
        and is not one -- `ok=False` is how a platform reports a system-level
        event, with the detail under the key the daemon watches for.
        """
        # Imported here rather than at module scope: facade.py imports this
        # module, so naming it at the top would be a cycle.
        from .facade import ChangeEvent, ChangeEventBatch

        fn = getattr(self._chassis, 'get_change_event', None)
        if fn is None:
            raise NotImplementedError('ChassisBase.get_change_event is not implemented')
        answer = fn(timeout_ms)
        try:
            ok, mapping = answer
        except (TypeError, ValueError):
            raise NotImplementedError(
                'ChassisBase.get_change_event did not answer (bool, dict)')

        events = []
        if not hasattr(mapping, 'items'):
            mapping = {}
        for device_type, changes in mapping.items():
            if not hasattr(changes, 'items'):
                # A platform that answered something other than a mapping of
                # device id to status.  Skipped rather than raised: this runs
                # in a polling loop, and one malformed device type should not
                # take the others with it.
                continue
            for device_id, status in changes.items():
                status = str(status)
                events.append(ChangeEvent(
                    device_type=str(device_type),
                    device_id=str(device_id),
                    status=status,
                    kind=CHANGE_EVENT_KINDS.get(status),
                ))
        return ChangeEventBatch(ok=bool(ok), events=events)

    # -- asics --------------------------------------------------------------

    def get_asics(self) -> Any:
        """`ModuleBase.get_all_asics()` answers `[(asic_id, pci_address), ...]`.

        A list of tuples, not of device objects, so a flatten plan has nothing
        to call a getter on.  Short entries read as a missing address rather
        than raising: this runs every cycle.
        """
        from .facade import AsicInfo

        rows = []
        modules = _call(getattr(self._chassis, 'get_all_modules', None)) or ()
        for index, module in enumerate(modules):
            name = _call(getattr(module, 'get_name', None)) or 'Module %d' % (index + 1)
            for entry in _call(getattr(module, 'get_all_asics', None)) or ():
                try:
                    asic_id = str(entry[0])
                except (TypeError, IndexError, KeyError):
                    continue
                try:
                    address = str(entry[1])
                except (TypeError, IndexError, KeyError):
                    address = None
                rows.append(AsicInfo(
                    parent_name=name, asic_id=asic_id, pci_address=address))
        return rows

    # -- bmc commands -------------------------------------------------------

    def _bmc(self) -> Any:
        bmc = _call(getattr(self._chassis, 'get_bmc', None))
        if bmc is None:
            raise NotImplementedError('ChassisBase.get_bmc is not implemented')
        return bmc

    def _bmc_call(self, method: str, *args: Any) -> Any:
        """`(code, payload)` from one BMC command, or NotImplementedError."""
        fn = getattr(self._bmc(), method, None)
        if fn is None:
            raise NotImplementedError('BMCBase.%s is not implemented' % method)
        answer = fn(*args)
        try:
            code, payload = answer
        except (TypeError, ValueError):
            raise NotImplementedError(
                'BMCBase.%s did not answer (code, payload)' % method)
        return int(code), payload

    def _result(self, method: str, *args: Any) -> Any:
        from .facade import BmcResult

        code, payload = self._bmc_call(method, *args)
        return BmcResult(code=code, message=None if payload is None else str(payload))

    def bmc_open_session(self) -> Any:
        """`(code, (message, (session_id, token)))`.

        The credentials are absent on failure, and `config/bmc.py:41` checks
        for that before reading them -- so a row with the code set and the
        credentials None is the shape a caller already handles.
        """
        from .facade import BmcResult

        code, payload = self._bmc_call('open_session')
        message, credentials = None, None
        try:
            message, credentials = payload
        except (TypeError, ValueError):
            message = None if payload is None else str(payload)
        session_id = token = None
        if credentials:
            try:
                session_id, token = str(credentials[0]), str(credentials[1])
            except (TypeError, IndexError, KeyError):
                session_id = token = None
        return BmcResult(
            code=code,
            message=None if message is None else str(message),
            session_id=session_id,
            token=token,
        )

    def bmc_close_session(self, session_id: str) -> Any:
        return self._result('close_session', session_id)

    def bmc_reset_root_password(self) -> Any:
        return self._result('reset_root_password')

    def bmc_reset(self, graceful: bool) -> Any:
        return self._result('request_bmc_reset', graceful)

    def bmc_update_firmware(self, image_path: str) -> Any:
        """`(code, (message, list))`; the list is the components it touched."""
        from .facade import BmcResult

        code, payload = self._bmc_call('update_firmware', image_path)
        message = payload
        try:
            message, _components = payload
        except (TypeError, ValueError):
            pass
        return BmcResult(code=code, message=None if message is None else str(message))

    def bmc_trigger_debug_log_dump(self) -> Any:
        """`(code, (task_id, message))` -- task id first, unlike every other."""
        from .facade import BmcResult

        code, payload = self._bmc_call('trigger_bmc_debug_log_dump')
        task_id, message = None, None
        try:
            task_id, message = payload
        except (TypeError, ValueError):
            message = None if payload is None else str(payload)
        return BmcResult(
            code=code,
            message=None if message is None else str(message),
            task_id=None if task_id is None else str(task_id),
        )

    def bmc_get_debug_log_dump(self, task_id: str, filename: str, path: str) -> Any:
        return self._result('get_bmc_debug_log_dump', task_id, filename, path)

    # -- from a name to a key -----------------------------------------------
    #
    # Each resolves a name the way the Python consumer it replaces does, so a
    # caller that starts from a name reaches the device that consumer would
    # have.  The key is what the walk would have published for that device:
    # the position in the list the walk iterates.

    def get_module_key(self, name: str) -> Any:
        """chassisd's resolution of a CONFIG_DB module key (chassisd:323).

        `get_module_index()` answers the position in `get_all_modules()`, and
        a negative one -- the base class's and the vendors' "no such module"
        -- is None.  An exception is the vendor's, and crosses as one.
        """
        fn = getattr(self._chassis, 'get_module_index', None)
        if fn is None:
            raise NotImplementedError('ChassisBase.get_module_index is not implemented')
        index = fn(name)
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            return None
        return 'modules[%d]' % index

    def get_component_key(self, name: str) -> Any:
        """fwutil's `chassis component <name>`: by name among the chassis's."""
        at = _the_one(_named(self._chassis.get_all_components(), name),
                      'chassis component %r' % name)
        return None if at is None else 'components[%d]' % at

    def get_module_component_key(self, module: str, name: str) -> Any:
        """fwutil's `module <module> component <name>`.

        The module by its own name, and only on a modular chassis, as
        `fwutil install module` refuses anything else; then the component by
        name among that module's.
        """
        if not self._chassis.is_modular_chassis():
            return None
        modules = list(self._chassis.get_all_modules() or ())
        at = _the_one(_named(modules, module), 'module %r' % module)
        if at is None:
            return None
        comp = _the_one(_named(modules[at].get_all_components(), name),
                        'component %r on module %r' % (name, module))
        return None if comp is None else 'modules[%d]/components[%d]' % (at, comp)


def _named(devices: Any, name: str) -> list[int]:
    """The positions of the devices whose `get_name()` is `name`."""
    return [i for i, dev in enumerate(devices or ()) if dev.get_name() == name]


def _the_one(positions: list[int], what: str) -> Any:
    """The only match, None for none, and an error for more than one.

    fwutil keeps the last of several matches, because it builds a dict; here
    two devices answering to one name is refused, since acting on either
    without saying so is the defect a key exists to remove.
    """
    if len(positions) > 1:
        raise ValueError('%s is ambiguous: %d devices answer to it' % (what, len(positions)))
    return positions[0] if positions else None
