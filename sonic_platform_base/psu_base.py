#
# psu_base.py
#
# Abstract base class for implementing a platform-specific class with which
# to interact with a power supply unit (PSU) in SONiC
#

from . import device_base


class PsuBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a power supply unit
    """
    # Device type definition. Note, this is a constant.
    DEVICE_TYPE = "psu"

    # List of FanBase-derived objects representing all fans
    # available on the PSU
    _fan_list = None

    # List of ThermalBase-derived objects representing all thermals
    # available on the PSU. Put a class level _thermal_list here to 
    # avoid an exception when call get_num_thermals, get_all_thermals
    # and get_thermal if vendor does not call PsuBase.__init__ in concrete
    # PSU class
    _thermal_list = []

    # Status of Master LED
    psu_master_led_color = None

    def __init__(self):
        self._fan_list = []

        # List of ThermalBase-derived objects representing all thermals
        # available on the PSU
        self._thermal_list = []

        self.psu_master_led_color = self.STATUS_LED_COLOR_OFF

    def get_num_fans(self):
        """
        Retrieves the number of fan modules available on this PSU

        Returns:
            An integer, the number of fan modules available on this PSU
        """
        return len(self._fan_list)

    def get_all_fans(self):
        """
        Retrieves all fan modules available on this PSU

        Returns:
            A list of objects derived from FanBase representing all fan
            modules available on this PSU
        """
        return self._fan_list

    def get_fan(self, index):
        """
        Retrieves fan module represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the fan module to
            retrieve

        Returns:
            An object dervied from FanBase representing the specified fan
            module
        """
        fan = None

        try:
            fan = self._fan_list[index]
        except IndexError:
            sys.stderr.write("Fan index {} out of range (0-{})\n".format(
                             index, len(self._fan_list)-1))

        return fan

    def get_num_thermals(self):
        """
        Retrieves the number of thermals available on this PSU

        Returns:
            An integer, the number of thermals available on this PSU
        """
        return len(self._thermal_list)

    def get_all_thermals(self):
        """
        Retrieves all thermals available on this PSU

        Returns:
            A list of objects derived from ThermalBase representing all thermals
            available on this PSU
        """
        return self._thermal_list

    def get_thermal(self, index):
        """
        Retrieves thermal unit represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the thermal to
            retrieve

        Returns:
            An object dervied from ThermalBase representing the specified thermal
        """
        thermal = None

        try:
            thermal = self._thermal_list[index]
        except IndexError:
            sys.stderr.write("THERMAL index {} out of range (0-{})\n".format(
                             index, len(self._thermal_list)-1))

        return thermal

    def get_voltage(self):
        """
        Retrieves current PSU voltage output

        Returns:
            A float number, the output voltage in volts, 
            e.g. 12.1 
        """
        raise NotImplementedError

    def get_current(self):
        """
        Retrieves present electric current supplied by PSU

        Returns:
            A float number, the electric current in amperes, e.g 15.4
        """
        raise NotImplementedError

    def get_power(self):
        """
        Retrieves current energy supplied by PSU

        Returns:
            A float number, the power in watts, e.g. 302.6
        """
        raise NotImplementedError

    def get_powergood_status(self):
        """
        Retrieves the powergood status of PSU

        Returns:
            A boolean, True if PSU has stablized its output voltages and passed all
            its internal self-tests, False if not.
        """
        raise NotImplementedError

    def set_status_led(self, color):
        """
        Sets the state of the PSU status LED

        Args:
            color: A string representing the color with which to set the
                   PSU status LED

        Returns:
            bool: True if status LED state is set successfully, False if not
        """
        raise NotImplementedError

    def get_status_led(self):
        """
        Gets the state of the PSU status LED

        Returns:
            A string, one of the predefined STATUS_LED_COLOR_* strings above
        """
        raise NotImplementedError

    def get_temperature(self):
        """
        Retrieves current temperature reading from PSU

        Returns:
            A float number of current temperature in Celsius up to nearest thousandth
            of one degree Celsius, e.g. 30.125 
        """
        raise NotImplementedError

    def get_temperature_high_threshold(self):
        """
        Retrieves the high threshold temperature of PSU

        Returns:
            A float number, the high threshold temperature of PSU in Celsius
            up to nearest thousandth of one degree Celsius, e.g. 30.125
        """
        raise NotImplementedError

    def get_voltage_high_threshold(self):
        """
        Retrieves the high threshold PSU voltage output

        Returns:
            A float number, the high threshold output voltage in volts, 
            e.g. 12.1 
        """
        raise NotImplementedError

    def get_voltage_low_threshold(self):
        """
        Retrieves the low threshold PSU voltage output

        Returns:
            A float number, the low threshold output voltage in volts, 
            e.g. 12.1 
        """
        raise NotImplementedError

    def get_maximum_supplied_power(self):
        """
        Retrieves the maximum supplied power by PSU

        Returns:
            A float number, the maximum power output in Watts.
            e.g. 1200.1
        """
        raise NotImplementedError

    @classmethod
    def get_status_master_led(cls):
        """
        Gets the state of the Master status LED for a given device-type

        Returns:
            A string, one of the predefined STATUS_LED_COLOR_* strings.
        """
        return cls.psu_master_led_color

    @classmethod
    def set_status_master_led(cls, color):
        """
        Gets the state of the Master status LED for a given device-type

        Returns:
            bool: True if status LED state is set successfully, False if
                  not
        """
        cls.psu_master_led_color = color
        return True
