"""
    module_base.py

    Base class for implementing a platform-specific class with which
    to interact with a module (as used in a modular chassis) SONiC.
"""

import sys
import os
import fcntl
from . import device_base
import json
import threading
import contextlib
import shutil
import subprocess
import os

# PCI state database constants
PCIE_DETACH_INFO_TABLE = "PCIE_DETACH_INFO"
PCIE_OPERATION_DETACHING = "detaching"
PCIE_OPERATION_ATTACHING = "attaching"

class ModuleBase(device_base.DeviceBase):
    """
    Base class for interfacing with a module (supervisor module, line card
    module, etc. (applicable for a modular chassis)
    """
    # Device type definition. Note, this is a constant.
    DEVICE_TYPE = "module"
    PCI_OPERATION_LOCK_FILE_PATH = "/var/lock/{}_pci.lock"
    SENSORD_OPERATION_LOCK_FILE_PATH = "/var/lock/sensord.lock"

    # Possible card types for modular chassis
    MODULE_TYPE_SUPERVISOR = "SUPERVISOR"
    MODULE_TYPE_LINE    = "LINE-CARD"
    MODULE_TYPE_FABRIC  = "FABRIC-CARD"
    MODULE_TYPE_DPU  = "DPU"

    # Possible card status for modular chassis
    # Module state is Empty if no module is inserted in the slot
    MODULE_STATUS_EMPTY   = "Empty"
    # Module state if Offline. This is also the admin-down state.
    MODULE_STATUS_OFFLINE = "Offline"
    # Module state if power down was triggered. Example, this could be a
    # policy action from sensors reaching a critical state triggering the
    # module to be powered-down.
    MODULE_STATUS_POWERED_DOWN = "PoweredDown"
    # Module state is Present when it is powered up, but not fully functional.
    MODULE_STATUS_PRESENT = "Present"
    # Module state is Present when it is powered up, but entered a fault state.
    # Module is not able to go Online.
    MODULE_STATUS_FAULT   = "Fault"
    # Module state is Online when fully operational
    MODULE_STATUS_ONLINE  = "Online"

    # Invalid slot for modular chassis
    MODULE_INVALID_SLOT = -1

    # Possible reboot types for modular chassis
    # Module reboot type to reboot entire card
    MODULE_REBOOT_DEFAULT = "Default"
    # Module reboot type to reboot CPU complex
    MODULE_REBOOT_CPU_COMPLEX = "CPU"
    # Module reboot type to reboot FPGA complex
    MODULE_REBOOT_FPGA_COMPLEX = "FPGA"
    # Module reboot type to reboot DPU
    MODULE_REBOOT_DPU = "DPU"
    # Module reboot type to reboot SMART SWITCH
    MODULE_REBOOT_SMARTSWITCH = "SMARTSWITCH"

    def __init__(self):
        # List of ComponentBase-derived objects representing all components
        # available on the module
        self._component_list = []

        # List of FanBase-derived objects representing all fans
        # available on the module
        self._fan_list = []

        # List of PsuBase-derived objects representing all power supply units
        # available on the module
        self._psu_list = []

        # List of ThermalBase-derived objects representing all thermals
        # available on the module
        self._thermal_list = []
        self._voltage_sensor_list = []
        self._current_sensor_list = []
        self.state_db_connector = None
        self.pci_bus_info = None

        # List of SfpBase-derived objects representing all sfps
        # available on the module
        self._sfp_list = []

        # List of ASIC-derived objects representing all ASICs
        # visibile in PCI domain on the module
        self._asic_list = []

        # Flag to indicate if the module is running on the host/container
        self.is_host = self._is_host()
    
    @contextlib.contextmanager
    def _file_operation_lock(self, lock_file_path):
        """Common file-based lock for operations using flock"""
        with open(lock_file_path, 'w') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    @contextlib.contextmanager
    def _pci_operation_lock(self):
        """File-based lock for PCI operations using flock"""
        lock_file_path = self.PCI_OPERATION_LOCK_FILE_PATH.format(self.get_name())
        with self._file_operation_lock(lock_file_path):
            yield

    @contextlib.contextmanager
    def _sensord_operation_lock(self):
        """File-based lock for sensord operations using flock"""
        lock_file_path = self.SENSORD_OPERATION_LOCK_FILE_PATH
        with self._file_operation_lock(lock_file_path):
            yield

    def get_base_mac(self):
        """
        Retrieves the base MAC address for the module

        Returns:
            A string containing the MAC address in the format
            'XX:XX:XX:XX:XX:XX'
        """
        raise NotImplementedError

    def get_system_eeprom_info(self):
        """
        Retrieves the full content of system EEPROM information for the module

        Returns:
            A dictionary where keys are the type code defined in
            OCP ONIE TlvInfo EEPROM format and values are their corresponding
            values.
            Ex. { '0x21': 'AG9064', '0x22': 'V1.0', '0x23': 'AG9064-0109867821',
                  '0x24': '001c0f000fcd0a', '0x25': '02/03/2018 16:22:00',
                  '0x26': '01', '0x27': 'REV01', '0x28': 'AG9064-C2358-16G'}
        """
        raise NotImplementedError

    def get_name(self):
        """
        Retrieves the name of the module prefixed by SUPERVISOR, LINE-CARD,
        FABRIC-CARD, DPU0, DPUX

        Returns:
            A string, the module name prefixed by one of MODULE_TYPE_SUPERVISOR,
            MODULE_TYPE_LINE or MODULE_TYPE_FABRIC or MODULE_TYPE_DPU and followed
            by a 0-based index.

            Ex. A Chassis having 1 supervisor, 4 line-cards and 6 fabric-cards
            can provide names SUPERVISOR0, LINE-CARD0 to LINE-CARD3,
            FABRIC-CARD0 to FABRIC-CARD5.
            A SmartSwitch having 4 DPUs names DPU0 to DPU3
        """
        raise NotImplementedError

    def get_description(self):
        """
        Retrieves the platform vendor's product description of the module

        Returns:
            A string, providing the vendor's product description of the module.
        """
        raise NotImplementedError

    def get_slot(self):
        """
        Retrieves the platform vendor's slot number of the module

        Returns:
            An integer, indicating the slot number in the chassis
        """
        raise NotImplementedError

    def get_type(self):
        """
        Retrieves the type of the module.

        Returns:
            A string, the module-type from one of the predefined types:
            MODULE_TYPE_SUPERVISOR, MODULE_TYPE_LINE or MODULE_TYPE_FABRIC
            or MODULE_TYPE_DPU
        """
        raise NotImplementedError

    def get_oper_status(self):
        """
        Retrieves the operational status of the module

        Returns:
            A string, the operational status of the module from one of the
            predefined status values: MODULE_STATUS_EMPTY, MODULE_STATUS_OFFLINE,
            MODULE_STATUS_FAULT, MODULE_STATUS_PRESENT or MODULE_STATUS_ONLINE
        """
        raise NotImplementedError

    def reboot(self, reboot_type):
        """
        Request to reboot the module

        Args:
            reboot_type: A string, the type of reboot requested from one of the
            predefined reboot types: MODULE_REBOOT_DEFAULT, MODULE_REBOOT_CPU_COMPLEX,
            MODULE_REBOOT_FPGA_COMPLEX, MODULE_REBOOT_DPU or MODULE_REBOOT_SMARTSWITCH

            MODULE_REBOOT_DPU is only applicable for smartswitch chassis.

            MODULE_REBOOT_SMARTSWITCH is only applicable for smartswitch chassis.

        Returns:
            bool: True if the request has been issued successfully, False if not
        """
        raise NotImplementedError

    def set_admin_state(self, up):
        """
        Request to keep the card in administratively up/down state.
        The down state will power down the module and the status should show
        MODULE_STATUS_OFFLINE.
        The up state will take the module to MODULE_STATUS_FAULT or
        MODULE_STATUS_ONLINE states.

        Args:
            up: A boolean, True to set the admin-state to UP. False to set the
            admin-state to DOWN.

        Returns:
            bool: True if the request has been issued successfully, False if not
        """
        raise NotImplementedError

    def get_maximum_consumed_power(self):
        """
        Retrives the maximum power drawn by this module

        Returns:
            A float, with value of the maximum consumable power of the
            module.
        """
        raise NotImplementedError

    ##############################################
    # SmartSwitch methods
    ##############################################

    def get_dpu_id(self):
        """
        Retrieves the DPU ID. Returns None for non-smartswitch chassis.

        Returns:
            An integer, indicating the DPU ID. DPU0 returns 0, DPUX returns X
            DPU ID can be greater than or equal to 0.
        """
        raise NotImplementedError

    def get_reboot_cause(self):
        """
        Retrieves the cause of the previous reboot of the DPU module

        Returns:
            A tuple (string, string) where the first element is a string
            containing the cause of the previous reboot. This string must
            be one of the predefined strings in this class. If the first
            string is "REBOOT_CAUSE_HARDWARE_OTHER", the second string can be
            used to pass a description of the reboot cause.

        """
        raise NotImplementedError

    def get_state_info(self):
        """
        Retrieves the dpu state object having the detailed dpu state progression.
        Fetched from ChassisStateDB.

        Returns:
            An object instance of the DPU_STATE (see DB schema)
            Returns None on switch module

        Sample Output:
        {
            'dpu_control_plane': {
                'state': 'UP',
                'time': '20240626 21:13:25',
                'reason': 'All containers are up and running, host-ethlink-status: Uplink1/1 is UP'
            },
            'dpu_data_plane': {
                'state': 'UP',
                'time': '20240626 21:13:25',
                'reason': 'DPU container named polaris is running, pciemgrd running : OK'
            },
            'dpu_midplane_link': {
                'state': 'UP',
                'time': '20240626 21:13:25',
                'reason': 'INTERNAL-MGMT : admin state - UP, oper_state - UP, status - OK'
            }
        }
        """
        raise NotImplementedError

    def get_pci_bus_info(self):
        """
        Retrieves the bus information.

        Returns:
            Returns the PCI bus information in list of BDF format like "[DDDD:]BB:SS:F"
        """
        raise NotImplementedError

    def handle_pci_removal(self):
        """
        Handles PCI device removal by updating state database and detaching device.

        Returns:
            bool: True if operation was successful, False otherwise
        """
        try:
            bus_info_list = self.get_pci_bus_info()
            with self._pci_operation_lock():
                for bus in bus_info_list:
                    self.pci_entry_state_db(bus, PCIE_OPERATION_DETACHING)
                return self.pci_detach()
        except Exception as e:
            sys.stderr.write("Failed to handle PCI removal: {}\n".format(str(e)))
            return False

    def pci_entry_state_db(self, pcie_string, operation):
        """
        Generic function to handle PCI device state database entry.

        Args:
            pcie_string (str): The PCI bus string to be written to state database
            operation (str): The operation being performed ("detaching" or "attaching")

        Raises:
            RuntimeError: If state database connection fails
        """
        try:
            # Do not use import if swsscommon is not needed
            import swsscommon
            PCIE_DETACH_INFO_TABLE_KEY = PCIE_DETACH_INFO_TABLE+"|"+pcie_string
            if not self.state_db_connector:
                self.state_db_connector = swsscommon.swsscommon.DBConnector("STATE_DB", 0)
            if operation == PCIE_OPERATION_ATTACHING:
                self.state_db_connector.delete(PCIE_DETACH_INFO_TABLE_KEY)
                return
            self.state_db_connector.hset(PCIE_DETACH_INFO_TABLE_KEY, "bus_info", pcie_string)
            self.state_db_connector.hset(PCIE_DETACH_INFO_TABLE_KEY, "dpu_state", operation)
        except Exception as e:
            sys.stderr.write("Failed to write pcie bus info to state database: {}\n".format(str(e)))

    def handle_pci_rescan(self):
        """
        Handles PCI device rescan by updating state database and reattaching device.

        Returns:
            bool: True if operation was successful, False otherwise
        """
        try:
            bus_info_list = self.get_pci_bus_info()
            with self._pci_operation_lock():
                return_value = self.pci_reattach()
                for bus in bus_info_list:
                    self.pci_entry_state_db(bus, PCIE_OPERATION_ATTACHING)
                return return_value
        except Exception as e:
            sys.stderr.write("Failed to handle PCI rescan: {}\n".format(str(e)))
            return False

    def pci_detach(self):
        """
        Detaches the PCI device.

        Returns: True once the PCI is successfully detached.
        Returns False, if PCI detachment fails or specified device is not found.
        """
        raise NotImplementedError

    def pci_reattach(self):
        """
        Rescans and reconnects the PCI device.

        Returns: True once the PCI is successfully reconnected.
        Returns False, if PCI rescan fails or specified device is not found.
        """
        raise NotImplementedError

    ##############################################
    # Component methods
    ##############################################

    def get_num_components(self):
        """
        Retrieves the number of components available on this module

        Returns:
            An integer, the number of components available on this module
        """
        return len(self._component_list)

    def get_all_components(self):
        """
        Retrieves all components available on this module

        Returns:
            A list of objects derived from ComponentBase representing all components
            available on this module
        """
        return self._component_list

    def get_component(self, index):
        """
        Retrieves component represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the component to retrieve

        Returns:
            An object derived from ComponentBase representing the specified component
        """
        component = None

        try:
            component = self._component_list[index]
        except IndexError:
            sys.stderr.write("Component index {} out of range (0-{})\n".format(
                             index, len(self._component_list)-1))

        return component

    ##############################################
    # Fan module methods
    ##############################################

    def get_num_fans(self):
        """
        Retrieves the number of fan modules available on this module

        Returns:
            An integer, the number of fan modules available on this module
        """
        return len(self._fan_list)

    def get_all_fans(self):
        """
        Retrieves all fan modules available on this module

        Returns:
            A list of objects derived from FanBase representing all fan
            modules available on this module
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

    ##############################################
    # PSU module methods
    ##############################################

    def get_num_psus(self):
        """
        Retrieves the number of power supply units available on this module

        Returns:
            An integer, the number of power supply units available on this
            module
        """
        return len(self._psu_list)

    def get_all_psus(self):
        """
        Retrieves all power supply units available on this module

        Returns:
            A list of objects derived from PsuBase representing all power
            supply units available on this module
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
        Retrieves the number of thermals available on this module

        Returns:
            An integer, the number of thermals available on this module
        """
        return len(self._thermal_list)

    def get_all_thermals(self):
        """
        Retrieves all thermals available on this module

        Returns:
            A list of objects derived from ThermalBase representing all thermals
            available on this module
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

    ##############################################
    # Voltage Sensor methods
    ##############################################

    def get_num_voltage_sensors(self):
        """
        Retrieves the number of voltage sensors available on this module

        Returns:
            An integer, the number of voltage sensors available on this module
        """
        return len(self._voltage_sensor_list)

    def get_all_voltage_sensors(self):
        """
        Retrieves all voltage sensors available on this module

        Returns:
            A list of objects derived from VoltageSensorBase representing all voltage
            sensors available on this module
        """
        return self._voltage_sensor_list

    def get_voltage_sensor(self, index):
        """
        Retrieves voltage sensor unit represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the voltage sensor to
            retrieve

        Returns:
            An object derived from VoltageSensorBase representing the specified voltage
            sensor
        """
        voltage_sensor = None

        try:
            voltage_sensor = self._voltage_sensor_list[index]
        except IndexError:
            sys.stderr.write("Voltage sensor index {} out of range (0-{})\n".format(
                             index, len(self._voltage_sensor_list)-1))

        return voltage_sensor

    def _is_host(self):
        docker_env_file = '/.dockerenv'
        return not os.path.exists(docker_env_file)

    ##############################################
    # Current sensor methods
    ##############################################

    def get_num_current_sensors(self):
        """
        Retrieves the number of current sensors available on this module

        Returns:
            An integer, the number of current sensors available on this module
        """
        return len(self._current_sensor_list)

    def get_all_current_sensors(self):
        """
        Retrieves all current sensors available on this module

        Returns:
            A list of objects derived from CurrentSensorBase representing all current
            sensors available on this module
        """
        return self._current_sensor_list

    def get_current_sensor(self, index):
        """
        Retrieves current sensor object represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the current sensor to
            retrieve

        Returns:
            An object derived from CurrentSensorBase representing the specified current_sensor
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
        Retrieves the number of sfps available on this module

        Returns:
            An integer, the number of sfps available on this module
        """
        return len(self._sfp_list)

    def get_all_sfps(self):
        """
        Retrieves all sfps available on this module

        Returns:
            A list of objects derived from PsuBase representing all sfps
            available on this module
        """
        return self._sfp_list

    def get_sfp(self, index):
        """
        Retrieves sfp represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the sfp to retrieve

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

    def get_change_event(self, timeout=0):
        """
        Returns a nested dictionary containing all devices which have
        experienced a change in this module

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
        """
        raise NotImplementedError

    ##############################################
    # Midplane methods for modular chassis
    ##############################################
    def get_midplane_ip(self):
        """
        Retrieves the midplane IP-address of the module in a modular chassis
        When called from the Supervisor, the module could represent the
        line-card and return the midplane IP-address of the line-card.
        When called from the line-card, the module will represent the
        Supervisor and return its midplane IP-address.

        When called from the SmartSwitch returns the midplane IP-address of
        the DPU module.

        Returns:
            A string, the IP-address of the module reachable over the midplane

        """
        raise NotImplementedError

    def is_midplane_reachable(self):
        """
        Retrieves the reachability status of the module from the Supervisor or
        of the Supervisor from the module via the midplane of the modular chassis

        Returns:
            A bool value, should return True if module is reachable via midplane
        """
        return NotImplementedError

    ##############################################
    # ASIC methods
    ##############################################
    def get_all_asics(self):
        """
        Retrieves the list of all ASICs on the module that are visible in PCI domain.
        When called from the Supervisor of modular system, the module could be
        fabric card, and the function returns all fabric ASICs on this module that
        appear in PCI domain of the Supervisor.

        Returns:
            A list of ASICs. Index of an ASIC in the list is the index of the ASIC
            on the module. Index is 0 based.

            An item in the list is a tuple that includes:
               - ASIC instance number (indexed globally across all modules of
                 the chassis). This number is used to find settings for the ASIC
                 from /usr/share/sonic/device/platform/hwsku/asic_instance_number/.
               - ASIC PCI address: It is used by syncd to attach the correct ASIC.

            For example: [('4', '0000:05:00.0'), ('5', '0000:07:00.0')]
               In this example, from the output, we know the module has 2 ASICs.
               Item ('4', '0000:05:00.0') describes information about the first ASIC
               in the module.
               '4' means it is asic4 in the chassis. Settings for this ASIC is at
               /usr/share/sonic/device/platform/hwsku/4/.
               And '0000:05:00.0' is its PCI address.
        """
        return self._asic_list

    def handle_sensor_removal(self):
        """
        Handles sensor removal by copying ignore configuration file from platform folder
        to sensors.d directory and restarting sensord if the file exists.

        Returns:
            bool: True if operation was successful, False otherwise
        """
        try:
            module_name = self.get_name()
            source_file = f"/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_{module_name}.conf"
            target_file = f"/etc/sensors.d/ignore_sensors_{module_name}.conf"
            file_exists_command = ['test', '-f', source_file]
            copy_command = ['cp', source_file, target_file]
            container_command = ['docker', 'exec', 'pmon']
            restart_command = ['service', 'sensord', 'restart']


            if self.is_host:
                file_exists_command = container_command + file_exists_command
                copy_command = container_command + copy_command
                restart_command = container_command + restart_command

            # If source file does not exist, we dont need to copy it and restart sensord
            if subprocess.call(file_exists_command, stdout=subprocess.DEVNULL) != 0:
                return True

            subprocess.call(copy_command, stdout=subprocess.DEVNULL)

            # Restart sensord with lock
            with self._sensord_operation_lock():
                subprocess.call(restart_command, stdout=subprocess.DEVNULL)

            return True
        except Exception as e:
            sys.stderr.write("Failed to handle sensor removal: {}\n".format(str(e)))
            return False

    def handle_sensor_addition(self):
        """
        Handles sensor addition by removing the ignore configuration file from
        sensors.d directory and restarting sensord.

        Returns:
            bool: True if operation was successful, False otherwise
        """
        try:
            module_name = self.get_name()
            target_file = f"/etc/sensors.d/ignore_sensors_{module_name}.conf"
            remove_command = ['rm', target_file]
            restart_command = ['service', 'sensord', 'restart']
            container_command = ['docker', 'exec', 'pmon']
            file_exists_command = ['test', '-f', target_file]

            if self.is_host:
                file_exists_command = container_command + file_exists_command
                remove_command = container_command + remove_command
                restart_command = container_command + restart_command

            # If target file does not exist, we dont need to remove it and restart sensord
            if subprocess.call(file_exists_command, stdout=subprocess.DEVNULL) != 0:
                return True

            # Remove the file
            subprocess.call(remove_command, stdout=subprocess.DEVNULL)

            # Restart sensord with lock
            with self._sensord_operation_lock():
                subprocess.call(restart_command, stdout=subprocess.DEVNULL)

            return True
        except Exception as e:
            sys.stderr.write("Failed to handle sensor addition: {}\n".format(str(e)))
            return False

    def module_pre_shutdown(self):
        """
        Handles module pre-shutdown operations by detaching PCI devices and handling sensor removal.
        This function should be called before shutting down a module.

        Returns:
            bool: True if all operations were successful, False otherwise
        """
        sensor_result = self.handle_sensor_removal()
        pci_result = self.handle_pci_removal()
        return pci_result and sensor_result

    def module_post_startup(self):
        """
        Handles module post-startup operations by reattaching PCI devices and handling sensor addition.
        This function should be called after a module has started up.

        Returns:
            bool: True if all operations were successful, False otherwise
        """
        pci_result = self.handle_pci_rescan()
        sensor_result = self.handle_sensor_addition()
        return pci_result and sensor_result
