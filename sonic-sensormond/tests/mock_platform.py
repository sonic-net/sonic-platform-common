from sonic_platform_base import chassis_base
from sonic_platform_base import module_base

class MockVoltageSensor():
    def __init__(self, index=None):
        self._name = 'Voltage sensor {}'.format(index) if index != None else None
        self._presence = True
        self._model = 'Voltage sensor model'
        self._serial = 'Voltage sensor serial'
        self._status = True
        self._position_in_parent = 1
        self._replaceable = False

        self._value = 2
        self._minimum_value = 1
        self._maximum_value = 5
        self._high_threshold = 3
        self._low_threshold = 1
        self._high_critical_threshold = 4
        self._low_critical_threshold = 0

    def get_value(self):
        return self._value

    def get_unit(self):
        return "mV"

    def get_minimum_recorded(self):
        return self._minimum_value

    def get_maximum_recorded(self):
        return self._maximum_value

    def get_high_threshold(self):
        return self._high_threshold

    def get_low_threshold(self):
        return self._low_threshold

    def get_high_critical_threshold(self):
        return self._high_critical_threshold

    def get_low_critical_threshold(self):
        return self._low_critical_threshold

    def make_over_threshold(self):
        self._high_threshold = 2
        self._value = 3
        self._low_threshold = 1

    def make_under_threshold(self):
        self._high_threshold = 3
        self._value = 1
        self._low_threshold = 2

    def make_normal_value(self):
        self._high_threshold = 3
        self._value = 2
        self._low_threshold = 1

    # Methods inherited from DeviceBase class and related setters
    def get_name(self):
        return self._name

    def get_presence(self):
        return self._presence

    def set_presence(self, presence):
        self._presence = presence

    def get_model(self):
        return self._model

    def get_serial(self):
        return self._serial

    def get_status(self):
        return self._status

    def set_status(self, status):
        self._status = status

    def get_position_in_parent(self):
        return self._position_in_parent

    def is_replaceable(self):
        return self._replaceable

class MockCurrentSensor():
    def __init__(self, index=None):
        self._name = 'Current sensor {}'.format(index) if index != None else None
        self._presence = True
        self._model = 'Current sensor model'
        self._serial = 'Current sensor serial'
        self._status = True
        self._position_in_parent = 1
        self._replaceable = False

        self._value = 2
        self._minimum_value = 1
        self._maximum_value = 5
        self._high_threshold = 3
        self._low_threshold = 1
        self._high_critical_threshold = 4
        self._low_critical_threshold = 0

    def get_value(self):
        return self._value

    def get_unit(self):
        return "mA"

    def get_minimum_recorded(self):
        return self._minimum_value

    def get_maximum_recorded(self):
        return self._maximum_value

    def get_high_threshold(self):
        return self._high_threshold

    def get_low_threshold(self):
        return self._low_threshold

    def get_high_critical_threshold(self):
        return self._high_critical_threshold

    def get_low_critical_threshold(self):
        return self._low_critical_threshold

    def make_over_threshold(self):
        self._high_threshold = 2
        self._value = 3
        self._low_threshold = 1

    def make_under_threshold(self):
        self._high_threshold = 3
        self._value = 1
        self._low_threshold = 2

    def make_normal_value(self):
        self._high_threshold = 3
        self._value = 2
        self._low_threshold = 1

    # Methods inherited from DeviceBase class and related setters
    def get_name(self):
        return self._name

    def get_presence(self):
        return self._presence

    def set_presence(self, presence):
        self._presence = presence

    def get_model(self):
        return self._model

    def get_serial(self):
        return self._serial

    def get_status(self):
        return self._status

    def set_status(self, status):
        self._status = status

    def get_position_in_parent(self):
        return self._position_in_parent

    def is_replaceable(self):
        return self._replaceable

class MockErrorVoltageSensor(MockVoltageSensor):
    def get_value(self):
        raise Exception('Failed to get voltage')

class MockErrorCurrentSensor(MockCurrentSensor):
    def get_value(self):
        raise Exception('Failed to get current')

class MockChassis(chassis_base.ChassisBase):
    def __init__(self):
        super(MockChassis, self).__init__()
        self._name = None
        self._presence = True
        self._model = 'Chassis Model'
        self._serial = 'Chassis Serial'
        self._status = True
        self._position_in_parent = 1
        self._replaceable = False
        self._current_sensor_list = []
        self._voltage_sensor_list = []

        self._is_chassis_system = False
        self._my_slot = module_base.ModuleBase.MODULE_INVALID_SLOT

    def get_num_voltage_sensors(self):
        return len(self._voltage_sensor_list)

    def get_num_current_sensors(self):
        return len(self._current_sensor_list)

    def get_all_voltage_sensors(self):
        return self._voltage_sensor_list

    def get_all_current_sensors(self):
        return self._current_sensor_list

    def make_over_threshold_voltage_sensor(self):
        voltage_sensor = MockVoltageSensor()
        voltage_sensor.make_over_threshold()
        self._voltage_sensor_list.append(voltage_sensor)

    def make_under_threshold_voltage_sensor(self):
        voltage_sensor = MockVoltageSensor()
        voltage_sensor.make_under_threshold()
        self._voltage_sensor_list.append(voltage_sensor)

    def make_error_voltage_sensor(self):
        voltage_sensor = MockErrorVoltageSensor()
        self._voltage_sensor_list.append(voltage_sensor)

    def make_module_voltage_sensor(self):
        module = MockModule()
        self._module_list.append(module)
        module._voltage_sensor_list.append(MockVoltageSensor())

    def make_over_threshold_current_sensor(self):
        current_sensor = MockCurrentSensor()
        current_sensor.make_over_threshold()
        self._current_sensor_list.append(current_sensor)

    def make_under_threshold_current_sensor(self):
        current_sensor = MockCurrentSensor()
        current_sensor.make_under_threshold()
        self._current_sensor_list.append(current_sensor)

    def make_error_current_sensor(self):
        current_sensor = MockErrorCurrentSensor()
        self._current_sensor_list.append(current_sensor)

    def make_module_current_sensor(self):
        module = MockModule()
        self._module_list.append(module)
        module._current_sensor_list.append(MockCurrentSensor())

    def is_modular_chassis(self):
        return self._is_chassis_system

    def set_modular_chassis(self, is_true):
        self._is_chassis_system = is_true

    def set_my_slot(self, my_slot):
        self._my_slot = my_slot

    def get_my_slot(self):
        return self._my_slot

    # Methods inherited from DeviceBase class and related setters
    def get_name(self):
        return self._name

    def get_presence(self):
        return self._presence

    def set_presence(self, presence):
        self._presence = presence

    def get_model(self):
        return self._model

    def get_serial(self):
        return self._serial

    def get_status(self):
        return self._status

    def set_status(self, status):
        self._status = status

    def get_position_in_parent(self):
        return self._position_in_parent

    def is_replaceable(self):
        return self._replaceable


class MockModule(module_base.ModuleBase):
    def __init__(self):
        super(MockModule, self).__init__()
        self._current_sensor_list = []
        self._voltage_sensor_list = []

    def get_all_voltage_sensors(self):
        return self._voltage_sensor_list

    def get_all_current_sensors(self):
        return self._current_sensor_list

