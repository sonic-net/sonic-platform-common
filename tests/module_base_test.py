from sonic_platform_base.module_base import ModuleBase

class TestModuleBase:

    def test_module_base(self):
        module = ModuleBase()
        not_implemented_methods = [
                [module.get_dpu_id],
                [module.get_reboot_cause],
                [module.get_state_info],
                [module.get_health_info],
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

