"""
    leakage_sensor_test_base.py

    Abstract base class for implementing a platform-specific leak test, used
    to inject a simulated leak into the leak detection path in SONiC
"""

from .liquid_cooling_base import LeakSeverity


class LeakageSensorTestBase:
    """
    Platform-specific leak test interface.

    Provides a vendor-independent way to inject a simulated leak so that the
    leak reporting path can be validated without wetting hardware. Injection is
    non-destructive: a leak reported through this interface is flagged as a
    test leak and must not cause any mitigation action to be taken.

    Reached through LiquidCoolingBase.get_leak_sensor_test().

    Injected state must live wherever the platform's LeakageSensorBase reads
    its leak status from, such as a hardware test bit, the BMC or sysfs, so
    that is_leak(), get_leak_severity() and is_test_leak() on the sensor all
    report the injection and a separate process polling the platform observes
    it. Withdrawing an injection must return the sensor to reporting its
    hardware state rather than restoring a snapshot taken at injection time,
    since a genuine leak may have started in the meantime.

    Sensor names passed to this interface must be unique on the platform.
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

    def set_test_leak(self, sensor_name: str, enable: bool, *,
                      severity: LeakSeverity = LeakSeverity.MINOR) -> bool:
        """
        Injects or withdraws a test leak on the given sensor.

        Idempotent: the return value reports whether the sensor is left in the
        requested state, not whether a change was made. Injecting on a sensor
        that already carries an injection, or withdrawing from one that is
        already clear, returns True.

        Args:
            sensor_name: name of the leak sensor to inject the leak on
            enable: True to inject the test leak, False to withdraw it
            severity: severity the injected leak is reported with. Keyword
                only, so that a platform override declaring it positionally
                cannot change the calling convention, and defaulting to MINOR
                so an injection that omits it does not select the severity
                mapped to the most destructive mitigation action. Ignored
                when enable is False.

        Returns:
            bool: True if the sensor is left in the requested test leak state,
            False otherwise. An unknown sensor_name must return False rather
            than raise.
        """
        raise NotImplementedError

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
        raise NotImplementedError

    def clear_test_leaks(self) -> bool:
        """
        Withdraws every injected test leak on the platform.

        Returns:
            bool: True if no test leak remains injected on any sensor,
            including when none was injected to begin with, False otherwise
        """
        raise NotImplementedError
