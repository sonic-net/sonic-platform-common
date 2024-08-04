"""
    chassis_base.py

    Base class for implementing a platform-specific class with which
    to interact with a chassis device in SONiC.
"""

import sys
from . import device_base
from . import sfp_base

class ChassisBase(device_base.DeviceBase):
    """
    Base class for interfacing with a platform chassis
    """
    # Device type definition. Note, this is a constant.
    DEVICE_TYPE = "chassis"

    # Possible reboot causes
    REBOOT_CAUSE_POWER_LOSS = "Power Loss"
    REBOOT_CAUSE_THERMAL_OVERLOAD_CPU = "Thermal Overload: CPU"
    REBOOT_CAUSE_THERMAL_OVERLOAD_ASIC = "Thermal Overload: ASIC"
    REBOOT_CAUSE_THERMAL_OVERLOAD_OTHER = "Thermal Overload: Other"
    REBOOT_CAUSE_INSUFFICIENT_FAN_SPEED = "Insufficient Fan Speed"
    REBOOT_CAUSE_WATCHDOG = "Watchdog"
    REBOOT_CAUSE_HARDWARE_OTHER = "Hardware - Other"
    REBOOT_CAUSE_HARDWARE_BIOS = "BIOS"
    REBOOT_CAUSE_HARDWARE_CPU = "CPU"
    REBOOT_CAUSE_HARDWARE_BUTTON = "Push button"
    REBOOT_CAUSE_HARDWARE_RESET_FROM_ASIC = "Reset from ASIC"
    REBOOT_CAUSE_NON_HARDWARE = "Non-Hardware"

    def __init__(self):
        # List of ComponentBase-derived objects representing all components
        # available on the chassis
        self._component_list = []

        # List of ModuleBase-derived objects representing all modules
        # available on the chassis (for use with modular chassis)
        self._module_list = []

        # List of FanBase-derived objects representing all fans
        # available on the chassis
        self._fan_list = []

        # List of FanDrawerBase-derived objects representing all fan drawers
        # available on the chassis
        self._fan_drawer_list = []

        # List of PsuBase-derived objects representing all power supply units
        # available on the chassis
        self._psu_list = []

        # List of ThermalBase-derived objects representing all thermals
        # available on the chassis
        self._thermal_list = []
        self._voltage_sensor_list = []
        self._current_sensor_list = []

        # List of SfpBase-derived objects representing all sfps
        # available on the chassis
        self._sfp_list = []

        # Object derived from WatchdogBase for interacting with hardware watchdog
        self._watchdog = None

        # Object derived from eeprom_tlvinfo.TlvInfoDecoder indicating the eeprom on the chassis
        self._eeprom = None

        # System status LED
        self._status_led = None


    def get_base_mac(self):
        """
        Retrieves the base MAC address for the chassis

        Returns:
            A string containing the MAC address in the format
            'XX:XX:XX:XX:XX:XX'
        """
        raise NotImplementedError

    def get_system_eeprom_info(self):
        """
        Retrieves the full content of system EEPROM information for the chassis

        Returns:
            A dictionary where keys are the type code defined in
            OCP ONIE TlvInfo EEPROM format and values are their corresponding
            values.
            Ex. { '0x21':'AG9064', '0x22':'V1.0', '0x23':'AG9064-0109867821',
                  '0x24':'001c0f000fcd0a', '0x25':'02/03/2018 16:22:00',
                  '0x26':'01', '0x27':'REV01', '0x28':'AG9064-C2358-16G'}
        """
        raise NotImplementedError

    def get_reboot_cause(self):
        """
        Retrieves the cause of the previous reboot

        Returns:
            A tuple (string, string) where the first element is a string
            containing the cause of the previous reboot. This string must be
            one of the predefined strings in this class. If the first string
            is "REBOOT_CAUSE_HARDWARE_OTHER", the second string can be used
            to pass a description of the reboot cause.
        """
        raise NotImplementedError

    def get_supervisor_slot(self):
        """
        Retrieves the physical-slot of the supervisor-module in the modular
        chassis. On the supervisor or line-card modules, it will return the
        physical-slot of the supervisor-module.

        On the fixed-platforms, the API can be ignored.

        Users of the API can catch the exception and return a default
        ModuleBase.MODULE_INVALID_SLOT and bypass code for fixed-platforms.

        Returns:
            An integer, the vendor specific physical slot identifier of the
            supervisor module in the modular-chassis.
        """
        return NotImplementedError

    def get_my_slot(self):
        """
        Retrieves the physical-slot of this module in the modular chassis.
        On the supervisor, it will return the physical-slot of the supervisor
        module. On the linecard, it will return the physical-slot of the
        linecard module where this instance of SONiC is running.

        On the fixed-platforms, the API can be ignored.

        Users of the API can catch the exception and return a default
        ModuleBase.MODULE_INVALID_SLOT and bypass code for fixed-platforms.

        Returns:
            An integer, the vendor specific physical slot identifier of this
            module in the modular-chassis.
        """
        return NotImplementedError

    def is_modular_chassis(self):
        """
        Retrieves whether the sonic instance is part of modular chassis

        Returns:
            A bool value, should return False by default or for fixed-platforms.
            Should return True for supervisor-cards, line-cards etc running as part
            of modular-chassis.
            For SmartSwitch platforms this should return True even if they are
            fixed-platforms, as they are treated like a modular chassis as the
            DPU cards are treated like line-cards of a modular-chassis.
        """
        return False

    def init_midplane_switch(self):
        """
        Initializes the midplane functionality of the modular chassis. For
        example, any validation of midplane, populating any lookup tables etc
        can be done here. The expectation is that the required kernel modules,
        ip-address assignment etc are done before the pmon, database dockers
        are up.

        Returns:
            A bool value, should return True if the midplane initialized
            successfully.
        """
        return NotImplementedError

    ##############################################
    # Component methods
    ##############################################

    def get_num_components(self):
        """
        Retrieves the number of components available on this chassis

        Returns:
            An integer, the number of components available on this chassis
        """
        return len(self._component_list)

    def get_all_components(self):
        """
        Retrieves all components available on this chassis

        Returns:
            A list of objects derived from ComponentBase representing all components
            available on this chassis
        """
        return self._component_list

    def get_component(self, index):
        """
        Retrieves component represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the component to retrieve

        Returns:
            An object dervied from ComponentBase representing the specified component
        """
        component = None

        try:
            component = self._component_list[index]
        except IndexError:
            sys.stderr.write("Component index {} out of range (0-{})\n".format(
                             index, len(self._component_list)-1))

        return component

    ##############################################
    # Module methods
    ##############################################

    def get_num_modules(self):
        """
        Retrieves the number of modules available on this chassis
        On a SmarSwitch chassis this will be the number of DPUs.

        Returns:
            An integer, the number of modules available on this chassis.
            On a SmartSwitch this will be the number of DPUs
        """
        return len(self._module_list)

    def get_all_modules(self):
        """
        Retrieves all modules available on this chassis. On a SmartSwitch
        chassis this will return all the DPUs.

        Returns:
            A list of objects derived from ModuleBase representing all
            modules available on this chassis. On a SmartSwitch this 
            will be a list of DPU objects.
        """
        return self._module_list

    def get_module(self, index):
        """
        Retrieves module represented by (0-based) index <index>
        On a SmartSwitch index:0 is not used, index:1 will fetch
        DPU0 and so on

        Args:
            index: An integer, the index (0-based) of the module to
            retrieve

        Returns:
            An object derived from ModuleBase representing the specified
            module
        """
        module = None

        try:
            module = self._module_list[index]
        except IndexError:
            sys.stderr.write("Module index {} out of range (0-{})\n".format(
                             index, len(self._module_list)-1))

        return module

    def get_module_index(self, module_name):
        """
        Retrieves module index from the module name

        Args:
            module_name: A string, prefixed by SUPERVISOR, LINE-CARD or FABRIC-CARD
            Ex. SUPERVISOR0, LINE-CARD1, FABRIC-CARD5
            SmartSwitch Example: DPU0, DPU1, DPU2 ... DPUX

        Returns:
            An integer, the index of the ModuleBase object in the module_list
        """
        raise NotImplementedError

    ##############################################
    # SmartSwitch methods
    ##############################################

    def get_dpu_id(self, name):
        """
        Retrieves the DPU ID for the given dpu-module name.
        Returns None for non-smartswitch chassis.

        Returns:
            An integer, indicating the DPU ID Ex: name:DPU0 return value 0,
            name:DPU1 return value 1, name:DPUX return value X
        """
        raise NotImplementedError

    def is_smartswitch(self):
        """
        Retrieves whether the sonic instance is part of smartswitch

        Returns:
            Returns:True for SmartSwitch and False for other platforms
        """
        return False 

    def get_module_dpu_data_port(self, index):
        """
        Retrieves the DPU data port NPU-DPU association represented for
        the DPU index. Platforms that need to overwrite the platform.json
        file will use this API. This is valid only on the Switch and not on DPUs

        Args:
        index: An integer, the index of the module to retrieve

        Returns:
            A dictionary giving the NPU-DPU port association:
            Ex: When queried for DPU0 it will return
            {
                "interface": {"Ethernet224": "Ethernet0"}
            }
            where "Ethernet192: is the NPU port and the string
            right of ":" (Ethernet0) is the DPU port
        """
        raise NotImplementedError

    ##############################################
    # Fan methods
    ##############################################

    def get_num_fans(self):
        """
        Retrieves the number of fans available on this chassis

        Returns:
            An integer, the number of fan modules available on this chassis
        """
        return len(self._fan_list)

    def get_all_fans(self):
        """
        Retrieves all fan modules available on this chassis

        Returns:
            A list of objects derived from FanBase representing all fan
            modules available on this chassis
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

    def get_num_fan_drawers(self):
        """
        Retrieves the number of fan drawers available on this chassis

        Returns:
            An integer, the number of fan drawers available on this chassis
        """
        return len(self._fan_drawer_list)

    def get_all_fan_drawers(self):
        """
        Retrieves all fan drawers available on this chassis

        Returns:
            A list of objects derived from FanDrawerBase representing all fan
            drawers available on this chassis
        """
        return self._fan_drawer_list

    def get_fan_drawer(self, index):
        """
        Retrieves fan drawers represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the fan drawer to
            retrieve

        Returns:
            An object dervied from FanDrawerBase representing the specified fan
            drawer
        """
        fan_drawer = None

        try:
            fan_drawer = self._fan_drawer_list[index]
        except IndexError:
            sys.stderr.write("Fan drawer index {} out of range (0-{})\n".format(
                             index, len(self._fan_drawer_list)-1))

        return fan_drawer

    ##############################################
    # PSU methods
    ##############################################

    def get_num_psus(self):
        """
        Retrieves the number of power supply units available on this chassis

        Returns:
            An integer, the number of power supply units available on this
            chassis
        """
        return len(self._psu_list)

    def get_all_psus(self):
        """
        Retrieves all power supply units available on this chassis

        Returns:
            A list of objects derived from PsuBase representing all power
            supply units available on this chassis
        """
        return self._psu_list

    def get_psu(self, index):
        """
        Retrieves power supply unit represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the power supply unit to
            retrieve

        Returns:
            An object dervied from PsuBase representing the specified power
            supply unit
        """
        psu = None

        try:
            psu = self._psu_list[index]
        except IndexError:
            sys.stderr.write("PSU index {} out of range (0-{})\n".format(
                             index, len(self._psu_list)-1))

        return psu

    ##############################################
    # THERMAL methods
    ##############################################

    def get_num_thermals(self):
        """
        Retrieves the number of thermals available on this chassis

        Returns:
            An integer, the number of thermals available on this chassis
        """
        return len(self._thermal_list)

    def get_all_thermals(self):
        """
        Retrieves all thermals available on this chassis

        Returns:
            A list of objects derived from ThermalBase representing all thermals
            available on this chassis
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

    def get_thermal_manager(self):
        """
        Retrieves thermal manager class on this chassis
        :return: A class derived from ThermalManagerBase representing the
        specified thermal manager. ThermalManagerBase is returned as default
        """
        raise NotImplementedError

    ##############################################
    # Voltage Sensor Methods
    ##############################################

    def get_num_voltage_sensors(self):
        """
        Retrieves the number of voltage sensors available on this chassis

        Returns:
            An integer, the number of voltage sensors available on this chassis
        """
        return len(self._voltage_sensor_list)

    def get_all_voltage_sensors(self):
        """
        Retrieves all voltage sensors available on this chassis

        Returns:
            A list of objects derived from VoltageSensorBase representing all voltage 
            sensors available on this chassis
        """
        return self._voltage_sensor_list

    def get_voltage_sensor(self, index):
        """
        Retrieves voltage sensor unit represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the voltage sensor to
            retrieve

        Returns:
            An object derived from VoltageSensorBase representing the specified voltage sensor
        """
        voltage_sensor = None

        try:
            voltage_sensor = self._voltage_sensor_list[index]
        except IndexError:
            sys.stderr.write("Voltage sensor index {} out of range (0-{})\n".format(
                             index, len(self._voltage_sensor_list)-1))

        return voltage_sensor

    ##############################################
    # Current Sensor Methods
    ##############################################

    def get_num_current_sensors(self):
        """
        Retrieves the number of current sensors available on this chassis

        Returns:
            An integer, the number of current sensors available on this chassis
        """
        return len(self._current_sensor_list)

    def get_all_current_sensors(self):
        """
        Retrieves all current sensors available on this chassis

        Returns:
            A list of objects derived from CurrentSensorBase representing all current
            sensors available on this chassis
        """
        return self._current_sensor_list

    def get_current_sensor(self, index):
        """
        Retrieves current sensor object represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the current sensor to
            retrieve

        Returns:
            An object derived from CurrentSensorBase representing the specified current 
            sensor
        """
        current_sensor = None

        try:
            current_sensor = self._current_sensor_list[index]
        except IndexError:
            sys.stderr.write("Current sensor index {} out of range (0-{})\n".format(
                             index, len(self._current_sensor_list)-1))

        return current_sensor

    ##############################################
    # SFP methods
    ##############################################

    def get_num_sfps(self):
        """
        Retrieves the number of sfps available on this chassis

        Returns:
            An integer, the number of sfps available on this chassis
        """
        return len(self._sfp_list)

    def get_all_sfps(self):
        """
        Retrieves all sfps available on this chassis

        Returns:
            A list of objects derived from SfpBase representing all sfps
            available on this chassis
        """
        return [ sfp for sfp in self._sfp_list if sfp is not None ]

    def get_sfp(self, index):
        """
        Retrieves sfp corresponding to physical port <index>

        Args:
            index: An integer (>=0), the index of the sfp to retrieve.
                   The index should correspond to the physical port in a chassis.
                   For example:-
                   1 for Ethernet0, 2 for Ethernet4 and so on for one platform.
                   0 for Ethernet0, 1 for Ethernet4 and so on for another platform.

        Returns:
            An object dervied from SfpBase representing the specified sfp
        """
        sfp = None

        try:
            sfp = self._sfp_list[index]
        except IndexError:
            sys.stderr.write("SFP index {} out of range (0-{})\n".format(
                             index, len(self._sfp_list)-1))

        return sfp


    def get_port_or_cage_type(self, index):
        """
        Retrieves sfp port or cage type corresponding to physical port <index>

        Args:
            index: An integer (>=0), the index of the sfp to retrieve.
                   The index should correspond to the physical port in a chassis.
                   For example:-
                   1 for Ethernet0, 2 for Ethernet4 and so on for one platform.
                   0 for Ethernet0, 1 for Ethernet4 and so on for another platform.

        Returns:
            The masks of all types of port or cage that can be supported on the port
            Types are defined in sfp_base.py
            Eg.
                Both SFP and SFP+ are supported on the port, the return value should be 0x0a
                which is 0x02 | 0x08
        """
        raise NotImplementedError

    ##############################################
    # System LED methods
    ##############################################

    def set_status_led(self, color):
        """
        Sets the state of the system LED

        Args:
            color: A string representing the color with which to set the
                   system LED

        Returns:
            bool: True if system LED state is set successfully, False if not
        """
        raise NotImplementedError

    def get_status_led(self):
        """
        Gets the state of the system LED

        Returns:
            A string, one of the valid LED color strings which could be vendor
            specified.
        """
        raise NotImplementedError

    ##############################################
    # System LED methods
    ##############################################

    def set_uid_led(self, color):
        """
        Sets the state of the system UID LED

        Args:
            color: A string representing the color with which to set the
                   system UID LED

        Returns:
            bool: True if system LED state is set successfully, False if not
        """
        raise NotImplementedError

    def get_uid_led(self):
        """
        Gets the state of the system UID LED

        Returns:
            A string, one of the valid LED color strings which could be vendor
            specified.
        """
        raise NotImplementedError

    ##############################################
    # Other methods
    ##############################################

    def get_watchdog(self):
        """
        Retreives hardware watchdog device on this chassis

        Returns:
            An object derived from WatchdogBase representing the hardware
            watchdog device
        """
        return self._watchdog

    def get_eeprom(self):
        """
        Retreives eeprom device on this chassis

        Returns:
            An object derived from WatchdogBase representing the hardware
            eeprom device
        """
        return self._eeprom

    def get_change_event(self, timeout=0):
        """
        Returns a nested dictionary containing all devices which have
        experienced a change at chassis level

        Args:
            timeout: Timeout in milliseconds (optional). If timeout == 0,
                this method will block until a change is detected.

        Returns:
            (bool, dict):
                - True if call successful, False if not;
                - A nested dictionary where key is a device type,
                  value is a dictionary with key:value pairs in the format of
                  {'device_id':'device_event'},
                  where device_id is the device ID for this device and
                        device_event,
                             status='1' represents device inserted,
                             status='0' represents device removed.
                  Ex. {'fan':{'0':'0', '2':'1'}, 'sfp':{'11':'0'}}
                      indicates that fan 0 has been removed, fan 2
                      has been inserted and sfp 11 has been removed.
                  Specifically for SFP event, besides SFP plug in and plug out,
                  there are some other error event could be raised from SFP, when
                  these error happened, SFP eeprom will not be avalaible, XCVRD shall
                  stop to read eeprom before SFP recovered from error status.
                      status='2' I2C bus stuck,
                      status='3' Bad eeprom,
                      status='4' Unsupported cable,
                      status='5' High Temperature,
                      status='6' Bad cable.
        """
        raise NotImplementedError
