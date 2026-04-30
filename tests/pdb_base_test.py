"""
Unit tests for PdbBase class.

Validates the PDB base object API: default is_replaceable is False,
and platform-specific methods raise NotImplementedError. Ensures
PDB can be used where PSU is expected (voltage/current/power delegation).
"""

from unittest.mock import patch

from sonic_platform_base.pdb_base import PdbBase


class _PdbForDelegation(PdbBase):
    """Concrete PDB with output readings for delegation tests."""

    def get_output_voltage(self):
        return 48.0

    def get_output_current(self):
        return 2.25

    def get_output_power(self):
        return 108.0


class TestPdbBase:

    def test_pdb_base_device_type(self):
        """PDB device type constant."""
        assert PdbBase.DEVICE_TYPE == "pdb"

    def test_pdb_base_not_implemented_methods(self):
        """Platform must implement these; base raises NotImplementedError."""
        pdb = PdbBase()
        not_implemented_methods = [
            pdb.get_name,
            pdb.get_presence,
            pdb.get_status,
            pdb.get_model,
            pdb.get_serial,
            pdb.get_revision,
            pdb.get_temperature,
            pdb.get_output_current,
            pdb.get_output_power,
            pdb.get_output_voltage,
            pdb.get_input_current,
            pdb.get_input_power,
            pdb.get_input_voltage,
            pdb.get_maximum_supplied_power,
        ]
        for method in not_implemented_methods:
            exception_raised = False
            try:
                method()
            except NotImplementedError:
                exception_raised = True
            assert exception_raised, "Expected NotImplementedError from {}".format(method.__name__)

    def test_pdb_base_thermal_inherited(self):
        """PDB inherits thermal list from PsuBase; empty by default."""
        pdb = PdbBase()
        assert pdb.get_num_thermals() == 0
        assert pdb.get_all_thermals() == []
        assert pdb.get_thermal(0) is None

    def test_pdb_get_voltage_current_power_delegate(self):
        """get_voltage/get_current/get_power forward to output* methods."""
        pdb = _PdbForDelegation()
        assert pdb.get_voltage() == 48.0
        assert pdb.get_current() == 2.25
        assert pdb.get_power() == 108.0

    def test_pdb_get_voltage_current_power_delegate_on_base_instance(self):
        """
        Exercise delegation return paths on a plain PdbBase instance by
        stubbing get_output_* (the abstract implementations raise otherwise).
        """
        pdb = PdbBase()
        with patch.object(pdb, "get_output_voltage", return_value=12.5):
            assert pdb.get_voltage() == 12.5
        with patch.object(pdb, "get_output_current", return_value=3.0):
            assert pdb.get_current() == 3.0
        with patch.object(pdb, "get_output_power", return_value=37.5):
            assert pdb.get_power() == 37.5
