from unittest.mock import Mock, call
import copy
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.sfp_optoe_base import SfpOptoeBase

EEPROM_HEX = [
 '18', '40', '80', '07', '00', '00', '00', '00', '00', '00', '00', '00', '00', 
 '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', 
 '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', 
 '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', 
 '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', 
 '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', 
 '00', '00', '00', '00', '00', '00', '00', '03', '1d', '01', '88', '01', '1c', 
 '01', '44', '11', '1b', '01', '22', '55', '1a', '01', '44', '11', '18', '01', 
 '11', 'ff', '45', '01', '22', '55', '16', '01', '11', 'ff', '01', '01', '11', 
 'ff', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '18', '4d', 
 '65', '6c', '6c', '61', '6e', '6f', '78', '20', '20', '20', '20', '20', '20', 
 '20', '20', '00', '02', 'c9', '4d', '43', '50', '31', '36', '36', '30', '2d', 
 '57', '30', '30', '41', '45', '33', '30', '20', '41', '33', '4d', '54', '32', 
 '31', '32', '30', '56', '53', '30', '33', '38', '37', '35', '20', '20', '20', 
 '32', '31', '30', '35', '31', '34', '20', '20', '20', '20', '20', '20', '20', 
 '20', '20', '20', '20', '20', '00', '01', '05', '23', '03', '04', '06', '10', 
 '00', '00', '00', '02', '0a', '00', '00', '00', '00', '00', '00', '00', '00', 
 '00', 'a6', '00', '33', '30', '33', '33', '30', '4b', '4c', '36', '36', '30', 
 '31', '4c', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', '00', 
 '00', '00', '00', '00', '00', '00', '00', '00', '00'
]

ADMIN_INFO_OUTPUT = {
    "Identifier": "QSFP-DD Double Density 8X Pluggable Transceiver",
    "Identifier Abbreviation": "QSFP-DD",
    "VendorName": "Mellanox        ",
    "VendorOUI": "00-02-c9",
    "VendorPN": "MCP1660-W00AE30 ",
    "VendorRev": "A3",
    "VendorSN": "MT2120VS03875   ",
    "VendorDate": "2021-05-14   ",
    "Extended Identifier": {
        "Power Class": "Power Class 1",
        "MaxPower": 0.25
    },
    "LengthMultiplier": 0,
    "Connector": "No separable connector",
    "HostElectricalInterfaceID": "400G CR8",
    "ModuleMediaType": "passive_copper_media_interface",
    "ModuleMediaInterface850nm": "10GBASE-SW (Clause 52)",
    "ModuleMediaInterfaceSM": "10GBASE-LW (Cl 52)",
    "ModuleMediaInterfacePassiveCopper": "Copper cable",
    "ModuleMediaInterfaceActiveCable": "Active Cable assembly with BER < 10^-12",
    "ModuleMediaInterfaceBaseT": "1000BASE-T (Clause 40)",
    "MediaLaneCount": 8,
    "HostLaneCount": 8,
    "HostLaneAssignmentOptions": 1,
    "MediaInterfaceTechnology": "Copper cable unequalized",
    "CmisMajorRevision": 4,
    "CmisMinorRevision": 0,
    "ModuleActiveFirmwareMajorRevision": 0,
    "ModuleActiveFirmwareMinorRevision": 0,
    "Length Cable Assembly": 0.5
}

def mock_eeprom_reader(offset, length):
    if offset + length > 256:
        return None
    global EEPROM_HEX
    eeprom_raw = list(map(lambda h: int(h, base=16), EEPROM_HEX))
    return bytearray(eeprom_raw[offset:offset+length])

class MockSfp(SfpOptoeBase):

    def __init__(self): #reader_mock):
        # self.reader_mock = reader_mock
        SfpOptoeBase.__init__(self)

    def read_eeprom(self, offset, length):
        return mock_eeprom_reader(offset, length)
        # return self.reader_mock(offset, length)


class TestXcvrEeprom:
    def test_xcvr_read(self):
        reader_mock = Mock()
        reader_mock.side_effect = mock_eeprom_reader
        codes = CmisCodes
        mem_map = CmisMemMap(codes)
        xcvr_eeprom = XcvrEeprom(reader_mock, Mock(), mem_map)
        assert xcvr_eeprom.read("ModuleMediaType") == "passive_copper_media_interface"
        reader_mock.assert_called_with(85, 1)
        result = xcvr_eeprom.read("AdminInfo")
        reader_mock.assert_called_with(0, 213)
        for key, val in ADMIN_INFO_OUTPUT.items():
            assert key in result
            assert result[key] == val
    
    def test_xcvr_raw_read(self):
        reader_mock = Mock()
        reader_mock.side_effect = mock_eeprom_reader
        codes = CmisCodes
        mem_map = CmisMemMap(codes)
        xcvr_eeprom = XcvrEeprom(reader_mock, Mock(), mem_map)
        assert xcvr_eeprom.read_raw(85, 1) == 3
        reader_mock.assert_called_with(85, 1)
        xcvr_eeprom.read_raw(0, 213)
        reader_mock.assert_called_with(0, 213)

    def test_xcvr_read(self):
        reader_mock = Mock()
        reader_mock.side_effect = mock_eeprom_reader
        codes = CmisCodes
        mem_map = CmisMemMap(codes)
        xcvr_eeprom = XcvrEeprom(reader_mock, Mock(), mem_map)
        assert xcvr_eeprom.read("ModuleMediaType") == "passive_copper_media_interface"
        reader_mock.assert_called_with(85, 1)
        result = xcvr_eeprom.read("AdminInfo")
        reader_mock.assert_called_with(0, 213)
        for key, val in ADMIN_INFO_OUTPUT.items():
            assert key in result
            assert result[key] == val
    
    def test_xcvr_read_data_change(self):
        reader_mock = Mock()
        reader_mock.side_effect = mock_eeprom_reader
        codes = CmisCodes
        mem_map = CmisMemMap(codes)
        xcvr_eeprom = XcvrEeprom(reader_mock, Mock(), mem_map)
        global EEPROM_HEX
        EEPROM_HEX_ORIG = copy.deepcopy(EEPROM_HEX)
        assert xcvr_eeprom.read("ModuleMediaType") == "passive_copper_media_interface"
        EEPROM_HEX[85] = '04'
        assert xcvr_eeprom.read("ModuleMediaType") == "active_cable_media_interface"
        EEPROM_HEX[85] = '05'
        assert xcvr_eeprom.read("ModuleMediaType") == "base_t_media_interface"
        EEPROM_HEX[85] = '02'
        assert xcvr_eeprom.read("ModuleMediaType") == "sm_media_interface"
        EEPROM_HEX = copy.deepcopy(EEPROM_HEX_ORIG)
    
    def test_xcvr_read_cache(self):
        reader_mock = Mock()
        reader_mock.side_effect = mock_eeprom_reader
        codes = CmisCodes
        mem_map = CmisMemMap(codes)
        xcvr_eeprom = XcvrEeprom(reader_mock, Mock(), mem_map)
        xcvr_eeprom.refresh_cache()
        assert xcvr_eeprom.read("ModuleMediaType") == "passive_copper_media_interface"
        result = xcvr_eeprom.read("AdminInfo")
        for key, val in ADMIN_INFO_OUTPUT.items():
            assert key in result
            assert result[key] == val
        reader_mock.assert_called_once_with(0, 256) # only one call is made to eeprom
        assert xcvr_eeprom.cache is not None
        xcvr_eeprom.clear_cache()
        assert xcvr_eeprom.cache is None
    
    def test_xcvr_raw_read_outside_cache_range(self):
        reader_mock = Mock()
        reader_mock.side_effect = mock_eeprom_reader
        codes = CmisCodes
        mem_map = CmisMemMap(codes)
        xcvr_eeprom = XcvrEeprom(reader_mock, Mock(), mem_map)
        xcvr_eeprom.refresh_cache()
        assert xcvr_eeprom.read_raw(85, 1) == 3
        assert xcvr_eeprom.read_raw(256, 1) == None
        reader_mock.assert_has_calls([call(0, 256), call(256, 1)])
        xcvr_eeprom.clear_cache()

    def test_xcvr_read_cache_dynamic_data(self):
        reader_mock = Mock()
        reader_mock.side_effect = mock_eeprom_reader
        codes = CmisCodes
        mem_map = CmisMemMap(codes)
        xcvr_eeprom = XcvrEeprom(reader_mock, Mock(), mem_map)
        xcvr_eeprom.refresh_cache()
        assert xcvr_eeprom.read("ModuleMediaType") == "passive_copper_media_interface"
        assert xcvr_eeprom.cache is not None
        global EEPROM_HEX
        EEPROM_HEX_ORIG = copy.deepcopy(EEPROM_HEX)
        # Data is read from cache and dynamic changes are not updated
        assert xcvr_eeprom.read("ModuleMediaType") == "passive_copper_media_interface"
        EEPROM_HEX[85] = '04'
        assert xcvr_eeprom.read("ModuleMediaType") == "passive_copper_media_interface"
        EEPROM_HEX[85] = '05'
        assert xcvr_eeprom.read("ModuleMediaType") == "passive_copper_media_interface"
        EEPROM_HEX[85] = '02'
        assert xcvr_eeprom.read("ModuleMediaType") == "passive_copper_media_interface"
        EEPROM_HEX = copy.deepcopy(EEPROM_HEX_ORIG)
        reader_mock.assert_called_once_with(0, 256)
        xcvr_eeprom.clear_cache()
        assert xcvr_eeprom.cache is None
    
    def test_sfp_get_transciever_info(self):
        sfp = MockSfp()
        # Mokey patch the xcvr_eeprom with mock reader
        reader_mock = Mock()
        reader_mock.side_effect = mock_eeprom_reader
        sfp.get_xcvr_api().xcvr_eeprom.reader = reader_mock
        sfp.get_transceiver_info()
        reader_mock.assert_called_once_with(0, 256)
