'''
Reusable conformance suite for the leak test API.

Exercises every API exposed by LeakageSensorTestBase and the leak test related
APIs on LeakageSensorBase, so a platform can validate its implementation
against the common contract instead of rewriting the same assertions.

This module ships inside the sonic_platform_base package so platform test
suites can import it from the installed wheel. It deliberately does not
import pytest: per-test setup and cleanup use the xunit-style
setup_method/teardown_method hooks, which pytest honours natively, so the
runtime package gains no test-framework dependency.

A platform test subclasses LeakTestApiBase and overrides get_liquid_cooling()
to return its own LiquidCoolingBase object, plus the sensor names the platform
exposes:

    from sonic_platform_base.leak_test_api_base import LeakTestApiBase

    class TestMyPlatformLeakTest(LeakTestApiBase):
        SENSOR_NAMES = ["leakage1", "leakage2"]

        def get_liquid_cooling(self):
            return MyPlatformLiquidCooling()

The class name deliberately avoids pytest's Test* collection pattern, so only
the platform subclasses run — never this module directly.
'''

from .leakage_sensor_test_base import LeakageSensorTestBase
from .liquid_cooling_base import LeakSeverity


class LeakTestApiBase:
    '''
    Collection of leak test API conformance checks.

    Subclasses must override get_liquid_cooling() and SENSOR_NAMES.
    '''

    # Names of the leak sensors the platform exposes, in order. Deliberately
    # None rather than an empty list, so a subclass that forgets to declare
    # its sensors fails loudly instead of passing vacuously.
    SENSOR_NAMES = None

    # A name that is guaranteed not to match any sensor on the platform.
    UNKNOWN_SENSOR_NAME = "no_such_sensor"

    def get_liquid_cooling(self):
        '''
        Returns the platform LiquidCoolingBase object to run the suite
        against. Must be overridden by the platform test. Called once per
        test by setup_method.
        '''
        raise NotImplementedError

    def setup_method(self, method):
        '''
        Builds the platform object each test runs against, failing loudly
        when the platform subclass forgets to declare its sensor names.
        '''
        assert self.SENSOR_NAMES, \
            "platform test must override SENSOR_NAMES with the leak sensor names"
        self.liquid_cooling = self.get_liquid_cooling()
        self.leak_test = self.liquid_cooling.get_leak_sensor_test()

    def teardown_method(self, method):
        '''
        Withdraws injected leaks on the same object the test ran against,
        even when an assertion failed, so a failing test cannot leave the
        platform reporting a leak.
        '''
        if self.leak_test is not None:
            self.leak_test.clear_test_leaks()

    def assert_no_leaks(self):
        '''
        Asserts no sensor reports a leak, a test leak, or an armed injection.
        '''
        assert self.liquid_cooling.get_leak_sensor_status() == []
        for sensor in self.liquid_cooling.get_all_leak_sensors():
            assert sensor.is_leak() == False
            assert sensor.is_test_leak() == False
        for name in self.SENSOR_NAMES:
            assert self.leak_test.is_test_leak_enabled(name) == False

    def test_sensor_names(self):
        '''
        Test the platform exposes the leak sensors it declares
        '''
        names = [s.get_name()
                 for s in self.liquid_cooling.get_all_leak_sensors()]
        assert names == self.SENSOR_NAMES
        assert self.liquid_cooling.get_num_leak_sensors() == \
            len(self.SENSOR_NAMES)

    def test_leak_test_interface_exposed(self):
        '''
        Test get_leak_sensor_test returns a LeakageSensorTestBase that reports
        injection support
        '''
        assert isinstance(self.leak_test, LeakageSensorTestBase)
        assert self.leak_test.is_leak_test_supported() == True

    def test_no_leak_before_injection(self):
        '''
        Test no leak or armed injection is reported until one is injected
        '''
        self.assert_no_leaks()

    def test_unknown_sensor_rejected(self):
        '''
        Test injection on an unknown sensor fails rather than raising
        '''
        assert self.leak_test.set_test_leak(
            self.UNKNOWN_SENSOR_NAME, True) == False
        assert self.leak_test.is_test_leak_enabled(
            self.UNKNOWN_SENSOR_NAME) == False

    def test_inject_every_severity(self):
        '''
        Test each severity can be injected on each sensor, is reported back
        unchanged, and is flagged as a test leak
        '''
        for name in self.SENSOR_NAMES:
            for severity in LeakSeverity:
                assert self.leak_test.set_test_leak(name, True,
                                                    severity=severity) == True
                assert self.leak_test.is_test_leak_enabled(name) == True

                leaking = self.liquid_cooling.get_leak_sensor_status()
                assert len(leaking) == 1
                assert leaking[0].get_name() == name
                assert leaking[0].is_leak() == True
                assert leaking[0].is_test_leak() == True
                assert leaking[0].get_leak_severity() is severity

                self.leak_test.clear_test_leaks()

    def test_injection_is_non_destructive(self):
        '''
        Test an injected leak leaves the sensor healthy, so it is observable
        without implying a hardware fault
        '''
        self.leak_test.set_test_leak(self.SENSOR_NAMES[0], True)

        for sensor in self.liquid_cooling.get_all_leak_sensors():
            assert sensor.is_leak_sensor_ok() == True

    def test_withdraw_single_injection(self):
        '''
        Test a single injection can be withdrawn, and withdrawing an already
        cleared sensor is not an error
        '''
        name = self.SENSOR_NAMES[0]

        self.leak_test.set_test_leak(name, True)
        assert self.leak_test.set_test_leak(name, False) == True
        self.assert_no_leaks()

        assert self.leak_test.set_test_leak(name, False) == True

    def test_clear_all_injections(self):
        '''
        Test clear_test_leaks withdraws every injected leak
        '''
        for name in self.SENSOR_NAMES:
            self.leak_test.set_test_leak(name, True)
        assert len(self.liquid_cooling.get_leak_sensor_status()) == \
            len(self.SENSOR_NAMES)

        assert self.leak_test.clear_test_leaks() == True
        self.assert_no_leaks()
