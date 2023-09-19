'''
Test sensor module base classes 
'''

from unittest import mock
from sonic_platform_base.sensor_base import SensorBase
from sonic_platform_base.sensor_base import VoltageSensorBase
from sonic_platform_base.sensor_base import CurrentSensorBase

class TestSensorBase:
    '''
    Collection of SensorBase test methods
    '''
    @staticmethod
    def test_sensor_base():
        '''
        Verify unimplemented methods
        '''
        sensor = SensorBase()
        not_implemented_methods = [
            (sensor.get_value,),
            (sensor.get_high_threshold,),
            (sensor.get_low_threshold,),
            (sensor.set_high_threshold,0),
            (sensor.set_low_threshold,0),
            (sensor.get_high_critical_threshold,),
            (sensor.set_high_critical_threshold,0),
            (sensor.get_low_critical_threshold,),
            (sensor.set_low_critical_threshold,0),
            (sensor.get_minimum_recorded,),
            (sensor.get_maximum_recorded,)]

        for method in not_implemented_methods:
            expected_exception = False
            try:
                func = method[0]
                args = method[1:]
                func(*args)
            except Exception as exc:
                expected_exception = isinstance(exc, NotImplementedError)
            assert expected_exception

    @staticmethod
    def test_voltage_sensor_base():
        assert(VoltageSensorBase.get_type() == "SENSOR_TYPE_VOLTAGE")
        assert(VoltageSensorBase.get_unit() == "mV")

    @staticmethod
    def test_current_sensor_base():
        assert(CurrentSensorBase.get_type() == "SENSOR_TYPE_CURRENT")
        assert(CurrentSensorBase.get_unit() == "mA")
