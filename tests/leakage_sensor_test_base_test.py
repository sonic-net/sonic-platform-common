'''
Test leakage_sensor_test_base module
'''
import pytest
from sonic_platform_base.leakage_sensor_test_base import LeakageSensorTestBase
from sonic_platform_base.liquid_cooling_base import LeakageSensorBase
from sonic_platform_base.liquid_cooling_base import LeakSeverity
from sonic_platform_base.liquid_cooling_base import LiquidCoolingBase


class PlatformSensor(LeakageSensorBase):
    '''
    Sensor whose leak state is computed from a "hardware" reading combined
    with any injection, standing in for a platform that reads a test bit
    alongside the physical sensor.

    Keeping the injected state on the sensor, next to the hardware state it
    overlays, means withdrawal re-derives the reported state from hardware
    rather than restoring a snapshot taken at injection time — so a genuine
    leak that arrives while an injection is armed survives the withdrawal.
    '''

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.hw_leak = False
        self.hw_severity = LeakSeverity.CRITICAL
        self.test_severity = None

    def refresh(self):
        '''
        Recomputes the reported state from the hardware reading and the
        injection, as a platform's is_leak() would on each poll.
        '''
        if self.test_leak:
            self.leaking = True
            self.leak_severity = self.test_severity
        else:
            self.leaking = self.hw_leak
            self.leak_severity = self.hw_severity

    def is_leak(self):
        self.refresh()
        return self.leaking


class PlatformLeakTest(LeakageSensorTestBase):
    '''
    Reference leak test implementation.

    Injection state lives on the sensor object itself, and withdrawal lets the
    sensor re-derive its state from hardware — so sensors that never carried
    an injection are untouched, and a genuine leak present before, during or
    after the test keeps its severity.
    '''

    def __init__(self, sensors):
        self._sensors = {s.get_name(): s for s in sensors}

    def set_test_leak(self, sensor_name, enable, *,
                      severity=LeakSeverity.MINOR):
        sensor = self._sensors.get(sensor_name)
        if sensor is None:
            return False
        sensor.test_leak = enable
        sensor.test_severity = severity if enable else None
        sensor.refresh()
        return True

    def is_test_leak_enabled(self, sensor_name):
        sensor = self._sensors.get(sensor_name)
        return bool(sensor and sensor.test_leak)

    def clear_test_leaks(self):
        # A list comprehension rather than a generator, so a failed withdrawal
        # does not stop the remaining sensors from being attempted
        return all([self.set_test_leak(name, False)
                    for name, sensor in self._sensors.items()
                    if sensor.test_leak])


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
    def test_injection_methods_not_implemented():
        '''
        Test the injection methods raise NotImplementedError until the
        platform provides them
        '''
        leak_test = LeakageSensorTestBase()

        with pytest.raises(NotImplementedError):
            leak_test.set_test_leak("sensor1", True)
        with pytest.raises(NotImplementedError):
            leak_test.is_test_leak_enabled("sensor1")
        with pytest.raises(NotImplementedError):
            leak_test.clear_test_leaks()

    @staticmethod
    def test_severity_is_keyword_only():
        '''
        Test severity cannot be passed positionally, so a platform override
        cannot change the calling convention for callers that omit it
        '''
        with pytest.raises(TypeError):
            LeakageSensorTestBase().set_test_leak("sensor1", True,
                                                  LeakSeverity.CRITICAL)

        sensors = [PlatformSensor("sensor1")]
        leak_test = PlatformLiquidCooling(sensors).get_leak_sensor_test()

        with pytest.raises(TypeError):
            leak_test.set_test_leak("sensor1", True, LeakSeverity.CRITICAL)

    @staticmethod
    def test_default_severity_is_minor():
        '''
        Test an injection that omits severity reports MINOR, so the least
        thought path does not select the severity mapped to the most
        destructive mitigation action
        '''
        sensors = [PlatformSensor("sensor1")]
        leak_test = PlatformLiquidCooling(sensors).get_leak_sensor_test()

        assert leak_test.set_test_leak("sensor1", True) == True
        assert sensors[0].get_leak_severity() is LeakSeverity.MINOR

    @staticmethod
    def test_set_test_leak_is_idempotent():
        '''
        Test the return value reports the resulting state rather than whether
        a change was made: a repeated injection or withdrawal returns True
        '''
        sensors = [PlatformSensor("sensor1")]
        leak_test = PlatformLiquidCooling(sensors).get_leak_sensor_test()

        assert leak_test.set_test_leak("sensor1", True) == True
        assert leak_test.set_test_leak("sensor1", True) == True
        assert leak_test.set_test_leak("sensor1", False) == True
        assert leak_test.set_test_leak("sensor1", False) == True
        assert leak_test.clear_test_leaks() == True

    @staticmethod
    def test_unknown_sensor_returns_false():
        '''
        Test an unknown sensor name is rejected rather than raising
        '''
        sensors = [PlatformSensor("sensor1")]
        leak_test = PlatformLiquidCooling(sensors).get_leak_sensor_test()

        assert leak_test.set_test_leak("no_such_sensor", True) == False
        assert leak_test.is_test_leak_enabled("no_such_sensor") == False

    @staticmethod
    def test_is_leak_test_supported_default():
        '''
        Test is_leak_test_supported defaults to True: reaching an instance
        through get_leak_sensor_test() already implies support, and the
        unsupported signal is get_leak_sensor_test() returning None
        '''
        assert LeakageSensorTestBase().is_leak_test_supported() == True

    @staticmethod
    def test_get_leak_sensor_test_default_none():
        '''
        Test LiquidCoolingBase reports no leak test interface by default, so
        platforms without injection support are unaffected
        '''
        liquid_cooling = LiquidCoolingBase(leakage_sensors_list=[])
        assert liquid_cooling.get_leak_sensor_test() is None

    @staticmethod
    def test_injected_leak_is_flagged():
        '''
        Test an injected leak is published like any other leak and is
        additionally flagged as a test leak, on a healthy sensor
        '''
        sensors = [PlatformSensor("sensor1"), PlatformSensor("sensor2")]
        liquid_cooling = PlatformLiquidCooling(sensors)
        leak_test = liquid_cooling.get_leak_sensor_test()

        assert leak_test.set_test_leak("sensor1", True,
                                       severity=LeakSeverity.CRITICAL) == True
        assert leak_test.is_test_leak_enabled("sensor1") == True

        leaking = liquid_cooling.get_leak_sensor_status()
        assert len(leaking) == 1
        assert leaking[0].get_name() == "sensor1"
        assert leaking[0].is_test_leak() == True
        assert leaking[0].get_leak_severity() is LeakSeverity.CRITICAL
        assert leaking[0].is_leak_sensor_ok() == True

        assert leak_test.clear_test_leaks() == True
        assert liquid_cooling.get_leak_sensor_status() == []
        assert sensors[0].is_test_leak() == False

    @staticmethod
    def test_clear_test_leaks_preserves_real_leaks():
        '''
        Test withdrawing test leaks only touches sensors that carry an
        injection: a genuine leak on another sensor must survive
        clear_test_leaks() with its severity intact
        '''
        sensors = [PlatformSensor("sensor1"), PlatformSensor("sensor2")]
        liquid_cooling = PlatformLiquidCooling(sensors)
        leak_test = liquid_cooling.get_leak_sensor_test()

        # A genuine leak is present on sensor2
        sensors[1].hw_leak = True
        sensors[1].hw_severity = LeakSeverity.CRITICAL

        leak_test.set_test_leak("sensor1", True, severity=LeakSeverity.MINOR)
        assert leak_test.clear_test_leaks() == True

        assert sensors[1].is_leak() == True
        assert sensors[1].get_leak_severity() is LeakSeverity.CRITICAL
        assert sensors[1].is_test_leak() == False
        assert sensors[0].is_leak() == False
        assert leak_test.is_test_leak_enabled("sensor1") == False

    @staticmethod
    def test_withdrawal_rereads_hardware():
        '''
        Test withdrawal returns the sensor to reporting hardware state rather
        than restoring a snapshot taken at injection time: a genuine leak that
        arrives while the injection is armed must survive the withdrawal
        '''
        sensors = [PlatformSensor("sensor1")]
        liquid_cooling = PlatformLiquidCooling(sensors)
        leak_test = liquid_cooling.get_leak_sensor_test()

        leak_test.set_test_leak("sensor1", True, severity=LeakSeverity.MINOR)

        # A genuine leak arrives while the injection is armed
        sensors[0].hw_leak = True
        sensors[0].hw_severity = LeakSeverity.CRITICAL

        assert leak_test.clear_test_leaks() == True
        assert sensors[0].is_leak() == True
        assert sensors[0].get_leak_severity() is LeakSeverity.CRITICAL
        assert sensors[0].is_test_leak() == False
