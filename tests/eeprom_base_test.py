import os
import pytest
import subprocess
from unittest import mock
from unittest.mock import patch, MagicMock
from sonic_platform_base.sonic_eeprom import eeprom_base, eeprom_tlvinfo
EEPROM_SYMLINK = "vpd_info"
EEPROM_HEX_FILE = "syseeprom.hex"
TEST_PATH = os.path.dirname(os.path.abspath(__file__))
EEPROM_HEX_FILE_FULL_PATH = os.path.join(TEST_PATH, EEPROM_HEX_FILE)
EEPROM_SYMLINK_FULL_PATH = os.path.join(TEST_PATH, EEPROM_SYMLINK)
class TestEepromTlvinfo:

    @classmethod
    def setup_class(cls):
        """
        Use a HEX file to generate a mock eeprom, the decoded content of the eeprom is like below:

        TlvInfo Header:
            Id String:    TlvInfo
            Version:      1
            Total Length: 527
        TLV Name             Code Len Value
        -------------------- ---- --- -----
        Product Name         0x21  64 MSN2700
        Part Number          0x22  20 MSN2700-CS2FO
        Serial Number        0x23  24 MT1623X09522
        Base MAC Address     0x24   6 7C:FE:90:F5:36:40
        Manufacture Date     0x25  19 06/10/2016 01:57:31
        Device Version       0x26   1 0
        MAC Addresses        0x2A   2 128
        Manufacturer         0x2B   8 Mellanox
        Platform Name        0x28  18 x86_64-mlnx_x86-r0
        ONIE Version         0x29  21 2018.05-5.2.0004-9600
        CRC-32               0xFE   4 0x89D74C56

        """
        if not os.path.exists(os.path.dirname(EEPROM_HEX_FILE_FULL_PATH)):
            assert False, "File {} is not exist".format(EEPROM_HEX_FILE_FULL_PATH)
        subprocess.check_call(['/usr/bin/xxd', '-r', '-p', EEPROM_HEX_FILE_FULL_PATH, EEPROM_SYMLINK_FULL_PATH])
    
    @classmethod
    def teardown_class(cls):
        # Remove the mock eeprom after test
        if os.path.exists(os.path.dirname(EEPROM_HEX_FILE_FULL_PATH)):
            subprocess.check_call(['rm', '-f', EEPROM_SYMLINK_FULL_PATH])

    def test_eeprom_tlvinfo_read_api(self):
        # Test using the api to fetch Base MAC, Switch Addr Range, Model,
        # Serial Number and Part Number.
        eeprom_class = eeprom_tlvinfo.TlvInfoDecoder(EEPROM_SYMLINK_FULL_PATH, 0, '', True)
        eeprom = eeprom_class.read_eeprom()
        eeprom_class.decode_eeprom(eeprom)
        assert(eeprom_class.base_mac_addr(eeprom).rstrip('\0') == '7C:FE:90:F5:36:40')
        assert(eeprom_class.switchaddrrange(eeprom).rstrip('\0') == '128')
        assert(eeprom_class.modelstr(eeprom).rstrip('\0') == 'MSN2700')
        assert(eeprom_class.serial_number_str(eeprom).rstrip('\0') == 'MT1623X09522')
        assert(eeprom_class.part_number_str(eeprom).rstrip('\0') == 'MSN2700-CS2FO')

    def test_eeprom_tlvinfo_get_tlv_field(self):
        # Test getting fields by field code
        eeprom_class = eeprom_tlvinfo.TlvInfoDecoder(EEPROM_SYMLINK_FULL_PATH, 0, '', True)
        eeprom = eeprom_class.read_eeprom()
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom, eeprom_class._TLV_CODE_MANUF_DATE)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == '06/10/2016 01:57:31')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom, eeprom_class._TLV_CODE_MANUF_NAME)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'Mellanox')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom, eeprom_class._TLV_CODE_PLATFORM_NAME)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'x86_64-mlnx_x86-r0')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom, eeprom_class._TLV_CODE_ONIE_VERSION)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == '2018.05-5.2.0004-9600')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom, 0xFF)
        assert(not is_valid)

    def test_eeprom_tlvinfo_set_eeprom(self):
        eeprom_class = eeprom_tlvinfo.TlvInfoDecoder(EEPROM_SYMLINK_FULL_PATH, 0, '', True)
        eeprom = eeprom_class.read_eeprom()

        # Test updating existing fields
        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x21 = MSN3700'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x21)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'MSN3700')

        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x22 = MSN3700-CS2FO'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x22)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'MSN3700-CS2FO')

        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x23 = MT1234567890'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x23)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'MT1234567890')

        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x24 = FF:FF:FF:FF:FF:FF'])
        assert(eeprom_class.base_mac_addr(eeprom_new).rstrip('\0') == 'FF:FF:FF:FF:FF:FF')

        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x25 = 11/11/1111 11:11:11'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x25)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == '11/11/1111 11:11:11')

        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x26 = 11'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x26)
        assert(is_valid and str(ord(t[2])) == '11')

        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x2A = 129'])
        assert(eeprom_class.switchaddrrange(eeprom_new).rstrip('\0') == '129')

        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x2B = Nvidia'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x2B)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'Nvidia')

        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x28 = x86_64-nvidia_x86-r0'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x28)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'x86_64-nvidia_x86-r0')

        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x29 = 2022.05-5.2.0004-115200'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x29)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == '2022.05-5.2.0004-115200')

        # Test adding none-existing fields
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x27)
        assert(not is_valid)
        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x27 = B2'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x27)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'B2')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x2F)
        assert(not is_valid)
        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x2F = service_tag'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x2F)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'service_tag')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x2C)
        assert(not is_valid)
        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x2C = CN'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x2C)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'CN')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x2D)
        assert(not is_valid)
        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x2D = NVDIA'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x2D)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'NVDIA')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x2E)
        assert(not is_valid)
        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x2E = A2'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x2E)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'A2')

        # Test adding invalid field
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x20)
        assert(not is_valid)
        with mock.patch('sys.exit') as exit_mock:
            eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x20 = Invalid'])
            assert exit_mock.called

    def test_eeprom_tlvinfo_update_eeprom_db(self):
        # mock read file of Redis ACL
        eeprom_tlvinfo.read_from_file = mock.MagicMock(return_value = None)
        # Test updating eeprom to DB by mocking redis hmset
        eeprom_class = eeprom_tlvinfo.TlvInfoDecoder(EEPROM_SYMLINK_FULL_PATH, 0, '', True)
        eeprom = eeprom_class.read_eeprom()
        eeprom_class.redis_client.hmset = mock.MagicMock(return_value = True)
        assert(0 == eeprom_class.update_eeprom_db(eeprom))

    def test_eeprom_tlvinfo_read_eeprom_db(self):
        # mock read file of Redis ACL
        eeprom_tlvinfo.read_from_file = mock.MagicMock(return_value = None)
        # Test reading from DB by mocking redis hget
        eeprom_class = eeprom_tlvinfo.TlvInfoDecoder(EEPROM_SYMLINK_FULL_PATH, 0, '', True)
        eeprom_class.redis_client.hget = mock.MagicMock(return_value = b'1')
        assert(0 == eeprom_class.read_eeprom_db())

class TestEepromDecoder(object):
    def setup(self):
        print("SETUP")

    @patch('builtins.print')
    @patch('sonic_platform_base.sonic_eeprom.eeprom_base.EepromDecoder.checksum_field_size', MagicMock(return_value=10))
    def test_encode_checksum_not_supported(self, mock_print):
        with pytest.raises(SystemExit) as e:
            eeprom = eeprom_base.EepromDecoder('path', 'format', 'start', 'status', 'readonly')
            eeprom.encode_checksum('crc')
        mock_print.assert_called_with('checksum type not yet supported')
        assert e.value.code == 1

    @patch('builtins.print')
    @patch('sonic_platform_base.sonic_eeprom.eeprom_base.EepromDecoder.checksum_type', MagicMock(return_value='dell-crc32'))
    def test_calculate_checksum_not_supported(self, mock_print):
        with pytest.raises(SystemExit) as e:
            eeprom = eeprom_base.EepromDecoder('path', 'format', 'start', 'status', 'readonly')
            eeprom.calculate_checksum('crc')
        mock_print.assert_called_with('checksum type not yet supported')
        assert e.value.code == 1

    @patch('builtins.print')
    def test_set_eeprom_invalid_field(self, mock_print):
        with pytest.raises(SystemExit) as e:
            eeprom = eeprom_base.EepromDecoder('path', ['format'], 'start', 'status', 'readonly')
            eeprom.set_eeprom('eeprom', ['0x20 = Invalid'])
        mock_print.assert_called_with("Error: invalid field '0x20'")
        assert e.value.code == 1

    def teardown(self):
        print("TEAR DOWN")

