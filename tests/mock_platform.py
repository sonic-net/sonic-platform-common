class MockFan:
    def __init__(self):
        self.presence = True
        self.speed = 60

    def get_presence(self):
        return self.presence

    def set_speed(self, speed):
        self.speed = speed


class MockPsu:
    def __init__(self):
        self.presence = True

    def get_presence(self):
        return self.presence


class MockChassis:
    def __init__(self):
        self.fan_list = []
        self.psu_list = []

    def get_all_psus(self):
        return self.psu_list

    def get_all_fans(self):
        return self.fan_list

    def get_thermal_manager(self):
        from sonic_platform_base.sonic_thermal_control.thermal_manager_base import ThermalManagerBase
        return ThermalManagerBase

    def make_fan_absence(self):
        fan = MockFan()
        fan.presence = False
        self.fan_list.append(fan)

    def make_psu_absence(self):
        psu = MockPsu()
        psu.presence = False
        self.psu_list.append(psu)
