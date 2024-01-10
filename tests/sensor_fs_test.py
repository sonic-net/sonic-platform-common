'''
Test Sensor_fs module
'''

import yaml
import os
from unittest import mock
from sonic_platform_base.sensor_fs import VoltageSensorFs
from sonic_platform_base.sensor_fs import CurrentSensorFs

yaml_data = """
voltage_sensors:
  - name : VSENSOR1
    sensor: 'sensor_data/VSENSOR1'
    high_thresholds: [ 1000, 1050, 1080 ]
    low_thresholds: [ 800, 850, 890 ]
  - name : VSENSOR2
    sensor: 'sensor_data/VSENSOR2'
    high_thresholds: [ 800, 850, 870 ]
    low_thresholds: [ 600, 620, 750 ]

current_sensors:
  - name : CSENSOR1
    sensor: 'sensor_data/CSENSOR1'
    high_thresholds: [ 1000, 1050, 1080 ]
    low_thresholds: [ 800, 850, 890 ]
  - name : CSENSOR2
    sensor: 'sensor_data/CSENSOR2'
    high_thresholds: [ 800, 850, 870 ]
    low_thresholds: [ 600, 620, 750 ]
"""

class TestSensorFs:
    '''
    Collection of SensorFs test methods
    '''

    @staticmethod
    def test_sensor_fs():
        '''
        Test voltage sensors
        '''
        sensors_data = yaml.safe_load(yaml_data)

        vsensors = VoltageSensorFs.factory(sensors_data['voltage_sensors'])
        csensors = CurrentSensorFs.factory(sensors_data['current_sensors'])

        assert(vsensors[0].get_name() == 'VSENSOR1')
        assert(vsensors[0].get_position_in_parent() == 1)

        vsensors[0].set_high_threshold(800)
        assert(vsensors[0].get_high_threshold() == 800)
        vsensors[0].set_high_critical_threshold(900)
        assert(vsensors[0].get_high_critical_threshold() == 900)

        vsensors[0].set_low_threshold(500)
        assert(vsensors[0].get_low_threshold() == 500)
        vsensors[0].set_low_critical_threshold(400)
        assert(vsensors[0].get_low_critical_threshold() == 400)

        assert(csensors[0].get_name() == 'CSENSOR1')
        assert(csensors[0].get_position_in_parent() == 1)

        csensors[0].set_high_threshold(800)
        assert(csensors[0].get_high_threshold() == 800)
        csensors[0].set_high_critical_threshold(900)
        assert(csensors[0].get_high_critical_threshold() == 900)

        csensors[0].set_low_threshold(500)
        assert(csensors[0].get_low_threshold() == 500)
        csensors[0].set_low_critical_threshold(400)
        assert(csensors[0].get_low_critical_threshold() == 400)

        assert(vsensors[0].get_minimum_recorded() == None)

        tests_path = os.path.dirname(os.path.abspath(__file__))
        vsensor_path = os.path.join(tests_path, "sensor_data/VSENSOR1")
        vsensors[0].sensor = vsensor_path
        print(vsensor_path, vsensors[0])

        assert(vsensors[0].get_value() == 900)
        assert(vsensors[0].get_minimum_recorded() == 900)
        assert(vsensors[0].get_maximum_recorded() == 900)
