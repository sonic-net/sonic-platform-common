from sonic_platform_base import chassis_base
from sonic_platform_base import fan_base
from sonic_platform_base import fan_drawer_base
from sonic_platform_base import module_base
from sonic_platform_base import psu_base
from sonic_platform_base import sfp_base
from sonic_platform_base import thermal_base
from sonic_platform_base.sonic_thermal_control import thermal_manager_base


class MockFan(fan_base.FanBase):
    def __init__(self):
        super(MockFan, self).__init__()
        self._name = None
        self._presence = True
        self._model = 'Fan Model'
        self._serial = 'Fan Serial'
        self._status = True
        self._position_in_parent = 1
        self._replaceable = True

        self._speed = 20
        self._speed_tolerance = 20
        self._target_speed = 20
        self._direction = self.FAN_DIRECTION_INTAKE
        self._status_led = self.STATUS_LED_COLOR_RED

    def get_speed(self):
        return self._speed

    def get_speed_tolerance(self):
        return self._speed_tolerance

    def get_target_speed(self):
        return self._target_speed

    def get_direction(self):
        return self._direction

    def get_status_led(self):
        return self._status_led

    def set_status_led(self, value):
        self._status_led = value

    def make_under_speed(self):
        self._speed = 1
        self._target_speed = 2
        self._speed_tolerance = 0

    def make_over_speed(self):
        self._speed = 2
        self._target_speed = 1
        self._speed_tolerance = 0

    def make_normal_speed(self):
        self._speed = 1
        self._target_speed = 1
        self._speed_tolerance = 0

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


class MockErrorFan(MockFan):
    def get_speed(self):
        raise Exception('Failed to get speed')


class MockFanDrawer(fan_drawer_base.FanDrawerBase):
    def __init__(self, index):
        super(MockFanDrawer, self).__init__()
        self._name = 'FanDrawer {}'.format(index)
        self._presence = True
        self._model = 'Fan Drawer Model'
        self._serial = 'Fan Drawer Serial'
        self._status = True
        self._position_in_parent = 1
        self._replaceable = True

        self._status_led = self.STATUS_LED_COLOR_RED

    def get_all_fans(self):
        return self._fan_list

    def get_status_led(self):
        return self._status_led

    def set_status_led(self, value):
        self._status_led = value

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
    def __init__(self):
        super(MockPsu, self).__init__()
        self._name = None
        self._presence = True
        self._model = 'PSU Model'
        self._serial = 'PSU Serial'
        self._status = True
        self._position_in_parent = 1
        self._replaceable = True

    def get_all_fans(self):
        return self._fan_list

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
    
    def get_powergood_status(self):
        return self._status

    def set_status(self, status):
        self._status = status

    def get_position_in_parent(self):
        return self._position_in_parent

    def is_replaceable(self):
        return self._replaceable


class MockSfp(sfp_base.SfpBase):
    def __init__(self):
        super(MockSfp, self).__init__()
        self._name = None
        self._presence = True
        self._model = 'SFP Model'
        self._serial = 'SFP Serial'
        self._status = True
        self._position_in_parent = 1
        self._replaceable = True

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


class MockThermal(thermal_base.ThermalBase):
    def __init__(self, index=None):
        super(MockThermal, self).__init__()
        self._name = 'Thermal {}'.format(index) if index != None else None
        self._presence = True
        self._model = 'Thermal Model'
        self._serial = 'Thermal Serial'
        self._status = True
        self._position_in_parent = 1
        self._replaceable = False

        self._temperature = 2
        self._minimum_temperature = 1
        self._maximum_temperature = 5
        self._high_threshold = 3
        self._low_threshold = 1
        self._high_critical_threshold = 4
        self._low_critical_threshold = 0

    def get_temperature(self):
        return self._temperature

    def get_minimum_recorded(self):
        return self._minimum_temperature

    def get_maximum_recorded(self):
        return self._maximum_temperature

    def get_high_threshold(self):
        return self._high_threshold

    def get_low_threshold(self):
        return self._low_threshold

    def get_high_critical_threshold(self):
        return self._high_critical_threshold

    def get_low_critical_threshold(self):
        return self._low_critical_threshold

    def make_over_temper(self):
        self._high_threshold = 2
        self._temperature = 3
        self._low_threshold = 1

    def make_under_temper(self):
        self._high_threshold = 3
        self._temperature = 1
        self._low_threshold = 2

    def make_normal_temper(self):
        self._high_threshold = 3
        self._temperature = 2
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


class MockErrorThermal(MockThermal):
    def get_temperature(self):
        raise Exception('Failed to get temperature')


class MockThermalManager(thermal_manager_base.ThermalManagerBase):
    def __init__(self):
        super(MockThermalManager, self).__init__()


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

        self._is_chassis_system = False
        self._my_slot = module_base.ModuleBase.MODULE_INVALID_SLOT
        self._thermal_manager = MockThermalManager()

    def make_absent_fan(self):
        fan = MockFan()
        fan.set_presence(False)
        fan_drawer = MockFanDrawer(len(self._fan_drawer_list))
        fan_drawer._fan_list.append(fan)
        self._fan_list.append(fan)
        self._fan_drawer_list.append(fan_drawer)

    def make_faulty_fan(self):
        fan = MockFan()
        fan.set_status(False)
        fan_drawer = MockFanDrawer(len(self._fan_drawer_list))
        fan_drawer._fan_list.append(fan)
        self._fan_list.append(fan)
        self._fan_drawer_list.append(fan_drawer)

    def make_under_speed_fan(self):
        fan = MockFan()
        fan.make_under_speed()
        fan_drawer = MockFanDrawer(len(self._fan_drawer_list))
        fan_drawer._fan_list.append(fan)
        self._fan_list.append(fan)
        self._fan_drawer_list.append(fan_drawer)

    def make_over_speed_fan(self):
        fan = MockFan()
        fan.make_over_speed()
        fan_drawer = MockFanDrawer(len(self._fan_drawer_list))
        fan_drawer._fan_list.append(fan)
        self._fan_list.append(fan)
        self._fan_drawer_list.append(fan_drawer)

    def make_error_fan(self):
        fan = MockErrorFan()
        fan_drawer = MockFanDrawer(len(self._fan_drawer_list))
        fan_drawer._fan_list.append(fan)
        self._fan_list.append(fan)
        self._fan_drawer_list.append(fan_drawer)

    def make_over_temper_thermal(self):
        thermal = MockThermal()
        thermal.make_over_temper()
        self._thermal_list.append(thermal)

    def make_under_temper_thermal(self):
        thermal = MockThermal()
        thermal.make_under_temper()
        self._thermal_list.append(thermal)

    def make_error_thermal(self):
        thermal = MockErrorThermal()
        self._thermal_list.append(thermal)

    def make_module_thermal(self):
        module = MockModule()
        self._module_list.append(module)
        sfp = MockSfp()
        sfp._thermal_list.append(MockThermal())
        psu = MockPsu()
        psu._thermal_list.append(MockThermal())
        module._sfp_list.append(sfp)
        module._psu_list.append(psu)
        module._thermal_list.append(MockThermal())

    def is_modular_chassis(self):
        return self._is_chassis_system

    def set_modular_chassis(self, is_true):
        self._is_chassis_system = is_true

    def set_my_slot(self, my_slot):
        self._my_slot = my_slot

    def get_my_slot(self):
        return self._my_slot

    def get_thermal_manager(self):
        return self._thermal_manager

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
