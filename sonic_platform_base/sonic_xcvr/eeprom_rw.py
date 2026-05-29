from abc import ABC

VENDOR_NAME_OFFSET = 129
VENDOR_PART_NUM_OFFSET = 148
VENDOR_NAME_LENGTH = 16
VENDOR_PART_NUM_LENGTH = 16


def get_id(reader):
    id_byte_raw = reader(0, 1)
    if id_byte_raw is None:
        return None
    return id_byte_raw[0]

def get_revision_compliance(reader):
    id_byte_raw = reader(1, 1)
    if id_byte_raw is None:
        return None
    return id_byte_raw[0]

def get_vendor_name(reader):
   name_data = reader(VENDOR_NAME_OFFSET, VENDOR_NAME_LENGTH)
   if name_data is None:
       return None
   vendor_name = name_data.decode('utf-8', errors='ignore')
   return vendor_name.strip()

def get_vendor_part_num(reader):
   part_num = reader(VENDOR_PART_NUM_OFFSET, VENDOR_PART_NUM_LENGTH)
   if part_num is None:
       return None
   vendor_pn = part_num.decode('utf-8', errors='ignore')
   return vendor_pn.strip()

class EepromReadWriteMixin(ABC):
    def read_eeprom(self, offset, num_bytes):
        """
        read eeprom specfic bytes beginning from a random offset with size as num_bytes

        Args:
             offset :
                     Integer, the offset from which the read transaction will start
             num_bytes:
                     Integer, the number of bytes to be read

        Returns:
            bytearray, if raw sequence of bytes are read correctly from the offset of size num_bytes
            None, if the read_eeprom fails
        """
        raise NotImplementedError

    def write_eeprom(self, offset, num_bytes, write_buffer):
        """
        write eeprom specfic bytes beginning from a random offset with size as num_bytes
        and write_buffer as the required bytes

        Args:
             offset :
                     Integer, the offset from which the read transaction will start
             num_bytes:
                     Integer, the number of bytes to be written
             write_buffer:
                     bytearray, raw bytes buffer which is to be written beginning at the offset

        Returns:
            a Boolean, true if the write succeeded and false if it did not succeed.
        """
        raise NotImplementedError

