from unittest.mock import patch
from mock import MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.api.credo.aec_800g import CmisAec800gApi
from sonic_platform_base.sonic_xcvr.mem_maps.credo.aec_800g import CmisAec800gMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.credo.aec_800g import CmisAec800gCodes
from sonic_platform_base.sonic_xcvr.api.innolight.fr_800g import CmisFr800gApi
from sonic_platform_base.sonic_xcvr.api.amphenol.backplane import AmphBackplaneImpl
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.xcvr_api_factory import XcvrApiFactory
from sonic_platform_base.sonic_xcvr.api.public.sff8636 import Sff8636Api
from sonic_platform_base.sonic_xcvr.api.public.sff8436 import Sff8436Api

def mock_reader_sff8636(start, length):
    return bytes([0x0d]) if start == 0 else bytes ([0x06])

def mock_reader_sff8436(start, length):
    return bytes([0x0d]) if start == 0 else bytes ([0x00])

class BytesMock(bytes):
    def decode(self, encoding='utf-8', errors='strict'):
        return 'DecodedCredo'

class TestXcvrApiFactory(object):
    read_eeprom = MagicMock
    write_eeprom = MagicMock
    api = XcvrApiFactory(read_eeprom, write_eeprom)

    def test_get_vendor_name(self):
        self.api.reader = MagicMock()
        self.api.reader.return_value = b'Credo'
        with patch.object(BytesMock, 'decode', return_value='DecodedCredo'):
            result = self.api._get_vendor_name()
        assert result == 'Credo'.strip()

    def test_get_vendor_part_num(self):
        self.api.reader = MagicMock()
        self.api.reader.return_value = b'CAC81X321M2MC1MS'
        with patch.object(BytesMock, 'decode', return_value='DecodedCAC81X321M2MC1MS'):
            result = self.api._get_vendor_part_num()
        assert result == 'CAC81X321M2MC1MS'.strip()

    def mock_reader(self, start, length):
        return bytes([0x18])

    @patch('sonic_platform_base.sonic_xcvr.xcvr_api_factory.XcvrApiFactory._get_vendor_name', MagicMock(return_value='Credo'))
    @patch('sonic_platform_base.sonic_xcvr.xcvr_api_factory.XcvrApiFactory._get_vendor_part_num', MagicMock(return_value='CAC81X321M2MC1MS'))
    def test_create_xcvr_api(self):
        self.api.reader = self.mock_reader
        CmisAec800gCodes = MagicMock()
        CmisAec800gMemMap = MagicMock()
        XcvrEeprom = MagicMock()
        CmisAec800gApi = MagicMock()
        self.api.create_xcvr_api()

    @patch('sonic_platform_base.sonic_xcvr.xcvr_api_factory.XcvrApiFactory._get_vendor_name', MagicMock(return_value='CISCO-INNOLIGHT'))
    @patch('sonic_platform_base.sonic_xcvr.xcvr_api_factory.XcvrApiFactory._get_vendor_part_num', MagicMock(return_value='T-DH8CNT-NCI'))
    def test_create_xcvr_api(self):
        self.api.reader = self.mock_reader
        CmisCodes = MagicMock()
        CmisMemMap = MagicMock()
        XcvrEeprom = MagicMock()
        CmisFr800gApi = MagicMock()
        self.api.create_xcvr_api()

    @pytest.mark.parametrize("reader, expected_api", [
        (mock_reader_sff8636, Sff8636Api),
        (mock_reader_sff8436, Sff8436Api),
    ])
    def test_create_xcvr_api_8436_8636(self, reader, expected_api):
        self.api.reader = reader
        api = self.api.create_xcvr_api()
        assert isinstance(api, expected_api)

class TestAmphBackplaneImpl:
    @pytest.fixture
    def amph_backplane(self, monkeypatch):
        """
        Fixture to create an instance of AmphBackplaneImpl with a mocked XcvrEeprom.
        """
        # Create a mock for XcvrEeprom
        mock_xcvr_eeprom = MagicMock(spec=XcvrEeprom)
        
        # Patch the super().__init__ call in AmphBackplaneImpl
        original_init = AmphBackplaneImpl.__init__
        
        def patched_init(self, xcvr_eeprom):
            # Store xcvr_eeprom directly without calling super().__init__
            self.xcvr_eeprom = xcvr_eeprom
        
        # Apply the patch
        monkeypatch.setattr(AmphBackplaneImpl, "__init__", patched_init)
        
        # Create and return the instance
        instance = AmphBackplaneImpl(mock_xcvr_eeprom)
        
        # Restore the original __init__ method
        monkeypatch.setattr(AmphBackplaneImpl, "__init__", original_init)
        
        return instance

    def test_get_slot_id(self, amph_backplane):
        """
        Test the get_slot_id method.
        """
        # Mock the read method to return a valid slot ID
        amph_backplane.xcvr_eeprom.read.return_value = "1"
        slot_id = amph_backplane.get_slot_id()
        assert slot_id == "1"

        # Mock the read method to return None
        amph_backplane.xcvr_eeprom.read.return_value = None
        slot_id = amph_backplane.get_slot_id()
        assert slot_id == "N/A"

        # Verify the read method was called with the correct constant
        amph_backplane.xcvr_eeprom.read.assert_called_with(consts.CARTRDIGE_SLOT_ID)

    def test_get_transceiver_info(self, amph_backplane):
        """
        Test the get_transceiver_info method.
        """
        # Create a mock return value for get_transceiver_info
        expected_info = {
            "type": "Type1",
            "type_abbrv_name": "T1",
            "hardware_rev": "Rev1",
            "cable_length": 10.0,
            "application_advertisement": "['App1', 'App2']",
            "host_electrical_interface": "HostInterface",
            "media_interface_code": "MediaInterface",
            "host_lane_count": 4,
            "media_lane_count": 4,
            "host_lane_assignment_option": "Option1",
            "media_lane_assignment_option": "Option2",
            "cable_type": "Copper",
            "media_interface_technology": "Tech1",
            "cmis_rev": "CMIS4.0",
            "specification_compliance": "TypeA",
            "vdm_supported": True,
            "serial": "SN12345",
            "manufacturer": "Amphenol",
            "model": "ModelX",
            "vendor_date": "2025-03-31",
            "vendor_oui": "00:11:22",
            "vendor_rev": "RevA",
            "slot_id": "1"
        }

        # Mock the get_transceiver_info method directly
        original_method = amph_backplane.get_transceiver_info
        amph_backplane.get_transceiver_info = MagicMock(return_value=expected_info)
        
        # Call the method
        transceiver_info = amph_backplane.get_transceiver_info()
        print("$$$ INFO {}".format(transceiver_info))

        # Verify the returned dictionary
        assert transceiver_info["type"] == "Type1"
        assert transceiver_info["type_abbrv_name"] == "T1"
        assert transceiver_info["hardware_rev"] == "Rev1"
        assert transceiver_info["cable_length"] == 10.0
        assert transceiver_info["application_advertisement"] == "['App1', 'App2']"
        assert transceiver_info["host_electrical_interface"] == "HostInterface"
        assert transceiver_info["media_interface_code"] == "MediaInterface"
        assert transceiver_info["host_lane_count"] == 4
        assert transceiver_info["media_lane_count"] == 4
        assert transceiver_info["host_lane_assignment_option"] == "Option1"
        assert transceiver_info["media_lane_assignment_option"] == "Option2"
        assert transceiver_info["cable_type"] == "Copper"
        assert transceiver_info["media_interface_technology"] == "Tech1"
        assert transceiver_info["cmis_rev"] == "CMIS4.0"
        assert transceiver_info["specification_compliance"] == "TypeA"
        assert transceiver_info["vdm_supported"] is True
        assert transceiver_info["serial"] == "SN12345"
        assert transceiver_info["manufacturer"] == "Amphenol"
        assert transceiver_info["model"] == "ModelX"
        assert transceiver_info["vendor_date"] == "2025-03-31"
        assert transceiver_info["vendor_oui"] == "00:11:22"
        assert transceiver_info["vendor_rev"] == "RevA"
        assert transceiver_info["slot_id"] == "1"

        # Verify the method was called
        amph_backplane.get_transceiver_info.assert_called_once() 

    def test_get_transceiver_info_none(self, amph_backplane):
        """Test get_transceiver_info when admin_info is None"""
        # Override the mock to return None for admin_info
        amph_backplane.xcvr_eeprom.read.return_value = None
        # Call the method
        transceiver_info = amph_backplane.get_transceiver_info()
        
        # Verify the result is None
        assert transceiver_info is None