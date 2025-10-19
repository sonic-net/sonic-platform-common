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
import time
from datetime import datetime, timezone


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
    TRANSITION_OPERATION_LOCK_FILE_PATH = "/var/lock/{}_transition.lock"
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
        self.pci_bus_info = None

        # List of SfpBase-derived objects representing all sfps
        # available on the module
        self._sfp_list = []

        # List of ASIC-derived objects representing all ASICs
        # visibile in PCI domain on the module
        self._asic_list = []

        # Initialize state database connector
        self._state_db_connector = self._initialize_state_db_connector()

    def _initialize_state_db_connector(self):
        """Initialize a STATE_DB connector using swsscommon only."""
        from swsscommon.swsscommon import SonicV2Connector  # type: ignore
        db = SonicV2Connector()
        try:
            db.connect(db.STATE_DB)
        except Exception as e:
            # Some environments autoconnect; preserve tolerant behavior
            sys.stderr.write(f"Failed to connect to STATE_DB, continuing: {e}\n")
            return None
        return db

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
    def _transition_operation_lock(self):
        """File-based lock for module state transition operations using flock"""
        lock_file_path = self.TRANSITION_OPERATION_LOCK_FILE_PATH.format(self.get_name())
        with self._file_operation_lock(lock_file_path):
            yield

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

    def set_admin_state_using_graceful_handler(self, up):
        """
        Request to set the module's administrative state with graceful shutdown coordination.

        This function is specifically designed for SmartSwitch platforms and should be
        called by chassisd to ensure proper graceful shutdown coordination with external
        agents (e.g., gNOI clients) before setting admin state to DOWN.

        For non-SmartSwitch platforms or direct platform API usage, use set_admin_state()
        instead.

        Args:
            up (bool): True for admin UP, False for admin DOWN.

        Returns:
            bool: True if the request was successful, False otherwise.
        """
        if up:
            # Admin UP: Clear any transition state and proceed with admin state change
            module_name = self.get_name()
            admin_state_success = self.set_admin_state(True)
            
            # Clear transition state after admin state operation completes
            if not self.clear_module_state_transition(self._state_db_connector, module_name):
                context = "after successful admin state change" if admin_state_success else "after failed admin state change"
                sys.stderr.write(f"Failed to clear transition state for module {module_name} {context}.\n")
            
            return admin_state_success

        # Admin DOWN: Perform graceful shutdown first
        module_name = self.get_name()
        graceful_success = self.graceful_shutdown_handler()

        if not graceful_success:
            # Clear transition state on graceful shutdown failure
            if not self.clear_module_state_transition(self._state_db_connector, module_name):
                sys.stderr.write(f"Failed to clear transition state for module {module_name} after graceful shutdown failure.\n")
            sys.stderr.write(f"Aborting admin-down for module {module_name} due to graceful shutdown failure.\n")

        # Proceed with admin state change
        admin_state_success = self.set_admin_state(False)

        # Always clear transition state after admin state operation completes
        if not self.clear_module_state_transition(self._state_db_connector, module_name):
            context = "after successful admin state change" if admin_state_success else "after failed admin state change"
            sys.stderr.write(f"Failed to clear transition state for module {module_name} {context}.\n")

        return admin_state_success

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
        """
        try:
            db = self._state_db_connector
            PCIE_DETACH_INFO_TABLE_KEY = PCIE_DETACH_INFO_TABLE + "|" + pcie_string

            if operation == PCIE_OPERATION_ATTACHING:
                # Delete the entire entry for attaching operation
                if hasattr(db, 'delete'):
                    db.delete(db.STATE_DB, PCIE_DETACH_INFO_TABLE_KEY, "bus_info")
                    db.delete(db.STATE_DB, PCIE_DETACH_INFO_TABLE_KEY, "dpu_state")
                return
            # Set the PCI detach info for detaching operation
            db.set(db.STATE_DB, PCIE_DETACH_INFO_TABLE_KEY, {
                "bus_info": pcie_string,
                "dpu_state": operation
            })
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

    # ###########################################
    # Smartswitch DPU graceful shutdown helpers
    # Transition timeout defaults (seconds)
    # These are used unless overridden by /usr/share/sonic/platform/platform.json
    # with optional keys: dpu_startup_timeout, dpu_shutdown_timeout, dpu_reboot_timeout
    # ###########################################
    _TRANSITION_TIMEOUT_DEFAULTS = {
        "startup": 300,   # 5 minutes
        "shutdown": 180,  # 3 minutes
        "reboot": 240,    # 4 minutes
    }
    # class-level cache to avoid multiple reads per process
    _TRANSITION_TIMEOUTS_CACHE = None



    def _transition_key(self) -> str:
        """Return the STATE_DB key for this module's transition state."""
        # Use get_name() to avoid relying on an attribute that may not exist.
        return f"CHASSIS_MODULE_TABLE|{self.get_name()}"

    def _load_transition_timeouts(self) -> dict:
        """
        Load per-operation timeouts from /usr/share/sonic/platform/platform.json if present,
        otherwise fall back to _TRANSITION_TIMEOUT_DEFAULTS.

        Recognized keys in platform.json:
        - dpu_startup_timeout
        - dpu_shutdown_timeout
        - dpu_reboot_timeout
        """
        if ModuleBase._TRANSITION_TIMEOUTS_CACHE is not None:
            return ModuleBase._TRANSITION_TIMEOUTS_CACHE

        timeouts = dict(self._TRANSITION_TIMEOUT_DEFAULTS)
        try:
            # NOTE: On PMON/containers this path is bind-mounted; use it directly.
            path = "/usr/share/sonic/platform/platform.json"
            with open(path, "r") as f:
                data = json.load(f) or {}

            if "dpu_startup_timeout" in data:
                timeouts["startup"] = int(data["dpu_startup_timeout"])
            if "dpu_shutdown_timeout" in data:
                timeouts["shutdown"] = int(data["dpu_shutdown_timeout"])
            if "dpu_reboot_timeout" in data:
                timeouts["reboot"] = int(data["dpu_reboot_timeout"])
        except Exception as e:
            # On any error, just use defaults
            sys.stderr.write(f"Failed to load transition timeouts from platform.json, using defaults: {e}\n")

        ModuleBase._TRANSITION_TIMEOUTS_CACHE = timeouts
        return ModuleBase._TRANSITION_TIMEOUTS_CACHE

    def graceful_shutdown_handler(self):
        """
        SmartSwitch graceful shutdown gate for DPU modules with race condition protection.

        Coordinates shutdown with external agents (e.g., gNOI clients) by:
        1. Atomically setting CHASSIS_MODULE_TABLE|<MODULE_NAME> transition state to "shutdown"
        2. Waiting for external completion signal or module offline status
        3. Cleaning up transition state on completion or timeout

        Race Condition Handling:
        - File-based locking ensures only one agent can modify transition state at a time
        - Multiple concurrent calls are serialized through set_module_state_transition()
        - Timed-out transitions are automatically cleared and new ones can proceed
        - Timeout based on database-recorded start time, not individual agent wait time

        Exit Conditions:
        - External agent sets state_transition_in_progress="False" (graceful completion)
        - Module operational status becomes "Offline" (platform-detected shutdown)
        - Timeout after configured period (default: 180s from platform.json dpu_shutdown_timeout)

        Returns:
            bool: True if graceful shutdown completes, False on timeout.

        Note:
            Called by platform set_admin_state() when transitioning DPU to admin DOWN.
            Implements SONiC SmartSwitch graceful shutdown HLD requirements.
        """
        db = self._state_db_connector

        module_name = self.get_name()

        # Atomically set transition state (handles race conditions with locking)
        # Note: This is safe to call even if caller already set transition state,
        # as the function is idempotent and will not overwrite existing valid transitions
        self.set_module_state_transition(db, module_name, "shutdown")

        # Determine shutdown timeout (do NOT use get_reboot_timeout())
        timeouts = self._load_transition_timeouts()
        shutdown_timeout = int(timeouts.get("shutdown", self._TRANSITION_TIMEOUT_DEFAULTS["shutdown"]))

        interval = 2
        waited = 0

        key = self._transition_key()
        while waited < shutdown_timeout:
            # Get current transition state
            result = db.get_all(db.STATE_DB, key) or {}
            entry = {k.decode('utf-8') if isinstance(k, bytes) else k: 
                    v.decode('utf-8') if isinstance(v, bytes) else v 
                    for k, v in result.items()}

            # (a) Someone else completed the graceful phase
            if entry.get("state_transition_in_progress", "False") == "False":
                return True

            # (b) Platform reports oper Offline — complete & clear transition
            try:
                oper = self.get_oper_status()
                if oper and str(oper).lower() == "offline":
                    if not self.clear_module_state_transition(db, module_name):
                        sys.stderr.write(f"Graceful shutdown for module {module_name} failed to clear transition state.\n")
                    return True
            except Exception as e:
                # Don't fail the graceful gate on a transient platform call error
                sys.stderr.write("Graceful shutdown for module {} failed to get oper status: {}\n".format(module_name, str(e)))

            # Check if the transition has timed out based on the recorded start time
            # This handles cases where multiple agents might be waiting
            if self.is_module_state_transition_timed_out(db, module_name, shutdown_timeout):
                # Clear only if we can confirm it's actually timed out
                if not self.clear_module_state_transition(db, module_name):
                    sys.stderr.write(f"Graceful shutdown for module {module_name} timed out and failed to clear transition state.\n")
                else:
                    sys.stderr.write("Graceful shutdown for module {} timed out.\n".format(module_name))
                return False

            time.sleep(interval)
            waited += interval

        # Final timeout check before clearing - use recorded start time, not our local wait time
        if self.is_module_state_transition_timed_out(db, module_name, shutdown_timeout):
            if not self.clear_module_state_transition(db, module_name):
                sys.stderr.write(f"Graceful shutdown for module {module_name} timed out and failed to clear transition state.\n")
            else:
                sys.stderr.write("Graceful shutdown for module {} timed out.\n".format(module_name))

        return False

    # ############################################################
    # Centralized APIs for CHASSIS_MODULE_TABLE transition flags
    # ############################################################

    def set_module_state_transition(self, db, module_name: str, transition_type: str):
        """
        Atomically mark the given module as being in a state transition if not already in progress.

        This function is thread-safe and prevents race conditions when multiple agents
        (chassis_modules.py, chassisd, reboot) attempt to set module state transitions
        simultaneously by using a file-based lock.

        Args:
            db: Connected SonicV2Connector
            module_name: e.g., 'DPU0'
            transition_type: 'shutdown' | 'startup' | 'reboot'

        Returns:
            bool: True if transition was successfully set, False if already in progress
        """
        with self._transition_operation_lock():
            key = f"CHASSIS_MODULE_TABLE|{module_name}"
            # Check if a transition is already in progress
            result = db.get_all(db.STATE_DB, key) or {}
            existing_entry = {k.decode('utf-8') if isinstance(k, bytes) else k: 
                            v.decode('utf-8') if isinstance(v, bytes) else v 
                            for k, v in result.items()}
            if existing_entry.get("state_transition_in_progress", "False").lower() in ("true", "1", "yes", "on"):
                # Already in progress - check if it's timed out
                timeout_seconds = int(self._load_transition_timeouts().get(
                    existing_entry.get("transition_type", "shutdown"),
                    self._TRANSITION_TIMEOUT_DEFAULTS.get("shutdown", 180)
                ))

                if not self.is_module_state_transition_timed_out(db, module_name, timeout_seconds):
                    # Still valid, don't overwrite
                    return False

                # Timed out, clear and proceed with new transition
                if not self.clear_module_state_transition(db, module_name):
                    sys.stderr.write(f"Failed to clear timed-out transition for module {module_name} before setting new one.\n")
                    return False
            # Set new transition atomically
            db.set(db.STATE_DB, key, {
                "state_transition_in_progress": "True",
                "transition_type": transition_type,
                "transition_start_time": datetime.now(timezone.utc).isoformat(),
            })
            return True

    def clear_module_state_transition(self, db, module_name: str):
        """
        Clear transition flags for the given module after a transition completes.
        Field-scoped update to avoid clobbering concurrent writers.

        This function is thread-safe and uses the same lock as set_module_state_transition
        to prevent race conditions.

        Args:
            db: Connected SonicV2Connector.
            module_name: The name of the module (e.g., 'DPU0').

        Returns:
            bool: True if the transition state was cleared successfully, False otherwise.
        """
        with self._transition_operation_lock():
            key = f"CHASSIS_MODULE_TABLE|{module_name}"
            try:
                # Mark not in-progress and clear type (prevents stale 'startup' blocks)
                db.set(db.STATE_DB, key, {
                    "state_transition_in_progress": "False",
                    "transition_type": ""
                })
                # Remove the start timestamp (avoid stale value lingering)
                if hasattr(db, 'delete'):
                    db.delete(db.STATE_DB, key, "transition_start_time")
                return True
            except Exception as e:
                sys.stderr.write(f"Failed to clear module state transition for {module_name}: {e}\n")
                return False

    def get_module_state_transition(self, db, module_name: str) -> dict:
        """
        Return the transition entry for a given module from STATE_DB.

        Note: This is a read-only operation and doesn't require locking.

        Returns:
            dict with keys: state_transition_in_progress, transition_type,
            transition_start_time (if present).
        """
        key = f"CHASSIS_MODULE_TABLE|{module_name}"
        result = db.get_all(db.STATE_DB, key) or {}
        return {k.decode('utf-8') if isinstance(k, bytes) else k: 
               v.decode('utf-8') if isinstance(v, bytes) else v 
               for k, v in result.items()}

    def is_module_state_transition_timed_out(self, db, module_name: str, timeout_seconds: int) -> bool:
        """
        Check whether the state transition for the given module has exceeded timeout.

        Note: This is a read-only operation and doesn't require locking.

        Args:
            db: Connected SonicV2Connector
            module_name: e.g., 'DPU0'
            timeout_seconds: max allowed seconds for the transition

        Returns:
            True if transition exceeded timeout, False otherwise.
        """
        entry = self.get_module_state_transition(db, module_name)

        # Missing entry means no active transition recorded; allow new operation to proceed.
        if not entry:
            return True

        # Only consider timeout if a transition is actually in progress
        inprog = str(entry.get("state_transition_in_progress", "")).lower() in ("1", "true", "yes", "on")
        if not inprog:
            return True

        start_str = entry.get("transition_start_time")
        if not start_str:
            # If no start time, assume it's not timed out to be safe
            return False

        # Parse ISO format datetime with timezone
        try:
            t0 = datetime.fromisoformat(start_str)
        except Exception:
            # Bad format → fail-safe to timed out
            return True

        if t0.tzinfo is None:
            # If timezone-naive, assume UTC
            t0 = t0.replace(tzinfo=timezone.utc)

        age = (datetime.now(timezone.utc) - t0).total_seconds()
        return age > timeout_seconds

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

            # If source file does not exist, we dont need to copy it and restart sensord
            if not os.path.exists(source_file):
                return True

            shutil.copy2(source_file, target_file)

            # Restart sensord with lock
            with self._sensord_operation_lock():
                os.system("service sensord restart")

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

            # If target file does not exist, we dont need to remove it and restart sensord
            if not os.path.exists(target_file):
                return True

            # Remove the file
            os.remove(target_file)

            # Restart sensord with lock
            with self._sensord_operation_lock():
                os.system("service sensord restart")

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
