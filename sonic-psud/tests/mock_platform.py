from .mock_device_base import DeviceBase

class MockDevice:
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

    psu_master_led_color = DeviceBase.STATUS_LED_COLOR_OFF

    def __init__(self, psu_presence, psu_status, psu_name):
        self.name = psu_name
        self.presence = True
        self.psu_status = psu_status

    def get_powergood_status(self):
        return self.psu_status

    def set_status(self, status):
        self.psu_status = status

    def set_maximum_supplied_power(self, supplied_power):
        self.max_supplied_power = supplied_power

    def get_maximum_supplied_power(self):
        return self.max_supplied_power

    @classmethod
    def set_status_master_led(cls, color):
        cls.psu_master_led_color = color

    @classmethod
    def get_status_master_led(cls):
        return cls.psu_master_led_color

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
