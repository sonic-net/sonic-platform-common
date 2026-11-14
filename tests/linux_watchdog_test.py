"""Exercise Linux watchdog semantics using fake sysfs and ioctl; no hardware I/O."""

import array
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sonic_platform_base import linux_watchdog


class LinuxWatchdogTest(unittest.TestCase):
    module = linux_watchdog

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.device = self.root / "watchdog0"
        self.device.mkdir()
        self.state("inactive")
        (self.device / "identity").write_text("iTCO_wdt\n")
        self.path = patch.object(self.module.LinuxWatchdog, "SYSFS", self.root)
        self.path.start()
        self.addCleanup(self.path.stop)
        self.open = self.mock(self.module.os, "open", return_value=123)
        self.close = self.mock(self.module.os, "close")
        self.ioctl = self.mock(self.module.fcntl, "ioctl", side_effect=self.kernel)

    def mock(self, target, name, **kwargs):
        replacement = patch.object(target, name, **kwargs)
        self.addCleanup(replacement.stop)
        return replacement.start()

    def state(self, value):
        (self.device / "state").write_text(value)

    def kernel(self, fd, operation, value, mutate=None):
        self.assertEqual(fd, 123)
        if operation == self.module.LinuxWatchdog.WDIOC_SETTIMEOUT:
            self.assertIsInstance(value, array.array)
            self.assertEqual(value.itemsize, 4)
            value[0] = ((value[0] + 9) // 10) * 10
            self.state("active")
        elif operation == self.module.LinuxWatchdog.WDIOC_SETOPTIONS:
            self.assertEqual(value.itemsize, 4)
            self.assertEqual(value[0], 1)
            self.state("inactive")

    def test_real_kernel_state_and_optional_timeleft(self):
        self.state("active")
        (self.device / "timeleft").write_text("27\n")
        device = self.module.LinuxWatchdog()
        self.assertTrue(device.is_armed())
        self.assertEqual(device.get_remaining_time(), 27)
        (self.device / "timeleft").unlink()
        self.assertEqual(device.get_remaining_time(), -1)
        self.open.assert_not_called()

    def test_arm_uses_actual_timeout_and_disarm_is_idempotent(self):
        device = self.module.LinuxWatchdog()
        self.assertEqual(device.arm(61), 70)
        self.assertTrue(device.is_armed())
        self.assertTrue(device.disarm())
        self.close.assert_called_once_with(123)
        count = self.ioctl.call_count
        self.assertTrue(device.disarm())
        self.assertEqual(self.ioctl.call_count, count)

    def test_invalid_or_unavailable_device_never_reports_success(self):
        device = self.module.LinuxWatchdog()
        for value in (0, -1, True, 1.5, "30", 2**31):
            self.assertEqual(device.arm(value), -1)
        self.open.assert_not_called()
        self.open.side_effect = PermissionError("denied")
        self.assertEqual(device.arm(30), -1)
        self.state("active")
        self.assertFalse(device.disarm())
        (self.device / "identity").write_text("unrelated_driver")
        with self.assertRaises(RuntimeError):
            self.module.LinuxWatchdog()

    def test_ioctl_failure_or_short_timeout_disables_opened_device(self):
        for result in (OSError("unsupported"), 10):
            self.state("inactive")
            device = self.module.LinuxWatchdog()

            def ioctl(fd, op, values, mutate=None):
                if op == device.WDIOC_SETTIMEOUT:
                    self.state("active")
                    if isinstance(result, OSError):
                        raise result
                    values[0] = result
                else:
                    return self.kernel(fd, op, values, mutate)

            self.ioctl.side_effect = ioctl
            self.assertEqual(device.arm(60), -1)
            self.assertFalse(device.is_armed())
            self.assertIsNone(device._fd)

    def test_nowayout_and_unknown_state_do_not_fake_success(self):
        self.state("active")
        device = self.module.LinuxWatchdog()
        self.ioctl.side_effect = OSError("nowayout")
        self.assertFalse(device.disarm())
        self.state("unknown")
        with self.assertRaises(RuntimeError):
            device.is_armed()
