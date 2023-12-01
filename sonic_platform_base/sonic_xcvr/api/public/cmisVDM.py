"""
    cmisCDB.py

    Implementation of APIs related to VDMs
"""

from ...fields import consts
from ..xcvr_api import XcvrApi
import struct
import time

PAGE_SIZE = 128
PAGE_OFFSET = 128
THRSH_SPACING = 8
VDM_SIZE = 2
VDM_FLAG_PAGE = 0x2c
VDM_FREEZE = 128
VDM_UNFREEZE = 0

class CmisVdmApi(XcvrApi):
    def __init__(self, xcvr_eeprom):
        super(CmisVdmApi, self).__init__(xcvr_eeprom)
    
    def get_F16(self, value):
        '''
        This function converts raw data to "F16" format defined in cmis.
        '''
        scale_exponent = (value >> 11) & 0x1f
        mantissa = value & 0x7ff
        result = mantissa*10**(scale_exponent-24)
        return result

    def get_vdm_page(self, page, VDM_flag_page):
        '''
        This function returns VDM items from a specific VDM page.
        Output format is a dictionary. Key is observable type; value is a dictionary.
        In the inside dictionary, key is lane; value is a list
        [
            vdm_value,
            vdm_thrsh_high_alarm,
            vdm_thrsh_low_alarm,
            vdm_thrsh_high_warn,
            vdm_thrsh_low_warn,
            vdm_high_alarm_flag,
            vdm_low_alarm_flag,
            vdm_high_warn_flag,
            vdm_low_warn_flag
        ]
        '''
        if page not in [0x20, 0x21, 0x22, 0x23]:
            raise ValueError('Page not in VDM Descriptor range!')
        vdm_descriptor = self.xcvr_eeprom.read_raw(page * PAGE_SIZE + PAGE_OFFSET, PAGE_SIZE)
        if not vdm_descriptor:
            return {}

        # Odd Adress VDM observable type ID, real-time monitored value in Page + 4
        vdm_typeID = vdm_descriptor[1::2]
        # Even Address
        # Bit 7-4: Threshold set ID in Page + 8, in group of 8 bytes, 16 sets/page
        # Bit 3-0: n. Monitored lane n+1 
        vdm_lane = [(elem & 0xf) for elem in vdm_descriptor[0::2]]
        VDM_thresholdID = [(elem>>4) for elem in vdm_descriptor[0::2]]
        vdm_valuePage = page + 4
        vdm_thrshPage = page + 8
        vdm_Page_data = {}
        VDM_TYPE_DICT = self.xcvr_eeprom.mem_map.codes.VDM_TYPE
        for index, typeID in enumerate(vdm_typeID):
            if typeID not in VDM_TYPE_DICT:
                continue
            else:
                vdm_info_dict = VDM_TYPE_DICT[typeID]
                thrshID = VDM_thresholdID[index]
                vdm_type = vdm_info_dict[0]
                vdm_format = vdm_info_dict[1]
                scale = vdm_info_dict[2]

                vdm_value_offset = vdm_valuePage * PAGE_SIZE + PAGE_OFFSET + VDM_SIZE * index
                vdm_high_alarm_offset = vdm_thrshPage * PAGE_SIZE + PAGE_OFFSET + THRSH_SPACING * thrshID
                vdm_low_alarm_offset = vdm_high_alarm_offset + 2
                vdm_high_warn_offset = vdm_high_alarm_offset + 4
                vdm_low_warn_offset = vdm_high_alarm_offset + 6

                vdm_value_raw = self.xcvr_eeprom.read_raw(vdm_value_offset, VDM_SIZE, True)
                vdm_thrsh_high_alarm_raw = self.xcvr_eeprom.read_raw(vdm_high_alarm_offset, VDM_SIZE, True)
                vdm_thrsh_low_alarm_raw = self.xcvr_eeprom.read_raw(vdm_low_alarm_offset, VDM_SIZE, True)
                vdm_thrsh_high_warn_raw = self.xcvr_eeprom.read_raw(vdm_high_warn_offset, VDM_SIZE, True)
                vdm_thrsh_low_warn_raw = self.xcvr_eeprom.read_raw(vdm_low_warn_offset, VDM_SIZE, True)
                if not vdm_value_raw or not vdm_thrsh_high_alarm_raw or not vdm_thrsh_low_alarm_raw \
                   or not vdm_high_warn_offset or not vdm_thrsh_low_warn_raw:
                    return {}
                if vdm_format == 'S16':
                    vdm_value = struct.unpack('>h',vdm_value_raw)[0] * scale
                    vdm_thrsh_high_alarm = struct.unpack('>h', vdm_thrsh_high_alarm_raw)[0] * scale
                    vdm_thrsh_low_alarm = struct.unpack('>h', vdm_thrsh_low_alarm_raw)[0] * scale
                    vdm_thrsh_high_warn = struct.unpack('>h', vdm_thrsh_high_warn_raw)[0] * scale
                    vdm_thrsh_low_warn = struct.unpack('>h', vdm_thrsh_low_warn_raw)[0] * scale
                elif vdm_format == 'U16':
                    vdm_value = struct.unpack('>H',vdm_value_raw)[0] * scale
                    vdm_thrsh_high_alarm = struct.unpack('>H', vdm_thrsh_high_alarm_raw)[0] * scale
                    vdm_thrsh_low_alarm = struct.unpack('>H', vdm_thrsh_low_alarm_raw)[0] * scale
                    vdm_thrsh_high_warn = struct.unpack('>H', vdm_thrsh_high_warn_raw)[0] * scale
                    vdm_thrsh_low_warn = struct.unpack('>H', vdm_thrsh_low_warn_raw)[0] * scale
                elif vdm_format == 'F16':
                    vdm_value_int = struct.unpack('>H',vdm_value_raw)[0]
                    vdm_value = self.get_F16(vdm_value_int)
                    vdm_thrsh_high_alarm_int = struct.unpack('>H', vdm_thrsh_high_alarm_raw)[0]
                    vdm_thrsh_low_alarm_int = struct.unpack('>H', vdm_thrsh_low_alarm_raw)[0]
                    vdm_thrsh_high_warn_int = struct.unpack('>H', vdm_thrsh_high_warn_raw)[0]
                    vdm_thrsh_low_warn_int = struct.unpack('>H', vdm_thrsh_low_warn_raw)[0]
                    vdm_thrsh_high_alarm = self.get_F16(vdm_thrsh_high_alarm_int)
                    vdm_thrsh_low_alarm = self.get_F16(vdm_thrsh_low_alarm_int)
                    vdm_thrsh_high_warn = self.get_F16(vdm_thrsh_high_warn_int)
                    vdm_thrsh_low_warn = self.get_F16(vdm_thrsh_low_warn_int)
                else:
                    continue

            vdm_flag_offset = 32 * (page - 0x20) + index//2
            bit_offset = 4*(index%2)
            vdm_high_alarm_flag = bool((VDM_flag_page[vdm_flag_offset] >> (bit_offset)) & 0x1)
            vdm_low_alarm_flag = bool((VDM_flag_page[vdm_flag_offset] >> (bit_offset+1)) & 0x1)
            vdm_high_warn_flag = bool((VDM_flag_page[vdm_flag_offset] >> (bit_offset+2)) & 0x1)
            vdm_low_warn_flag = bool((VDM_flag_page[vdm_flag_offset] >> (bit_offset+3)) & 0x1)

            if vdm_type not in vdm_Page_data:
                vdm_Page_data[vdm_type] = {
                    vdm_lane[index]+1: [
                        vdm_value,
                        vdm_thrsh_high_alarm,
                        vdm_thrsh_low_alarm,
                        vdm_thrsh_high_warn,
                        vdm_thrsh_low_warn,
                        vdm_high_alarm_flag,
                        vdm_low_alarm_flag,
                        vdm_high_warn_flag,
                        vdm_low_warn_flag]
                }

            else:
                vdm_Page_data[vdm_info_dict[0]][vdm_lane[index]+1] = [
                    vdm_value,
                    vdm_thrsh_high_alarm,
                    vdm_thrsh_low_alarm,
                    vdm_thrsh_high_warn,
                    vdm_thrsh_low_warn,
                    vdm_high_alarm_flag,
                    vdm_low_alarm_flag,
                    vdm_high_warn_flag,
                    vdm_low_warn_flag]
        return vdm_Page_data

    def get_vdm_allpage(self):
        '''
        This function returns VDM items from all advertised VDM pages.
        Output format is a dictionary. Key is observable type; value is a dictionary.
        In the inside dictionary, key is lane; value is a list
        [
            vdm_value,
            vdm_thrsh_high_alarm,
            vdm_thrsh_low_alarm,
            vdm_thrsh_high_warn,
            vdm_thrsh_low_warn,
            vdm_high_alarm_flag,
            vdm_low_alarm_flag,
            vdm_high_warn_flag,
            vdm_low_warn_flag
        ]
        '''
        vdm_page_supported_raw = self.xcvr_eeprom.read(consts.VDM_SUPPORTED_PAGE)
        if vdm_page_supported_raw is None:
            return None
        VDM_START_PAGE = 0x20
        vdm = dict()
        vdm_flag_page = self.xcvr_eeprom.read_raw(VDM_FLAG_PAGE * PAGE_SIZE + PAGE_OFFSET, PAGE_SIZE)
        for page in range(VDM_START_PAGE, VDM_START_PAGE + vdm_page_supported_raw + 1):
            vdm_current_page = self.get_vdm_page(page, vdm_flag_page)
            vdm.update(vdm_current_page)
        return vdm
