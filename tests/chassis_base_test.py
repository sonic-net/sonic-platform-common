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
                [chassis.get_uid_led],
                [chassis.set_uid_led, "COLOR"],
            ]

        for method in not_implemented_methods:
            exception_raised = False
            try:
                func = method[0]
                args = method[1:]
                func(*args)
            except NotImplementedError:
                exception_raised = True

            assert exception_raised