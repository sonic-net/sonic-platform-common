########################################################################
# DellEMC
#
# Module contains the base abstract class from which the form-factor
# implementations inherit
#
########################################################################

from abc import abstractmethod

class media_static_info:
    @abstractmethod
    def get_cable_length_detailed(self, eeprom):
        """
        Returns cable length in meters as float of 1DP.
        """
        pass

    @abstractmethod
    def get_link_length(self, eeprom):
        """
        Returns link length for separable mediain meters.
        """
        pass

    @abstractmethod
    def get_media_interface(self, eeprom):
        """
        Returns media interface as str.
        """
        pass

    @abstractmethod
    def get_cable_class(self, eeprom):
        """
        Returns a string of cable type. Ex: 'DAC'.
        """
        pass

    @abstractmethod
    def get_cable_breakout(self, eeprom):
        """
        Returns a string of breakout type. Ex: '1x4'.
        """
        pass

    @abstractmethod
    def get_display_name(self, eeprom):
        """
        Returns a string of display name. Ex: "QSFP+ 40GBASE-CR4-DAC-1.0M".
        See ext_media_common.build_media_display_name for rules
        """
        pass

    @abstractmethod
    def get_lane_count(self, eeprom):
        """
        Returns an int of lane count. Ex: 8.
        """
        pass

    @abstractmethod
    def get_host_electrical_lane_count(self, eeprom):
        """
        Returns an int of the electrical lane count. Ex: 8.
        This is the number of lanes mating with the host side
        """
        pass

    @abstractmethod
    def get_module_lane_count(self, eeprom):
        """
        Returns an int of the module lane count. Ex: 4.
        This is the number of lanes toward the outside/laser
        It can sometimes differ from the electrical lane count due to gearboxes etc
        """
        pass

    @abstractmethod
    def get_form_factor(self, eeprom):
        """
        Returns a string of form factor name. Ex: 'SFP28'.
        """
        pass

    @abstractmethod
    def get_connector_type(self, eeprom):
        """
        Returns a string of connector type. Ex: 'LC', 'RJ45'.
        """
        pass

    @abstractmethod
    def get_power_rating_max(self, eeprom):
        """
        Returns the maximum power that can be drawn by the module as float in Watts. Ex: '2.0W', '12.5W'.
        """
        pass

    @abstractmethod
    def get_vendor_name(self, eeprom):
        """
        Returns the vendor name as string.
        """
        pass

    @abstractmethod
    def get_vendor_part_number(self, eeprom):
        """
        Returns the vendor number as string.
        """
        pass

    @abstractmethod
    def get_vendor_serial_number(self, eeprom):
        """
        Returns the serial number as string.
        """
        pass

    @abstractmethod
    def get_vendor_oui(self, eeprom):
        """
        Returns the OUI as string.
        """
        pass

    @abstractmethod
    def get_vendor_revision(self, eeprom):
        """
        Returns the vendor revision as string.
        """
        pass

    @abstractmethod
    def get_vendor_date_code(self, eeprom):
        """
        Returns the date code as string.
        """
        pass

    @abstractmethod
    def get_special_fields(self, eeprom):
        """
        Returns a string of arbitrary special fields. Ex: 'BER:5e-10'.
        """
        pass
