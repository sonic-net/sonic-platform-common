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

    def test_is_bmc(self):
        chassis = ChassisBase()
        assert chassis.is_bmc() is False

        class BmcChassis(ChassisBase):
            def is_bmc(self):
                return True

        bmc = BmcChassis()
        assert bmc.is_bmc() is True

    def test_switch_host_module_at_index_zero(self):
        '''
        On a BMC chassis, only the Switch-Host is modelled as a module.
        get_all_modules() returns [switch_host] and index 0 fetches it.
        get_module_index() maps the Switch-Host name back to index 0.
        '''
        from sonic_platform_base.module_base import ModuleBase

        class SwitchHostModule(ModuleBase):
            def get_name(self):
                return ModuleBase.MODULE_TYPE_SWITCH_HOST

        switch_host = SwitchHostModule()
        chassis = ChassisBase()
        chassis._module_list = [switch_host]

        assert chassis.get_num_modules() == 1
        assert chassis.get_all_modules() == [switch_host]
        assert chassis.get_module(0) is switch_host

    def test_pdbs(self, capsys):
        chassis = ChassisBase()
        assert chassis.get_num_pdbs() == 0
        assert chassis.get_all_pdbs() == []
        assert chassis.get_pdb(0) is None
        err = capsys.readouterr().err
        assert "PDB index 0 out of range" in err

        pdb0 = object()
        chassis._pdb_list = [pdb0]
        assert chassis.get_num_pdbs() == 1
        assert chassis.get_all_pdbs() == [pdb0]
        assert chassis.get_pdb(0) is pdb0

        assert chassis.get_pdb(1) is None
        err_oob = capsys.readouterr().err
        assert "PDB index 1 out of range (0-0)" in err_oob

    def test_pdbs_multiple_and_negative_index(self, capsys):
        """Several PDB entries: success paths, high index error, valid negative index."""
        chassis = ChassisBase()
        pdb0, pdb1, pdb2 = object(), object(), object()
        chassis._pdb_list = [pdb0, pdb1, pdb2]

        assert chassis.get_num_pdbs() == 3
        assert chassis.get_all_pdbs() == [pdb0, pdb1, pdb2]
        assert chassis.get_pdb(0) is pdb0
        assert chassis.get_pdb(1) is pdb1
        assert chassis.get_pdb(2) is pdb2
        capsys.readouterr()

        assert chassis.get_pdb(3) is None
        err_high = capsys.readouterr().err
        assert "PDB index 3 out of range (0-2)" in err_high

        assert chassis.get_pdb(-1) is pdb2
        assert chassis.get_pdb(-2) is pdb1
        assert chassis.get_pdb(-3) is pdb0

        assert chassis.get_pdb(-4) is None
        err_neg = capsys.readouterr().err
        assert "PDB index -4 out of range (0-2)" in err_neg
