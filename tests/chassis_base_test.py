from sonic_platform_base.chassis_base import ChassisBase

class TestChassisBase:

    def test_reboot_cause(self):
        chassis = ChassisBase()
        assert(chassis.REBOOT_CAUSE_POWER_LOSS == "Power Loss")
        assert(chassis.REBOOT_CAUSE_THERMAL_OVERLOAD_CPU == "Thermal Overload: CPU")
        assert(chassis.REBOOT_CAUSE_THERMAL_OVERLOAD_ASIC == "Thermal Overload: ASIC")
        assert(chassis.REBOOT_CAUSE_THERMAL_OVERLOAD_OTHER == "Thermal Overload: Other")
        assert(chassis.REBOOT_CAUSE_INSUFFICIENT_FAN_SPEED == "Insufficient Fan Speed")
        assert(chassis.REBOOT_CAUSE_WATCHDOG == "Watchdog")
        assert(chassis.REBOOT_CAUSE_HARDWARE_OTHER == "Hardware - Other")
        assert(chassis.REBOOT_CAUSE_HARDWARE_BIOS == "BIOS")
        assert(chassis.REBOOT_CAUSE_HARDWARE_CPU == "CPU")
        assert(chassis.REBOOT_CAUSE_HARDWARE_BUTTON == "Push button")
        assert(chassis.REBOOT_CAUSE_HARDWARE_RESET_FROM_ASIC == "Reset from ASIC")
        assert(chassis.REBOOT_CAUSE_NON_HARDWARE == "Non-Hardware")

    def test_chassis_base(self):
        chassis = ChassisBase()
        not_implemented_methods = [
                [chassis.get_uid_led, [], {}],
                [chassis.set_uid_led, ["COLOR"], {}],
                [chassis.get_dpu_id, [], {"name": "DPU0"}],
                [chassis.get_dataplane_state, [], {}],
                [chassis.get_controlplane_state, [], {}],
            ]

        for method in not_implemented_methods:
            exception_raised = False
            try:
                func = method[0]
                args = method[1]
                kwargs = method[2]
                func(*args, **kwargs)
            except NotImplementedError:
                exception_raised = True

            assert exception_raised

    def test_smartswitch(self):
        chassis = ChassisBase()
        assert(chassis.is_smartswitch() == False)
        assert(chassis.is_dpu() == False)

    def test_sensors(self):
        chassis = ChassisBase()
        assert(chassis.get_num_voltage_sensors() == 0)
        assert(chassis.get_all_voltage_sensors() == [])
        assert(chassis.get_voltage_sensor(0) == None)
        chassis._voltage_sensor_list = ["s1"]
        assert(chassis.get_all_voltage_sensors() == ["s1"])
        assert(chassis.get_voltage_sensor(0) == "s1")
        assert(chassis.get_num_current_sensors() == 0)
        assert(chassis.get_all_current_sensors() == [])
        assert(chassis.get_current_sensor(0) == None)
        chassis._current_sensor_list = ["s1"]
        assert(chassis.get_all_current_sensors() == ["s1"])
        assert(chassis.get_current_sensor(0) == "s1")

    def test_get_bmc(self):
        chassis = ChassisBase()
        assert(chassis.get_bmc() == None)
        mock_bmc = "mock_bmc_instance"
        chassis._bmc = mock_bmc
        assert(chassis.get_bmc() == mock_bmc)
