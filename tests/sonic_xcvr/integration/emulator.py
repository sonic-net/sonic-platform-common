"""
emulator.py

Test harness for driving the `xcvr-emu <https://github.com/az-pz/xcvr-emu>`_
CMIS transceiver emulator from the integration tests.

The harness has three pieces:

* :class:`XcvrEmuDaemon` runs ``xcvr-emud`` as a plain OS process (no container)
  on an ephemeral port and tears it down afterwards.
* :class:`XcvrEmuClient` is a small synchronous gRPC client for the emulator's
  ``SfpEmulatorService``, which addresses the EEPROM as ``(bank, page, offset)``.
* :class:`EmulatedSfp` is an :class:`SfpOptoeBase` whose ``read_eeprom`` /
  ``write_eeprom`` are served by the emulator. It performs the same linear
  address translation the kernel ``optoe`` driver does, so the production
  ``XcvrApiFactory`` / ``CmisApi`` stack runs unmodified on top of it.
"""

import os
import socket
import subprocess
import sys
import time

from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.pages.consts import (
    CMIS_ARCH_PAGES,
    CMIS_EEPROM_PAGE_SIZE,
)
from sonic_platform_base.sonic_xcvr.sfp_optoe_base import SfpOptoeBase

try:
    import grpc
    from xcvr_emu.proto import emulator_pb2 as pb2
    from xcvr_emu.proto import emulator_pb2_grpc as pb2_grpc

    XCVR_EMU_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - depends on the environment
    grpc = None
    pb2 = None
    pb2_grpc = None
    XCVR_EMU_IMPORT_ERROR = exc

#: Path to the transceiver definitions handed to ``xcvr-emud``.
EMU_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "xcvr_emu_config.yaml")

#: Index of the transceiver that is plugged in when the emulator starts.
PRESENT_XCVR_INDEX = 0

#: Index of the transceiver that starts unplugged.
ABSENT_XCVR_INDEX = 1

#: Bytes per bank in the linear (optoe-style) EEPROM address space: 32 KiB.
BYTES_PER_BANK = CMIS_ARCH_PAGES * CMIS_EEPROM_PAGE_SIZE


def is_available():
    """Whether the xcvr-emu package is importable in the running interpreter.

    Returns:
        bool: True if the emulator can be started, False otherwise.
    """
    return XCVR_EMU_IMPORT_ERROR is None


def linear_to_page_address(offset):
    """Translate a linear EEPROM offset into a CMIS ``(bank, page, offset)`` triple.

    This is the inverse of
    :meth:`sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.pages.page.CmisPage.linear_offset`,
    which is the addressing scheme the kernel ``optoe`` driver exposes through
    its ``eeprom`` sysfs file: lower memory occupies bytes 0-127, every
    subsequent 128-byte slot is one page's upper memory, and each bank is a full
    256-page (32 KiB) block.

    Args:
        offset: Integer, a linear offset into the optoe EEPROM address space.

    Returns:
        Tuple of (bank, page, page_offset), where page_offset is the offset
        within the 256-byte CMIS page address space.
    """
    if offset < CMIS_EEPROM_PAGE_SIZE:
        return 0, 0, offset
    page_index = offset // CMIS_EEPROM_PAGE_SIZE - 1
    page_offset = CMIS_EEPROM_PAGE_SIZE + offset % CMIS_EEPROM_PAGE_SIZE
    return page_index // CMIS_ARCH_PAGES, page_index % CMIS_ARCH_PAGES, page_offset


def _pick_free_port():
    """Reserve an ephemeral TCP port and return it.

    Returns:
        int: A port number that was free at the time of the call.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class XcvrEmuDaemon(object):
    """Runs ``xcvr-emud`` as a child process for the lifetime of a test.

    The daemon is launched with the interpreter running the tests, so it always
    picks up the same virtualenv, and it is bound to loopback on an ephemeral
    port so concurrent test sessions do not collide.

    Args:
        config: String, path to the YAML transceiver configuration.
        port: Integer, TCP port to listen on. A free port is chosen if omitted.
        startup_timeout: Float, seconds to wait for the daemon to accept
                         connections before giving up.
    """

    def __init__(self, config=EMU_CONFIG_PATH, port=None, startup_timeout=30.0):
        self.config = config
        self.port = port
        self.startup_timeout = startup_timeout
        self._process = None

    @property
    def target(self):
        """gRPC target string for the running daemon.

        Returns:
            string: "127.0.0.1:<port>"
        """
        return "127.0.0.1:%d" % self.port

    def start(self):
        """Start the daemon and block until it accepts connections.

        Returns:
            XcvrEmuDaemon: self, to allow chaining.

        Raises:
            RuntimeError: if the daemon exits or does not become reachable
                          within `startup_timeout` seconds.
        """
        if self._process is not None:
            return self

        if self.port is None:
            self.port = _pick_free_port()

        self._process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "xcvr_emu.xcvr_emud",
                "--port",
                str(self.port),
                "--config",
                self.config,
            ],
            env=self._child_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        try:
            self._wait_until_listening()
        except Exception:
            self.stop()
            raise
        return self

    @staticmethod
    def _child_env():
        """Environment for the daemon process.

        pytest-cov installs a ``.pth`` hook that starts coverage in any child
        process that inherits ``COV_CORE_*``. The emulator is a test fixture
        rather than code under test, so those variables are dropped: this keeps
        its startup fast and keeps its modules out of the coverage report.

        Returns:
            dict: a copy of the current environment without the pytest-cov
            subprocess hooks.
        """
        return {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("COV_CORE")
        }

    def _wait_until_listening(self):
        """Poll the daemon's port until the TCP listener is up.

        The port is probed with a plain socket rather than a gRPC call because a
        gRPC channel created against a closed port enters connection backoff and
        would add several seconds to every test.

        Raises:
            RuntimeError: if the process died or the deadline expired.
        """
        deadline = time.time() + self.startup_timeout
        while time.time() < deadline:
            if self._process.poll() is not None:
                raise RuntimeError(
                    "xcvr-emud exited with code %d during startup:\n%s"
                    % (self._process.returncode, self._drain_output())
                )
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.02)
        raise RuntimeError(
            "xcvr-emud did not start listening on port %d within %.1fs"
            % (self.port, self.startup_timeout)
        )

    def _drain_output(self):
        """Read whatever the daemon wrote to stdout/stderr.

        Returns:
            string: the captured output, or '' if nothing is available.
        """
        if self._process is None or self._process.stdout is None:
            return ""
        try:
            return self._process.stdout.read().decode(errors="replace")
        except (OSError, ValueError):
            return ""

    def stop(self):
        """Terminate the daemon, escalating to SIGKILL if it ignores SIGTERM."""
        if self._process is None:
            return
        process = self._process
        self._process = None
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        if process.stdout is not None:
            process.stdout.close()

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()


class XcvrEmuClient(object):
    """Synchronous gRPC client for the emulator's ``SfpEmulatorService``.

    Args:
        target: String, the "host:port" the daemon is listening on.
    """

    def __init__(self, target):
        self.channel = grpc.insecure_channel(target)
        self.stub = pb2_grpc.SfpEmulatorServiceStub(self.channel)

    def close(self):
        """Close the underlying gRPC channel."""
        self.channel.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def list(self):
        """List every transceiver known to the emulator.

        Returns:
            list: GetInfoResponse messages, one per transceiver.
        """
        return list(self.stub.List(pb2.ListRequest()).infos)

    def create(self, index):
        """Create a new transceiver instance.

        Args:
            index: Integer, the transceiver index to create.
        """
        self.stub.Create(pb2.CreateRequest(index=index))

    def delete(self, index):
        """Delete a transceiver instance.

        Args:
            index: Integer, the transceiver index to delete.
        """
        self.stub.Delete(pb2.DeleteRequest(index=index))

    def get_info(self, index):
        """Retrieve emulator-side state for a transceiver.

        Args:
            index: Integer, the transceiver index.

        Returns:
            GetInfoResponse: presence flag and data path state machines.
        """
        return self.stub.GetInfo(pb2.GetInfoRequest(index=index))

    def set_present(self, index, present):
        """Plug a transceiver in or out.

        Args:
            index: Integer, the transceiver index.
            present: Boolean, True to plug in, False to plug out.
        """
        self.stub.UpdateInfo(pb2.UpdateInfoRequest(index=index, present=present))

    def read(self, index, page, offset, length, bank=0, force=False):
        """Read raw bytes using CMIS page addressing.

        Args:
            index: Integer, the transceiver index.
            page: Integer, the CMIS page number.
            offset: Integer, offset within the 256-byte page address space.
            length: Integer, number of bytes to read.
            bank: Integer, the bank number for banked pages.
            force: Boolean, read even when the module is not present.

        Returns:
            bytes: the bytes read.
        """
        return self.stub.Read(
            pb2.ReadRequest(
                index=index,
                bank=bank,
                page=page,
                offset=offset,
                length=length,
                force=force,
            )
        ).data

    def write(self, index, page, offset, data, bank=0):
        """Write raw bytes using CMIS page addressing.

        Args:
            index: Integer, the transceiver index.
            page: Integer, the CMIS page number.
            offset: Integer, offset within the 256-byte page address space.
            data: Bytes-like, the payload to write.
            bank: Integer, the bank number for banked pages.
        """
        data = bytes(data)
        self.stub.Write(
            pb2.WriteRequest(
                index=index,
                bank=bank,
                page=page,
                offset=offset,
                length=len(data),
                data=data,
            )
        )


class EmulatedSfp(SfpOptoeBase):
    """An :class:`SfpOptoeBase` whose EEPROM lives in ``xcvr-emud``.

    A vendor platform plugin only has to supply ``read_eeprom`` /
    ``write_eeprom``; everything above that (``XcvrApiFactory``, ``CmisApi``,
    the memory maps) is shared code. Wiring those two methods to the emulator
    therefore exercises the production stack end to end.

    Args:
        client: XcvrEmuClient, connected to a running daemon.
        index: Integer, the emulated transceiver index.
        bank: Integer, the bank this SFP instance addresses.
    """

    def __init__(self, client, index=PRESENT_XCVR_INDEX, bank=0):
        super(EmulatedSfp, self).__init__(bank=bank)
        self.client = client
        self.index = index

    def get_name(self):
        """Name of the emulated port.

        Returns:
            string: a synthetic port name.
        """
        return "emu-xcvr%d" % self.index

    def get_eeprom_path(self):
        """Path of the backing sysfs EEPROM file.

        The emulator is reached over gRPC, so there is no sysfs file. The path
        is only consulted by the optoe helpers (``set_optoe_write_max`` and
        friends), which tolerate it being absent.

        Returns:
            string: a path that intentionally does not exist.
        """
        return "/nonexistent/xcvr-emu/eeprom"

    def get_presence(self):
        """Whether the emulated module is plugged in.

        Returns:
            bool: True if present, False otherwise.
        """
        return self.client.get_info(self.index).present

    def read_eeprom(self, offset, num_bytes):
        """Read from the linear EEPROM address space.

        Reads that span a page boundary are split into per-page gRPC requests,
        mirroring what the optoe driver does on real hardware.

        Args:
            offset: Integer, linear offset to start reading from.
            num_bytes: Integer, number of bytes to read.

        Returns:
            bytearray: the bytes read, or None on failure.
        """
        data = bytearray()
        try:
            while num_bytes > 0:
                bank, page, page_offset = linear_to_page_address(offset)
                chunk = min(num_bytes, CMIS_EEPROM_PAGE_SIZE - offset % CMIS_EEPROM_PAGE_SIZE)
                data += self.client.read(self.index, page, page_offset, chunk, bank=bank)
                offset += chunk
                num_bytes -= chunk
        except grpc.RpcError:
            return None
        return data

    def write_eeprom(self, offset, num_bytes, write_buffer):
        """Write to the linear EEPROM address space.

        Args:
            offset: Integer, linear offset to start writing at.
            num_bytes: Integer, number of bytes to write.
            write_buffer: Bytes-like, the payload; only the first num_bytes are used.

        Returns:
            bool: True if the write succeeded, False otherwise.
        """
        write_buffer = bytes(write_buffer[:num_bytes])
        position = 0
        try:
            while num_bytes > 0:
                bank, page, page_offset = linear_to_page_address(offset)
                chunk = min(num_bytes, CMIS_EEPROM_PAGE_SIZE - offset % CMIS_EEPROM_PAGE_SIZE)
                self.client.write(
                    self.index,
                    page,
                    page_offset,
                    write_buffer[position:position + chunk],
                    bank=bank,
                )
                offset += chunk
                position += chunk
                num_bytes -= chunk
        except grpc.RpcError:
            return False
        return True


def wait_until(predicate, timeout=5.0, interval=0.05):
    """Poll `predicate` until it returns a truthy value.

    The emulator applies EEPROM writes from an asyncio task, so state changes
    are observed asynchronously by the API under test.

    Args:
        predicate: Callable taking no arguments.
        timeout: Float, seconds to keep polling.
        interval: Float, seconds to sleep between polls.

    Returns:
        The final value returned by `predicate`; falsy if it never succeeded.
    """
    deadline = time.time() + timeout
    result = predicate()
    while not result and time.time() < deadline:
        time.sleep(interval)
        result = predicate()
    return result
