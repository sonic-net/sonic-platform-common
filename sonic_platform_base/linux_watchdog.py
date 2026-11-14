"""Linux watchdog API for Edgecore platforms using iTCO/wdat watchdogs.

Discovery and status reads never open /dev/watchdog: opening it arms hardware.
Only explicit arm/disarm operations take ownership of the character device.
"""

import array
import fcntl
import os
from pathlib import Path

from sonic_platform_base.watchdog_base import WatchdogBase


class LinuxWatchdog(WatchdogBase):
    SYSFS = Path("/sys/class/watchdog")
    IDENTITIES = frozenset(("iTCO_wdt", "wdat_wdt"))
    WDIOC_SETOPTIONS = 0x80045704
    WDIOC_KEEPALIVE = 0x80045705
    WDIOC_SETTIMEOUT = 0xC0045706
    WDIOS_DISABLECARD = 1

    def __init__(self):
        self._fd = None
        for device in sorted(self.SYSFS.glob("watchdog[0-9]*")):
            try:
                identity = (device / "identity").read_text().strip()
            except OSError:
                continue
            if identity in self.IDENTITIES:
                self._device = device
                self._path = "/dev/" + device.name
                break
        else:
            raise RuntimeError("No supported Linux hardware watchdog found")

    def _open(self):
        if self._fd is None:
            self._fd = os.open(self._path, os.O_RDWR | os.O_CLOEXEC)
        return self._fd

    def _close(self):
        if self._fd is not None:
            fd, self._fd = self._fd, None
            os.close(fd)

    def is_armed(self):
        # Kernel state survives short-lived watchdogutil CLI processes.
        # A missing state must not be treated as safely disarmed.
        state = (self._device / "state").read_text().strip()
        if state not in ("active", "inactive"):
            raise RuntimeError("Unknown hardware watchdog state: " + state)
        return state == "active"

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
            if self._fd is None and not self.is_armed():
                return True
            options = array.array("i", [self.WDIOS_DISABLECARD])
            fcntl.ioctl(self._open(), self.WDIOC_SETOPTIONS, options, True)
            # Do not report success when nowayout or a driver prevents disable.
            if self.is_armed():
                return False
            self._close()
            return True
        except (OSError, RuntimeError):
            return False

    def get_remaining_time(self):
        try:
            if not self.is_armed():
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
