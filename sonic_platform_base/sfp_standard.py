#
# sfp_standard.py
#
# Abstract base class for implementing a platform-specific class with which
# to interact with a SFP module in SONiC
#

from __future__ import print_function

try:
    import abc
    import sys
    import time
    from multiprocessing import Lock
    from .sfp_base import SfpBase
    from .sonic_sfp.sff8436 import sff8436InterfaceId
    from .sonic_sfp.sff8436 import sff8436Dom
    from .sonic_sfp.sff8472 import sff8472InterfaceId
    from .sonic_sfp.sff8472 import sff8472Dom
    from .sonic_sfp.inf8628 import inf8628InterfaceId
    from .sonic_sfp.inf8628 import inf8628Dom
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

sfp_cable_length_tup = ('LengthSMFkm-UnitsOfKm', 'LengthSMF(UnitsOf100m)',
                        'Length50um(UnitsOf10m)', 'Length62.5um(UnitsOfm)',
                        'LengthCable(UnitsOfm)', 'LengthOM3(UnitsOf10m)')

sfp_compliance_code_tup = ('10GEthernetComplianceCode', 'InfinibandComplianceCode',
                            'ESCONComplianceCodes', 'SONETComplianceCodes',
                            'EthernetComplianceCodes','FibreChannelLinkLength',
                            'FibreChannelTechnology', 'SFP+CableTechnology',
                            'FibreChannelTransmissionMedia','FibreChannelSpeed')

qsfp_cable_length_tup = ('Length(km)', 'Length OM3(2m)',
                         'Length OM2(m)', 'Length OM1(m)',
                         'Length Cable Assembly(m)')

XCVR_EEPROM_TYPE_UNKNOWN = 0
XCVR_EEPROM_TYPE_SFP = 1
XCVR_EEPROM_TYPE_QSFP = 2
XCVR_EEPROM_TYPE_QSFPDD = 3
XCVR_EEPROM_TYPE_OSFP = XCVR_EEPROM_TYPE_QSFPDD

SFF8024_TYPE_QSFPDD = '18,19'

SFF8472_DOM_TEMP_ADDR = (96 | 0x100)
SFF8472_DOM_VOLT_ADDR = (98 | 0x100)
SFF8472_DOM_CHAN_MON_ADDR = (100 | 0x100)
SFF8472_DOM_STCR_ADDR = (110 | 0x100)
SFF8472_DOM_MOD_THRES_ADDR = (0 | 0x100)

SFF8636_DOM_TYPE_ADDR = 220
SFF8636_DOM_TEMP_ADDR = 22
SFF8636_DOM_VOLT_ADDR = 26
SFF8636_DOM_CHAN_MON_ADDR = 34
SFF8636_DOM_MOD_THRES_ADDR = 512
SFF8636_DOM_CHAN_THRES_ADDR = 560

CMIS4_IMPL_MEM_PAGES_ADDR = ((142 & 0x7f) | 0x100)
CMIS4_PAGE_SIZE = 128
CMIS4_PAGE_ADDR_10h = 0x880
CMIS4_PAGE_ADDR_11h = 0x900

class SfpStandard(SfpBase):
    """
    Abstract base class for interfacing with a SFP module
    """

    __metaclass__ = abc.ABCMeta

    CMIS_IDS = [0x18, 0x19]
    CMIS_REG_REV = 1
    CMIS_REG_MOD_CTRL = 26
    CMIS_REG_ID = 128

    CMIS_MOD_CTRL_SW_RESET = 0x08
    CMIS_MOD_CTRL_FORCE_LP = 0x10

    PORT_TYPE_SFP = 1
    PORT_TYPE_QSFP = 2
    PORT_TYPE_QSFPDD = 3

    def __init__(self):
        SfpBase.__init__(self)
        self.eeprom_lock = Lock()

    @abc.abstractproperty
    def port_index(self):
        pass

    @abc.abstractproperty
    def port_type(self):
        pass

    @abc.abstractproperty
    def eeprom_path(self):
        pass

    # Read out any bytes from any offset
    def __read_eeprom(self, offset, num_bytes):
        """
        read eeprom specfic bytes beginning from a random offset with size as num_bytes

        Args:
             offset :
                     Integer, the offset from which the read transaction will start
             num_bytes:
                     Integer, the number of bytes to be read

        Returns:
            bytearray, if raw sequence of bytes are read correctly from the offset of size num_bytes
            None, if the read_eeprom fails
        """
        buf = None
        eeprom_raw = []
        sysfs_sfp_i2c_client_eeprom_path = self.eeprom_path

        if not self.get_presence():
            return None

        sysfsfile_eeprom = None
        try:
            sysfsfile_eeprom = open(sysfs_sfp_i2c_client_eeprom_path, "rb", 0)
            sysfsfile_eeprom.seek(offset)
            buf = sysfsfile_eeprom.read(num_bytes)
        except Exception as ex:
            # Eliminate the redundant errors by showing errors only for lower page and page 0
            if offset < 256:
                print("port {0}: {1}: offset {2}: read failed: {3}".format(self.port_index, sysfs_sfp_i2c_client_eeprom_path, hex(offset), ex))
            return None
        finally:
            if sysfsfile_eeprom is not None:
                sysfsfile_eeprom.close()

        if buf is None:
            return None
        # TODO: Remove this check once we no longer support Python 2
        if sys.version_info >= (3,0):
            for x in buf:
                eeprom_raw.append(x)
        else:
            for x in buf:
                eeprom_raw.append(ord(x))
        while len(eeprom_raw) < num_bytes:
            eeprom_raw.append(0)
        return eeprom_raw

    # Read out any bytes from any offset
    def read_eeprom(self, offset, num_bytes):
        """
        read eeprom specfic bytes beginning from a random offset with size as num_bytes

        Args:
             offset :
                     Integer, the offset from which the read transaction will start
             num_bytes:
                     Integer, the number of bytes to be read

        Returns:
            bytearray, if raw sequence of bytes are read correctly from the offset of size num_bytes
            None, if the read_eeprom fails
        """
        self.eeprom_lock.acquire()
        bytes = self.__read_eeprom(offset, num_bytes)
        self.eeprom_lock.release()
        return bytes

    def __write_eeprom(self, offset, num_bytes, write_buffer):
        """
        write eeprom specfic bytes beginning from a random offset with size as num_bytes
        and write_buffer as the required bytes

        Args:
             offset :
                     Integer, the offset from which the read transaction will start
             num_bytes:
                     Integer, the number of bytes to be written
             write_buffer:
                     bytearray, raw bytes buffer which is to be written beginning at the offset

        Returns:
            a Boolean, true if the write succeeded and false if it did not succeed.
        """
        sysfs_sfp_i2c_client_eeprom_path = self.eeprom_path
        if not self.get_presence():
            return False

        sysfsfile_eeprom = None
        try:
            sysfsfile_eeprom = open(sysfs_sfp_i2c_client_eeprom_path, "wb", 0)
            sysfsfile_eeprom.seek(offset)
            # TODO: Remove this check once we no longer support Python 2
            if sys.version_info >= (3,0):
                for i in range(num_bytes):
                    sysfsfile_eeprom.write(write_buffer[i])
            else:
                for i in range(num_bytes):
                    sysfsfile_eeprom.write(chr(write_buffer[i]))
        except Exception as ex:
            print("port {0}: {1}: offset {2}: write failed: {3}".format(self.port_index, sysfs_sfp_i2c_client_eeprom_path, hex(offset), ex))
            return False
        finally:
            if sysfsfile_eeprom is not None:
                sysfsfile_eeprom.close()

        return True

    def write_eeprom(self, offset, num_bytes, write_buffer):
        """
        write eeprom specfic bytes beginning from a random offset with size as num_bytes
        and write_buffer as the required bytes

        Args:
             offset :
                     Integer, the offset from which the read transaction will start
             num_bytes:
                     Integer, the number of bytes to be written
             write_buffer:
                     bytearray, raw bytes buffer which is to be written beginning at the offset

        Returns:
            a Boolean, true if the write succeeded and false if it did not succeed.
        """
        self.eeprom_lock.acquire()
        ret = self.__write_eeprom(offset, num_bytes, write_buffer)
        self.eeprom_lock.release()
        return ret

    def get_eeprom_raw(self, offset = 0, num_bytes = 256):
        buf = self.read_eeprom(offset, num_bytes)
        if buf is None:
            return None
        eeprom_raw = []
        for n in range(len(buf)):
            eeprom_raw.append("{0:0{1}x}".format(buf[n], 2))
        while len(eeprom_raw) < num_bytes:
            eeprom_raw.append("00")
        return eeprom_raw

    def get_eeprom_type(self, eeprom_ifraw = None):
        type = XCVR_EEPROM_TYPE_UNKNOWN

        raw = eeprom_ifraw
        if raw is None:
            raw = self.get_eeprom_raw(0, 64 if self.port_type == self.PORT_TYPE_SFP else 256)

        if raw is None:
            return type

        if (self.port_type == self.PORT_TYPE_QSFP) or (self.port_type == self.PORT_TYPE_QSFPDD):
            # QSFPDD check code validation
            if raw[128] in SFF8024_TYPE_QSFPDD:
                sum = 0
                for i in range(128, 222):
                    sum += int(raw[i], 16)
                if (sum & 0xff) == int(raw[222], 16):
                    type = XCVR_EEPROM_TYPE_OSFP
            # QSFP check code validation (CC_BASE)
            if type == XCVR_EEPROM_TYPE_UNKNOWN:
                sum = 0
                for i in range(128, 191):
                    sum += int(raw[i], 16)
                if (sum & 0xff) == int(raw[191], 16):
                    type = XCVR_EEPROM_TYPE_QSFP
        else:
            # SFP check code validation (CC_BASE)
            sum = 0
            for i in range(0, 63):
                sum += int(raw[i], 16)
            if (sum & 0xff) == int(raw[63], 16):
                type = XCVR_EEPROM_TYPE_SFP

        return type

    def get_transceiver_info(self):
        """
        Retrieves transceiver info of this SFP

        Returns:
            A dict which contains following keys/values :
        ========================================================================
        keys                       |Value Format   |Information	
        ---------------------------|---------------|----------------------------
        type                       |1*255VCHAR     |type of SFP
        hardwarerev                |1*255VCHAR     |hardware version of SFP
        serialnum                  |1*255VCHAR     |serial number of the SFP
        manufacturename            |1*255VCHAR     |SFP vendor name
        modelname                  |1*255VCHAR     |SFP model name
        Connector                  |1*255VCHAR     |connector information
        encoding                   |1*255VCHAR     |encoding information
        ext_identifier             |1*255VCHAR     |extend identifier
        ext_rateselect_compliance  |1*255VCHAR     |extended rateSelect compliance
        cable_length               |INT            |cable length in m
        mominal_bit_rate           |INT            |nominal bit rate by 100Mbs
        specification_compliance   |1*255VCHAR     |specification compliance
        vendor_date                |1*255VCHAR     |vendor date
        vendor_oui                 |1*255VCHAR     |vendor OUI
        ========================================================================
        """
        info_dict_keys = ['type', 'hardware_rev', 'serial', 'manufacturer',
                          'model', 'connector', 'encoding', 'ext_identifier',
                          'ext_rateselect_compliance','cable_type', 'cable_length', 'nominal_bit_rate',
                          'specification_compliance','type_abbrv_name','vendor_date', 'vendor_oui',
                          'application_advertisement']
        transceiver_info_dict = {}.fromkeys(info_dict_keys, 'N/A')

        eeprom_ifraw = self.get_eeprom_raw(0, 128 if self.port_type == self.PORT_TYPE_SFP else 256)
        type = self.get_eeprom_type(eeprom_ifraw)

        sfpi_obj = None
        sfp_data = None
        sfp_keys = {}
        if type == XCVR_EEPROM_TYPE_UNKNOWN:
            return None
        elif type == XCVR_EEPROM_TYPE_QSFPDD:
            sfpi_obj = inf8628InterfaceId(eeprom_ifraw)
            if sfpi_obj is None:
                return None
            sfp_data = sfpi_obj.get_data_pretty()

            sfp_keys['type']             = 'Identifier'
            sfp_keys['type_abbrv_name']  = 'type_abbrv_name'
            sfp_keys['manufacturer']     = 'Vendor Name'
            sfp_keys['model']            = 'Vendor Part Number'
            sfp_keys['hardware_rev']     = 'Vendor Revision'
            sfp_keys['serial']           = 'Vendor Serial Number'
            sfp_keys['vendor_date']      = 'Vendor Date Code(YYYY-MM-DD Lot)'
            sfp_keys['vendor_oui']       = 'Vendor OUI'
            sfp_keys['module_state']     = 'Module State'
            sfp_keys['media_type']       = 'Media Type'
            sfp_keys['power_class']      = 'Power Class'
            sfp_keys['revision_compliance'] = 'Revision Compliance'

            cable_length = float(sfp_data['data']['Length Cable Assembly(m)'])
            if cable_length != 0.0:
                transceiver_info_dict['cable_type'] = 'Length Cable Assembly(m)'
                transceiver_info_dict['cable_length'] = str(cable_length)

            app_adv_dict = sfp_data['data'].get('Application Advertisement')
            if (app_adv_dict is not None) and len(app_adv_dict) > 0:
                transceiver_info_dict['application_advertisement'] = str(app_adv_dict)

            # It's expected that PAGE1 could be unavailable
            mem_page_raw = self.get_eeprom_raw(CMIS4_IMPL_MEM_PAGES_ADDR, 1)
            if mem_page_raw is None:
                mem_page_raw = ['00']

            mem_page_data = sfpi_obj.parse_implemented_memory_pages(mem_page_raw, 0)
            if mem_page_data is not None:
                transceiver_info_dict['memory_pages'] = mem_page_data['data']['Implemented Memory Pages']['value']

        elif type == XCVR_EEPROM_TYPE_QSFP:
            sfpi_obj = sff8436InterfaceId(eeprom_ifraw)
            if sfpi_obj is None:
                return None
            sfp_data = sfpi_obj.get_data_pretty()

            sfp_keys['type']             = 'Identifier'
            sfp_keys['type_abbrv_name']  = 'type_abbrv_name'
            sfp_keys['ext_identifier']   = 'Extended Identifier'
            sfp_keys['encoding']         = 'Encoding'
            sfp_keys['ext_rateselect_compliance'] = 'Extended RateSelect Compliance'
            sfp_keys['connector']        = 'Connector'
            sfp_keys['hardware_rev']     = 'Vendor Rev'
            sfp_keys['manufacturer']     = 'Vendor Name'
            sfp_keys['model']            = 'Vendor PN'
            sfp_keys['nominal_bit_rate'] = 'Nominal Bit Rate(100Mbs)'
            sfp_keys['serial']           = 'Vendor SN'
            sfp_keys['vendor_date']      = 'Vendor Date Code(YYYY-MM-DD Lot)'
            sfp_keys['vendor_oui']       = 'Vendor OUI'

            for key in qsfp_cable_length_tup:
                if key in sfp_data['data']:
                    if sfp_data['data'][key] <= 0:
                        continue
                    transceiver_info_dict['cable_type'] = key
                    transceiver_info_dict['cable_length'] = str(sfp_data['data'][key])
                    break

            compliance_code_dict = sfp_data['data'].get('Specification compliance')
            if (compliance_code_dict is not None) and len(compliance_code_dict) > 0:
                transceiver_info_dict['specification_compliance'] = str(compliance_code_dict)

        elif type == XCVR_EEPROM_TYPE_SFP:
            sfpi_obj = sff8472InterfaceId(eeprom_ifraw)
            if sfpi_obj is None:
                return None
            sfp_data = sfpi_obj.get_data_pretty()

            sfp_keys['type']             = 'TypeOfTransceiver'
            sfp_keys['type_abbrv_name']  = 'type_abbrv_name'
            sfp_keys['manufacturer']     = 'VendorName'
            sfp_keys['model']            = 'VendorPN'
            sfp_keys['hardware_rev']     = 'VendorRev'
            sfp_keys['serial']           = 'VendorSN'
            sfp_keys['connector']        = 'Connector'
            sfp_keys['encoding']         = 'EncodingCodes'
            sfp_keys['ext_identifier']   = 'ExtIdentOfTypeOfTransceiver'
            sfp_keys['nominal_bit_rate'] = 'NominalSignallingRate(UnitsOf100Mbd)'
            sfp_keys['vendor_date']      = 'VendorDataCode(YYYY-MM-DD Lot)'
            sfp_keys['vendor_oui']       = 'VendorOUI'

            compliance_code_dict = sfp_data['data'].get('TransceiverCodes')
            if (compliance_code_dict is not None) and len(compliance_code_dict) > 0:
                transceiver_info_dict['specification_compliance'] = str(compliance_code_dict)

        for k in sfp_keys:
            dict = sfp_data['data']
            name = sfp_keys[k]
            if name in dict:
                transceiver_info_dict[k] = str(dict[name])
            else:
                transceiver_info_dict[k] = 'N/A'

        return transceiver_info_dict

    def get_transceiver_bulk_status(self):
        """
        Retrieves transceiver bulk status of this SFP

        Returns:
            A dict which contains following keys/values :
        ========================================================================
        keys                       |Value Format   |Information
        ---------------------------|---------------|----------------------------
        rx_los                     |BOOLEAN        |RX loss-of-signal status, True if has RX los, False if not.
        tx_fault                   |BOOLEAN        |TX fault status, True if has TX fault, False if not.
        reset_status               |BOOLEAN        |reset status, True if SFP in reset, False if not.
        lp_mode                    |BOOLEAN        |low power mode status, True in lp mode, False if not.
        tx_disable                 |BOOLEAN        |TX disable status, True TX disabled, False if not.
        tx_disabled_channel        |HEX            |disabled TX channels in hex, bits 0 to 3 represent channel 0
                                   |               |to channel 3.
        temperature                |INT            |module temperature in Celsius
        voltage                    |INT            |supply voltage in mV
        tx<n>bias                  |INT            |TX Bias Current in mA, n is the channel number,
                                   |               |for example, tx2bias stands for tx bias of channel 2.
        rx<n>power                 |INT            |received optical power in mW, n is the channel number,
                                   |               |for example, rx2power stands for rx power of channel 2.
        tx<n>power                 |INT            |TX output power in mW, n is the channel number,
                                   |               |for example, tx2power stands for tx power of channel 2.
        ========================================================================
        """
        transceiver_dom_info_dict = {}

        dom_info_dict_keys = ['temperature', 'voltage',  'rx1power',
                              'rx2power',    'rx3power', 'rx4power',
                              'tx1bias',     'tx2bias',  'tx3bias',
                              'tx4bias',     'tx1power', 'tx2power',
                              'tx3power',    'tx4power',
                             ]
        transceiver_dom_info_dict = {}.fromkeys(dom_info_dict_keys, 'N/A')

        eeprom_ifraw = self.get_eeprom_raw()
        type = self.get_eeprom_type(eeprom_ifraw)

        if type == XCVR_EEPROM_TYPE_UNKNOWN:
            return transceiver_dom_info_dict

        elif type == XCVR_EEPROM_TYPE_QSFPDD:
            dom_raw = [ '00' for i in range(CMIS4_PAGE_ADDR_11h + CMIS4_PAGE_SIZE) ]

            dom_pos = 0
            for x in eeprom_ifraw:
                dom_raw[dom_pos] = x
                dom_pos += 1
            dom_pos = CMIS4_PAGE_ADDR_11h
            # Clear the Lane-specific Clear-on-Read registers (e.g. LOS, LOL...)
            tmp = self.get_eeprom_raw(dom_pos + (137 & 0x7f), 16)
            # Now fetch the page 11h
            tmp = self.get_eeprom_raw(dom_pos, CMIS4_PAGE_SIZE)
            if tmp is not None:
                for x in tmp:
                    dom_raw[dom_pos] = x
                    dom_pos += 1

            sfpd_obj = inf8628Dom(dom_raw)
            if sfpd_obj is None:
                return transceiver_dom_info_dict
            dom_data = sfpd_obj.get_data_pretty()
            if dom_data is None:
                return transceiver_dom_info_dict

            transceiver_dom_info_dict['temperature'] = dom_data['data']['Temperature']
            transceiver_dom_info_dict['voltage'] = dom_data['data']['Vcc']
            transceiver_dom_info_dict['rx1power'] = dom_data['data']['RX1Power']
            transceiver_dom_info_dict['rx2power'] = dom_data['data']['RX2Power']
            transceiver_dom_info_dict['rx3power'] = dom_data['data']['RX3Power']
            transceiver_dom_info_dict['rx4power'] = dom_data['data']['RX4Power']
            transceiver_dom_info_dict['rx5power'] = dom_data['data']['RX5Power']
            transceiver_dom_info_dict['rx6power'] = dom_data['data']['RX6Power']
            transceiver_dom_info_dict['rx7power'] = dom_data['data']['RX7Power']
            transceiver_dom_info_dict['rx8power'] = dom_data['data']['RX8Power']
            transceiver_dom_info_dict['tx1bias'] = dom_data['data']['TX1Bias']
            transceiver_dom_info_dict['tx2bias'] = dom_data['data']['TX2Bias']
            transceiver_dom_info_dict['tx3bias'] = dom_data['data']['TX3Bias']
            transceiver_dom_info_dict['tx4bias'] = dom_data['data']['TX4Bias']
            transceiver_dom_info_dict['tx5bias'] = dom_data['data']['TX5Bias']
            transceiver_dom_info_dict['tx6bias'] = dom_data['data']['TX6Bias']
            transceiver_dom_info_dict['tx7bias'] = dom_data['data']['TX7Bias']
            transceiver_dom_info_dict['tx8bias'] = dom_data['data']['TX8Bias']
            transceiver_dom_info_dict['tx1power'] = dom_data['data']['TX1Power']
            transceiver_dom_info_dict['tx2power'] = dom_data['data']['TX2Power']
            transceiver_dom_info_dict['tx3power'] = dom_data['data']['TX3Power']
            transceiver_dom_info_dict['tx4power'] = dom_data['data']['TX4Power']
            transceiver_dom_info_dict['tx5power'] = dom_data['data']['TX5Power']
            transceiver_dom_info_dict['tx6power'] = dom_data['data']['TX6Power']
            transceiver_dom_info_dict['tx7power'] = dom_data['data']['TX7Power']
            transceiver_dom_info_dict['tx8power'] = dom_data['data']['TX8Power']

        elif type == XCVR_EEPROM_TYPE_QSFP:
            sfpd_obj = sff8436Dom()
            if sfpd_obj is None:
                return transceiver_dom_info_dict

            dom_temperature_data = sfpd_obj.parse_temperature(eeprom_ifraw, SFF8636_DOM_TEMP_ADDR)
            dom_voltage_data = sfpd_obj.parse_voltage(eeprom_ifraw, SFF8636_DOM_VOLT_ADDR)
            if (int(eeprom_ifraw[SFF8636_DOM_TYPE_ADDR], 16) & 0x04) > 0:
                dom_channel_monitor_data = sfpd_obj.parse_channel_monitor_params_with_tx_power(eeprom_ifraw, SFF8636_DOM_CHAN_MON_ADDR)
                transceiver_dom_info_dict['tx1power'] = dom_channel_monitor_data['data']['TX1Power']['value']
                transceiver_dom_info_dict['tx2power'] = dom_channel_monitor_data['data']['TX2Power']['value']
                transceiver_dom_info_dict['tx3power'] = dom_channel_monitor_data['data']['TX3Power']['value']
                transceiver_dom_info_dict['tx4power'] = dom_channel_monitor_data['data']['TX4Power']['value']
            else:
                dom_channel_monitor_data = sfpd_obj.parse_channel_monitor_params(eeprom_ifraw, SFF8636_DOM_CHAN_MON_ADDR)
            transceiver_dom_info_dict['temperature'] = dom_temperature_data['data']['Temperature']['value']
            transceiver_dom_info_dict['voltage'] = dom_voltage_data['data']['Vcc']['value']
            transceiver_dom_info_dict['rx1power'] = dom_channel_monitor_data['data']['RX1Power']['value']
            transceiver_dom_info_dict['rx2power'] = dom_channel_monitor_data['data']['RX2Power']['value']
            transceiver_dom_info_dict['rx3power'] = dom_channel_monitor_data['data']['RX3Power']['value']
            transceiver_dom_info_dict['rx4power'] = dom_channel_monitor_data['data']['RX4Power']['value']
            transceiver_dom_info_dict['tx1bias'] = dom_channel_monitor_data['data']['TX1Bias']['value']
            transceiver_dom_info_dict['tx2bias'] = dom_channel_monitor_data['data']['TX2Bias']['value']
            transceiver_dom_info_dict['tx3bias'] = dom_channel_monitor_data['data']['TX3Bias']['value']
            transceiver_dom_info_dict['tx4bias'] = dom_channel_monitor_data['data']['TX4Bias']['value']

        else:
            dom_raw = [ '00' for i in range(128) ]

            dom_temp_raw = self.get_eeprom_raw(SFF8472_DOM_TEMP_ADDR, 16)
            if dom_temp_raw is None:
                return transceiver_dom_info_dict
            for i in range(len(dom_temp_raw)):
                dom_raw[(SFF8472_DOM_TEMP_ADDR & 0xff) + i] = dom_temp_raw[i]

            dom_stcr_raw = self.get_eeprom_raw(SFF8472_DOM_STCR_ADDR, 1)
            if dom_stcr_raw is None:
                return transceiver_dom_info_dict
            for i in range(len(dom_stcr_raw)):
                dom_raw[(SFF8472_DOM_STCR_ADDR & 0xff) + i] = dom_stcr_raw[i]

            sfpd_obj = sff8472Dom(eeprom_raw_data=dom_raw, calibration_type=1)
            if sfpd_obj is None:
                return transceiver_dom_info_dict
            dom_data = sfpd_obj.get_data_pretty()
            transceiver_dom_info_dict['temperature'] = dom_data['data']['MonitorData']['Temperature']
            transceiver_dom_info_dict['voltage']     = dom_data['data']['MonitorData']['Vcc']
            transceiver_dom_info_dict['rx1power']    = dom_data['data']['MonitorData']['RXPower']
            transceiver_dom_info_dict['tx1power']    = dom_data['data']['MonitorData']['TXPower']
            transceiver_dom_info_dict['tx1bias']     = dom_data['data']['MonitorData']['TXBias']
            transceiver_dom_info_dict['rx1los']      = dom_data['data']['StatusControl']['RXLOSState']
            transceiver_dom_info_dict['rx1los']      = 'true' if transceiver_dom_info_dict['rx1los'] == 'On' else 'false'
            transceiver_dom_info_dict['tx1disable']  = dom_data['data']['StatusControl']['TXDisableState']
            transceiver_dom_info_dict['tx1disable']  = 'true' if transceiver_dom_info_dict['tx1disable'] == 'On' else 'false'
            transceiver_dom_info_dict['tx1fault']    = dom_data['data']['StatusControl']['TXFaultState']
            transceiver_dom_info_dict['tx1fault']    = 'true' if transceiver_dom_info_dict['tx1fault'] == 'On' else 'false'

        return transceiver_dom_info_dict

    def get_transceiver_threshold_info(self):
        """
        Retrieves transceiver threshold info of this SFP

        Returns:
            A dict which contains following keys/values :
        ========================================================================
        keys                       |Value Format   |Information
        ---------------------------|---------------|----------------------------
        temphighalarm              |FLOAT          |High Alarm Threshold value of temperature in Celsius.
        templowalarm               |FLOAT          |Low Alarm Threshold value of temperature in Celsius.
        temphighwarning            |FLOAT          |High Warning Threshold value of temperature in Celsius.
        templowwarning             |FLOAT          |Low Warning Threshold value of temperature in Celsius.
        vcchighalarm               |FLOAT          |High Alarm Threshold value of supply voltage in mV.
        vcclowalarm                |FLOAT          |Low Alarm Threshold value of supply voltage in mV.
        vcchighwarning             |FLOAT          |High Warning Threshold value of supply voltage in mV.
        vcclowwarning              |FLOAT          |Low Warning Threshold value of supply voltage in mV.
        rxpowerhighalarm           |FLOAT          |High Alarm Threshold value of received power in dBm.
        rxpowerlowalarm            |FLOAT          |Low Alarm Threshold value of received power in dBm.
        rxpowerhighwarning         |FLOAT          |High Warning Threshold value of received power in dBm.
        rxpowerlowwarning          |FLOAT          |Low Warning Threshold value of received power in dBm.
        txpowerhighalarm           |FLOAT          |High Alarm Threshold value of transmit power in dBm.
        txpowerlowalarm            |FLOAT          |Low Alarm Threshold value of transmit power in dBm.
        txpowerhighwarning         |FLOAT          |High Warning Threshold value of transmit power in dBm.
        txpowerlowwarning          |FLOAT          |Low Warning Threshold value of transmit power in dBm.
        txbiashighalarm            |FLOAT          |High Alarm Threshold value of tx Bias Current in mA.
        txbiaslowalarm             |FLOAT          |Low Alarm Threshold value of tx Bias Current in mA.
        txbiashighwarning          |FLOAT          |High Warning Threshold value of tx Bias Current in mA.
        txbiaslowwarning           |FLOAT          |Low Warning Threshold value of tx Bias Current in mA.
        ========================================================================
        """
        transceiver_dom_threshold_info_dict = {}

        dom_info_dict_keys = ['temphighalarm',    'temphighwarning',
                              'templowalarm',     'templowwarning',
                              'vcchighalarm',     'vcchighwarning',
                              'vcclowalarm',      'vcclowwarning',
                              'rxpowerhighalarm', 'rxpowerhighwarning',
                              'rxpowerlowalarm',  'rxpowerlowwarning',
                              'txpowerhighalarm', 'txpowerhighwarning',
                              'txpowerlowalarm',  'txpowerlowwarning',
                              'txbiashighalarm',  'txbiashighwarning',
                              'txbiaslowalarm',   'txbiaslowwarning'
                             ]
        transceiver_dom_threshold_info_dict = {}.fromkeys(dom_info_dict_keys, 'N/A')

        eeprom_ifraw = self.get_eeprom_raw()
        type = self.get_eeprom_type(eeprom_ifraw)

        if type == XCVR_EEPROM_TYPE_UNKNOWN:
            return transceiver_dom_threshold_info_dict

        elif type == XCVR_EEPROM_TYPE_QSFPDD:
            return transceiver_dom_threshold_info_dict

        elif type == XCVR_EEPROM_TYPE_QSFP:
            dom_raw = self.get_eeprom_raw(SFF8636_DOM_MOD_THRES_ADDR, 128)
            if dom_raw is None:
                return transceiver_dom_threshold_info_dict

            sfpd_obj = sff8436Dom()
            if sfpd_obj is None:
                return transceiver_dom_threshold_info_dict

            dom_module_threshold_data = sfpd_obj.parse_module_threshold_values(dom_raw, 0)
            dom_channel_threshold_data = sfpd_obj.parse_channel_threshold_values(dom_raw, SFF8636_DOM_CHAN_THRES_ADDR - SFF8636_DOM_MOD_THRES_ADDR)
            transceiver_dom_threshold_info_dict['temphighalarm']   = dom_module_threshold_data['data']['TempHighAlarm']['value']
            transceiver_dom_threshold_info_dict['temphighwarning'] = dom_module_threshold_data['data']['TempHighWarning']['value']
            transceiver_dom_threshold_info_dict['templowalarm']    = dom_module_threshold_data['data']['TempLowAlarm']['value']
            transceiver_dom_threshold_info_dict['templowwarning']  = dom_module_threshold_data['data']['TempLowWarning']['value']
            transceiver_dom_threshold_info_dict['vcchighalarm']    = dom_module_threshold_data['data']['VccHighAlarm']['value']
            transceiver_dom_threshold_info_dict['vcchighwarning']  = dom_module_threshold_data['data']['VccHighWarning']['value']
            transceiver_dom_threshold_info_dict['vcclowalarm']     = dom_module_threshold_data['data']['VccLowAlarm']['value']
            transceiver_dom_threshold_info_dict['vcclowwarning']   = dom_module_threshold_data['data']['VccLowWarning']['value']
            transceiver_dom_threshold_info_dict['rxpowerhighalarm']   = dom_channel_threshold_data['data']['RxPowerHighAlarm']['value']
            transceiver_dom_threshold_info_dict['rxpowerhighwarning'] = dom_channel_threshold_data['data']['RxPowerHighWarning']['value']
            transceiver_dom_threshold_info_dict['rxpowerlowalarm']    = dom_channel_threshold_data['data']['RxPowerLowAlarm']['value']
            transceiver_dom_threshold_info_dict['rxpowerlowwarning']  = dom_channel_threshold_data['data']['RxPowerLowWarning']['value']
            transceiver_dom_threshold_info_dict['txbiashighalarm']    = dom_channel_threshold_data['data']['TxBiasHighAlarm']['value']
            transceiver_dom_threshold_info_dict['txbiashighwarning']  = dom_channel_threshold_data['data']['TxBiasHighWarning']['value']
            transceiver_dom_threshold_info_dict['txbiaslowalarm']     = dom_channel_threshold_data['data']['TxBiasLowAlarm']['value']
            transceiver_dom_threshold_info_dict['txbiaslowwarning']   = dom_channel_threshold_data['data']['TxBiasLowWarning']['value']

        elif type == XCVR_EEPROM_TYPE_SFP:
            dom_raw = self.get_eeprom_raw(SFF8472_DOM_MOD_THRES_ADDR, 40)
            if dom_raw is None:
                return transceiver_dom_threshold_info_dict
            sfpd_obj = sff8472Dom(calibration_type=1)
            if sfpd_obj is None:
                return transceiver_dom_threshold_info_dict

            dom_threshold_data = sfpd_obj.parse_alarm_warning_threshold(dom_raw, 0)
            transceiver_dom_threshold_info_dict['temphighalarm']      = dom_threshold_data['data']['TempHighAlarm']['value']
            transceiver_dom_threshold_info_dict['temphighwarning']    = dom_threshold_data['data']['TempHighWarning']['value']
            transceiver_dom_threshold_info_dict['templowalarm']       = dom_threshold_data['data']['TempLowAlarm']['value']
            transceiver_dom_threshold_info_dict['templowwarning']     = dom_threshold_data['data']['TempLowWarning']['value']
            transceiver_dom_threshold_info_dict['vcchighalarm']       = dom_threshold_data['data']['VoltageHighAlarm']['value']
            transceiver_dom_threshold_info_dict['vcchighwarning']     = dom_threshold_data['data']['VoltageHighWarning']['value']
            transceiver_dom_threshold_info_dict['vcclowalarm']        = dom_threshold_data['data']['VoltageLowAlarm']['value']
            transceiver_dom_threshold_info_dict['vcclowwarning']      = dom_threshold_data['data']['VoltageLowWarning']['value']
            transceiver_dom_threshold_info_dict['rxpowerhighalarm']   = dom_threshold_data['data']['RXPowerHighAlarm']['value']
            transceiver_dom_threshold_info_dict['rxpowerhighwarning'] = dom_threshold_data['data']['RXPowerHighWarning']['value']
            transceiver_dom_threshold_info_dict['rxpowerlowalarm']    = dom_threshold_data['data']['RXPowerLowAlarm']['value']
            transceiver_dom_threshold_info_dict['rxpowerlowwarning']  = dom_threshold_data['data']['RXPowerLowWarning']['value']
            transceiver_dom_threshold_info_dict['txbiashighalarm']    = dom_threshold_data['data']['BiasHighAlarm']['value']
            transceiver_dom_threshold_info_dict['txbiashighwarning']  = dom_threshold_data['data']['BiasHighWarning']['value']
            transceiver_dom_threshold_info_dict['txbiaslowalarm']     = dom_threshold_data['data']['BiasLowAlarm']['value']
            transceiver_dom_threshold_info_dict['txbiaslowwarning']   = dom_threshold_data['data']['BiasLowWarning']['value']
            transceiver_dom_threshold_info_dict['txpowerhighalarm']   = dom_threshold_data['data']['TXPowerHighAlarm']['value']
            transceiver_dom_threshold_info_dict['txpowerhighwarning'] = dom_threshold_data['data']['TXPowerHighWarning']['value']
            transceiver_dom_threshold_info_dict['txpowerlowalarm']    = dom_threshold_data['data']['TXPowerLowAlarm']['value']
            transceiver_dom_threshold_info_dict['txpowerlowwarning']  = dom_threshold_data['data']['TXPowerLowWarning']['value']

        else:
            pass

        return transceiver_dom_threshold_info_dict

    def soft_reset(self):
        """
        Reset SFP and return all user module settings to their default srate.

        Returns:
            A boolean, True if successful, False if not
        """
        if (self.port_type != SfpStandard.PORT_TYPE_QSFPDD):
            return False

        self.eeprom_lock.acquire()

        # Identifier
        id = self.__read_eeprom(SfpStandard.CMIS_REG_ID, 1)
        if (id is None) or (id[0] not in SfpStandard.CMIS_IDS):
            self.eeprom_lock.release()
            return False

        # Revision Compliance ID
        rev = self.__read_eeprom(SfpStandard.CMIS_REG_REV, 1)
        if (rev is None) or (rev[0] < 0x30):
            self.eeprom_lock.release()
            return False

        off = SfpStandard.CMIS_REG_MOD_CTRL
        val = SfpStandard.CMIS_MOD_CTRL_SW_RESET | SfpStandard.CMIS_MOD_CTRL_FORCE_LP
        ret = self.__write_eeprom(off, 1, [val])
        if ret:
            time.sleep(1)

        self.eeprom_lock.release()
        return ret
