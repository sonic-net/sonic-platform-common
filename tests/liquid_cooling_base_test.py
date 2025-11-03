'''
Test liquid_cooling_base module
'''
import unittest
import sys
from io import StringIO
from sonic_platform_base.liquid_cooling_base import LeakageSensorBase
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
        assert leakage_sensor.is_leak() == False

class TestLiquidCoolingBase():
    '''
    Collection of LiquidCoolingBase test methods
    '''
    
    @staticmethod
    def test_liquid_cooling_base_init():
        '''
        Test liquid cooling base default implementation
        '''
        liquid_cooling = LiquidCoolingBase()

        assert liquid_cooling.get_num_leak_sensors() == 0
        assert liquid_cooling.get_all_leak_sensors() == []
        assert liquid_cooling.get_leak_sensor_status() == []

    @staticmethod
    def test_get_leak_sensor_out_of_range():
        '''
        Test get_leak_sensor method with an out-of-range index
        '''
        liquid_cooling = LiquidCoolingBase()
        liquid_cooling.leakage_sensors = [LeakageSensorBase("Sensor1"), 
                                          LeakageSensorBase("Sensor2"), 
                                          LeakageSensorBase("Sensor3")]

        # Redirect stderr to capture error message
        captured_output = StringIO()
        sys.stderr = captured_output

        # Call get_leak_sensor and check the return value
        sensor = liquid_cooling.get_leak_sensor(5)
        assert sensor == None

        captured_output.seek(0)
        error_message = captured_output.read()
        assert "Leakage sensor index 5 out of range (0-2)" in error_message

