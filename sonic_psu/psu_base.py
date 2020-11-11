#
# psu_base.py
#
# Abstract base class for implementing platform-specific
#  PSU control functionality for SONiC
#

try:
    import abc
except ImportError as e:
    raise ImportError (str(e) + " - required module not found")

class PsuBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_num_psus(self):
        """
        Retrieves the number of PSUs supported on the device

        :return: An integer, the number of PSUs supported on the device
        """
        return 0

    @abc.abstractmethod
    def get_psu_status(self, index):
        """
        Retrieves the operational status of power supply unit (PSU) defined
                by index 1-based <index>

        :param index: An integer, 1-based index of the PSU of which to query status
        :return: Boolean,
            - True if PSU is operating properly: PSU is inserted and powered in the device
            - False if PSU is faulty: PSU is inserted in the device but not powered
        """
        return False

    @abc.abstractmethod
    def get_psu_presence(self, index):
        """
        Retrieves the presence status of power supply unit (PSU) defined
                by 1-based index <index>

        :param index: An integer, 1-based index of the PSU of which to query status
        :return: Boolean, True if PSU is plugged, False if not
        """
        return False

    def get_model(self, idx):
        """
        Retrieves the model number/name of a power supply unit (PSU) defined
                by 1-based index <idx>
        :param idx: An integer, 1-based index of the PSU of which to query model number
        :return: String, denoting model number/name
        """
        return ""

    def get_mfr_id(self, idx):
        """
        Retrieves the manufacturing id of a power supply unit (PSU) defined
                by 1-based index <idx>
        :param idx: An integer, 1-based index of the PSU of which to query mfr id
        :return: String, denoting manufacturing id
        """
        return ""

    def get_serial(self, idx):
        """
        Retrieves the serial number of a power supply unit (PSU) defined
                by 1-based index <idx>
        :param idx: An integer, 1-based index of the PSU of which to query serial number
        :return: String, denoting serial number of the PSU unit
        """
        return ""

    def get_direction(self, idx):
        """
        Retrieves the airflow direction of a power supply unit (PSU) defined
                by 1-based index <idx>
        :param idx: An integer, 1-based index of the PSU of which to query airflow direction
        :return: String, denoting the airflow direction
        """
        return ""

    def get_output_voltage(self, idx):
        """
        Retrieves the ouput volatage in milli volts of a power supply unit (PSU) defined
                by 1-based index <idx>
        :param idx: An integer, 1-based index of the PSU of which to query o/p volatge
        :return: A float, value of o/p voltage in Volts if PSU is good, else zero
        """
        return 0.0

    def get_output_current(self, idx):
        """
        Retrieves the output current in milli amperes of a power supply unit (PSU) defined
                by 1-based index <idx>
        :param idx: An integer, 1-based index of the PSU of which to query o/p current
        :return: A float, value of o/p current in Amps if PSU is good, else zero
        """
        return 0.0

    def get_output_power(self, idx):
        """
        Retrieves the output power in micro watts of a power supply unit (PSU) defined
                by 1-based index <idx>
        :param idx: An integer, 1-based index of the PSU of which to query o/p power
        :return: A float, value of o/p power in Watts if PSU is good, else zero
        """
        return 0.0

    def get_fan_rpm(self, idx, fan_idx):
        """
        Retrieves the speed of fan, in rpm, denoted by 1-based <fan_idx> of a power 
                supply unit (PSU) defined by 1-based index <idx>
        :param idx: An integer, 1-based index of the PSU of which to query fan speed
        :param fan_idx: An integer, 1-based index of the PSU-fan of which to query speed
        :return: An integer, value of PSU-fan speed in rpm if PSU-fan is good, else zero
        """
        return 0
