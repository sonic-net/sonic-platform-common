from unittest.mock import patch, MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.api.pinewave.cmis_module_precoding import PinewaveCmisApi
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.pinewave.cmis_module_precoding import PinewaveCmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.xcvr_api_factory import XcvrApiFactory
from sonic_platform_base.sonic_xcvr.fields import pinewave_consts as pw


def mock_reader_cmis(start, length):
    return bytes([0x18])


class TestCmisApiModulePrecodingDefaults(object):
    def test_defaults(self):
        api = CmisApi(XcvrEeprom(MagicMock(), MagicMock(), CmisMemMap(CmisCodes)))
        assert not api.is_module_precoding_supported()
        assert api.get_module_precoding() is None
        assert not api.set_module_precoding({'TP1': False})


class TestPinewaveCmisMemMap(object):
    def test_module_precoding_field(self):
        field = PinewaveCmisMemMap(CmisCodes).get_field(pw.MODULE_PRECODING_CONTROL)
        assert field.get_offset() == 29
        assert field.get_size() == 1
        assert not field.ro


class TestPinewaveCmisApi(object):
    def make_api(self, byte29, write_ret=True, latch=True):
        api = PinewaveCmisApi(XcvrEeprom(MagicMock(), MagicMock(), PinewaveCmisMemMap(CmisCodes)))
        reg = {pw.MODULE_PRECODING_CONTROL: byte29}

        def write(field, value):
            if write_ret and latch:
                reg[field] = value
            return write_ret

        api.xcvr_eeprom.read = MagicMock(side_effect=lambda field: reg.get(field))
        api.xcvr_eeprom.write = MagicMock(side_effect=write)
        return api

    def test_is_module_precoding_supported(self):
        assert self.make_api(0x0C).is_module_precoding_supported()

    @pytest.mark.parametrize("byte29, expected", [
        (0x0C, {'TP1': True, 'TP4': True}),
        (0x04, {'TP1': False, 'TP4': True}),
        (0xF3, {'TP1': False, 'TP4': False}),
        (None, None),
    ])
    def test_get_module_precoding(self, byte29, expected):
        assert self.make_api(byte29).get_module_precoding() == expected

    @pytest.mark.parametrize("precoding, byte29, expected_write", [
        ({'TP1': False}, 0x0C, 0x04),
        ({'TP1': False, 'TP4': True}, 0x09, 0x05),
        ({'TP1': 1, 'TP4': 1}, 0x01, 0x0D),
        ({'TP4': False}, 0xFF, 0xFB),
    ])
    def test_set_module_precoding(self, precoding, byte29, expected_write):
        api = self.make_api(byte29)
        assert api.set_module_precoding(precoding)
        api.xcvr_eeprom.write.assert_called_once_with(pw.MODULE_PRECODING_CONTROL, expected_write)
        assert api.xcvr_eeprom.read.call_count == 2

    @pytest.mark.parametrize("precoding, byte29", [
        ({'TP1': False}, 0x04),  # already set
        ({}, 0x0C),              # nothing requested
    ])
    def test_set_module_precoding_no_write(self, precoding, byte29):
        api = self.make_api(byte29)
        assert api.set_module_precoding(precoding)
        api.xcvr_eeprom.write.assert_not_called()

    @pytest.mark.parametrize("precoding, byte29, write_ret", [
        (None, 0x0C, True),
        (['TP1'], 0x0C, True),
        ({'TP2': True}, 0x0C, True),
        ({'TP1': 'false'}, 0x0C, True),
        ({'TP1': '1'}, 0x0C, True),
        ({'TP1': 1.0}, 0x0C, True),
        ({'TP1': 2}, 0x0C, True),
        ({'TP1': None}, 0x0C, True),
        ({'TP1': False}, None, True),
        ({'TP1': False}, 0x0C, False),
    ])
    def test_set_module_precoding_failure(self, precoding, byte29, write_ret):
        api = self.make_api(byte29, write_ret=write_ret)
        assert not api.set_module_precoding(precoding)

    def test_set_module_precoding_readback_mismatch(self):
        api = self.make_api(0x0C, latch=False)
        assert not api.set_module_precoding({'TP1': False})
        api.xcvr_eeprom.write.assert_called_once_with(pw.MODULE_PRECODING_CONTROL, 0x04)


class TestPinewaveFactory(object):
    @pytest.mark.parametrize("vendor, pn, expected", [
        ('PINEWAVE', 'T-RH8ENH-NMT', PinewaveCmisApi),
        ('PINEWAVE', 'T-OH8CNT-NMT', CmisApi),
        ('OTHER', 'T-RH8ENH-NMT', CmisApi),
    ])
    def test_create_xcvr_api_pinewave(self, vendor, pn, expected):
        with patch('sonic_platform_base.sonic_xcvr.eeprom_rw.ModuleEepromLowerMemoryInfo.get_vendor_name',
                   MagicMock(return_value=vendor)), \
             patch('sonic_platform_base.sonic_xcvr.eeprom_rw.ModuleEepromLowerMemoryInfo.get_vendor_part_num',
                   MagicMock(return_value=pn)), \
             patch.object(CmisApi, 'is_coherent_module', return_value=False):
            api = XcvrApiFactory(mock_reader_cmis, MagicMock()).create_xcvr_api()
        assert type(api) is expected
