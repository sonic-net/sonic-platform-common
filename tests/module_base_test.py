import unittest
from unittest.mock import patch, MagicMock
from sonic_platform_base.module_base import ModuleBase

class TestModuleBase:

    def test_module_base(self):
        module = ModuleBase()
        not_implemented_methods = [
                [module.get_dpu_id],
                [module.get_reboot_cause],
                [module.get_state_info],
                [module.get_pci_bus_info],
                [module.pci_detach],
                [module.pci_reattach],
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

    def test_sensors(self):
        module = ModuleBase()
        assert(module.get_num_voltage_sensors() == 0)
        assert(module.get_all_voltage_sensors() == [])
        assert(module.get_voltage_sensor(0) == None)
        module._voltage_sensor_list = ["s1"]
        assert(module.get_all_voltage_sensors() == ["s1"])
        assert(module.get_voltage_sensor(0) == "s1")
        assert(module.get_num_current_sensors() == 0)
        assert(module.get_all_current_sensors() == [])
        assert(module.get_current_sensor(0) == None)
        module._current_sensor_list = ["s1"]
        assert(module.get_all_current_sensors() == ["s1"])
        assert(module.get_current_sensor(0) == "s1")


class DummyModule(ModuleBase):
    def __init__(self, name="DPU0"):
        self.name = name

    def set_admin_state(self, up):
        return True  # Dummy override


class TestModuleBaseGracefulShutdown:

    @patch("sonic_platform_base.module_base.SonicV2Connector")
    def test_get_reboot_timeout_default(self, mock_db):
        mock_instance = mock_db.return_value
        mock_instance.get_entry.return_value = {'platform': 'x86_64-foo'}
        with patch("builtins.open", unittest.mock.mock_open(read_data='{}')):
            module = DummyModule()
            timeout = module.get_reboot_timeout()
            assert timeout == 60

    @patch("sonic_platform_base.module_base.SonicV2Connector")
    def test_graceful_shutdown_handler_success(self, mock_db):
        dpu_name = "DPU0"
        mock_instance = mock_db.return_value
        mock_instance.get_all.side_effect = [
            {},  # First poll
            {"start": "true", "status": "success", "message": "OK"}  # Second poll
        ]

        module = DummyModule(name=dpu_name)

        with patch.object(module, "get_reboot_timeout", return_value=10), \
             patch("time.sleep"):
            module.graceful_shutdown_handler()
            mock_instance.set_entry.assert_any_call("GNOI_REBOOT_RESULT", dpu_name, {"start": "false"})

    @patch("sonic_platform_base.module_base.SonicV2Connector")
    def test_graceful_shutdown_handler_timeout(self, mock_db):
        dpu_name = "DPU1"
        mock_instance = mock_db.return_value
        mock_instance.get_all.return_value = {}

        module = DummyModule(name=dpu_name)

        with patch.object(module, "get_reboot_timeout", return_value=5), \
             patch("time.sleep"):
            try:
                module.graceful_shutdown_handler()
            except TimeoutError as e:
                assert "timeout" in str(e).lower()
