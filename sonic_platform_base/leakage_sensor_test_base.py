"""
    leakage_sensor_test_base.py

    Abstract base class for implementing a platform-specific leak test, used
    to inject a simulated leak into the leak detection path in SONiC
"""

from abc import ABC, abstractmethod

from .liquid_cooling_base import LeakSeverity


class LeakageSensorTestBase(ABC):
    """
    Platform-specific leak test interface.

    Provides a vendor-independent way to inject a simulated leak so that the
    leak reporting path can be validated without wetting hardware. Injection is
    non-destructive: a leak reported through this interface is flagged as a
    test leak and must not cause any mitigation action to be taken.

    Reached through LiquidCoolingBase.get_leak_sensor_test().
    """

    def is_leak_test_supported(self) -> bool:
        """
        Retrieves whether this platform supports leak test injection.

        The base implementation returns True: reaching an instance through
        LiquidCoolingBase.get_leak_sensor_test() already implies support, and
        a platform without support signals it by returning None from
        get_leak_sensor_test(). Platforms with conditional support (e.g.
        dependent on a BMC feature) may override.

        Returns:
            bool: True if leak test injection is supported, False otherwise
        """
        return True

    @abstractmethod
    def set_test_leak(self, sensor_name: str, enable: bool,
                      severity: LeakSeverity = LeakSeverity.CRITICAL) -> bool:
        """
        Injects or withdraws a test leak on the given sensor.

        Args:
            sensor_name: name of the leak sensor to inject the leak on
            enable: True to inject the test leak, False to withdraw it
            severity: severity the injected leak is reported with

        Returns:
            bool: True if the test leak state was applied, False otherwise.
            An unknown sensor_name must return False rather than raise.
        """
        pass

    @abstractmethod
    def is_test_leak_enabled(self, sensor_name: str) -> bool:
        """
        Retrieves whether a test leak is currently injected on the given sensor.

        Args:
            sensor_name: name of the leak sensor

        Returns:
            bool: True if a test leak is injected on the sensor, False
            otherwise. An unknown sensor_name must return False rather than
            raise.
        """
        pass

    @abstractmethod
    def clear_test_leaks(self) -> bool:
        """
        Withdraws every injected test leak on the platform.

        Returns:
            bool: True if all test leaks were withdrawn, False otherwise
        """
        pass
