from sonic_platform_base import chassis_base
from sonic_platform_base import fan_base
from sonic_platform_base import fan_drawer_base
from sonic_platform_base import module_base
from sonic_platform_base import psu_base


class MockChassis(chassis_base.ChassisBase):
    def __init__(self,
                 name='Fixed Chassis',
                 position_in_parent=0,
                 presence=True,
                 model='Module Model',
                 serial='Module Serial',
                 status=True):
        super(MockChassis, self).__init__()
        self._name = name
        self._presence = presence
        self._model = model
        self._serial = serial
        self._status = status
        self._position_in_parent = position_in_parent

        self._psu_list = []
        self._fan_drawer_list = []
        self._module_list = []

    def get_num_psus(self):
        return len(self._psu_list)

    def get_all_psus(self):
        return self._psu_list

    def get_psu(self, index):
        return self._psu_list[index]

    def get_num_fan_drawers(self):
        return len(self._fan_drawer_list)

    def get_all_fan_drawers(self):
        return self._fan_drawer_list

    def get_num_modules(self):
        return len(self._module_list)

    def get_all_modules(self):
        return self._module_list

    def get_status_led(self):
        return self._status_led_color

    def set_status_led(self, color):
        self._status_led_color = color
        return True

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


class MockFan(fan_base.FanBase):
    def __init__(self,
                 name,
                 position_in_parent,
                 presence=True,
                 model='Module Model',
                 serial='Module Serial',
                 status=True,
                 direction=fan_base.FanBase.FAN_DIRECTION_INTAKE,
                 speed=50):
        super(MockFan, self).__init__()
        self._name = name
        self._presence = presence
        self._model = model
        self._serial = serial
        self._status = status
        self._position_in_parent = position_in_parent

        self._direction = direction
        self._speed = speed
        self._status_led_color = self.STATUS_LED_COLOR_OFF

    def get_direction(self):
        return self._direction

    def get_speed(self):
        return self._speed

    def get_status_led(self):
        return self._status_led_color

    def set_status_led(self, color):
        self._status_led_color = color
        return True

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


class MockFanDrawer(fan_drawer_base.FanDrawerBase):
    def __init__(self,
                 name,
                 position_in_parent,
                 presence=True,
                 model='Module Model',
                 serial='Module Serial',
                 status=True):
        super(MockFanDrawer, self).__init__()
        self._name = name
        self._presence = presence
        self._model = model
        self._serial = serial
        self._status = status
        self._position_in_parent = position_in_parent

        self._max_consumed_power = 500.0
        self._status_led_color = self.STATUS_LED_COLOR_OFF

    def get_status(self):
        return self._status

    def set_status(self, status):
        self._status = status

    def get_maximum_consumed_power(self):
        return self._max_consumed_power

    def set_maximum_consumed_power(self, consumed_power):
        self._max_consumed_power = consumed_power

    def get_status_led(self):
        return self._status_led_color

    def set_status_led(self, color):
        self._status_led_color = color
        return True

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
    def __init__(self,
                 name,
                 position_in_parent,
                 presence=True,
                 model='Module Model',
                 serial='Module Serial',
                 status=True):
        super(MockModule, self).__init__()
        self._name = name
        self._presence = presence
        self._model = model
        self._serial = serial
        self._status = status
        self._position_in_parent = position_in_parent

        self._max_consumed_power = 500.0

    def set_maximum_consumed_power(self, consumed_power):
        self._max_consumed_power = consumed_power

    def get_maximum_consumed_power(self):
        return self._max_consumed_power

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


class MockPsu(psu_base.PsuBase):
    def __init__(self,
                 name,
                 position_in_parent,
                 presence=True,
                 model='Module Model',
                 serial='Module Serial',
                 revision='Module Revision',
                 status=True,
                 voltage=12.0,
                 current=8.0,
                 power=100.0,
                 temp=30.00,
                 temp_high_th=50.0,
                 voltage_low_th=11.0,
                 voltage_high_th=13.0,
                 replaceable=True):
        super(MockPsu, self).__init__()
        self._name = name
        self._presence = presence
        self._model = model
        self._serial = serial
        self._revision = revision
        self._status = status
        self._position_in_parent = position_in_parent
        self._replaceable = replaceable

        self._voltage = voltage
        self._current = current
        self._power = power
        self._temp = temp
        self._temp_high_th = temp_high_th
        self._voltage_low_th = voltage_low_th
        self._voltage_high_th = voltage_high_th
        self._status_led_color = self.STATUS_LED_COLOR_OFF

    def get_voltage(self):
        return self._voltage

    def set_voltage(self, voltage):
        self._voltage = voltage

    def get_current(self):
        return self._current

    def set_current(self, current):
        self._current = current

    def get_power(self):
        return self._power

    def set_power(self, power):
        self._power = power

    def get_powergood_status(self):
        return self._status

    def get_temperature(self):
        return self._temp

    def set_temperature(self, power):
        self._temp = temp

    def get_temperature_high_threshold(self):
        return self._temp_high_th

    def get_voltage_high_threshold(self):
        return self._voltage_high_th

    def get_voltage_low_threshold(self):
        return self._voltage_low_th

    def get_maximum_supplied_power(self):
        return self._max_supplied_power

    def set_maximum_supplied_power(self, supplied_power):
        self._max_supplied_power = supplied_power

    def get_status_led(self):
        return self._status_led_color

    def set_status_led(self, color):
        self._status_led_color = color
        return True

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

    def get_revision(self):
        return self._revision

    def get_status(self):
        return self._status

    def set_status(self, status):
        self._status = status

    def get_position_in_parent(self):
        return self._position_in_parent

    def is_replaceable(self):
        return self._replaceable
