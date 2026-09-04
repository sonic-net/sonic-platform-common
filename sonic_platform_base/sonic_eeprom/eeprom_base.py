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
    import binascii
    import os
    import io
    import sys
    import struct
    import fcntl
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")


class EepromDecoder(object):
    def __init__(self, path, format, start, status, readonly):
        self.p = path
        self.f = format
        self.s = start
        self.u = status
        self.r = readonly
        # Warning: the following members are deprecated, the parsed EEPROM data is stored in the
        # Redis STATE_DB, cached data should be fetched from STATE_DB.EEPROM_INFO. 
        self.cache_name = None
        self.cache_update_needed = False
        self.eeprom_file_handle = None
        self.eeprom_raw_bytes = None
        self.lock_file = None

    def check_status(self):
        if self.u != '':
            F = None
            try:
                F = open(self.u, "r")
                d = F.readline().rstrip()
            except IOError as e:
                raise IOError("Failed to check status : %s" % (str(e)))
            finally:
                if F is not None:
                    F.close()
            return d
        else:
            return 'ok'

    def set_cache_name(self, name):
        # Warning: this method is deprecated, the parsed EEPROM data is stored in the
        # Redis STATE_DB, cached data should be fetched from STATE_DB.EEPROM_INFO. 

        # before accessing the eeprom we acquire an exclusive lock on the eeprom file.
        # this will prevent a race condition where multiple instances of this app
        # could try to update the cache at the same time
        self.cache_name = name
        self.lock_file = open(self.p, 'r')
        fcntl.flock(self.lock_file, fcntl.LOCK_EX)

    def is_read_only(self):
        return self.r

    def decoder(self, s, t):
        return t

    def encoder(self, I, v):
        return v

    def checksum_field_size(self):
        return 4  # default

    def is_checksum_field(self, I):
        return I[0] == 'crc'  # default

    def checksum_type(self):
        return 'crc32'

    def encode_checksum(self, crc):
        if self.checksum_field_size() == 4:
            return struct.pack('>I', crc)
        elif self.checksum_field_size() == 1:
            return struct.pack('>B', crc)
        print('checksum type not yet supported')
        sys.exit(1)

    def compute_2s_complement(self, e, size):
        crc = 0
        loc = 0
        end = len(e)
        while loc != end:
            crc += int('0x' + binascii.b2a_hex(e[loc:loc+size]), 0)
            loc += size
        T = 1 << (size * 8)
        return (T - crc) & (T - 1)

    def compute_dell_crc(self, message):
        poly = 0x8005
        reg = 0x0000
        message += bytearray(b'\x00\x00')
        for byte in message:
            mask = 0x80
            while (mask > 0):
                reg<<=1
                if byte & mask:
                    reg += 1
                mask>>=1
                if reg > 0xffff:
                    reg &= 0xffff
                    reg ^= poly
        return reg

    def calculate_checksum(self, e):
        if self.checksum_type() == 'crc32':
            return binascii.crc32(e) & 0xffffffff

        if self.checksum_type() == '2s-complement':
            size = self.checksum_field_size()
            return self.compute_2s_complement(e, size)

        if self.checksum_type() == 'dell-crc':
            return self.compute_dell_crc(e)
        print('checksum type not yet supported')
        sys.exit(1)

    def is_checksum_valid(self, e):
        offset = 0 - self.checksum_field_size()
        crc = self.calculate_checksum(e[:offset])

        loc = 0
        for I in self.f:
            end = loc + I[2]
            t = e[loc:end]
            loc = end
            if self.is_checksum_field(I):
                i = self.decoder(I[0], t)
                if int(i, 0) == crc:
                    return (True, crc)
                else:
                    return (False, crc)
            else:
                continue
        return (False, crc)

    def decode_eeprom(self, e):
        loc = 0
        for I in self.f:
            end = loc + I[2]
            t = e[loc:end]
            loc = end
            if I[0] == 'burn':
                continue
            elif I[1] == 's':
                i = t
            else:
                i = self.decoder(I[0], t)
            print("%-20s: %s" %(I[0], i))

    def set_eeprom(self, e, cmd_args):
        line = ''
        loc = 0
        ndict = {}
        fields = list(I[0] for I in list(self.f))
        if len(cmd_args):
            for arg in cmd_args[0].split(','):
                k, v = arg.split('=')
                k = k.strip()
                v = v.strip()
                if k not in fields:
                    print("Error: invalid field '%s'" %(k))
                    sys.exit(1)
                ndict[k] = v

        for I in self.f:
            # print the original value
            end = loc + I[2]
            sl = e[loc:end]
            loc = end
            if I[0] == 'burn':
                #line += sl
                # fill with zeros
                line = line.ljust(len(line) + I[2], '\x00')
                continue
            elif I[1] == 's':
                i = sl
            else:
                i = self.decoder(I[0], sl)

            if len(cmd_args) == 0:
                if self.is_checksum_field(I):
                    print("%-20s: %s " %(I[0], i))
                    continue

                # prompt for new value
                v = raw_input("%-20s: [%s] " %(I[0], i))
                if v == '':
                    v = i
            else:
                if I[0] not in ndict.keys():
                    v = i
                else:
                    v = ndict[I[0]]

            line += self.encoder(I, v)

        # compute and append crc at the end
        crc = self.encode_checksum(self.calculate_checksum(line))

        line += crc

        return line

    def open_eeprom(self):
        '''
        Open the EEPROM device file.
        If a cache file exists, use that instead of the EEPROM.
        '''
        using_eeprom = True
        eeprom_file = self.p
        try:
        # Warning: cache file is deprecated, the parsed EEPROM data is stored in the
        # Redis STATE_DB, cached data should be fetched from STATE_DB.EEPROM_INFO. This
        # code need to be adjusted once cache file is completely removing from the system.
            if os.path.isfile(self.cache_name):
                eeprom_file = self.cache_name
                using_eeprom = False
        except Exception:
            pass
        self.cache_update_needed = using_eeprom
        self.eeprom_file_handle = io.open(eeprom_file, "rb")
        return io.open(eeprom_file, "rb")

    def read_eeprom(self):
        sizeof_info = 0
        for I in self.f:
            sizeof_info += I[2]
        self.eeprom_raw_bytes = self.read_eeprom_bytes(sizeof_info)
        return self.eeprom_raw_bytes

    def read_eeprom_bytes(self, byteCount, offset=0):
        F = None
        try:
            F = self.eeprom_file_handle
            F.seek(self.s + offset)
            o = F.read(byteCount)

            # If we read from the cache file and the byte count isn't what we
            # expect, the file may be corrupt. Delete it and try again, this
            # time reading from the actual EEPROM.
            if len(o) != byteCount and not self.cache_update_needed:
                # Warning: cache file is deprecated, the parsed EEPROM data is stored in the
                # Redis STATE_DB, cached data should be fetched from STATE_DB.EEPROM_INFO. This
                # code needs to be adjusted once cache file is completely removed from the system.
                os.remove(self.cache_name)
                self.cache_update_needed = True
                F.close()
                F = self.open_eeprom()
                F = self.eeprom_file_handle
                F.seek(self.s + offset)
                o = F.read(byteCount)

            if len(o) != byteCount:
                raise RuntimeError("Expected to read %d bytes from %s, "
                               % (byteCount, self.p) +
                               "but only read %d" % (len(o)))
        except IOError as e:
            raise IOError("Failed to read eeprom : %s" % (str(e)))
        finally:
            if F is not None:
                F.close()
                
        return bytearray(o)

    def read_eeprom_db(self):
        return 0

    def write_eeprom(self, e):
        F = None
        try:
            F = open(self.p, "wb")
            F.seek(self.s)
            F.write(e)
        except IOError as e:
            raise IOError("Failed to write eeprom : %s" % (str(e)))
        finally:
            if F is not None:
                F.close()

        self.write_cache(e)

    def write_cache(self, e):
        # Warning: this method is deprecated, the parsed EEPROM data is stored in the
        # Redis STATE_DB, cached data should be fetched from STATE_DB.EEPROM_INFO. 

        if self.cache_name:
            F = None
            try:
                F = open(self.cache_name, "wb")
                F.seek(self.s)
                F.write(e)
            except IOError as e:
                raise IOError("Failed to write cache : %s" % (str(e)))
            finally:
                if F is not None:
                    F.close()

    def update_cache(self, e):
        # Warning: this method is deprecated, the parsed EEPROM data is stored in the
        # Redis STATE_DB, cached data should be fetched from STATE_DB.EEPROM_INFO. 

        if self.cache_update_needed:
            self.write_cache(e)
        fcntl.flock(self.lock_file, fcntl.LOCK_UN)
        self.lock_file.close()

    def update_eeprom_db(self, e):
        return 0

    def diff_mac(self, mac1, mac2):
        if mac1 == '' or mac2 == '':
            return 0
        mac1_octets = []
        mac1_octets = mac1.split(':')
        mac1val = int(mac1_octets[5], 16) | int(mac1_octets[4], 16) << 8 | int(mac1_octets[3], 16) << 16
        mac2_octets = []
        mac2_octets = mac2.split(':')
        mac2val = int(mac2_octets[5], 16) | int(mac2_octets[4], 16) << 8 | int(mac2_octets[3], 16) << 16
        # check oui matches
        if (mac1_octets[0] != mac2_octets[0]
            or mac1_octets[1] != mac2_octets[1]
            or mac1_octets[2] != mac2_octets[2]) :
            return 0

        if mac2val < mac1val:
            return 0

        return (mac2val - mac1val)

    def increment_mac(self, mac):
        if mac != "":
            mac_octets = []
            mac_octets = mac.split(':')
            ret_mac = int(mac_octets[5], 16) | int(mac_octets[4], 16) << 8 | int(mac_octets[3], 16) << 16
            ret_mac = ret_mac + 1

            if (ret_mac & 0xff000000):
                print('Error: increment carries into OUI')
                return ''

            mac_octets[5] = hex(ret_mac & 0xff)[2:].zfill(2)
            mac_octets[4] = hex((ret_mac >> 8) & 0xff)[2:].zfill(2)
            mac_octets[3] = hex((ret_mac >> 16) & 0xff)[2:].zfill(2)

            return ':'.join(mac_octets).upper()

        return ''

    @classmethod
    def find_field(cls, e, name):
        if not hasattr(cls, 'brd_fmt'):
            raise RuntimeError("Class %s does not have brb_fmt" % cls)
        if not e:
            raise RuntimeError("EEPROM can not be empty")
        brd_fmt = cls.brd_fmt
        loc = 0
        for f in brd_fmt:
            end = loc + f[2]
            t = e[loc:end]
            loc = end
            if f[0] == name:
                return t

    def base_mac_addr(self, e):
        '''
        Returns the base MAC address found in the EEPROM.

        Sub-classes must override this method as reading the EEPROM
        and finding the base MAC address entails platform specific
        details.

        See also mgmtaddrstr() and switchaddrstr().
        '''
        print("ERROR: Platform did not implement base_mac_addr()")
        raise NotImplementedError

    def mgmtaddrstr(self, e):
        '''
        Returns the base MAC address to use for the Ethernet
        management interface(s) on the CPU complex.

        By default this is the same as the base MAC address listed in
        the EEPROM.

        See also switchaddrstr().
        '''
        return self.base_mac_addr(e)

    def switchaddrstr(self, e):
        '''
        Returns the base MAC address to use for the switch ASIC
        interfaces.

        By default this is *next* address after the base MAC address
        listed in the EEPROM.

        See also mgmtaddrstr().
        '''
        return self.increment_mac(self.base_mac_addr(e))

    def switchaddrrange(self, e):
        # this function is in the base class only to catch errors
        # the platform specific import should have an override of this method
        # to provide the allocated mac range from syseeprom or flash sector or
        # wherever that platform stores this info
        print("Platform did not indicate allocated mac address range")
        raise NotImplementedError

    def serial_number_str(self, e):
        raise NotImplementedError("Platform did not indicate serial number")
