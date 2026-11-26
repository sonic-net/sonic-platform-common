"""Linux watchdog API without arming hardware during discovery or queries.

Discovery and status reads never open /dev/watchdog: opening it arms hardware.
Only explicit arm/disarm operations take ownership of the character device.
"""

import array
import fcntl
import os
from pathlib import Path

from sonic_platform_base.watchdog_base import WatchdogBase


class LinuxWatchdog(WatchdogBase):
    """Use the Linux watchdog userspace API for a platform-selected device.

    ``identity`` selects a kernel driver identity and ``device`` selects an
    exact sysfs name, for example ``watchdog2``. Platforms may specify both.
    With neither selector, discovery accepts iTCO/wdat drivers only. An
    explicit identity permits other drivers implementing the same Linux API.

    Missing or ambiguous hardware raises RuntimeError. Platform get_watchdog()
    adapters must catch discovery failures and return None for no watchdog.
    Discovery never opens the character device to probe ioctl capabilities.
    """

    SYSFS = Path("/sys/class/watchdog")
    IDENTITIES = frozenset(("iTCO_wdt", "wdat_wdt"))
    # Linux UAPI <linux/watchdog.h>; requests do not depend on driver identity.
    # Drivers may reject optional operations, which arm/disarm report as failure.
    WDIOC_SETOPTIONS = 0x80045704
    WDIOC_KEEPALIVE = 0x80045705
    WDIOC_SETTIMEOUT = 0xC0045706
    WDIOS_DISABLECARD = 1

    def __init__(self, identity=None, device=None):
        self._fd = None
        candidates = []
        identities = self.IDENTITIES if identity is None else (identity,)
        for entry in self.SYSFS.glob("watchdog[0-9]*"):
            if not entry.name[len("watchdog"):].isdigit():
                continue
            if device is not None and entry.name != device:
                continue
            try:
                driver = (entry / "identity").read_text().strip()
            except OSError:
                continue
            if driver in identities:
                candidates.append(entry)
        if not candidates:
            raise RuntimeError("No supported Linux hardware watchdog found")
        if len(candidates) != 1:
            raise RuntimeError("Multiple Linux hardware watchdogs found; "
                               "platform must select an identity or device")
        self._device = candidates[0]
        self._path = "/dev/" + self._device.name

    def _open(self):
        if self._fd is None:
            self._fd = os.open(self._path, os.O_RDWR | os.O_CLOEXEC)
        return self._fd

    def _close(self):
        if self._fd is not None:
            fd, self._fd = self._fd, None
            os.close(fd)

    def _read_armed_state(self):
        # Kernel state survives short-lived watchdogutil CLI processes.
        # A missing state must not be treated as safely disarmed.
        state = (self._device / "state").read_text().strip()
        if state not in ("active", "inactive"):
            raise RuntimeError("Unknown hardware watchdog state: " + state)
        return state == "active"

    def is_armed(self):
        """Return a boolean without opening or changing the watchdog device."""
        try:
            return self._read_armed_state()
        except (OSError, RuntimeError):
            return False

    def arm(self, seconds):
        if type(seconds) is not int or not 0 < seconds <= 0x7FFFFFFF:
            return -1
        try:
            fd = self._open()
            timeout = array.array("i", [seconds])
            fcntl.ioctl(fd, self.WDIOC_SETTIMEOUT, timeout, True)
            if timeout[0] < seconds:
                # SONiC promises the next greater supported timeout, never less.
                raise ValueError("Driver returned a shorter watchdog timeout")
            fcntl.ioctl(fd, self.WDIOC_KEEPALIVE, 0)
            return timeout[0]
        except (OSError, ValueError):
            # Opening may already have armed hardware. Attempt to disable it
            # before returning an error; do not falsely report successful arm.
            if self._fd is not None:
                try:
                    self.disarm()
                except (OSError, RuntimeError):
                    pass
            return -1

    def disarm(self):
        try:
            if self._fd is None and not self._read_armed_state():
                return True
            options = array.array("i", [self.WDIOS_DISABLECARD])
            fcntl.ioctl(self._open(), self.WDIOC_SETOPTIONS, options, True)
            # Do not report success when nowayout or a driver prevents disable.
            if self._read_armed_state():
                return False
            self._close()
            return True
        except (OSError, RuntimeError):
            return False

    def get_remaining_time(self):
        try:
            if not self._read_armed_state():
                return -1
            # timeleft is optional. Reading sysfs avoids arming it for a query.
            return int((self._device / "timeleft").read_text().strip())
        except (OSError, ValueError, RuntimeError):
            return -1

    def __del__(self):
        # Deliberately no magic-close 'V': an explicit arm must survive the CLI
        # process exiting. An explicit disarm uses SETOPTIONS above.
        try:
            self._close()
        except OSError:
            pass
