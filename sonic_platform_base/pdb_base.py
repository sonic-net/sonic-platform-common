"""
    pdb_base.py

    Abstract base class for implementing a platform-specific class with which
    to interact with a power distribution board (PDB) in SONiC. PDB is used on
    direct-current platforms and replaces PSU. This class inherits from PsuBase
    to allow reuse of PSU daemon and CLI for a consistent power monitoring experience.
"""

from . import psu_base


class PdbBase(psu_base.PsuBase):
    """
    Abstract base class for interfacing with a power distribution board (PDB).
    Inherits from PsuBase so that PSU daemon and CLI can operate on PDB objects
    with a consistent user experience. PDB is generally not replaceable and has
    thermals but no fans.
    """
    # Device type definition. Note, this is a constant.
    DEVICE_TYPE = "pdb"

    def __init__(self):
        super(PdbBase, self).__init__()
        # PDB has no fans; _fan_list remains empty from parent.
        # _thermal_list is used for PDB thermals.

    def get_output_current(self):
        """
        Retrieves the output current reading.

        Returns:
            A float representing the output current in Amperes, or 'N/A' if not available.
        """
        raise NotImplementedError

    def get_output_power(self):
        """
        Retrieves the output power reading.

        Returns:
            A float representing the output power in Watts, or 'N/A' if not available.
        """
        raise NotImplementedError

    def get_output_voltage(self):
        """
        Retrieves the output voltage reading.

        Returns:
            A float representing the output voltage in Volts, or 'N/A' if not available.
        """
        raise NotImplementedError

    def get_input_power(self):
        """
        Retrieves the input power reading.

        Returns:
            A float representing the input power in Watts, or 'N/A' if not available.
        """
        raise NotImplementedError

    def get_voltage(self):
        """
        Retrieves the output voltage reading.

        Returns:
            A float representing the output voltage in Volts, or 'N/A' if not available.
        """
        return self.get_output_voltage()

    def get_current(self):
        """
        Retrieves the output current reading.

        Returns:
            A float representing the output current in Amperes, or 'N/A' if not available.
        """
        return self.get_output_current()

    def get_power(self):
        """
        Retrieves the output power reading.

        Returns:
            A float representing the output power in Watts, or 'N/A' if not available.
        """
        return self.get_output_power()
