"""
    cpo_optoe_base.py

    Platform-independent class with which to interact with a cpo module
    in SONiC
"""

from sfp_optoe_base import SfpOptoeBase
from sonic_xcvr.cpo_xcvr_api_factory import CpoXcvrApiFactory
import abc
from .fields import consts
import copy

class CpoOptoeBase(SfpOptoeBase):
    def __init__(self):
        SfpOptoeBase.__init__(self)
        self._oe_bank_id = -1
        self._oe_id = -1
        self._els_id = -1
        self._els_bank_id = -1
        """
        When a vendor instantiates the CpoOptoeBase class, if there are custom registers beyond the CmisMemMap,
        these custom register mappings must be initialized into the eeprom member variable. For example:
        self._vendor_sepcific_eeprom = XcvrEeprom(self.read_eeprom, self.write_eeprom, 
            BaillyCmisMemMap(CmisCodes, self._oe_bank, chassis.get_elsfp_base_page_by_id(els_id)))
        """ 
        self._vendor_specific_eeprom = None
        self._xcvr_api_factory = CpoXcvrApiFactory(self.read_oe_eeprom, self.write_oe_eeprom,
            self.read_els_eeprom, self.write_els_eeprom, self._oe_bank_id, self._els_bank_id, "separate")

    def get_oe_bank_id(self):
        return self._oe_bank_id
    def get_oe_id(self):
        return self._oe_id
    def get_els_bank_id(self):
        return self._els_bank_id
    def get_els_id(self):
        return self._els_id

    def get_elsfp_cmis_rev(self):
        '''
        This function returns the CMIS version the esfp module complies to
        '''
        # Give priority to reading from the vendor's dedicated EEPROM
        if self._vendor_specific_eeprom:
            try:
                major = self._vendor_specific_eeprom.read(consts.ELSFP_CMIS_MAJOR_REVISION)
                minor = self._vendor_specific_eeprom.read(consts.ELSFP_CMIS_MINOR_REVISION)
                if major is not None and minor is not None:
                    return f"{major}.{minor}"
            except (AttributeError, TypeError, IOError):
                pass
        # If no custom EEPROM from vendor, use generic API to retrieve data.
        api = self.get_xcvr_api()
        if api:
            try:
                return api.get_elsfp_cmis_rev()
            except Exception:
                return None
    
        return None
    
    def get_elsfp_vendor_rev(self):
        '''
        This function returns the revision level for part number provided by vendor
        '''
        # Give priority to reading from the vendor's dedicated EEPROM
        if self._vendor_specific_eeprom:
            try:
                return self._strip_str(self._vendor_specific_eeprom.read(consts.ELSFP_VENDOR_REV_FIELD))
            except (AttributeError, TypeError, IOError):
                pass
        # If no custom EEPROM from vendor, use generic API to retrieve data.
        api = self.get_xcvr_api()
        if api:
            try:
                return api.get_elsfp_vendor_rev()
            except Exception:
                return None
    
        return None
    
    def get_elsfp_transceiver_info(self):
        
        # Give priority to reading from the vendor's dedicated EEPROM
        if self._vendor_specific_eeprom:
            admin_info = self._vendor_specific_eeprom.read(consts.ELSFP_ADMIN_INFO_FIELD)
            if admin_info is None:
                return None

            ext_id = admin_info[consts.ELSFP_EXT_ID_FIELD]
            power_class = ext_id[consts.ELSFP_POWER_CLASS_FIELD]
            max_power = ext_id[consts.ELSFP_MAX_POWER_FIELD]
            xcvr_info = copy.deepcopy(self._get_xcvr_info_default_dict())
            xcvr_info.update({
                "type": admin_info[consts.ELSFP_ID_FIELD],
                "type_abbrv_name": admin_info[consts.ELSFP_ID_ABBRV_FIELD],
                "serial": self._strip_str(admin_info[consts.ELSFP_VENDOR_SERIAL_NO_FIELD]),
                "manufacturer": self._strip_str(admin_info[consts.ELSFP_VENDOR_NAME_FIELD]),
                "model": self._strip_str(admin_info[consts.ELSFP_VENDOR_PART_NO_FIELD]),
                "connector": admin_info[consts.ELSFP_CONNECTOR_FIELD],
                "ext_identifier": "%s (%sW Max)" % (power_class, max_power),
                "cable_length": float(admin_info[consts.ELSFP_LENGTH_ASSEMBLY_FIELD]),
                "vendor_date": self._strip_str(admin_info[consts.ELSFP_VENDOR_DATE_FIELD]),
                "vendor_oui": admin_info[consts.ELSFP_VENDOR_OUI_FIELD],
                "vendor_rev": self._strip_str(self.get_elsfp_vendor_rev()),
                "cmis_rev": self.get_elsfp_cmis_rev(),
            })
            apsel_dict = self.get_active_apsel_hostlane()
            for lane in range(1, self.NUM_CHANNELS + 1):
                xcvr_info["%s%d" % ("active_apsel_hostlane", lane)] = \
                apsel_dict["%s%d" % (consts.ACTIVE_APSEL_HOSTLANE, lane)]
            if None in xcvr_info.values():
                return None
            else:
                return xcvr_info
        # If no custom EEPROM from vendor, use generic API to retrieve data.
        api = self.get_xcvr_api()
        if api:
            try:
                return api.get_elsfp_vendor_rev()
            except Exception:
                return None
    
        return None

    @abc.abstractmethod
    def get_oe_eeprom_path(self, oe):
        """
        Get oe cmis eeprom file path
        """
        ...

    @abc.abstractmethod
    def read_oe_eeprom(self, offset, num_bytes):
        """
        Read oe eeprom
        """
        ...

    @abc.abstractmethod
    def write_oe_eeprom(self, offset, num_bytes, write_buffer):
        """
        Write oe eeprom
        """
        ...

    @abc.abstractmethod
    def get_els_eeprom_path(self, els_id):
        """
        Get els cmis eeprom file path
        """
        ...

    @abc.abstractmethod
    def read_els_eeprom(self, offset, num_byte):
        """
        Read els eeprom
        """
        ...

    @abc.abstractmethod
    def write_els_eeprom(self, offset, num_bytes, write_buffer):
        """
        Write els eeprom
        """
        ...

    @abc.abstractmethod
    def get_els_presence(self, els_id):
        """
        Get els presence state
        """
        ...

    @abc.abstractmethod
    def check_fiber_dirty(self):
        """
        Check whether the fiber is dirty. True:check ok; False: check failed
        """
        ...

    @abc.abstractmethod
    def check_calibration(self):
        """
        Check whether the calibration such as oe power sufficient. True:check ok; False: check failed
        """
        ...

    @abc.abstractmethod
    def is_els_power_sufficient(self):
        """
        Check whether els power sufficient.
        """
        ...

    @abc.abstractmethod
    def is_calibration_checked(self):
        """
        Check whether the calibration such as oe power sufficient detection​ has been completed.
        """
        ...

    @abc.abstractmethod
    def is_fiber_checked(self):
        """
        Check whether the fiber detection​ has been completed.
        """
        ...

    @abc.abstractmethod
    def is_els_tx_on(self):
        """
        Check the ELS TX​ status to see if it is emitting light normally.
        """
        ...

    @abc.abstractmethod
    def is_els_tx_enabled(self):
        """
        Check whether the ELS TX enable​ has been set.
        """
        ...