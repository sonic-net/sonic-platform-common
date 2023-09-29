from mock import MagicMock 
from mock import patch 
import pytest 
from sonic_platform_base.sonic_xcvr.sfp_optoe_base import SfpOptoeBase 
from sonic_platform_base.sonic_xcvr.api.public.c_cmis import CCmisApi 
from sonic_platform_base.sonic_xcvr.mem_maps.public.c_cmis import CCmisMemMap 
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom 
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes 
 
class TestSfpOptoeBase(object): 
 
    codes = CmisCodes 
    mem_map = CCmisMemMap(codes) 
    reader = MagicMock(return_value=None) 
    writer = MagicMock() 
    eeprom = XcvrEeprom(reader, writer, mem_map) 
    sfp_optoe_api = SfpOptoeBase() 
    ccmis_api = CCmisApi(eeprom) 
 
    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [ 
        (0, ccmis_api, 0), 
        (1, ccmis_api, 1), 
    ]) 
    def test_freeze_vdm_stats(self, mock_response1, mock_response2, expected): 
        self.sfp_optoe_api.get_xcvr_api = MagicMock() 
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2  
        self.ccmis_api.freeze_vdm_stats = MagicMock() 
        self.ccmis_api.freeze_vdm_stats.return_value = mock_response1 
         
        result = self.sfp_optoe_api.freeze_vdm_stats() 
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (0, ccmis_api, 0),
        (1, ccmis_api, 1),
        (None, None, None),
    ])
    def test_unfreeze_vdm_stats(self, mock_response1, mock_response2, expected):
        self.sfp_optoe_api.get_xcvr_api = MagicMock()
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2
        self.ccmis_api.unfreeze_vdm_stats = MagicMock()
        self.ccmis_api.unfreeze_vdm_stats.return_value = mock_response1

        result = self.sfp_optoe_api.unfreeze_vdm_stats()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (0, ccmis_api, 0),
        (1, ccmis_api, 1),
        (None, None, None),
    ])
    def test_get_freeze_vdm_stats(self, mock_response1, mock_response2, expected):
        self.sfp_optoe_api.get_xcvr_api = MagicMock()
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2
        self.ccmis_api.get_freeze_vdm_stats = MagicMock()
        self.ccmis_api.get_freeze_vdm_stats.return_value = mock_response1

        result = self.sfp_optoe_api.get_freeze_vdm_stats()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (0, ccmis_api, 0),
        (1, ccmis_api, 1), 
        (None, None, None),
    ])
    def test_get_unfreeze_vdm_stats(self, mock_response1, mock_response2, expected):
        self.sfp_optoe_api.get_xcvr_api = MagicMock()
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2
        self.ccmis_api.get_unfreeze_vdm_stats = MagicMock()
        self.ccmis_api.get_unfreeze_vdm_stats.return_value = mock_response1
        
        result = self.sfp_optoe_api.get_unfreeze_vdm_stats()
        assert result == expected

