'''
Test liquid_cooling_base module
'''
import unittest
import sys
from io import StringIO
import pytest
from sonic_platform_base.liquid_cooling_base import LeakageSensorBase
from sonic_platform_base.liquid_cooling_base import LeakSensorProfileBase
from sonic_platform_base.liquid_cooling_base import LeakSeverity
from sonic_platform_base.liquid_cooling_base import LiquidCoolingBase

class TestLeakageSensorBase:
    '''
    Collection of LeakageSensorBase test methods
    '''

    @staticmethod
    def test_leakage_sensor_base_init():
        '''
        Test leakage sensor base default implementation
        '''
        leakage_sensor = LeakageSensorBase("test_sensor")

        assert leakage_sensor.get_name() == "test_sensor"
        assert leakage_sensor.get_leak_sensor_type() == None
        assert leakage_sensor.get_leak_sensor_location() == None
        assert leakage_sensor.get_leak_severity() == LeakSeverity.CRITICAL
        assert leakage_sensor.is_leak() == False

        leakage_sensor2 = LeakageSensorBase("test_sensor2", type="rope",
                                            location="drip tray",
                                            severity=LeakSeverity.MINOR)
        
        assert leakage_sensor2.get_name() == "test_sensor2"
        assert leakage_sensor2.get_leak_sensor_type() == "rope"
        assert leakage_sensor2.get_leak_sensor_location() == "drip tray"
        assert leakage_sensor2.get_leak_severity() == LeakSeverity.MINOR
        assert leakage_sensor2.is_leak() == False

    @staticmethod
    def test_severity_constants():
        '''
        Test LEAK_SEVERITY_CRITICAL and LEAK_SEVERITY_MINOR are LeakSeverity enum members,
        and that the LeakSeverity enum has the expected string values.
        '''
        assert LeakSeverity.CRITICAL.value == "CRITICAL"
        assert LeakSeverity.MINOR.value == "MINOR"
        assert LeakageSensorBase.LEAK_SEVERITY_CRITICAL is LeakSeverity.CRITICAL
        assert LeakageSensorBase.LEAK_SEVERITY_MINOR is LeakSeverity.MINOR

    @staticmethod
    def test_is_leak_sensor_ok_default():
        '''
        Test is_leak_sensor_ok default value is True
        '''
        sensor = LeakageSensorBase("sensor1")
        assert sensor.is_leak_sensor_ok() == True

    @staticmethod
    def test_is_leak_sensor_ok_faulty():
        '''
        Test is_leak_sensor_ok returns False when sensor is faulty
        '''
        sensor = LeakageSensorBase("sensor1")
        sensor.leak_sensor_ok = False
        assert sensor.is_leak_sensor_ok() == False

    @staticmethod
    def test_get_leak_sensor_type_default():
        '''
        Test get_leak_sensor_type default value is None
        '''
        sensor = LeakageSensorBase("sensor1")
        assert sensor.get_leak_sensor_type() is None

    @staticmethod
    def test_get_leak_sensor_type_set():
        '''
        Test get_leak_sensor_type returns assigned sensor type
        '''
        sensor = LeakageSensorBase("sensor1")
        for sensor_type in ["rope", "spot", "flex_pcb"]:
            sensor.leak_type = sensor_type
            assert sensor.get_leak_sensor_type() == sensor_type

    @staticmethod
    def test_get_leak_sensor_location_default():
        '''
        Test get_leak_sensor_location default value is None
        '''
        sensor = LeakageSensorBase("sensor1")
        assert sensor.get_leak_sensor_location() is None

    @staticmethod
    def test_get_leak_sensor_location_set():
        '''
        Test get_leak_sensor_location returns assigned location
        '''
        sensor = LeakageSensorBase("sensor1")
        sensor.leak_location = "rear_left"
        assert sensor.get_leak_sensor_location() == "rear_left"

    @staticmethod
    def test_get_leak_severity_default():
        '''
        Test get_leak_severity default value is None
        '''
        sensor = LeakageSensorBase("sensor1")
        assert sensor.get_leak_severity() is LeakSeverity.CRITICAL

    @staticmethod
    def test_get_leak_severity_critical():
        '''
        Test get_leak_severity returns LeakSeverity.CRITICAL enum member
        '''
        sensor = LeakageSensorBase("sensor1")
        sensor.leak_severity = LeakSeverity.CRITICAL
        assert sensor.get_leak_severity() is LeakSeverity.CRITICAL
        assert sensor.get_leak_severity().value == "CRITICAL"

    @staticmethod
    def test_get_leak_severity_minor():
        '''
        Test get_leak_severity returns LeakSeverity.MINOR enum member
        '''
        sensor = LeakageSensorBase("sensor1")
        sensor.leak_severity = LeakSeverity.MINOR
        assert sensor.get_leak_severity() is LeakSeverity.MINOR
        assert sensor.get_leak_severity().value == "MINOR"

    @staticmethod
    def test_get_leak_profile_not_implemented():
        '''
        Test get_leak_profile raises NotImplementedError — must be overridden by platform
        '''
        sensor = LeakageSensorBase("sensor1")
        with pytest.raises(NotImplementedError):
            sensor.get_leak_profile()

    @staticmethod
    def test_concrete_sensor_with_profile():
        '''
        Test a concrete LeakageSensorBase subclass that implements get_leak_profile(),
        returning a real LeakSensorProfileBase object
        '''
        class RopeProfile(LeakSensorProfileBase):
            def get_type(self): return ""
            def get_leak_max_minor_duration_sec(self):
                return 300

        class RopeSensor(LeakageSensorBase):
            def __init__(self, name):
                super().__init__(name)
                self.leak_type = "rope"
                self.leak_location = "rear_left"
                self._profile = RopeProfile()

            def get_leak_profile(self):
                return self._profile

        sensor = RopeSensor("rope_sensor_1")
        assert sensor.get_leak_sensor_type() == "rope"
        assert sensor.get_leak_sensor_location() == "rear_left"
        profile = sensor.get_leak_profile()
        assert isinstance(profile, LeakSensorProfileBase)
        assert profile.get_leak_max_minor_duration_sec() == 300

    @staticmethod
    def test_leaking_sensor_with_full_attributes():
        '''
        Test a sensor with all new attributes set, simulating a real leak event
        '''
        sensor = LeakageSensorBase("leak_sensor_critical")
        sensor.leaking = True
        sensor.leak_sensor_ok = True
        sensor.leak_type = "flex_pcb"
        sensor.leak_location = "front_panel"
        sensor.leak_severity = LeakSeverity.CRITICAL

        assert sensor.is_leak() == True
        assert sensor.is_leak_sensor_ok() == True
        assert sensor.get_leak_sensor_type() == "flex_pcb"
        assert sensor.get_leak_sensor_location() == "front_panel"
        assert sensor.get_leak_severity() is LeakSeverity.CRITICAL

    @staticmethod
    def test_faulty_leaking_sensor():
        '''
        Test a sensor that is both leaking and faulty — faulty sensor with minor severity
        '''
        sensor = LeakageSensorBase("faulty_sensor")
        sensor.leaking = True
        sensor.leak_sensor_ok = False
        sensor.leak_type = "spot"
        sensor.leak_severity = LeakSeverity.MINOR

        assert sensor.is_leak() == True
        assert sensor.is_leak_sensor_ok() == False
        assert sensor.get_leak_sensor_type() == "spot"
        assert sensor.get_leak_severity() is LeakSeverity.MINOR


class TestLeakSensorProfileBase:
    '''
    Collection of LeakSensorProfileBase test methods
    '''

    @staticmethod
    def test_not_implemented():
        '''
        Test get_leak_max_minor_duration_sec raises NotImplementedError — must be overridden by platform
        '''
        with pytest.raises(TypeError):
            _ = LeakSensorProfileBase()

    @staticmethod
    def test_concrete_profile_implementation():
        '''
        Test that a concrete subclass can override get_leak_max_minor_duration_sec
        '''
        class RopeProfile(LeakSensorProfileBase):
            def get_type(self): return "rope"
            def get_leak_max_minor_duration_sec(self):
                return 300

        profile = RopeProfile()
        assert profile.get_leak_max_minor_duration_sec() == 300

    @staticmethod
    def test_multiple_sensor_type_profiles():
        '''
        Test profiles for all sensor types specified in the spec: rope=300, spot=600, flex_pcb=180
        '''
        class RopeProfile(LeakSensorProfileBase):
            def get_type(self): return "rope"
            def get_leak_max_minor_duration_sec(self):
                return 300

        class SpotProfile(LeakSensorProfileBase):
            def get_type(self): return "spot"
            def get_leak_max_minor_duration_sec(self):
                return 600

        class FlexPcbProfile(LeakSensorProfileBase):
            def get_type(self): return "flex_pcb"
            def get_leak_max_minor_duration_sec(self):
                return 180

        expected = [("rope", RopeProfile, 300), ("spot", SpotProfile, 600), ("flex_pcb", FlexPcbProfile, 180)]
        for sensor_type, profile_cls, expected_duration in expected:
            profile = profile_cls()
            assert profile.get_leak_max_minor_duration_sec() == expected_duration, \
                f"{sensor_type} profile duration mismatch"
            assert profile.get_type() == sensor_type

class TestLiquidCoolingBase():
    '''
    Collection of LiquidCoolingBase test methods
    '''
    
    @staticmethod
    def test_liquid_cooling_base_init():
        '''
        Test liquid cooling base default implementation
        '''
        liquid_cooling = LiquidCoolingBase([])

        assert liquid_cooling.get_num_leak_sensors() == 0
        assert liquid_cooling.get_all_leak_sensors() == []
        assert liquid_cooling.get_leak_sensor_status() == []

    @staticmethod
    def test_get_leak_sensor_out_of_range():
        '''
        Test get_leak_sensor method with an out-of-range index
        '''
        common = {"type": "rope", "location": "chassis",
                       "severity": LeakSeverity.MINOR}
        liquid_cooling = LiquidCoolingBase(0,
                                           [LeakageSensorBase("Sensor1", **common),
                                            LeakageSensorBase("Sensor2", **common), 
                                            LeakageSensorBase("Sensor3", **common)])

        # Redirect stderr to capture error message
        captured_output = StringIO()
        sys.stderr = captured_output

        # Call get_leak_sensor and check the return value
        sensor = liquid_cooling.get_leak_sensor(5)
        assert sensor == None

        captured_output.seek(0)
        error_message = captured_output.read()
        assert "Leakage sensor index 5 out of range (0-2)" in error_message

    @staticmethod
    def test_get_leak_sensor_by_valid_index():
        '''
        Test get_leak_sensor returns the correct sensor for a valid index
        '''
        sensor0 = LeakageSensorBase("Sensor0")
        sensor1 = LeakageSensorBase("Sensor1")
        sensor2 = LeakageSensorBase("Sensor2")
        liquid_cooling = LiquidCoolingBase(
            leakage_sensors_list=[sensor0, sensor1, sensor2]
        )

        assert liquid_cooling.get_leak_sensor(0) is sensor0
        assert liquid_cooling.get_leak_sensor(1) is sensor1
        assert liquid_cooling.get_leak_sensor(2) is sensor2

    @staticmethod
    def test_get_leak_sensor_status_with_leaking_sensors():
        '''
        Test get_leak_sensor_status returns only leaking sensors from a mixed set.
        Leaking sensors have type, location and severity populated.
        '''
        ok_sensor = LeakageSensorBase("ok_sensor")
        ok_sensor.leaking = False
        ok_sensor.leak_type = "spot"
        ok_sensor.leak_location = "zone_a"

        minor_sensor = LeakageSensorBase("minor_sensor")
        minor_sensor.leaking = True
        minor_sensor.leak_type = "rope"
        minor_sensor.leak_location = "zone_b"
        minor_sensor.leak_severity = LeakSeverity.MINOR

        critical_sensor = LeakageSensorBase("critical_sensor")
        critical_sensor.leaking = True
        critical_sensor.leak_type = "flex_pcb"
        critical_sensor.leak_location = "zone_c"
        critical_sensor.leak_severity = LeakSeverity.CRITICAL

        liquid_cooling = LiquidCoolingBase(
            leakage_sensors_list=[ok_sensor, minor_sensor, critical_sensor]
        )

        leaking = liquid_cooling.get_leak_sensor_status()
        assert len(leaking) == 2
        assert minor_sensor in leaking
        assert critical_sensor in leaking
        assert ok_sensor not in leaking

        # Verify the leaking sensors carry correct severity
        severities = {s.get_name(): s.get_leak_severity() for s in leaking}
        assert severities["minor_sensor"] is LeakSeverity.MINOR
        assert severities["critical_sensor"] is LeakSeverity.CRITICAL

    @staticmethod
    def test_get_leak_sensor_status_none_leaking():
        '''
        Test get_leak_sensor_status returns empty list when no sensors are leaking
        '''
        sensors = []
        for i in range(3):
            s = LeakageSensorBase(f"sensor_{i}")
            s.leaking = False
            s.leak_sensor_ok = True
            s.leak_type = "spot"
            sensors.append(s)

        liquid_cooling = LiquidCoolingBase(leakage_sensors_list=sensors)
        assert liquid_cooling.get_leak_sensor_status() == []

    @staticmethod
    def test_get_leak_sensor_status_faulty_sensor_ignored():
        '''
        Test that a faulty (but non-leaking) sensor is excluded from get_leak_sensor_status
        '''
        faulty_sensor = LeakageSensorBase("faulty")
        faulty_sensor.leaking = False
        faulty_sensor.leak_sensor_ok = False  # faulty but not reporting a leak

        liquid_cooling = LiquidCoolingBase(
            leakage_sensors_list=[faulty_sensor]
        )
        assert liquid_cooling.get_leak_sensor_status() == []

    @staticmethod
    def test_liquid_cooling_with_sensor_profiles():
        '''
        Test LiquidCoolingBase with concrete sensors that return profiles.
        Simulates full platform implementation per spec.
        '''
        class RopeProfile(LeakSensorProfileBase):
            def get_type(self): return "rope"
            def get_leak_max_minor_duration_sec(self):
                return 300

        class PlatformRopeSensor(LeakageSensorBase):
            def __init__(self, name, location):
                super().__init__(name)
                self.leak_type = "rope"
                self.leak_location = location
                self._profile = RopeProfile()

            def get_leak_profile(self):
                return self._profile

        s1 = PlatformRopeSensor("rope_sensor_0", "rear")
        s2 = PlatformRopeSensor("rope_sensor_1", "front")
        s2.leaking = True
        s2.leak_severity = LeakSeverity.MINOR

        liquid_cooling = LiquidCoolingBase(
            leakage_sensors_list=[s1, s2]
        )

        assert liquid_cooling.get_num_leak_sensors() == 2
        leaking = liquid_cooling.get_leak_sensor_status()
        assert len(leaking) == 1
        assert leaking[0].get_name() == "rope_sensor_1"
        assert leaking[0].get_leak_sensor_type() == "rope"
        assert leaking[0].get_leak_sensor_location() == "front"
        assert leaking[0].get_leak_severity() is LeakSeverity.MINOR
        assert leaking[0].get_leak_profile().get_leak_max_minor_duration_sec() == 300

