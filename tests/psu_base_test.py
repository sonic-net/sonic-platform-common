from sonic_platform_base.psu_base import PsuBase

class TestPsuBase:

    def test_psu_base(self):
        psu = PsuBase()
        not_implemented_methods = [
            psu.get_voltage,
            psu.get_current,
            psu.get_power,
            psu.get_powergood_status,
            psu.get_temperature,
            psu.get_temperature_high_threshold,
            psu.get_voltage_high_threshold,
            psu.get_voltage_low_threshold,
            psu.get_maximum_supplied_power,
            psu.get_psu_power_warning_suppress_threshold,
            psu.get_psu_power_critical_threshold,
            psu.get_input_voltage,
            psu.get_input_current]

        for method in not_implemented_methods:
            exception_raised = False
            try:
                method()
            except NotImplementedError:
                exception_raised = True

            assert exception_raised
