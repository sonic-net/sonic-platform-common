from abc import ABC
from typing import Optional


class ModuleEepromInfo:
    VENDOR_NAME_OFFSET = 129
    VENDOR_PART_NUM_OFFSET = 148
    VENDOR_NAME_LENGTH = 16
    VENDOR_PART_NUM_LENGTH = 16

    def __init__(self, reader, offset: Optional[int] = None):
        self.reader = reader
        # Offset can be used to shift any reads farther into
        # the address space to accomodate cases where a device's
        # EEPROM has been mapped into a different address space.
        # For instance, an ELSFP EEPROM can be mapped into a
        # part of another I2C device's address space.
        self.offset = offset

    def _translate(self, initial_offset: int) -> int:
        return initial_offset + self.offset if self.offset else initial_offset

    def get_id(self):
        id_byte_raw = self.reader(self._translate(0), 1)
        if id_byte_raw is None:
            return None
        return id_byte_raw[0]

    def get_revision_compliance(self):
        id_byte_raw = self.reader(self._translate(1), 1)
        if id_byte_raw is None:
            return None
        return id_byte_raw[0]

    def get_vendor_name(self):
        name_data = self.reader(self._translate(self.VENDOR_NAME_OFFSET), self.VENDOR_NAME_LENGTH)
        if name_data is None:
            return None
        vendor_name = name_data.decode('utf-8', errors='ignore')
        return vendor_name.strip()

    def get_vendor_part_num(self):
        part_num = self.reader(self._translate(self.VENDOR_PART_NUM_OFFSET), self.VENDOR_PART_NUM_LENGTH)
        if part_num is None:
            return None
        vendor_pn = part_num.decode('utf-8', errors='ignore')
        return vendor_pn.strip()


class EepromReadWriteMixin(ABC):
    def read_eeprom(self, offset, num_bytes):
        """
        read eeprom specific bytes beginning from a random offset with size as num_bytes

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
        write eeprom specific bytes beginning from a random offset with size as num_bytes
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

