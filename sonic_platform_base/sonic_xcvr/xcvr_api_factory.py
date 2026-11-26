"""
    xcvr_api_factory.py

    Factory class responsible for instantiating the appropriate XcvrApi
    implementation for a xcvr module in SONiC
"""
import logging
import re
from fnmatch import fnmatchcase
from pathlib import Path

import yaml
from .xcvr_eeprom import XcvrEeprom
from .eeprom_rw import ModuleEepromLowerMemoryInfo
# TODO: remove the following imports
from .codes.public.cmis import CmisCodes
from .api.public.cmis import CmisApi
from .api.public.c_cmis import CCmisApi
from .mem_maps.public.cmis import CmisMemMap
from .mem_maps.public.cmis.c_cmis import CCmisMemMap

from .codes.credo.aec_800g import CredoAec800gCodes
from .api.credo.aec_800g import CredoAec800gApi
from .mem_maps.credo.aec_800g import CredoAec800gMemMap

from .api.arista.cmis_enhanced_lpo import CmisEnhancedLpoApi
from .mem_maps.arista.cmis_enhanced_lpo import CmisEnhancedLpoMemMap

from .api.pinewave.cmis_module_precoding import PinewaveCmisApi
from .mem_maps.pinewave.cmis_module_precoding import PinewaveCmisMemMap

from .api.innolight.fr_800g import CmisFr800gApi
from .api.hisense.aoc_2x100g import CmisAocSingleBankApi

from .api.amphenol.backplane import AmphBackplaneImpl
from .mem_maps.amphenol.backplane import AmphBackplaneMemMap
from .codes.amphenol.backplane import AmphBackplaneCodes

from .codes.public.sff8436 import Sff8436Codes
from .api.public.sff8436 import Sff8436Api
from .mem_maps.public.sff8436 import Sff8436MemMap

from .codes.public.sff8636 import Sff8636Codes
from .api.public.sff8636 import Sff8636Api
from .mem_maps.public.sff8636 import Sff8636MemMap

from .codes.public.sff8472 import Sff8472Codes
from .api.public.sff8472 import Sff8472Api
from .mem_maps.public.sff8472 import Sff8472MemMap

CREDO_800G_AEC_VENDOR_PN_LIST = ["CAC81X321M2MC1MS", "CAC815321M2MC1MS", "CAC82X321M2MC1MS"]
ARISTA_ENHANCED_LPO_PN_LIST = ["LPO-800G-2DR4"]
PINEWAVE_MODULE_PRECODING_PN_LIST = ["T-RH8ENH-NMT"]
HISENSE_2X100G_VENDOR_PN = r"DEF8504-2C\d{2}-MB3$"

CMIS_FR800G_CONFIG_FILE = Path(__file__).with_name("cmis_fr800g.yaml")

class XcvrApiFactory(object):
    def __init__(self, reader, writer, cmis_firmware_config_path_cb=None):
        self.reader = reader
        self.writer = writer
        self.lower_memory_info = ModuleEepromLowerMemoryInfo(self.reader)
        self._cmis_firmware_config_path_cb = cmis_firmware_config_path_cb

    @staticmethod
    def _matches_cmis_firmware_config(config_file, vendor_name, vendor_pn):
        try:
            with config_file.open() as stream:
                modules = yaml.safe_load(stream)
            if not isinstance(modules, dict):
                raise ValueError("Expected a vendor-to-PN-list mapping")
            for vendor_pattern, part_numbers in modules.items():
                if (not isinstance(vendor_pattern, str) or not isinstance(part_numbers, list) or
                        not all(isinstance(pn, str) for pn in part_numbers)):
                    raise ValueError("Expected vendor patterns mapped to lists of part numbers")
            return any(fnmatchcase(vendor_name, pattern) and vendor_pn in part_numbers
                       for pattern, part_numbers in modules.items())
        except (OSError, yaml.YAMLError, ValueError) as error:
            logging.getLogger(__name__).warning(
                "Unable to read CMIS firmware compatibility list %s; "
                "trying remaining rules: %s", config_file, error)
            return False

    def _is_cmis_fr800g_module(self, vendor_name, vendor_pn):
        if self._matches_cmis_firmware_config(
                CMIS_FR800G_CONFIG_FILE, vendor_name, vendor_pn):
            return True

        # A common file without this model must not hide platform additions.
        if self._cmis_firmware_config_path_cb is not None:
            try:
                config_file = self._cmis_firmware_config_path_cb()
                if config_file is not None:
                    return self._matches_cmis_firmware_config(
                        Path(config_file), vendor_name, vendor_pn)
            except Exception as error:
                logging.getLogger(__name__).warning(
                    "Unable to resolve platform CMIS firmware compatibility list; "
                    "using default API: %s", error)
        return False

    def _create_cmis_api(self, bank=0):
        api = None
        vendor_name = self.lower_memory_info.get_vendor_name()
        vendor_pn = self.lower_memory_info.get_vendor_part_num()
        if not isinstance(vendor_name, str) or not isinstance(vendor_pn, str):
            return None

        if vendor_name == 'Credo' and vendor_pn in CREDO_800G_AEC_VENDOR_PN_LIST:
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, CredoAec800gMemMap(CredoAec800gCodes, bank=bank))
            api = CredoAec800gApi(xcvr_eeprom, init_cdb_fw_handler=True)
        elif self._is_cmis_fr800g_module(vendor_name, vendor_pn):
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, CmisMemMap(CmisCodes, bank=bank))
            api = CmisFr800gApi(xcvr_eeprom, init_cdb_fw_handler=True)
        elif vendor_name == 'Hisense' and vendor_pn is not None and re.match(HISENSE_2X100G_VENDOR_PN, vendor_pn):
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, CmisMemMap(CmisCodes, bank=bank))
            api = CmisAocSingleBankApi(xcvr_eeprom, init_cdb_fw_handler=True)
        elif vendor_pn in ARISTA_ENHANCED_LPO_PN_LIST:
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, CmisEnhancedLpoMemMap(CmisCodes, bank=bank))
            api = CmisEnhancedLpoApi(xcvr_eeprom, init_cdb_fw_handler=True)
        elif vendor_name == 'PINEWAVE' and vendor_pn in PINEWAVE_MODULE_PRECODING_PN_LIST:
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, PinewaveCmisMemMap(CmisCodes, bank=bank))
            api = PinewaveCmisApi(xcvr_eeprom, init_cdb_fw_handler=True)
        else:
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, CmisMemMap(CmisCodes, bank=bank))
            api = CmisApi(xcvr_eeprom, init_cdb_fw_handler=True)
            if api.is_coherent_module():
                xcvr_eeprom = XcvrEeprom(self.reader, self.writer, CCmisMemMap(CmisCodes, bank=bank))
                api = CCmisApi(xcvr_eeprom, init_cdb_fw_handler=True)
        return api

    def _create_qsfp_api(self):
        """
        QSFP/QSFP+ API implementation
        """
        revision_compliance = self.lower_memory_info.get_revision_compliance()
        if revision_compliance >= 3:
            return self._create_api(Sff8636Codes, Sff8636MemMap, Sff8636Api)
        else:
            return self._create_api(Sff8436Codes, Sff8436MemMap, Sff8436Api)

    def _create_api(self, codes_class, mem_map_class, api_class):
        codes = codes_class
        mem_map = mem_map_class(codes)
        xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
        return api_class(xcvr_eeprom)

    def create_xcvr_api(self, bank=0):
        id = self.lower_memory_info.get_id()

        # Instantiate various Optics implementation based upon their respective ID as per SFF8024
        id_mapping = {
            0x03: (self._create_api, (Sff8472Codes, Sff8472MemMap, Sff8472Api)),
            0x0D: (self._create_qsfp_api, ()),
            0x11: (self._create_api, (Sff8636Codes, Sff8636MemMap, Sff8636Api)),
            0x18: (self._create_cmis_api, (bank,)),
            0x19: (self._create_cmis_api, (bank,)),
            0x1b: (self._create_cmis_api, (bank,)),
            0x1e: (self._create_cmis_api, (bank,)),
            0x7e: (self._create_api, (AmphBackplaneCodes,
                                     AmphBackplaneMemMap, AmphBackplaneImpl)),
        }

        # Check if the ID exists in the mapping
        if id in id_mapping:
            func, args = id_mapping[id]
            if isinstance(args, tuple):
                try:
                    return func(*args)
                except Exception as e:
                    print(f"Error creating API: {e}")
                    return None
        return None
