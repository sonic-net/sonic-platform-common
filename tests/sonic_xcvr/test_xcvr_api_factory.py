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

    def test_get_transceiver_info(self, amph_backplane, monkeypatch):
        """
        Test the get_transceiver_info method.
        """
        # Mock the admin_info returned by xcvr_eeprom.read
        admin_info = {
            consts.VENDOR_SERIAL_NO_FIELD: "SN12345",
            consts.VENDOR_NAME_FIELD: "Amphenol",
            consts.VENDOR_PART_NO_FIELD: "ModelX",
            consts.VENDOR_DATE_FIELD: "2025-03-31", 
            consts.VENDOR_OUI_FIELD: "00:11:22",
            consts.VENDOR_REV_FIELD: "RevA",
            "type": "Type1",
            "type_abbrv_name": "T1",
            "specification_compliance": "passive_copper_media_interface",
            "Identifier": "Backplane Catridge",
            "Identifier Abbreviation" : "BPC",
            "Length Cable Assembly" : "2.0",
        }

        amph_backplane.xcvr_eeprom.read = MagicMock()
        amph_backplane.xcvr_eeprom.read.side_effect = lambda field: admin_info if field == consts.ADMIN_INFO_FIELD else "1" if field == consts.CARTRDIGE_SLOT_ID else None

        # Mock all the required functions
        monkeypatch.setattr(amph_backplane, "get_module_hardware_revision", MagicMock(return_value="Rev1"))
        monkeypatch.setattr(amph_backplane, "get_application_advertisement", MagicMock(return_value="['App1', 'App2']"))
        monkeypatch.setattr(amph_backplane, "get_host_electrical_interface", MagicMock(return_value="400GBASE-CR4 (Clause 162)"))
        monkeypatch.setattr(amph_backplane, "get_host_lane_count", MagicMock(return_value=4))
        monkeypatch.setattr(amph_backplane, "get_cable_length", MagicMock(return_value=2.0))
        monkeypatch.setattr(amph_backplane, "get_cmis_rev", MagicMock(return_value="CMIS5.0"))
        monkeypatch.setattr(amph_backplane, "is_transceiver_vdm_supported", MagicMock(return_value=False))
        monkeypatch.setattr(amph_backplane, "get_host_lane_assignment_option", MagicMock(return_value=1))
        monkeypatch.setattr(amph_backplane, "get_vendor_rev", MagicMock(return_value="RevA"))
        monkeypatch.setattr(amph_backplane, "get_module_media_type", MagicMock(return_value='passive_copper_media_interface'))

        # Call the method under test
        result = amph_backplane.get_transceiver_info()

        # Expected result based on mocked values and admin_info
        expected_info = {
            "type": "Backplane Catridge",
            "type_abbrv_name": "BPC",
            "hardware_rev": "Rev1",
            "cable_length": 2.0,
            "application_advertisement": "['App1', 'App2']",
            "host_electrical_interface": "400GBASE-CR4 (Clause 162)",
            "host_lane_count": 4,
            "cable_type": "Length Cable Assembly(m)",
            "cmis_rev": "CMIS5.0",
            "specification_compliance": "passive_copper_media_interface",
            "vdm_supported": False,
            "serial": "SN12345",
            "manufacturer": "Amphenol",
            "model": "ModelX",
            "vendor_date": "2025-03-31",
            "vendor_oui": "00:11:22",
            "vendor_rev": "RevA",
            "slot_id": "1",
            "host_lane_assignment_option": 1,
        }

        # Verify the result
        assert result == expected_info
    
    def test_get_transceiver_info_none(self, amph_backplane):
        """Test get_transceiver_info when admin_info is None"""
        # Override the mock to return None for admin_info
        amph_backplane.xcvr_eeprom.read.return_value = None
        # Call the method
        transceiver_info = amph_backplane.get_transceiver_info()
        
        # Verify the result is None
        assert transceiver_info is None