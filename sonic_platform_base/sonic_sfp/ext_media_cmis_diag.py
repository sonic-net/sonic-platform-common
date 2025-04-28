import time
import sys
from math import log10
from datetime import datetime
from ext_media_utils import media_eeprom_address

# Addr, len of bytes to read

# For factor version
FORM_FACTOR_VER_ADDR = (media_eeprom_address(offset=0), 1)
# Version of the CMIS-compliant module
CMIS_VER_ADDR = (media_eeprom_address(offset=1), 1)
# Power limit of the module
MOD_PWR_LIMIT_ADDR = (media_eeprom_address(offset=201), 1)
# Module flags
MOD_FLAGS_ADDR = (media_eeprom_address(offset=3), 9)
# Monitor registers
CMIS_MODULE_MONITOR1_ADDR = (media_eeprom_address(offset=14), 2)
CMIS_MODULE_MONITOR2_ADDR = (media_eeprom_address(offset=16), 2)
CMIS_MODULE_MONITOR3_ADDR = (media_eeprom_address(offset=18), 2)
CMIS_MODULE_MONITOR4_ADDR = (media_eeprom_address(offset=20), 2)
CMIS_MODULE_MONITOR5_ADDR = (media_eeprom_address(offset=22), 2)
# Media type encoding
CMIS_MEDIA_TYPE_ENCODING_ADDR   = (media_eeprom_address(offset=85), 1)
#Monitor Advertising registers
CMIS_MODULE_CHARACTERISTICS_ADVERTISING = (media_eeprom_address(page=0x01, offset=145), 1)
CMIS_MODULE_IMPLEMENTED_FLAGS_ADVERTISEMENT = (media_eeprom_address(page=0x1, offset=157),2)
CMIS_MODULE_IMPLEMENTED_MONITORS_ADVERTISING_ADDR = (media_eeprom_address(page=0x01, offset=159), 2)
#Lane status registers
CMIS_MODULE_LANE_TX_FAULT_STATUS_ADDR = (media_eeprom_address(page=0x011, offset=135), 1)
CMIS_MODULE_LANE_TX_LOS_STATUS_ADDR = (media_eeprom_address(page=0x011, offset=136), 1)
CMIS_MODULE_LANE_TX_LOL_STATUS_ADDR = (media_eeprom_address(page=0x011, offset=137), 1)
CMIS_MODULE_LANE_RX_LOS_STATUS_ADDR = (media_eeprom_address(page=0x011, offset=147), 1)
CMIS_MODULE_LANE_RX_LOL_STATUS_ADDR = (media_eeprom_address(page=0x011, offset=148), 1)
#Lane Monitor registers
CMIS_MODULE_MEDIA_LANE_MONITORS_ADDR = (media_eeprom_address(page=0x11, offset=154),48)
#Loopback advertisement and controls
CMIS_MODULE_LOOPBACK_CAPABILITIES_ADDR = (media_eeprom_address(page=0x013, offset=128), 1)
CMIS_MODULE_MEDIA_SIDE_OUTPUT_LOOPBACK_ENABLE_ADDR = (media_eeprom_address(page=0x013, offset=180), 1)
CMIS_MODULE_MEDIA_SIDE_INPUT_LOOPBACK_ENABLE_ADDR = (media_eeprom_address(page=0x013, offset=181), 1)
CMIS_MODULE_HOST_SIDE_OUTPUT_LOOPBACK_ENABLE_ADDR = (media_eeprom_address(page=0x013, offset=182), 1)
CMIS_MODULE_HOST_SIDE_INPUT_LOOPBACK_ENABLE_ADDR = (media_eeprom_address(page=0x013, offset=183), 1)

DEFAULT_APPLICATION = 'N/A'
class cmis_diag:
    def logger(self, s):
        if self.logging:
            log = "{} : Log for device : {} : {}".format(datetime.now(), self.eeprom_path, s)
            print(log)

    def logger_error(self, s):
        log = "{} : Log for device : {} : {}".format(datetime.now(), self.eeprom_path, s)
        print(log)

    # Get the CMIS version
    def get_cmis_ver(self):
        self.logger("Reading CMIS version")
        ret = self.read_bytes(*CMIS_VER_ADDR)[0]
        self.logger("Got CMIS version value of "+str(ret))
        return ret

    def convert_uw_dbm(self, raw_power):
        self.logger("twos complement power = {}".format(raw_power))
        if raw_power > 0:
            dbm_power = (10.*log10((float(raw_power) / 10000)))
        else:
            dbm_power = -20

        self.logger("converted power = {} dbm".format(dbm_power))

        return dbm_power

    def convert_cmis_temperature(self, raw_value):
        self.logger("converting value {} to temperature and type {}".format(raw_value,type(raw_value)))

        try:
            if ((raw_value & 0x8000) !=0):
                val = -2**15
            else:
                val = 0

            for x in range(15):
                 if (((raw_value >> x) & 0x01) != 0):
                     val += 2**x

            val /= float(256)

            self.logger("raw_value = {}, cmis_temp = {} C".format(raw_value, val))
            return val
        except:
            pass

        return 0x0
    def convert_cmis_voltage(self, raw_value):
        self.logger("converting cmis voltage raw value = {}".format(raw_value))
        return (raw_value / float(10000))

    def convert_cmis_tec_current(self):
        return False

    def get_cmis_monitoring_advertisement(self):
        self.logger("Reading module monitoring advertisement")
        ret = self.read_bytes(*CMIS_MODULE_IMPLEMENTED_MONITORS_ADVERTISING_ADDR)
        self.logger("Got module implemented monitor advertisement at addr: {}, vals: {}".format(vars(CMIS_MODULE_IMPLEMENTED_MONITORS_ADVERTISING_ADDR[0]), ret))

        self.aux3_monitor_supported = ((ret[0] & 0x10) != 0)
        self.aux2_monitor_supported = ((ret[0] & 0x08) != 0)
        self.aux1_monitor_supported = ((ret[0] & 0x04) != 0)
        self.voltage_monitor_supported = ((ret[0] & 0x02) != 0)
        self.temp_monitor_supported = ((ret[0] & 0x001) != 0)
        self.rx_power_monitor_supported = ((ret[1] & 0x0004) != 0)
        self.tx_power_monitor_supported = ((ret[1] & 0x0002) != 0)
        self.tx_bias_monitor_supported  = ((ret[1] & 0x0001) != 0)
        if ((ret[1] >> 3) & 0x3 == 0):
            self.tx_bias_monitor_multiplier = 1
        elif ((ret[1] >> 3) & 0x3 == 1):
            self.tx_bias_monitor_multiplier = 2
        elif ((ret[1] >> 3) & 0x3 == 2):
            self.tx_bias_monitor_multiplier = 4

        ret = self.read_bytes(*CMIS_MODULE_CHARACTERISTICS_ADVERTISING)[0]
        self.logger("Got module characteristics advertisement at addr: {}, vals: {}".format(vars(CMIS_MODULE_CHARACTERISTICS_ADVERTISING[0]), ret))

        self.aux3_monitor_vcc = ((ret & 0x4) != 0)
        self.aux3_monitor_laser_temp = ((ret & 0x4) == 0)
        self.aux2_monitor_current = ((ret & 0x2) != 0)
        self.aux2_monitor_laser_temp = ((ret & 0x2) == 0)
        self.aux1_monitor_current = ((ret & 0x1) != 0)

        ret = self.read_bytes(*CMIS_MODULE_IMPLEMENTED_FLAGS_ADVERTISEMENT)
        self.logger("Got module implemented flags at addr: {}, vals: {}".format(vars(CMIS_MODULE_IMPLEMENTED_FLAGS_ADVERTISEMENT[0]), ret))

        self.txlol_supported = ((ret[1] & 0x04) != 0)
        self.txlos_supported = ((ret[1] & 0x02) != 0)
        self.rxlol_supported = ((ret[0] & 0x04) != 0)
        self.rxlos_supported = ((ret[0] & 0x02) != 0)

    # Get dom info
    def get_dom_info(self):

        self.logger("Get dom info ")
        if self.cmis_ver < 0x30:
            self.logger("Unsupported cmis version = {}".format(self.cmis_ver))
            return None

        if self.m_type not in [0x01,0x02]:
            return None

        try:
            temp_dict = {}
            dom_dict = {}

            dom_dict['cmis_version'] = self.cmis_ver

            if self.cmis_ver >= 0x40:
                dom_dict['cmis_diagnostics'] = True

            if self.cmis_ver >= 0x40:
                temp_dict = self.get_cmis_loopback_capabilities()
                if temp_dict is not None:
                    dom_dict.update(temp_dict)

            temp_dict = self.get_cmis_laser_temp()
            if temp_dict is not None:
                dom_dict.update(temp_dict)

            temp_dict = self.get_cmis_temp()
            if temp_dict is not None:
                dom_dict.update(temp_dict)

            temp_dict = self.get_cmis_voltage()
            if temp_dict is not None:
                dom_dict.update(temp_dict)

            temp_dict = self.get_cmis_los_status()
            if temp_dict is not None:
                dom_dict.update(temp_dict)

            temp_dict = self.get_cmis_lol_status()
            if temp_dict is not None:
                dom_dict.update(temp_dict)

            temp_dict = self.get_cmis_lane_specific_monitors()
            if temp_dict is not None:
                dom_dict.update(temp_dict)

            self.logger("dom_dict = {}".format(dom_dict))

            return dom_dict
        except:
            pass

        return None

    def get_cmis_laser_temp(self):
        self.logger("Reading cmis laser temp")

        laser_temp_monitor_supported = False

        if self.aux2_monitor_supported:
            if self.aux2_monitor_laser_temp:
                ret = self.read_bytes(*CMIS_MODULE_MONITOR3_ADDR)
                self.logger("Got laser temp at addr: {}, vals: {}".format(vars(CMIS_MODULE_MONITOR3_ADDR[0]), ret))
                lasert_temp_monitor_supported = True

        if self.aux3_monitor_supported:
            if self.aux3_monitor_laser_temp:
                ret = self.read_bytes(*CMIS_MODULE_MONITOR4_ADDR)
                self.logger("Got laser temp at addr: {}, vals: {}".format(vars(CMIS_MODULE_MONITOR4_ADDR[0]), ret))
                laser_temp_monitor_supported = True

        if laser_temp_monitor_supported == False:
            self.logger("laser temp monitor not supported")
            return None

        laser_temp_dict = {}
        laser_temp_dict['laser_temperature'] = self.convert_cmis_temperature(ret[0] << 8 | ret[1])

        self.logger("laser_temp_dict = {}".format(laser_temp_dict))

        return laser_temp_dict

    def get_cmis_tec_current(self):
        self.logger("Reading cmis tec current")

        if self.aux1_monitor_supported:
            if self.aux1_monitor_current:
                reg = CMIS_MODULE_MONITOR3_ADDR
            else:
                reg = None

        if reg is None:
            if self.aux2_monitor_supported:
                if self.aux2_monitor_current:
                    reg = CMIS_MODULE_MONITOR4_ADDR
                else:
                    reg = None
            else:
                reg = None

        if reg is None:
            return None

        ret = self.read_bytes(reg)[0]
        self.logger("Got cmis tec current at addr: {}, vals: {}".format(vars(reg[0]), ret))

        tec_current_dict = {}

        tec_current_dict['tec_current'] = self.convert_cmis_tec_current

    def get_cmis_voltage(self):
        self.logger("Reading cmis vcc2")
        ret = self.read_bytes(*CMIS_MODULE_MONITOR2_ADDR)
        self.logger("Got module voltage at addr: {}, vals: {}".format(vars(CMIS_MODULE_MONITOR2_ADDR[0]), ret))

        voltage_dict = {}

        voltage_dict['voltage'] = self.convert_cmis_voltage((ret[0] << 8) | ret[1])

        self.logger("voltage_dict = ".format(voltage_dict))

        return voltage_dict

    def get_cmis_temp(self):

        if self.temp_monitor_supported == False:
            return None

        self.logger("Reading cmis temp")
        ret = self.read_bytes(*CMIS_MODULE_MONITOR1_ADDR)
        self.logger("Got module temp at addr: {}, vals: {}".format(vars(CMIS_MODULE_MONITOR1_ADDR[0]), ret))

        temp_dict = {}

        temp_dict['temperature'] = self.convert_cmis_temperature(ret[0] << 8 | ret[1])
        self.logger("temp_dict = {}".format(temp_dict))

        return temp_dict

    def get_cmis_lane_specific_monitors(self):
        self.logger("Reading module flags")

        ret = self.read_bytes(*CMIS_MODULE_MEDIA_LANE_MONITORS_ADDR)
        self.logger("Got lane specific monitors at addr: {}, vals: {}".format(vars(CMIS_MODULE_MEDIA_LANE_MONITORS_ADDR[0]), ret))

        cmis_lane_monitor_dict = {}

        if self.tx_power_monitor_supported:
            self.logger("tx power monitor supported")

            cmis_lane_monitor_dict['tx1power'] = self.convert_uw_dbm((ret[0] << 8) | ret[1])
            cmis_lane_monitor_dict['tx2power'] = self.convert_uw_dbm((ret[2] << 8) | ret[3])
            cmis_lane_monitor_dict['tx3power'] = self.convert_uw_dbm((ret[4] << 8) | ret[5])
            cmis_lane_monitor_dict['tx4power'] = self.convert_uw_dbm((ret[6] << 8) | ret[7])
            cmis_lane_monitor_dict['tx5power'] = self.convert_uw_dbm((ret[8] << 8) | ret[9])
            cmis_lane_monitor_dict['tx6power'] = self.convert_uw_dbm((ret[10] << 8) | ret[11])
            cmis_lane_monitor_dict['tx7power'] = self.convert_uw_dbm((ret[12] << 8) | ret[13])
            cmis_lane_monitor_dict['tx8power'] = self.convert_uw_dbm((ret[14] << 8) | ret[15])
        else:
            cmis_lane_monitor_dict.update(dict.fromkeys(self.dom_tx_power_keys, 'N/A'))

        self.logger("cmis_lane_monitor_dict = {}".format(cmis_lane_monitor_dict))

        if self.rx_power_monitor_supported:
            self.logger("rx power monitor supported")

            cmis_lane_monitor_dict['rx1power'] = self.convert_uw_dbm((ret[32] << 8) | ret[33])
            cmis_lane_monitor_dict['rx2power'] = self.convert_uw_dbm((ret[34] << 8) | ret[35])
            cmis_lane_monitor_dict['rx3power'] = self.convert_uw_dbm((ret[36] << 8) | ret[37])
            cmis_lane_monitor_dict['rx4power'] = self.convert_uw_dbm((ret[38] << 8) | ret[39])
            cmis_lane_monitor_dict['rx5power'] = self.convert_uw_dbm((ret[40] << 8) | ret[41])
            cmis_lane_monitor_dict['rx6power'] = self.convert_uw_dbm((ret[42] << 8) | ret[43])
            cmis_lane_monitor_dict['rx7power'] = self.convert_uw_dbm((ret[44] << 8) | ret[45])
            cmis_lane_monitor_dict['rx8power'] = self.convert_uw_dbm((ret[46] << 8) | ret[47])
        else:
            cmis_lane_monitor_dict.update(dict.fromkeys(self.dom_rx_power_keys, 'N/A'))

        if self.tx_bias_monitor_supported:
            self.logger("tx bias monitor supported")

            cmis_lane_monitor_dict['tx1bias'] = self.tx_bias_monitor_multiplier * ((ret[16] << 8) | ret[17]) / 2000
            cmis_lane_monitor_dict['tx2bias'] = self.tx_bias_monitor_multiplier * ((ret[18] << 8) | ret[19]) / 2000
            cmis_lane_monitor_dict['tx3bias'] = self.tx_bias_monitor_multiplier * ((ret[20] << 8) | ret[21]) / 2000
            cmis_lane_monitor_dict['tx4bias'] = self.tx_bias_monitor_multiplier * ((ret[22] << 8) | ret[23]) / 2000
            cmis_lane_monitor_dict['tx5bias'] = self.tx_bias_monitor_multiplier * ((ret[24] << 8) | ret[26]) / 2000
            cmis_lane_monitor_dict['tx6bias'] = self.tx_bias_monitor_multiplier * ((ret[26] << 8) | ret[27]) / 2000
            cmis_lane_monitor_dict['tx7bias'] = self.tx_bias_monitor_multiplier * ((ret[28] << 8) | ret[29]) / 2000
            cmis_lane_monitor_dict['tx8bias'] = self.tx_bias_monitor_multiplier * ((ret[30] << 8) | ret[31]) / 2000
        else:
            cmis_lane_monitor_dict.update(dict.fromkeys(self.dom_tx_bias_keys, 'N/A'))

        self.logger("cmis_lane_monitor_dict = {}".format(cmis_lane_monitor_dict))

        return cmis_lane_monitor_dict

    def get_cmis_loopback_capabilities(self):
        self.logger("Reading loopback capabilities")
        ret = self.read_bytes(*CMIS_MODULE_LOOPBACK_CAPABILITIES_ADDR)[0]
        self.logger("Got module loopback capabilities at addr: {}, vals: {}".format(vars(CMIS_MODULE_LOOPBACK_CAPABILITIES_ADDR[0]), ret))

        capabilities_dict = dict.fromkeys(self.loopback_capabilities_keys, False)

        self.simultaneous_host_media_side_loopback_supported = (ret & (1 << 6) != 0)
        capabilities_dict['simultaneous_host_media_side_loopback_supported'] = (ret & (1 << 6) != 0)
        capabilities_dict['per_lane_media_side_loopback_supported'] = (ret & (1 << 5) != 0)
        capabilities_dict['per_lane_host_side_loopback_supported'] = (ret & (1 << 4) != 0)
        capabilities_dict['host_side_input_loopback_supported'] = (ret & (1 << 3) != 0)
        capabilities_dict['host_side_output_loopback_supported'] = (ret & (1 << 2) != 0)
        capabilities_dict['media_side_input_loopback_supported'] = (ret & (1 << 1) != 0)
        capabilities_dict['media_side_output_loopback_supported'] = (ret & (1 << 0) != 0)

        ret = self.read_bytes(*CMIS_MODULE_HOST_SIDE_INPUT_LOOPBACK_ENABLE_ADDR)[0]
        capabilities_dict['host_side_input_loopback_enable'] = (ret  != 0)

        ret = self.read_bytes(*CMIS_MODULE_HOST_SIDE_OUTPUT_LOOPBACK_ENABLE_ADDR)[0]
        capabilities_dict['host_side_output_loopback_enable'] = (ret  != 0)

        ret = self.read_bytes(*CMIS_MODULE_MEDIA_SIDE_INPUT_LOOPBACK_ENABLE_ADDR)[0]
        capabilities_dict['media_side_input_loopback_enable'] = (ret != 0)

        ret = self.read_bytes(*CMIS_MODULE_MEDIA_SIDE_OUTPUT_LOOPBACK_ENABLE_ADDR)[0]
        capabilities_dict['media_side_output_loopback_enable'] = (ret != 0)

        self.logger("loopback capabilities dict = {}".format(capabilities_dict))

        return capabilities_dict

    def set_cmis_loopback_mode_enable(self, mode, enable):
        self.logger_error("Entering set_cmis_loopback_mode_enable, mode={}, enable={}".format(mode,enable))

        try:
            if enable == 'True':
                val = 0xff
            else:
                val = 0x00

            if mode == 'media_side_input_loopback_enable':
                reg = CMIS_MODULE_MEDIA_SIDE_INPUT_LOOPBACK_ENABLE_ADDR[0]

                if enable == 'True':
                    val = 0xf
                else:
                    val = 0x0
            elif mode == 'host_side_input_loopback_enable':
                reg = CMIS_MODULE_HOST_SIDE_INPUT_LOOPBACK_ENABLE_ADDR[0]
            else:
                self.logger("Unknown loopback mode requested")
                return False

            self.write_byte(reg, val)
            self.logger_error("Set loopback controls reg = {}, val={}".format(reg, val))
            return True
        except:
            pass

        return False

    def get_cmis_los_status(self):
        self.logger("Reading module los status")

        los_dictionary = {}

        if self.txlos_supported:
            self.logger("tx los reporting supported")
            ret = self.read_bytes(*CMIS_MODULE_LANE_TX_LOS_STATUS_ADDR)[0]
            self.logger("Got module tx los status at addr: {}, vals: {}".format(vars(CMIS_MODULE_LANE_TX_LOS_STATUS_ADDR[0]), ret))

            los_dictionary['tx1los'] = ((ret & (1 << 0)) != 0)
            los_dictionary['tx2los'] = ((ret & (1 << 1)) != 0)
            los_dictionary['tx3los'] = ((ret & (1 << 2)) != 0)
            los_dictionary['tx4los'] = ((ret & (1 << 3)) != 0)
            los_dictionary['tx5los'] = ((ret & (1 << 4)) != 0)
            los_dictionary['tx6los'] = ((ret & (1 << 5)) != 0)
            los_dictionary['tx7los'] = ((ret & (1 << 6)) != 0)
            los_dictionary['tx8los'] = ((ret & (1 << 7)) != 0)
        else:
            self.logger("tx los reporting not supported")
            los_dictionary.update(dict.fromkeys(self.dom_tx_los_keys, 'N/A'))

        if self.rxlos_supported:
            self.logger("rx los reporting supported")
            ret = self.read_bytes(*CMIS_MODULE_LANE_RX_LOS_STATUS_ADDR)[0]
            self.logger("Got module rx los status at addr: {}, vals: {}".format(vars(CMIS_MODULE_LANE_RX_LOS_STATUS_ADDR[0]), ret))

            los_dictionary['rx1los'] = ((ret & (1 << 0)) != 0)
            los_dictionary['rx2los'] = ((ret & (1 << 1)) != 0)
            los_dictionary['rx3los'] = ((ret & (1 << 2)) != 0)
            los_dictionary['rx4los'] = ((ret & (1 << 3)) != 0)
            los_dictionary['rx5los'] = ((ret & (1 << 4)) != 0)
            los_dictionary['rx6los'] = ((ret & (1 << 5)) != 0)
            los_dictionary['rx7los'] = ((ret & (1 << 6)) != 0)
            los_dictionary['rx8los'] = ((ret & (1 << 7)) != 0)
        else:
            self.logger("rx los reporting not supported")
            los_dictionary.update(dict.fromkeys(self.dom_rx_los_keys, 'N/A'))

        self.logger("mylos_dictionary = {}".format(los_dictionary))
        return los_dictionary

    def get_cmis_lol_status(self):

        self.logger("Reading module lol status")

        lol_dictionary = {}

        if self.txlol_supported:
            ret = self.read_bytes(*CMIS_MODULE_LANE_TX_LOL_STATUS_ADDR)[0]
            self.logger("Got module tx lol status at addr: {}, vals: {}".format(vars(CMIS_MODULE_LANE_TX_LOL_STATUS_ADDR[0]), ret))

            lol_dictionary['tx1lol'] = ((ret & (1 << 0)) != 0)
            lol_dictionary['tx2lol'] = ((ret & (1 << 1)) != 0)
            lol_dictionary['tx3lol'] = ((ret & (1 << 2)) != 0)
            lol_dictionary['tx4lol'] = ((ret & (1 << 3)) != 0)
            lol_dictionary['tx5lol'] = ((ret & (1 << 4)) != 0)
            lol_dictionary['tx6lol'] = ((ret & (1 << 5)) != 0)
            lol_dictionary['tx7lol'] = ((ret & (1 << 6)) != 0)
            lol_dictionary['tx8lol'] = ((ret & (1 << 7)) != 0)
        else:
            self.logger("tx lol reporting not supported")
            lol_dictionary.update(dict.fromkeys(self.dom_tx_lol_keys, 'N/A'))

        if self.rxlol_supported:
            ret = self.read_bytes(*CMIS_MODULE_LANE_RX_LOL_STATUS_ADDR)[0]
            self.logger("Got module rx lol status at addr: {}, vals: {}".format(vars(CMIS_MODULE_LANE_RX_LOL_STATUS_ADDR[0]), ret))

            lol_dictionary['rx1lol'] = ((ret & (1 << 0)) != 0)
            lol_dictionary['rx2lol'] = ((ret & (1 << 1)) != 0)
            lol_dictionary['rx3lol'] = ((ret & (1 << 2)) != 0)
            lol_dictionary['rx4lol'] = ((ret & (1 << 3)) != 0)
            lol_dictionary['rx5lol'] = ((ret & (1 << 4)) != 0)
            lol_dictionary['rx6lol'] = ((ret & (1 << 5)) != 0)
            lol_dictionary['rx7lol'] = ((ret & (1 << 6)) != 0)
            lol_dictionary['rx8lol'] = ((ret & (1 << 7)) != 0)
        else:
            self.logger("rx los reporting not supported")
            lol_dictionary.update(dict.fromkeys(self.dom_tx_los_keys, 'N/A'))

        self.logger("lol_dictionary = {}".format(lol_dictionary))

        return lol_dictionary

    # The driver (optoe) uses a flat addressing space, while the actual device is paged
    def _page_to_flat_offset(self, addr):
        if addr.page > 0 and addr.offset > 127:
            # Convert page and offset to flat address
            return ((addr.page+1)*128) + (addr.offset-128)
        return addr.offset

    def read_bytes(self, addr, length):
        offset = self._page_to_flat_offset(addr)

        self.logger("Will read {} byte(s) from addr {}".format(length, vars(addr)))

        with open(self.eeprom_path, 'rb+') as fp:
            fp.seek(offset)
            b = fp.read(length)
            ret = [int(ord(a)) for a in b]
            self.logger("Read back "+str(ret))
            return ret
        self.logger("Read failed for addr {}".format(vars(addr)))
        return []

    def write_byte(self, addr, val):
        offset = self._page_to_flat_offset(addr)

        self.logger("Will write {} to byte from addr {}".format(val, vars(addr)))
        with open(self.eeprom_path, 'rb+') as fp:
            fp.seek(offset)
            fp.write(chr(val))
    
    def __hash__(self):
        return hash(self.sfp_obj)

    def __eq__(self, other):
        if not isinstance(other, type(self)): return NotImplemented
        return self.sfp_obj == other.sfp_obj

    def __init__(self, sfp_obj, logging=False):
        self.logging = logging

        if sfp_obj == None:
            raise ValueError("Need proper arg")
        self.sfp_obj = sfp_obj


        # Need EEPROM Path for SW control
        try:
            self.eeprom_path = sfp_obj.get_eeprom_sysfs_path()
            self.logger("Init got eeprom path of "+str(self.eeprom_path))
        except:
            raise ValueError("CMIS initializations needs valid device sysfs path")

        self.logger("Init new cmis obj with object "+str(sfp_obj))

        if self.read_bytes(*FORM_FACTOR_VER_ADDR)[0] != 0x18:
            self.logger("Invalid module for CMIS initialization. Expected 0x18 at byte 0. Exiting")
            self.cmis_ver = -1
            return

        self.m_type = self.read_bytes(*CMIS_MEDIA_TYPE_ENCODING_ADDR)[0]

        self.cmis_ver = self.get_cmis_ver()
        self.aux3_monitor_vcc = False
        self.aux3_monitor_laser_temp = False
        self.aux2_monitor_current = False
        self.aux2_monitor_laser_temp = False
        self.aux1_monitor_current = False

        self.txlol_supported = False
        self.txlos_supported = False
        self.rxlol_supported = False
        self.rxlos_supported = False

        self.aux3_monitor_supported = False
        self.aux2_monitor_supported = False
        self.aux1_monitor_supported = False
        self.voltage_monitor_supported = False
        self.temp_monitor_supported = False
        self.rx_power_monitor_supported = False
        self.tx_power_monitor_supported = False
        self.tx_bias_monitor_supported  = False
        self.tx_bias_monitor_multiplier = 0
        self.simultaneous_host_media_side_loopback_supported = False
        self.host_side_input_loopback_enable = False
        self.host_side_output_loopback_enable = False
        self.media_side_input_loopback_enable = False
        self.media_side_output_loopback_enable = False

        self.dom_tx_fault_dict_keys = ['tx1fault', 'tx2fault', 'tx3fault', 'tx4fault',
                                       'tx5fault', 'tx6fault', 'tx7fault', 'tx8fault']

        self.dom_tx_los_keys = ['tx1los', 'tx2los', 'tx3los', 'tx4los',
                                'tx5los', 'tx6los', 'tx7los', 'tx8los']

        self.dom_tx_lol_keys = ['tx1lol', 'tx2lol', 'tx3lol', 'tx4lol',
                                'tx5lol', 'tx6lol', 'tx7lol', 'tx8lol']

        self.dom_rx_los_keys = ['rx1los', 'rx2los', 'rx3los', 'rx4los',
                                'rx5los', 'rx6los', 'rx7los', 'rx8los']

        self.dom_rx_lol_keys = ['rx1lol', 'rx2lol', 'rx3lol', 'rx4lol',
                                'rx5lol', 'rx6lol', 'rx7lol', 'rx8lol']

        self.dom_tx_power_keys = ['tx1power', 'tx2power', 'tx3power', 'tx4power'
                                  'tx5power', 'tx6power', 'tx7power', 'tx8power']

        self.dom_rx_power_keys = ['rx1power', 'rx2power', 'rx3power', 'rx4power'
                                  'rx5power', 'rx6power', 'rx7power', 'rx8power']

        self.dom_tx_bias_keys = ['tx1bias', 'tx2bias','tx3bias', 'tx4bias',
                                 'tx5bias', 'tx6bias','tx7bias', 'tx8bias']

        self.dom_dict_keys = ['temperature', 'voltage', 'laser_temperature']

        self.loopback_capabilities_keys = ['simultaneous_host_media_side_loopback_supported',
                                           'per_lane_media_side_loopback_supported',
                                           'per_lane_host_side_loopback_supported',
                                           'host_side_input_loopback_supported',
                                           'host_side_output_loopback_supported',
                                           'media_side_input_loopback_supported',
                                           'media_side_output_loopback_supported']


        self.get_cmis_monitoring_advertisement()

