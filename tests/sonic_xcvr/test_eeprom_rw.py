from mock import MagicMock

from sonic_platform_base.sonic_xcvr.eeprom_rw import ModuleEepromLowerMemoryInfo


class TestModuleEepromLowerMemoryInfo(object):
    def test_get_id(self):
        reader = MagicMock(return_value=bytes([0x18]))
        info = ModuleEepromLowerMemoryInfo(reader)
        assert info.get_id() == 0x18
        reader.assert_called_once_with(
            ModuleEepromLowerMemoryInfo.ID_OFFSET, ModuleEepromLowerMemoryInfo.ID_LENGTH)

    def test_get_id_none(self):
        reader = MagicMock(return_value=None)
        info = ModuleEepromLowerMemoryInfo(reader)
        assert info.get_id() is None

    def test_get_revision_compliance(self):
        reader = MagicMock(return_value=bytes([0x06]))
        info = ModuleEepromLowerMemoryInfo(reader)
        assert info.get_revision_compliance() == 0x06
        reader.assert_called_once_with(
            ModuleEepromLowerMemoryInfo.REV_OFFSET, ModuleEepromLowerMemoryInfo.REV_LENGTH)

    def test_get_revision_compliance_none(self):
        reader = MagicMock(return_value=None)
        info = ModuleEepromLowerMemoryInfo(reader)
        assert info.get_revision_compliance() is None

    def test_get_vendor_name(self):
        reader = MagicMock(return_value=b'Credo')
        info = ModuleEepromLowerMemoryInfo(reader)
        assert info.get_vendor_name() == 'Credo'
        reader.assert_called_once_with(
            ModuleEepromLowerMemoryInfo.VENDOR_NAME_OFFSET,
            ModuleEepromLowerMemoryInfo.VENDOR_NAME_LENGTH)

    def test_get_vendor_name_strips_padding(self):
        reader = MagicMock(return_value=b'Credo           ')
        info = ModuleEepromLowerMemoryInfo(reader)
        assert info.get_vendor_name() == 'Credo'

    def test_get_vendor_name_none(self):
        reader = MagicMock(return_value=None)
        info = ModuleEepromLowerMemoryInfo(reader)
        assert info.get_vendor_name() is None

    def test_get_vendor_part_num(self):
        reader = MagicMock(return_value=b'CAC81X321M2MC1MS')
        info = ModuleEepromLowerMemoryInfo(reader)
        assert info.get_vendor_part_num() == 'CAC81X321M2MC1MS'
        reader.assert_called_once_with(
            ModuleEepromLowerMemoryInfo.VENDOR_PART_NUM_OFFSET,
            ModuleEepromLowerMemoryInfo.VENDOR_PART_NUM_LENGTH)

    def test_get_vendor_part_num_strips_padding(self):
        reader = MagicMock(return_value=b'CAC81X321M2MC1MS  ')
        info = ModuleEepromLowerMemoryInfo(reader)
        assert info.get_vendor_part_num() == 'CAC81X321M2MC1MS'

    def test_get_vendor_part_num_none(self):
        reader = MagicMock(return_value=None)
        info = ModuleEepromLowerMemoryInfo(reader)
        assert info.get_vendor_part_num() is None

    def test_offset_shifts_all_reads(self):
        offset = 0x4000
        reader = MagicMock(return_value=bytes([0x18]))
        info = ModuleEepromLowerMemoryInfo(reader, offset=offset)

        info.get_id()
        reader.assert_called_with(
            ModuleEepromLowerMemoryInfo.ID_OFFSET + offset,
            ModuleEepromLowerMemoryInfo.ID_LENGTH)

        info.get_revision_compliance()
        reader.assert_called_with(
            ModuleEepromLowerMemoryInfo.REV_OFFSET + offset,
            ModuleEepromLowerMemoryInfo.REV_LENGTH)

        info.get_vendor_name()
        reader.assert_called_with(
            ModuleEepromLowerMemoryInfo.VENDOR_NAME_OFFSET + offset,
            ModuleEepromLowerMemoryInfo.VENDOR_NAME_LENGTH)

        info.get_vendor_part_num()
        reader.assert_called_with(
            ModuleEepromLowerMemoryInfo.VENDOR_PART_NUM_OFFSET + offset,
            ModuleEepromLowerMemoryInfo.VENDOR_PART_NUM_LENGTH)
