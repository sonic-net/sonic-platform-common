from unittest.mock import patch
from mock import MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.api.hisense.aoc_2x100g import CmisAocSingleBankApi

class TestCmisAocSingleBankApi(object):
    codes = CmisCodes
    mem_map = CmisMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = CmisAocSingleBankApi(eeprom)

    @pytest.mark.parametrize("mock_response, expected", [
        ({'status': 1, 'rpl': (128, 1, [0x43, 0, 2, 5, 0, 3] + [0] * 122)}, {'status': True, 'info': "", 'result': 
        ('2.5.3', 1, 1, 0, 'N/A', 0, 0, 1, '2.5.3', '1.1.0')}),
        ({'status': 1, 'rpl': (128, 1, [0x40, 0, 1, 0, 0, 1] + [0] * 122)}, {'status': True, 'info': "", 'result': 
        ('1.0.1', 0, 0, 0, 'N/A', 0, 0, 1, 'N/A', 'N/A')}),
        ({'status': 1, 'rpl': (128, 1, [0x44] + [0] * 127)}, {'status': True, 'info': "", 'result': ('N/A', 0, 0, 1, 'N/A', 0, 0, 1, 'N/A', 'N/A')}),
        ({'status': 1, 'rpl': (None, 1, [0] * 128)}, {'status': False, 'info': "", 'result': 0}),
        ({'status': 1, 'rpl': (128, None, [0] * 128)}, {'status': False, 'info': "", 'result': 0}),
        ({'status': 1, 'rpl': (128, 0, [0] * 128)}, {'status': False, 'info': "", 'result': None}),
        ({'status': 0x46, 'rpl': (128, 0, [0] * 128)}, {'status': False, 'info': "", 'result': None}),
    ])
    def test_get_module_fw_info(self, mock_response, expected):
        self.api.cdb = MagicMock()
        self.api.cdb.cdb_chkcode = MagicMock()
        self.api.cdb.cdb_chkcode.return_value = 1
        self.api.get_module_inactive_firmware = MagicMock()
        self.api.get_module_inactive_firmware.return_value = "1.1"
        self.api.cdb.get_fw_info = MagicMock()
        self.api.cdb.get_fw_info.return_value = mock_response
        result = self.api.get_module_fw_info()
        assert result['status'] == expected['status']
        assert result['result'] == expected['result']

    def test_get_module_fw_info_cdb_none(self):
        self.api.cdb = None
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': "CDB Not supported", 'result': None}
