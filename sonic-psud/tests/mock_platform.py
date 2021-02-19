from .mock_device_base import DeviceBase


class MockDevice:
    STATUS_LED_COLOR_GREEN = "green"
    STATUS_LED_COLOR_AMBER = "amber"
    STATUS_LED_COLOR_RED = "red"
    STATUS_LED_COLOR_OFF = "off"

    def __init__(self):
        self.name = None
        self.presence = True
        self.model = 'Module Model'
        self.serial = 'Module Serial'

    def get_name(self):
        return self.name

    def set_presence(self, presence):
        self.presence = presence

    def get_presence(self):
        return self.presence

    def get_model(self):
        return self.model

    def get_serial(self):
        return self.serial


class MockPsu(MockDevice):
    master_led_color = MockDevice.STATUS_LED_COLOR_OFF

    def __init__(self, presence, status, name, position_in_parent):
        self.name = name
        self.presence = True
        self.status = status
        self.status_led_color = self.STATUS_LED_COLOR_OFF
        self.position_in_parent = position_in_parent
        self._fan_list = []

    def get_all_fans(self):
        return self._fan_list

    def get_powergood_status(self):
        return self.status

    def set_status_led(self, color):
        self.status_led_color = color
        return True

    def get_status_led(self):
        return self.status_led_color

    def set_status(self, status):
        self.status = status

    def get_position_in_parent(self):
        return self.position_in_parent

    def set_maximum_supplied_power(self, supplied_power):
        self.max_supplied_power = supplied_power

    def get_maximum_supplied_power(self):
        return self.max_supplied_power

    @classmethod
    def set_status_master_led(cls, color):
        cls.master_led_color = color

    @classmethod
    def get_status_master_led(cls):
        return cls.master_led_color


class MockFanDrawer(MockDevice):
    def __init__(self, fan_drawer_presence, fan_drawer_status, fan_drawer_name):
        self.name = fan_drawer_name
        self.presence = True
        self.fan_drawer_status = fan_drawer_status

    def get_status(self):
        return self.fan_drawer_status

    def set_status(self, status):
        self.fan_drawer_status = status

    def set_maximum_consumed_power(self, consumed_power):
        self.max_consumed_power = consumed_power

    def get_maximum_consumed_power(self):
        return self.max_consumed_power


class MockFan(MockDevice):
    FAN_DIRECTION_INTAKE = "intake"
    FAN_DIRECTION_EXHAUST = "exhaust"

    def __init__(self, name, direction, speed=50):
        self.name = name
        self.direction = direction
        self.speed = speed
        self.status_led_color = self.STATUS_LED_COLOR_OFF

    def get_direction(self):
        return self.direction

    def get_speed(self):
        return self.speed

    def set_status_led(self, color):
        self.status_led_color = color
        return True

    def get_status_led(self):
        return self.status_led_color



class MockModule(MockDevice):
    def __init__(self, module_presence, module_status, module_name):
        self.name = module_name
        self.presence = True
        self.module_status = module_status

    def get_status(self):
        return self.module_status

    def set_status(self, status):
        self.module_status = status

    def set_maximum_consumed_power(self, consumed_power):
        self.max_consumed_power = consumed_power

    def get_maximum_consumed_power(self):
        return self.max_consumed_power


class MockChassis:
    def __init__(self):
        self.psu_list = []
        self.fan_drawer_list = []
        self.module_list = []

    def get_num_psus(self):
        return len(self.psu_list)

    def get_all_psus(self):
        return self.psu_list

    def get_psu(self, index):
        return self.psu_list[index]

    def get_num_fan_drawers(self):
        return len(self.fan_drawer_list)

    def get_all_fan_drawers(self):
        return self.fan_drawer_list

    def get_num_modules(self):
        return len(self.module_list)

    def get_all_modules(self):
        return self.module_list
