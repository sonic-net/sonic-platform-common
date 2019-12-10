#! /usr/bin/python
# Copyright 2012 Cumulus Networks LLC, all rights reserved

#############################################################################
# Base eeprom class containing the main logic for reading, writing, and
# setting the eeprom.  The format definition is a list of tuples of:
# ('data name', 'data type', 'size in bytes')
# data type is one of 's', 'C', and 'x' (string, char, and ignore)
# 'burn' as a data name indicates the corresponding number of bytes are to
# be ignored

from __future__ import print_function

try:
    import exceptions              # Python 2
except ImportError:
    import builtins as exceptions  # Python 3
try:
    import binascii
    import optparse
    import os
    import sys
    import redis
    from . import eeprom_base    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

STATE_DB_INDEX = 6

#
# TlvInfo Format - This eeprom format was defined by Cumulus Networks
# and can be found here:
#
#
class TlvInfoDecoder(eeprom_base.EepromDecoder):

    # Header Field Constants
    _TLV_INFO_ID_STRING         = "TlvInfo\x00"
    _TLV_INFO_VERSION           = 0x01
    _TLV_INFO_HDR_LEN           = 11
    _TLV_INFO_MAX_LEN           = 2048
    _TLV_TOTAL_LEN_MAX          = _TLV_INFO_MAX_LEN - _TLV_INFO_HDR_LEN
    _TLV_HDR_ENABLED            = 1

    # The Undefined TLV Type
    _TLV_CODE_UNDEFINED         = 0xFC

    # Default TLV Types
    _TLV_CODE_PRODUCT_NAME      = 0x21
    _TLV_CODE_PART_NUMBER       = 0x22
    _TLV_CODE_SERIAL_NUMBER     = 0x23
    _TLV_CODE_MAC_BASE          = 0x24
    _TLV_CODE_MANUF_DATE        = 0x25
    _TLV_CODE_DEVICE_VERSION    = 0x26
    _TLV_CODE_LABEL_REVISION    = 0x27
    _TLV_CODE_PLATFORM_NAME     = 0x28
    _TLV_CODE_ONIE_VERSION      = 0x29
    _TLV_CODE_MAC_SIZE          = 0x2A
    _TLV_CODE_MANUF_NAME        = 0x2B
    _TLV_CODE_MANUF_COUNTRY     = 0x2C
    _TLV_CODE_VENDOR_NAME       = 0x2D
    _TLV_CODE_DIAG_VERSION      = 0x2E
    _TLV_CODE_SERVICE_TAG       = 0x2F
    _TLV_CODE_VENDOR_EXT        = 0xFD
    _TLV_CODE_CRC_32            = 0xFE

    # By default disable the Quanta specific codes
    _TLV_CODE_QUANTA_MAGIC      = _TLV_CODE_UNDEFINED
    _TLV_CODE_QUANTA_CRC        = _TLV_CODE_UNDEFINED
    _TLV_CODE_QUANTA_CARD_TYPE  = _TLV_CODE_UNDEFINED
    _TLV_CODE_QUANTA_HW_VERSION = _TLV_CODE_UNDEFINED
    _TLV_CODE_QUANTA_SW_VERSION = _TLV_CODE_UNDEFINED
    _TLV_CODE_QUANTA_MANUF_DATE = _TLV_CODE_UNDEFINED
    _TLV_CODE_QUANTA_MODEL_NAME = _TLV_CODE_UNDEFINED

    # TLV Value Display Switch
    _TLV_DISPLAY_VENDOR_EXT     = False


    def __init__(self, path, start, status, ro, max_len=_TLV_INFO_MAX_LEN):
        super(TlvInfoDecoder, self).__init__(path,      \
                                             None,      \
                                             start,     \
                                             status,    \
                                             ro)
        self.eeprom_start = start
        self.eeprom_max_len = max_len


    def __print_db(self, db, code, num=0):
        if not num:
            field_name = db.hget('EEPROM_INFO|{}'.format(hex(code)), 'Name')
            if not field_name:
                pass
            else:
                field_len = db.hget('EEPROM_INFO|{}'.format(hex(code)), 'Len')
                field_value = db.hget('EEPROM_INFO|{}'.format(hex(code)), 'Value')
                print("%-20s 0x%02X %3s %s" % (field_name, code, field_len, field_value))
        else:
            for index in range(num):
                field_name = db.hget('EEPROM_INFO|{}'.format(hex(code)), 'Name_{}'.format(index))
                field_len = db.hget('EEPROM_INFO|{}'.format(hex(code)), 'Len_{}'.format(index))
                field_value = db.hget('EEPROM_INFO|{}'.format(hex(code)), 'Value_{}'.format(index))
                print("%-20s 0x%02X %3s %s" % (field_name, code, field_len, field_value))


    def decode_eeprom(self, e):
        '''
        Decode and print out the contents of the EEPROM.
        '''
        if self._TLV_HDR_ENABLED :
            if not self.is_valid_tlvinfo_header(e):
                print("EEPROM does not contain data in a valid TlvInfo format.")
                return

            print("TlvInfo Header:")
            print("   Id String:    %s" % (e[0:7],))
            print("   Version:      %d" % (ord(e[8]),))
            total_len = (ord(e[9]) << 8) | ord(e[10])
            print("   Total Length: %d" % (total_len,))
            tlv_index = self._TLV_INFO_HDR_LEN
            tlv_end   = self._TLV_INFO_HDR_LEN + total_len
        else :
            tlv_index = self.eeprom_start
            tlv_end   = self._TLV_INFO_MAX_LEN

        print("TLV Name             Code Len Value")
        print("-------------------- ---- --- -----")
        while (tlv_index + 2) < len(e) and tlv_index < tlv_end:
            if not self.is_valid_tlv(e[tlv_index:]):
                print("Invalid TLV field starting at EEPROM offset %d" % (tlv_index,))
                return
            tlv = e[tlv_index:tlv_index + 2 + ord(e[tlv_index + 1])]
            name, value = self.decoder(None, tlv)
            print("%-20s 0x%02X %3d %s" % (name, ord(tlv[0]), ord(tlv[1]), value))
            if ord(e[tlv_index]) == self._TLV_CODE_QUANTA_CRC or \
               ord(e[tlv_index]) == self._TLV_CODE_CRC_32:
                return
            tlv_index += ord(e[tlv_index+1]) + 2


    def set_eeprom(self, e, cmd_args):
        '''
        Returns the new contents of the EEPROM. If command line arguments are supplied,
        then those fields are overwritten or added to the existing EEPROM contents. If
        not command line arguments are supplied, the user is prompted for the contents
        of the EEPROM.
        '''
        new_tlvs = ""
        (crc_is_valid, crc) = self.is_checksum_valid(e)
        if crc_is_valid:
            if self._TLV_HDR_ENABLED:
                tlv_index = self._TLV_INFO_HDR_LEN
                tlv_end   = self._TLV_INFO_HDR_LEN + ((ord(e[9]) << 8) | ord(e[10]))
            else :
                tlv_index = self.eeprom_start
                tlv_end   = self._TLV_INFO_MAX_LEN

            while tlv_index < len(e) and \
                  tlv_index < tlv_end and \
                  self.is_valid_tlv(e[tlv_index:]) and \
                  ord(e[tlv_index]) != self._TLV_CODE_CRC_32 and \
                  ord(e[tlv_index]) != self._TLV_CODE_QUANTA_CRC:
                new_tlvs += e[tlv_index:tlv_index + 2 + ord(e[tlv_index + 1])]
                tlv_index += ord(e[tlv_index+1]) + 2

        if len(cmd_args):
            for arg_str in cmd_args:
                for arg in arg_str.split(','):
                    k, v = arg.split('=')
                    k = int(k.strip(), 0)
                    v = v.strip()
                    new_tlv = self.encoder((k,), v)
                    (tlv_found, index) = self.get_tlv_index(new_tlvs, k)
                    if tlv_found:
                        new_tlvs = new_tlvs[:index] + new_tlv + \
                                   new_tlvs[index + 2 + ord(new_tlvs[index + 1]):]
                    else:
                        new_tlvs += new_tlv

        else:
            action = "a"
            while action not in ['f', 'F']:

                action = raw_input("\n[a]dd, [m]odify, [d]elete, [f]inished: ")
                if action in ['a', 'A', 'm', 'M']:
                    code = raw_input("Enter a TLV type code: ")
                    code = int(code, 0)
                    value = raw_input("Enter the value: ")
                    new_tlv = self.encoder((code,), value)
                    (tlv_found, index) = self.get_tlv_index(new_tlvs, code)
                    if tlv_found:
                        new_tlvs = new_tlvs[:index] + new_tlv + \
                                   new_tlvs[index + 2 + ord(new_tlvs[index + 1]):]
                    else:
                        new_tlvs += new_tlv
                elif action in ['d', 'D']:
                    code = raw_input("Enter a TLV type code: ")
                    code = int(code, 0)
                    (tlv_found, index) = self.get_tlv_index(new_tlvs, code)
                    if tlv_found:
                        new_tlvs = new_tlvs[:index] + \
                                   new_tlvs[index + 2 + ord(new_tlvs[index + 1]):]
                elif action in ['f', 'F']:
                    pass
                else:
                    print("\nInvalid input, please enter 'a', 'm', 'd', or 'f'\n")

        if self._TLV_HDR_ENABLED:
            new_tlvs_len = len(new_tlvs) + 6
            new_e = self._TLV_INFO_ID_STRING + chr(self._TLV_INFO_VERSION) + \
                    chr((new_tlvs_len >> 8) & 0xFF) + \
                    chr(new_tlvs_len & 0xFF) + new_tlvs
        else:
            new_e = new_tlvs

        if self._TLV_CODE_CRC_32 != self._TLV_CODE_UNDEFINED:
            new_e = new_e + chr(self._TLV_CODE_CRC_32) + chr(4)
        elif self._TLV_CODE_QUANTA_CRC != self._TLV_CODE_UNDEFINED:
            new_e = new_e + chr(self._TLV_CODE_QUANTA_CRC) + chr(2)
        else:
            print("\nFailed to formulate new eeprom\n")
            exit
        new_e += self.encode_checksum(self.calculate_checksum(new_e))
        self.decode_eeprom(new_e)
        if len(new_e) > min(self._TLV_INFO_MAX_LEN, self.eeprom_max_len):
            sys.stderr.write("\nERROR: There is not enough room in the EEPROM to save data.\n")
            exit(1)
        return new_e


    def is_valid_tlvinfo_header(self, e):
        '''
        Perform sanity checks on the first 11 bytes of the TlvInfo EEPROM
        data passed in as a string.
            1. Large enough to hold the header
            2. First 8 bytes contain null-terminated ASCII string "TlvInfo"
            3. Version byte is 1
            4. Total length bytes contain value which is less than or equal
               to the allowed maximum (2048-11)
        '''
        return len(e) >= self._TLV_INFO_HDR_LEN and \
               e[0:8] == self._TLV_INFO_ID_STRING and \
               ord(e[8]) == self._TLV_INFO_VERSION and \
               ((ord(e[9]) << 8) | ord(e[10])) <= self._TLV_TOTAL_LEN_MAX


    def is_valid_tlv(self, e):
        '''
        Perform basic sanity checks on a TLV field. The TLV is in the string
        provided.
            1. The TLV is at least 2 bytes long
            2. The length byte contains a value which does not cause the value
               field to go beyond the length of the string.
        '''
        return (len(e) >= 2 and (2 + ord(e[1]) <= len(e)))


    def is_checksum_valid(self, e):
        '''
        Validate the checksum in the provided TlvInfo EEPROM data.
        '''
        if not self.is_valid_tlvinfo_header(e):
            return (False, 0)

        offset = self._TLV_INFO_HDR_LEN + ((ord(e[9]) << 8) | ord(e[10]))
        if len(e) < offset or \
           ord(e[offset-6]) != self._TLV_CODE_CRC_32 or \
           ord(e[offset-5]) != 4:
            return (False, 0)

        crc = self.calculate_checksum(e[:offset-4])
        tlv_crc = ord(e[offset-4]) << 24 | ord(e[offset-3]) << 16 | \
                  ord(e[offset-2]) <<  8 | ord(e[offset-1])
        if tlv_crc == crc:
            return(True, crc)

        return (False, crc)


    def read_eeprom(self):
        '''
        Read the eeprom contents. This is performed in two steps. First
        the 11 bytes of the TlvInfo structure (the header) are read and
        sanity checked. Then using the total length field in the header,
        the rest of the data is read from the EEPROM.
        '''
        offset = 0
        if self._TLV_HDR_ENABLED:
            h = self.read_eeprom_bytes(self._TLV_INFO_HDR_LEN)
            offset = self._TLV_INFO_HDR_LEN
            if len(h) != self._TLV_INFO_HDR_LEN:
                raise RuntimeError("expected to read %d bytes from %s, " \
                                   %(self._TLV_INFO_HDR_LEN, self.p) + \
                                   "but only read %d" %(len(h),))
            if not self.is_valid_tlvinfo_header(h):
                return h
            sizeof_tlvs = (ord(h[9]) << 8) | ord(h[10])
        else:
            h = ""
            sizeof_tlvs   = self._TLV_INFO_MAX_LEN

        t = self.read_eeprom_bytes(sizeof_tlvs, offset)
        if len(t) != sizeof_tlvs:
            raise RuntimeError("expected to read %d bytes from %s, " \
                               %(sizeof_tlvs, self.p) + \
                               "but only read %d" %(len(t)))
        return h + t


    def read_eeprom_db(self):
        '''
        Print out the contents of the EEPROM from database
        '''
        client = redis.Redis(db = STATE_DB_INDEX)
        db_state = client.hget('EEPROM_INFO|State', 'Initialized')
        if db_state != '1':
            return -1
        tlv_version = client.hget('EEPROM_INFO|TlvHeader', 'Version')
        if tlv_version:
            print("TlvInfo Header:")
            print("   Id String:    %s" % client.hget('EEPROM_INFO|TlvHeader', 'Id String'))
            print("   Version:      %s" % tlv_version)
            print("   Total Length: %s" % client.hget('EEPROM_INFO|TlvHeader', 'Total Length'))

        print("TLV Name             Code Len Value")
        print("-------------------- ---- --- -----")

        for index in range(self._TLV_CODE_PRODUCT_NAME, self._TLV_CODE_SERVICE_TAG + 1):
            self.__print_db(client, index)

        try:
            num_vendor_ext = int(client.hget('EEPROM_INFO|{}'.format(hex(self._TLV_CODE_VENDOR_EXT)), 'Num_vendor_ext'))
        except (ValueError, TypeError):
            pass
        else:
            self.__print_db(client, self._TLV_CODE_VENDOR_EXT, num_vendor_ext)

        self.__print_db(client, self._TLV_CODE_CRC_32)

        print("")

        is_valid = client.hget('EEPROM_INFO|Checksum', 'Valid')
        if is_valid != '1':
            print("(*** checksum invalid)")
        else:
            print("(checksum valid)")

        return 0


    def update_eeprom_db(self, e):
        '''
        Decode the contents of the EEPROM and update the contents to database
        '''
        client = redis.Redis(db=STATE_DB_INDEX)
        fvs = {}
        if self._TLV_HDR_ENABLED:
            if not self.is_valid_tlvinfo_header(e):
                print("EEPROM does not contain data in a valid TlvInfo format.")
                return -1
            total_len = (ord(e[9]) << 8) | ord(e[10])
            fvs['Id String'] = e[0:7]
            fvs['Version'] = ord(e[8])
            fvs['Total Length'] = total_len
            client.hmset("EEPROM_INFO|TlvHeader", fvs)
            fvs.clear()
            tlv_index = self._TLV_INFO_HDR_LEN
            tlv_end = self._TLV_INFO_HDR_LEN + total_len
        else:
            tlv_index = self.eeprom_start
            tlv_end = self._TLV_INFO_MAX_LEN

        vendor_ext_tlv_num = 0
        while (tlv_index + 2) < len(e) and tlv_index < tlv_end:
            if not self.is_valid_tlv(e[tlv_index:]):
                break
            tlv = e[tlv_index:tlv_index + 2 + ord(e[tlv_index + 1])]
            tlv_code = ord(tlv[0])
            if tlv_code == self._TLV_CODE_VENDOR_EXT:
                vendor_index = str(vendor_ext_tlv_num)
                fvs['Len_{}'.format(vendor_index)] = ord(tlv[1])
                fvs['Name_{}'.format(vendor_index)], fvs['Value_{}'.format(vendor_index)] = self.decoder(None, tlv)
                vendor_ext_tlv_num += 1
            else:
                fvs['Len'] = ord(tlv[1])
                fvs['Name'], fvs['Value'] = self.decoder(None, tlv)
            client.hmset('EEPROM_INFO|{}'.format(hex(tlv_code)), fvs)
            fvs.clear()
            if ord(e[tlv_index]) == self._TLV_CODE_QUANTA_CRC or \
                    ord(e[tlv_index]) == self._TLV_CODE_CRC_32:
                break
            else:
                tlv_index += ord(e[tlv_index + 1]) + 2

        if vendor_ext_tlv_num > 0:
            fvs['Num_vendor_ext'] = str(vendor_ext_tlv_num)
            client.hmset('EEPROM_INFO|{}'.format(hex(self._TLV_CODE_VENDOR_EXT)), fvs)
            fvs.clear()

        (is_valid, valid_crc) = self.is_checksum_valid(e)
        if is_valid:
            fvs['Valid'] = '1'
        else:
            fvs['Valid'] = '0'

        client.hmset('EEPROM_INFO|Checksum', fvs)
        fvs.clear()

        fvs['Initialized'] = '1'
        client.hmset('EEPROM_INFO|State', fvs)
        return 0


    def get_tlv_field(self, e, code):
        '''
        Given an EEPROM string the TLV field for the provided code is
        returned. This routine validates the EEPROM data (checksum and
        other sanity checks) and then searches for a TLV field with the
        supplied type code. A tuple of two items is returned. The first
        item is a boolean indicating success and, if True, the second
        item is a 3 element list with the type (int), length (int),
        and value (string) of the requested TLV.
        '''
        (is_valid, valid_crc) = self.is_checksum_valid(e)
        if not is_valid:
            return (False, None)
        if self._TLV_HDR_ENABLED:
            tlv_index = self._TLV_INFO_HDR_LEN
            tlv_end = ((ord(e[9]) << 8) | ord(e[10])) + self._TLV_INFO_HDR_LEN
        else :
            tlv_index = self.eeprom_start
            tlv_end   = self._TLV_INFO_MAX_LEN
        while tlv_index < len(e) and tlv_index < tlv_end:
            if not self.is_valid_tlv(e[tlv_index:]):
                return (False, None)
            if ord(e[tlv_index]) == code:
                return (True, [ord(e[tlv_index]), ord(e[tlv_index+1]), \
                               e[tlv_index+2:tlv_index+2+ord(e[tlv_index+1])]])
            tlv_index += ord(e[tlv_index+1]) + 2
        return (False, None)


    def get_tlv_index(self, e, code):
        '''
        Given an EEPROM string with just TLV fields (no TlvInfo header)
        finds the index of the requested type code. This routine searches
        for a TLV field with the supplied type code. A tuple of two items
        is returned. The first item is a boolean indicating success and,
        if True, the second item is the index in the supplied EEPROM string
        of the matching type code.
        '''
        tlv_index = 0
        while tlv_index < len(e):
            if not self.is_valid_tlv(e[tlv_index:]):
                return (False, 0)
            if ord(e[tlv_index]) == code:
                return (True, tlv_index )
            tlv_index += ord(e[tlv_index+1]) + 2
        return (False, 0)


    def base_mac_addr(self, e):
        '''
        Returns the value field of the MAC #1 Base TLV formatted as a string
        of colon-separated hex digits.
        '''
        (is_valid, t) = self.get_tlv_field(e, self._TLV_CODE_MAC_BASE)
        if not is_valid or t[1] != 6:
            return super(TlvInfoDecoder, self).switchaddrstr(e)

        return ":".join([binascii.b2a_hex(T) for T in t[2]])


    def switchaddrrange(self, e):
        '''
        Returns the value field of the MAC #1 Size TLV formatted as a decimal
        string
        '''
        (is_valid, t) = self.get_tlv_field(e, self._TLV_CODE_MAC_SIZE)
        if not is_valid:
            return super(TlvInfoDecoder, self).switchaddrrange(e)

        return str((ord(t[2][0]) << 8) | ord(t[2][1]))


    def modelstr(self, e):
        '''
        Returns the value field of the Product Name TLV as a string
        '''
        (is_valid, t) = self.get_tlv_field(e, self._TLV_CODE_PRODUCT_NAME)
        if not is_valid:
            return super(TlvInfoDecoder, self).modelstr(e)

        return t[2]


    def serial_number_str(self, e):
        '''
        Returns the value field of the Serial Number TLV as a string
        '''
        valid, t = self.get_tlv_field(e, self._TLV_CODE_SERIAL_NUMBER)
        if not valid:
            return super(TlvInfoDecoder, self).serial_number_str(e)
        return t[2]


    def decoder(self, s, t):
        '''
        Return a string representing the contents of the TLV field. The format of
        the string is:
            1. The name of the field left justified in 20 characters
            2. The type code in hex right justified in 5 characters
            3. The length in decimal right justified in 4 characters
            4. The value, left justified in however many characters it takes
        The vailidity of EEPROM contents and the TLV field has been verified
        prior to calling this function. The 's' parameter is unused
        '''
        if ord(t[0]) == self._TLV_CODE_PRODUCT_NAME:
            name  = "Product Name"
            value = str(t[2:2 + ord(t[1])])
        elif ord(t[0]) == self._TLV_CODE_PART_NUMBER:
            name = "Part Number"
            value = t[2:2 + ord(t[1])]
        elif ord(t[0]) == self._TLV_CODE_SERIAL_NUMBER:
            name  = "Serial Number"
            value = t[2:2 + ord(t[1])]
        elif ord(t[0]) == self._TLV_CODE_MAC_BASE:
            name = "Base MAC Address"
            value = ":".join([binascii.b2a_hex(T) for T in t[2:8]]).upper()
        elif ord(t[0]) == self._TLV_CODE_MANUF_DATE:
            name = "Manufacture Date"
            value = t[2:2 + ord(t[1])]
        elif ord(t[0]) == self._TLV_CODE_DEVICE_VERSION:
            name  = "Device Version"
            value = str(ord(t[2]))
        elif ord(t[0]) == self._TLV_CODE_LABEL_REVISION:
            name  = "Label Revision"
            value = t[2:2 + ord(t[1])]
        elif ord(t[0]) == self._TLV_CODE_PLATFORM_NAME:
            name  = "Platform Name"
            value = t[2:2 + ord(t[1])]
        elif ord(t[0]) == self._TLV_CODE_ONIE_VERSION:
            name  = "ONIE Version"
            value = t[2:2 + ord(t[1])]
        elif ord(t[0]) == self._TLV_CODE_MAC_SIZE:
            name = "MAC Addresses"
            value = str((ord(t[2]) << 8) | ord(t[3]))
        elif ord(t[0]) == self._TLV_CODE_MANUF_NAME:
            name = "Manufacturer"
            value = t[2:2 + ord(t[1])]
        elif ord(t[0]) == self._TLV_CODE_MANUF_COUNTRY:
            name = "Manufacture Country"
            value = t[2:2 + ord(t[1])]
        elif ord(t[0]) == self._TLV_CODE_VENDOR_NAME:
            name = "Vendor Name"
            value = t[2:2 + ord(t[1])]
        elif ord(t[0]) == self._TLV_CODE_DIAG_VERSION:
            name = "Diag Version"
            value = t[2:2 + ord(t[1])]
        elif ord(t[0]) == self._TLV_CODE_SERVICE_TAG:
            name = "Service Tag"
            value = t[2:2 + ord(t[1])]
        elif ord(t[0]) == self._TLV_CODE_VENDOR_EXT:
            name = "Vendor Extension"
            value = ""
            if self._TLV_DISPLAY_VENDOR_EXT:
                for c in t[2:2 + ord(t[1])]:
                    value += "0x%02X " % (ord(c),)
        elif ord(t[0]) == self._TLV_CODE_CRC_32 and len(t) == 6:
            name = "CRC-32"
            value = "0x%08X" % (((ord(t[2]) << 24) | (ord(t[3]) << 16) | (ord(t[4]) << 8) | ord(t[5])),)
        # Quanta specific codes below here.
        # These decodes are lifted from their U-Boot codes
        elif ord(t[0]) == self._TLV_CODE_QUANTA_MAGIC and len(t) == 3:
            name  = "Magic Number"
            value = "0x%02X" % (ord(t[2]))
        elif ord(t[0]) == self._TLV_CODE_QUANTA_CRC and len(t) == 4:
            name = "QUANTA-CRC"
            value = "0x%04X" % ((ord(t[2]) << 8) + ord(t[3]))
        elif ord(t[0]) == self._TLV_CODE_QUANTA_CARD_TYPE and len(t) == 6:
            name = "Card Type"
            value = "0x%08X" % (((ord(t[2]) << 24) | (ord(t[3]) << 16) | (ord(t[4]) << 8) | ord(t[5])),)
        elif ord(t[0]) == self._TLV_CODE_QUANTA_HW_VERSION and len(t) == 6:
            name = "Hardware Version"
            value = "%d.%d" % (ord(t[2]), ord(t[3]))
        elif ord(t[0]) == self._TLV_CODE_QUANTA_SW_VERSION and len(t) == 6:
            name = "Software Version"
            value = "%d.%d.%d.%d" % ((ord(t[2]) >> 4), (ord(t[2]) & 0xF), (ord(t[3]) >> 4), (ord(t[3]) & 0xF))
        elif ord(t[0]) == self._TLV_CODE_QUANTA_MANUF_DATE and len(t) == 6:
            name = "Manufacture Date"
            value = "%04d/%d/%d" % (((ord(t[2]) << 8) | ord(t[3])), ord(t[4]), ord(t[5]))
        elif ord(t[0]) == self._TLV_CODE_QUANTA_MODEL_NAME:
            name  = "Model Name"
            value = t[2:2 + ord(t[1])]
        else:
            name = "Unknown"
            value = ""
            for c in t[2:2 + ord(t[1])]:
                value += "0x%02X " % (ord(c),)
        return name, value


    def encoder(self, I, v):
        '''
        Validate and encode the string 'v' into the TLV specified by 'I'.
        I[0] is the TLV code.
        '''
        try:
            if I[0] == self._TLV_CODE_PRODUCT_NAME   or \
               I[0] == self._TLV_CODE_PART_NUMBER    or \
               I[0] == self._TLV_CODE_SERIAL_NUMBER  or \
               I[0] == self._TLV_CODE_LABEL_REVISION or \
               I[0] == self._TLV_CODE_PLATFORM_NAME  or \
               I[0] == self._TLV_CODE_ONIE_VERSION   or \
               I[0] == self._TLV_CODE_MANUF_NAME     or \
               I[0] == self._TLV_CODE_VENDOR_NAME    or \
               I[0] == self._TLV_CODE_DIAG_VERSION   or \
               I[0] == self._TLV_CODE_SERVICE_TAG:
                errstr = "A string less than 256 characters"
                if len(v) > 255:
                    raise
                value = v
            elif I[0] == self._TLV_CODE_DEVICE_VERSION:
                errstr  = "A number between 0 and 255"
                num = int(v, 0)
                if num < 0 or num > 255:
                    raise
                value = chr(num)
            elif I[0] == self._TLV_CODE_MAC_SIZE:
                errstr  = "A number between 0 and 65535"
                num = int(v, 0)
                if num < 0 or num > 65535:
                    raise
                value = chr((num >> 8) & 0xFF) + chr(num & 0xFF)
            elif I[0] == self._TLV_CODE_MANUF_DATE:
                errstr = 'MM/DD/YYYY HH:MM:SS'
                date, time = v.split()
                mo, da, yr = [int(i) for i in date.split('/')]
                hr, mn, sc = [int(i) for i in time.split(':')]
                if len(v) < 19 or \
                   mo < 1 or mo > 12 or da < 1 or da > 31 or yr < 0 or yr > 9999 or \
                   hr < 0 or hr > 23 or mn < 0 or mn > 59 or sc < 0 or sc > 59:
                    raise
                value = v
            elif I[0] == self._TLV_CODE_MAC_BASE:
                errstr = 'XX:XX:XX:XX:XX:XX'
                mac_digits = v.split(':')
                if len(mac_digits) != 6:
                    raise
                value = ""
                for c in mac_digits:
                    value = value + chr(int(c, 16))
            elif I[0] == self._TLV_CODE_MANUF_COUNTRY:
                errstr = 'CC, a two character ISO 3166-1 alpha-2 country code'
                if len(v) < 2:
                    raise
                value = v[0:2]
            elif I[0] == self._TLV_CODE_CRC_32:
                value = ''
            # Disallow setting any Quanta specific codes
            elif I[0] == self._TLV_CODE_QUANTA_MAGIC      or \
                 I[0] == self._TLV_CODE_QUANTA_CARD_TYPE  or \
                 I[0] == self._TLV_CODE_QUANTA_HW_VERSION or \
                 I[0] == self._TLV_CODE_QUANTA_SW_VERSION or \
                 I[0] == self._TLV_CODE_QUANTA_MANUF_DATE or \
                 I[0] == self._TLV_CODE_QUANTA_MODEL_NAME:
                raise Exception('quanta-read-only')
            else:
                errstr = '0xXX ... A list of space-separated hexidecimal numbers'
                value = ""
                for c in v.split():
                    value += chr(int(c, 0))
        except Exception as inst:
            if (len(inst.args) > 0) and (inst.args[0] == 'quanta-read-only'):
                sys.stderr.write("Error: '" + "0x%02X" % (I[0],) + "' -- Unable to set the read-only Quanta codes.\n")
            else:
                sys.stderr.write("Error: '" + "0x%02X" % (I[0],) + "' correct format is " + errstr + "\n")
            exit(0)

        return chr(I[0]) + chr(len(value)) + value


    def is_checksum_field(self, I):
        return False


    def checksum_field_size(self):
        return 4


    def checksum_type(self):
        return 'crc32'
