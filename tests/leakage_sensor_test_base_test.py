'''
Test leakage_sensor_test_base module
'''
import pytest
from sonic_platform_base.leak_test_api_base import LeakTestApiBase
from sonic_platform_base.leakage_sensor_test_base import LeakageSensorTestBase
from sonic_platform_base.liquid_cooling_base import LeakageSensorBase
from sonic_platform_base.liquid_cooling_base import LeakSeverity
from sonic_platform_base.liquid_cooling_base import LiquidCoolingBase


class PlatformLeakTest(LeakageSensorTestBase):
    '''
    Reference leak test implementation, also exercised by the conformance
    suite below.

    Injection state lives on the sensor object itself, and withdrawal
    restores the sensor state saved at injection time — so sensors that never
    carried an injection are untouched, and a genuine leak present before or
    after the test keeps its severity.
    '''

    def __init__(self, sensors):
        self._sensors = {s.get_name(): s for s in sensors}
        self._saved = {}

    def set_test_leak(self, sensor_name, enable,
                      severity=LeakSeverity.CRITICAL):
        sensor = self._sensors.get(sensor_name)
        if sensor is None:
            return False
        if enable:
            if not sensor.test_leak:
                self._saved[sensor_name] = (sensor.leaking,
                                            sensor.leak_severity)
            sensor.leaking = True
            sensor.test_leak = True
            sensor.leak_severity = severity
        elif sensor.test_leak:
            sensor.leaking, sensor.leak_severity = \
                self._saved.pop(sensor_name)
            sensor.test_leak = False
        return True

    def is_test_leak_enabled(self, sensor_name):
        sensor = self._sensors.get(sensor_name)
        return bool(sensor and sensor.test_leak)

    def clear_test_leaks(self):
        results = [self.set_test_leak(name, False)
                   for name, sensor in self._sensors.items()
                   if sensor.test_leak]
        return all(results)


class PlatformLiquidCooling(LiquidCoolingBase):
    '''
    Reference liquid cooling implementation exposing the leak test interface.
    '''

    def __init__(self, sensors):
        super().__init__(len(sensors), sensors)
        self._leak_test = PlatformLeakTest(sensors)

    def get_leak_sensor_test(self):
        return self._leak_test


class TestLeakageSensorTestBase:
    '''
    Collection of LeakageSensorTestBase test methods
    '''

    @staticmethod
    def test_not_instantiable():
        '''
        Test LeakageSensorTestBase cannot be instantiated — the injection
        methods must be provided by the platform
        '''
        with pytest.raises(TypeError):
            _ = LeakageSensorTestBase()

    @staticmethod
    def test_is_leak_test_supported_default():
        '''
        Test is_leak_test_supported defaults to True: reaching an instance
        through get_leak_sensor_test() already implies support, and the
        unsupported signal is get_leak_sensor_test() returning None
        '''
        class MinimalLeakTest(LeakageSensorTestBase):
            def set_test_leak(self, sensor_name, enable,
                              severity=LeakSeverity.CRITICAL):
                return False

            def is_test_leak_enabled(self, sensor_name):
                return False

            def clear_test_leaks(self):
                return True

        assert MinimalLeakTest().is_leak_test_supported() == True

    @staticmethod
    def test_get_leak_sensor_test_default_none():
        '''
        Test LiquidCoolingBase reports no leak test interface by default, so
        platforms without injection support are unaffected
        '''
        liquid_cooling = LiquidCoolingBase(leakage_sensors_list=[])
        assert liquid_cooling.get_leak_sensor_test() is None

    @staticmethod
    def test_clear_test_leaks_preserves_real_leaks():
        '''
        Test withdrawing test leaks only touches sensors that carry an
        injection: a genuine leak on another sensor must survive
        clear_test_leaks() with its severity intact
        '''
        sensors = [LeakageSensorBase("sensor1"), LeakageSensorBase("sensor2")]
        liquid_cooling = PlatformLiquidCooling(sensors)
        leak_test = liquid_cooling.get_leak_sensor_test()

        # A genuine leak is present on sensor2
        sensors[1].leaking = True
        sensors[1].leak_severity = LeakSeverity.CRITICAL

        leak_test.set_test_leak("sensor1", True, severity=LeakSeverity.MINOR)
        assert leak_test.clear_test_leaks() == True

        assert sensors[1].is_leak() == True
        assert sensors[1].get_leak_severity() is LeakSeverity.CRITICAL
        assert sensors[0].is_leak() == False
        assert leak_test.is_test_leak_enabled("sensor1") == False

        # A genuine leak arriving after the test must report the sensor's
        # configured severity — injection must not leave it None for the
        # sensor's lifetime
        sensors[0].leaking = True
        assert sensors[0].get_leak_severity() is LeakSeverity.CRITICAL


class TestLeakTestApiConformance(LeakTestApiBase):
    '''
    Run the reusable leak test API conformance suite against the reference
    implementation, so the suite itself is exercised in CI
    '''

    SENSOR_NAMES = ["sensor1", "sensor2"]

    def get_liquid_cooling(self):
        sensors = [LeakageSensorBase(name) for name in self.SENSOR_NAMES]
        return PlatformLiquidCooling(sensors)
