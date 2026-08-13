import builtins
import importlib

import pytest
from unittest import mock

from sonic_platform_base import chassis_base
from sonic_platform_base.chassis_base import ChassisBase

class TestChassisBase:

    @pytest.fixture(autouse=True)
    def _mock_cpo_data(self):
        with mock.patch("sonic_py_common.device_info.get_cpo_data",
                        return_value=None) as mock_get:
            self.mock_get_cpo_data = mock_get
            yield

    def test_reboot_cause(self):
        chassis = ChassisBase()
        assert(chassis.REBOOT_CAUSE_POWER_LOSS == "Power Loss")
        assert(chassis.REBOOT_CAUSE_POWER_DOWN_REQUEST_FROM_BMC == "Power down request from BMC")
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
                [chassis.get_elsfp_change_event, [], {}],
                [chassis.get_elsfp_change_event, [1000], {}],
                [chassis.get_change_event, [], {}],
                [chassis.get_change_event, [1000], {}],
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

    def test_get_sed_mgmt(self):
        chassis = ChassisBase()
        assert(chassis.get_sed_mgmt() == None)
        mock_sed_mgmt = "mock_sed_mgmt_instance"
        chassis._sed_mgmt = mock_sed_mgmt
        assert(chassis.get_sed_mgmt() == mock_sed_mgmt)

    def test_is_bmc(self):
        chassis = ChassisBase()
        assert chassis.is_bmc() is False

        class BmcChassis(ChassisBase):
            def is_bmc(self):
                return True

        bmc = BmcChassis()
        assert bmc.is_bmc() is True

    def test_is_liquid_cooled(self):
        chassis = ChassisBase()
        assert chassis.is_liquid_cooled() is False

        class LiquidCooledChassis(ChassisBase):
            def is_liquid_cooled(self):
                return True

        liquid = LiquidCooledChassis()
        assert liquid.is_liquid_cooled() is True

    def test_get_liquid_cooling(self):
        chassis = ChassisBase()
        assert chassis.get_liquid_cooling() is NotImplementedError

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

    def test_no_cpo_data(self):
        chassis = ChassisBase()
        self.mock_get_cpo_data.assert_called_once()
        assert chassis.get_num_cpos() == 0

    def test_cpo_data_base_class_not_implemented(self):
        self.mock_get_cpo_data.return_value = {"devices": {}, "interfaces": {}}
        with pytest.raises(NotImplementedError):
            ChassisBase()

    def test_construct_cpo_list_for_topology(self):
        cpo_data = {
            "devices": {
                "OE1": {"device_type": "optical_engine"},
                "ELS1": {"device_type": "external_laser_source"},
            },
            "interfaces": {
                "Ethernet0": {
                    "associated_devices": [
                        {"device_id": "OE1", "bank": 0},
                        {"device_id": "ELS1", "bank": 0},
                    ]
                }
            },
        }
        self.mock_get_cpo_data.return_value = cpo_data

        class CpoChassis(ChassisBase):
            def construct_cpo_devices(self, cpo_data):
                for interface in cpo_data["interfaces"]:
                    self._cpo_list.append(interface)

        chassis = CpoChassis()
        assert chassis.get_num_cpos() == 1
        assert chassis.get_cpo(0) == "Ethernet0"

    def test_device_info_import_failure(self):
        # Some unit-test packages shadow sonic_py_common with a partial mock
        # that does not provide device_info. chassis_base must still import
        # successfully so these tests do not fail, since device_info is only
        # required for CPO hardware.
        real_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if name == "sonic_py_common":
                raise ImportError("no module named sonic_py_common.device_info")
            return real_import(name, *args, **kwargs)

        try:
            with mock.patch.object(builtins, "__import__", failing_import):
                importlib.reload(chassis_base)

            assert chassis_base.device_info is None
            chassis = chassis_base.ChassisBase()
            self.mock_get_cpo_data.assert_not_called()
            assert chassis.get_num_cpos() == 0
        finally:
            # Restore the module for the remaining tests
            importlib.reload(chassis_base)

        assert chassis_base.device_info is not None

    def test_sfp_counts_only_valid_objects(self):
        chassis = ChassisBase()
        sfp2 = mock.MagicMock()
        sfp3 = mock.MagicMock()
        chassis._sfp_list = [None, None, sfp2, sfp3]

        assert chassis.get_num_sfps() == 2
        assert chassis.get_all_sfps() == [sfp2, sfp3]
        assert chassis.get_sfp(0) is None
        assert chassis.get_sfp(2) is sfp2

    def test_port_lists_valid(self):
        chassis = ChassisBase()
        chassis._sfp_list = [None, None, mock.MagicMock(), mock.MagicMock()]
        chassis._cpo_list = [mock.MagicMock(), mock.MagicMock(), None, None]

        assert chassis.get_num_sfps() == 2
        assert chassis.get_num_cpos() == 2

    def test_port_lists_length_mismatch(self):
        chassis = ChassisBase()
        chassis._sfp_list = [None, None, mock.MagicMock(), mock.MagicMock()]
        chassis._cpo_list = [mock.MagicMock(), mock.MagicMock()]

        with pytest.raises(RuntimeError, match="must be the same length"):
            chassis.get_num_cpos()

        with pytest.raises(RuntimeError, match="must be the same length"):
            chassis.get_num_sfps()

    def test_port_lists_double_claimed_port(self):
        chassis = ChassisBase()
        chassis._sfp_list = [None, mock.MagicMock(), mock.MagicMock()]
        chassis._cpo_list = [mock.MagicMock(), mock.MagicMock(), None]

        with pytest.raises(RuntimeError,
                           match="Physical port 1 has both an SFP and a CPO object"):
            chassis.get_num_sfps()

    def test_port_lists_single_technology_not_checked(self):
        chassis = ChassisBase()
        chassis._sfp_list = [None, mock.MagicMock(), mock.MagicMock()]

        assert chassis.get_num_sfps() == 2
        assert chassis.get_num_cpos() == 0
