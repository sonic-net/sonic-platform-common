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
