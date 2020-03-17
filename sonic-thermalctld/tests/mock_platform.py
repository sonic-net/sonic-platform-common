class MockDevice:
    def __init__(self):
        self.name = None
        self.presence = True
        self.model = 'FAN Model'
        self.serial = 'Fan Serial'

    def get_name(self):
        return self.name

    def get_presence(self):
        return self.presence

    def get_model(self):
        return self.model

    def get_serial(self):
        return self.serial


class MockFan(MockDevice):
    STATUS_LED_COLOR_RED = 'red'
    STATUS_LED_COLOR_GREEN = 'green'

    def __init__(self):
        MockDevice.__init__(self)
        self.speed = 20
        self.speed_tolerance = 20
        self.target_speed = 20
        self.status = True
        self.direction = 'intake'
        self.led_status = 'red'

    def get_speed(self):
        return self.speed

    def get_speed_tolerance(self):
        return self.speed_tolerance

    def get_target_speed(self):
        return self.target_speed

    def get_status(self):
        return self.status

    def get_direction(self):
        return self.direction

    def get_status_led(self):
        return self.led_status

    def set_status_led(self, value):
        self.led_status = value

    def make_under_speed(self):
        self.speed = 1
        self.target_speed = 2
        self.speed_tolerance = 0

    def make_over_speed(self):
        self.speed = 2
        self.target_speed = 1
        self.speed_tolerance = 0

    def make_normal_speed(self):
        self.speed = 1
        self.target_speed = 1
        self.speed_tolerance = 0


class MockErrorFan(MockFan):
    def get_speed(self):
        raise Exception('Fail to get speed')


class MockPsu(MockDevice):
    def __init__(self):
        self.fan_list = []

    def get_all_fans(self):
        return self.fan_list


class MockThermal:
    def __init__(self):
        self.name = None
        self.temperature = 2
        self.high_threshold = 3
        self.low_threshold = 1
        self.high_critical_threshold = 4
        self.low_critical_threshold = 0
    
    def get_name(self):
        return self.name

    def get_temperature(self):
        return self.temperature

    def get_high_threshold(self):
        return self.high_threshold

    def get_low_threshold(self):
        return self.low_threshold

    def get_high_critical_threshold(self):
        return self.high_critical_threshold

    def get_low_critical_threshold(self):
        return self.low_critical_threshold

    def make_over_temper(self):
        self.high_threshold = 2
        self.temperature = 3
        self.low_threshold = 1

    def make_under_temper(self):
        self.high_threshold = 3
        self.temperature = 1
        self.low_threshold = 2

    def make_normal_temper(self):
        self.high_threshold = 3
        self.temperature = 2
        self.low_threshold = 1


class MockErrorThermal(MockThermal):
    def get_temperature(self):
        raise Exception('Fail to get temperature')

    
class MockChassis:
    def __init__(self):
        self.fan_list = []
        self.psu_list = []
        self.thermal_list = []

    def get_all_fans(self):
        return self.fan_list

    def get_all_psus(self):
        return self.psu_list

    def get_all_thermals(self):
        return self.thermal_list

    def make_absence_fan(self):
        fan = MockFan()
        fan.presence = False
        self.fan_list.append(fan)

    def make_under_speed_fan(self):
        fan = MockFan()
        fan.make_under_speed()
        self.fan_list.append(fan)

    def make_over_speed_fan(self):
        fan = MockFan()
        fan.make_over_speed()
        self.fan_list.append(fan)

    def make_error_fan(self):
        fan = MockErrorFan()
        self.fan_list.append(fan)

    def make_over_temper_thermal(self):
        thermal = MockThermal()
        thermal.make_over_temper()
        self.thermal_list.append(thermal)

    def make_under_temper_thermal(self):
        thermal = MockThermal()
        thermal.make_under_temper()
        self.thermal_list.append(thermal)

    def make_error_thermal(self):
        thermal = MockErrorThermal()
        self.thermal_list.append(thermal)

