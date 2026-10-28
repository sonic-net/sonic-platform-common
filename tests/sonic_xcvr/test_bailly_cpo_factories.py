"""Regression tests for hardware dispatch and Bailly shared-EEPROM addressing."""
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from sonic_platform_base.sonic_xcvr.api.broadcom.bailly_oe import BaillyOeApi
from sonic_platform_base.sonic_xcvr.api.broadcom.bailly_elsfp import BaillyElsfpApi
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoHardwareInfo, OeId
from sonic_platform_base.sonic_xcvr.cpo.oe import OeApiFactory
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpApiFactory
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly import BaillyMemMap, BaillyElsfpMemMap
from sonic_platform_base.sonic_xcvr.fields import consts


class TestBaillyCommonFactories(unittest.TestCase):
    def device(self, bank=0, base_page=0):
        data = bytearray(1024 * 1024)
        return SimpleNamespace(
            bank=bank, base_page=base_page,
            hardware_id=CpoHardwareInfo(OeId.BROADCOM_BAILLY, None),
            read_eeprom=MagicMock(side_effect=lambda offset, size: bytearray(data[offset:offset + size])),
            write_eeprom=MagicMock(return_value=True), data=data,
        )

    def test_oe_factory_preserves_bank_and_rlm_page(self):
        offsets = {}
        for bank in (0, 7):
            for base_page in (0, 4):
                with self.subTest(bank=bank, base_page=base_page):
                    device = self.device(bank, base_page)
                    api = OeApiFactory(device).create_api()
                    self.assertIsInstance(api, BaillyOeApi)
                    self.assertIsInstance(api.xcvr_eeprom.mem_map, BaillyMemMap)
                    self.assertEqual(api.xcvr_eeprom.mem_map.bank, bank)
                    self.assertIn(0xB0 + base_page, [p.page for p in api.xcvr_eeprom.mem_map.pages])
                    self.assertIs(api.xcvr_eeprom.reader, device.read_eeprom)
                    self.assertIs(api.xcvr_eeprom.writer, device.write_eeprom)
                    offsets[bank, base_page] = api.xcvr_eeprom.mem_map.get_field(consts.TX_DISABLE_FIELD).get_offset()
        self.assertNotEqual(offsets[0, 0], offsets[7, 0])

    def test_els_factory_selects_rlm_after_lower_memory_probe(self):
        for base_page, expected in ((0, 25.5), (4, 50.25)):
            with self.subTest(base_page=base_page):
                device = self.device(base_page=base_page)
                # Different values in B0 and B4 prove selection, not just map metadata.
                for page, value in ((0xB0, 25.5), (0xB4, 50.25)):
                    offset = page * 128 + 150
                    device.data[offset:offset + 2] = struct.pack(">h", int(value * 256))
                api = ElsfpApiFactory(device).create_api()
                self.assertIsInstance(api, BaillyElsfpApi)
                self.assertIsInstance(api.xcvr_eeprom.mem_map, BaillyElsfpMemMap)
                self.assertEqual(api.xcvr_eeprom.mem_map.base_page, base_page)
                self.assertTrue(device.read_eeprom.called)
                device.write_eeprom.assert_not_called()
                self.assertEqual(api.get_module_temperature(), expected)
                self.assertIs(api.xcvr_eeprom.reader, device.read_eeprom)
                self.assertIs(api.xcvr_eeprom.writer, device.write_eeprom)

    def test_explicit_elsfp_id_does_not_fall_back_to_bailly(self):
        device = self.device()
        device.hardware_id.elsfp_id = 123
        with self.assertRaises(ValueError):
            ElsfpApiFactory(device).create_api()
        device.read_eeprom.assert_not_called()

    def test_davisson_keeps_automatic_identification(self):
        device = self.device()
        device.hardware_id.oe_id = OeId.BROADCOM_DAVISSON
        factory = ElsfpApiFactory(device)
        factory._get_elsfp_info = MagicMock()
        factory._create_api = MagicMock()
        self.assertIs(factory.create_api(), factory._create_api.return_value)
        factory._get_elsfp_info.assert_called_once_with()
        factory._create_api.assert_called_once()


if __name__ == "__main__":
    unittest.main()
