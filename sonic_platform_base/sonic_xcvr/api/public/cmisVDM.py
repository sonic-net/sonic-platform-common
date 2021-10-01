from ...fields import consts
from ..xcvr_api import XcvrApi
import struct
import time

PAGE_SIZE = 128
PAGE_OFFSET = 128
THRSH_SPACING = 8
VDM_SIZE = 2

class CmisVdmApi(XcvrApi):
    def __init__(self, xcvr_eeprom):
        super(CmisVdmApi, self).__init__(xcvr_eeprom)
    
    def get_F16(self, value):
        scale_exponent = (value >> 11) & 0x1f
        mantissa = value & 0x7ff
        result = mantissa*10**(scale_exponent-24)
        return result

    def get_VDM_page(self, page):
        if page not in [0x20, 0x21, 0x22, 0x23]:
            raise ValueError('Page not in VDM Descriptor range!')
        VDM_descriptor = self.xcvr_eeprom.read_flexible(page * PAGE_SIZE + PAGE_OFFSET, PAGE_SIZE)
        # Odd Adress VDM observable type ID, real-time monitored value in Page + 4
        VDM_typeID = VDM_descriptor[1::2]
        # Even Address
        # Bit 7-4: Threshold set ID in Page + 8, in group of 8 bytes, 16 sets/page
        # Bit 3-0: n. Monitored lane n+1 
        VDM_lane = [(elem & 0xf) for elem in VDM_descriptor[0::2]]
        VDM_thresholdID = [(elem>>4) for elem in VDM_descriptor[0::2]]
        VDM_valuePage = page + 4
        VDM_thrshPage = page + 8
        VDM_Page_data = {}
        for index, typeID in enumerate(VDM_typeID):
            if typeID not in self.xcvr_eeprom.mem_map.codes['cmis_code'].VDM_TYPE:
                continue
            else:
                vdm_info_dict = self.xcvr_eeprom.mem_map.codes['cmis_code'].VDM_TYPE[typeID]
                thrshID = VDM_thresholdID[index]
                vdm_type = vdm_info_dict[0]
                vdm_format = vdm_info_dict[1]
                scale = vdm_info_dict[2]

                vdm_value_offset = VDM_valuePage * PAGE_SIZE + PAGE_OFFSET + VDM_SIZE * index
                vdm_high_alarm_offset = VDM_thrshPage * PAGE_SIZE + PAGE_OFFSET + THRSH_SPACING * thrshID
                vdm_low_alarm_offset = vdm_high_alarm_offset + 2
                vdm_high_warn_offset = vdm_high_alarm_offset + 4
                vdm_low_warn_offset = vdm_high_alarm_offset + 6

                thrshID = VDM_thresholdID[index]
                vdm_value_raw = self.xcvr_eeprom.read_flexible(vdm_value_offset, VDM_SIZE, True)
                vdm_thrsh_high_alarm_raw = self.xcvr_eeprom.read_flexible(vdm_high_alarm_offset, VDM_SIZE, True)
                vdm_thrsh_low_alarm_raw = self.xcvr_eeprom.read_flexible(vdm_low_alarm_offset, VDM_SIZE, True)
                vdm_thrsh_high_warn_raw = self.xcvr_eeprom.read_flexible(vdm_high_warn_offset, VDM_SIZE, True)
                vdm_thrsh_low_warn_raw = self.xcvr_eeprom.read_flexible(vdm_low_warn_offset, VDM_SIZE, True)
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

            if vdm_type not in VDM_Page_data:
                VDM_Page_data[vdm_type] = {
                    VDM_lane[index]+1: [vdm_value,
                                        vdm_thrsh_high_alarm,
                                        vdm_thrsh_low_alarm,
                                        vdm_thrsh_high_warn,
                                        vdm_thrsh_low_warn]
                }

            else:
                VDM_Page_data[vdm_info_dict[0]][VDM_lane[index]+1] = [
                    vdm_value,
                    vdm_thrsh_high_alarm,
                    vdm_thrsh_low_alarm,
                    vdm_thrsh_high_warn,
                    vdm_thrsh_low_warn
                ]
        return VDM_Page_data

    def get_VDM_allpage(self):
        vdm_page_supported_raw = self.xcvr_eeprom.read(consts.VDM_SUPPORTED_PAGE) & 0x3
        VDM_START_PAGE = 0x20
        VDM = dict()
        self.xcvr_eeprom.write(consts.VDM_CONTROL, 128)
        time.sleep(5)
        self.xcvr_eeprom.write(consts.VDM_CONTROL, 0)
        time.sleep(1)
        for page in range(VDM_START_PAGE, VDM_START_PAGE + vdm_page_supported_raw + 1):
            VDM_current_page = self.get_VDM_page(page)
            VDM.update(VDM_current_page)
        return VDM