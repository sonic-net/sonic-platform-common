import os
from pickle import FALSE
import subprocess
from unittest import mock
from sonic_platform_base.sonic_eeprom import eeprom_tlvinfo
EEPROM_SYMLINK = "./vpd_info"
EEPROM_HEX_FILE = "./syseeprom.hex"



class TestEepromBase:
    
    @classmethod
    def setup_class(cls):
        if not os.path.exists(os.path.dirname(EEPROM_HEX_FILE)):
            assert(False)
        subprocess.check_call(['/usr/bin/xxd', '-r', '-p', EEPROM_HEX_FILE, EEPROM_SYMLINK])
    
    @classmethod
    def teardown_class(cls):
        if os.path.exists(os.path.dirname(EEPROM_HEX_FILE)):
            subprocess.check_call(['rm', '-f', EEPROM_SYMLINK])

    def test_eeprom_tlvinfo_read_api(self):
        eeprom_class = eeprom_tlvinfo.TlvInfoDecoder(EEPROM_SYMLINK, 0, '', True)
        eeprom = eeprom_class.read_eeprom()
        eeprom_class.decode_eeprom(eeprom)
        assert(eeprom_class.base_mac_addr(eeprom).rstrip('\0') == '7C:FE:90:F5:36:40')
        assert(eeprom_class.switchaddrrange(eeprom).rstrip('\0') == '128')
        assert(eeprom_class.modelstr(eeprom).rstrip('\0') == 'MSN2700')
        assert(eeprom_class.serial_number_str(eeprom).rstrip('\0') == 'MT1623X09522')
        assert(eeprom_class.part_number_str(eeprom).rstrip('\0') == 'MSN2700-CS2FO')

    def test_eeprom_tlvinfo_get_tlv_field(self):
        eeprom_class = eeprom_tlvinfo.TlvInfoDecoder(EEPROM_SYMLINK, 0, '', True)
        eeprom = eeprom_class.read_eeprom()
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom, 0x25)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == '06/10/2016 01:57:31')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom, 0x2B)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'Mellanox')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom, 0x28)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'x86_64-mlnx_x86-r0')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom, 0x29)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == '2018.05-5.2.0004-9600')

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom, 0xFF)
        assert(not is_valid)

    def test_eeprom_tlvinfo_set_eeprom(self):
        eeprom_class = eeprom_tlvinfo.TlvInfoDecoder(EEPROM_SYMLINK, 0, '', True)
        eeprom = eeprom_class.read_eeprom()

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

        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x2F)
        assert(not is_valid)
        eeprom_new = eeprom_class.set_eeprom(eeprom, ['0x2F = service_tag'])
        (is_valid, t) = eeprom_class.get_tlv_field(eeprom_new, 0x2F)
        assert(is_valid and t[2].decode("ascii").rstrip('\0') == 'service_tag')
