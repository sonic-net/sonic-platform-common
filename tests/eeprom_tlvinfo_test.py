
from queue import Empty
import os
import sys
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

from sonic_eeprom import eeprom_base
from sonic_eeprom import eeprom_tlvinfo

""" test_eeprom output:
TlvInfo Header:
   Id String:    TlvInfo
   Version:      1
   Total Length: 177
TLV Name             Code Len Value
-------------------- ---- --- -----
Product Name         0x21  11 7215 IXS-T1
Part Number          0x22  14 3HE16794AARA01
Serial Number        0x23  11 NK203110020
Base MAC Address     0x24   6 50:E0:EF:51:27:91
Manufacture Date     0x25  19 08/24/2020 16:25:29
Platform Name        0x28  26 armhf-nokia_ixs7215_52x-r0
ONIE Version         0x29  45 2019.11-onie_version-nokia_ixs7215_52x-v1.5.1
MAC Addresses        0x2A   2 64
Service Tag          0x2F  10 0000000000
Vendor Extension     0xFD   7 
CRC-32               0xFE   4 0x7E1374C3

(checksum valid) """

tests_dir = os.path.dirname(os.path.abspath(__file__))
eeprom_path = os.path.join(tests_dir, 'test_eeprom')

class TestEEpromTlvInfo:
    def test_eeprom(self):
        tlvInfo = eeprom_tlvinfo.TlvInfoDecoder(eeprom_path, 0, "", True)
        e = tlvInfo.read_eeprom_bytes(256)
        tlvInfo.decode_eeprom(e)

        assert(tlvInfo.p == eeprom_path)
        assert(tlvInfo._TLV_DISPLAY_VENDOR_EXT == True)

        assert(tlvInfo.is_valid_tlvinfo_header(e) == True)
        (tf, crc) = tlvInfo.is_checksum_valid(e)
        assert(tf == True)

        (tf, s) = tlvInfo.get_tlv_field(e, tlvInfo._TLV_CODE_PRODUCT_NAME)
        assert(tf == True)
        assert(s[2].decode() == "7215 IXS-T1")
        
        (tf, s) = tlvInfo.get_tlv_field(e, tlvInfo._TLV_CODE_PART_NUMBER)
        assert(tf == True)
        assert(s[2].decode() == "3HE16794AARA01")
        
        assert(tlvInfo.base_mac_addr(e) == "50:E0:EF:51:27:91")