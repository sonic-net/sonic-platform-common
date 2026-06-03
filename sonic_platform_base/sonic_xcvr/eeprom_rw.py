from abc import ABC


class ModuleEepromLowerMemoryInfo:
    """
    This class is designed to provide raw read access to lower memory of a
    module's EEPROM for API / memory map bootstrapping purposes. It is not
    intended to provide access to upper memory. That is the job of the
    memory map / API abstraction that already exists.
    """
    ID_OFFSET = 0
    ID_LENGTH = 1
    REV_OFFSET = 1
    REV_LENGTH = 1
    VENDOR_NAME_OFFSET = 129
    VENDOR_PART_NUM_OFFSET = 148
    VENDOR_NAME_LENGTH = 16
    VENDOR_PART_NUM_LENGTH = 16

    def __init__(self, reader, offset: int = 0):
        self.reader = reader
        # Offset can be used to shift any reads farther into
        # the address space to accomodate cases where a device's
        # EEPROM has been mapped into a different address space.
        # For instance, an ELSFP EEPROM can be mapped into a
        # part of another I2C device's address space.
        self.offset = offset

    def _translate(self, initial_offset: int) -> int:
        return initial_offset + self.offset

    def get_id(self):
        id_byte_raw = self.reader(self._translate(self.ID_OFFSET), self.ID_LENGTH)
        if id_byte_raw is None:
            return None
        return id_byte_raw[0]

    def get_revision_compliance(self):
        id_byte_raw = self.reader(self._translate(self.REV_OFFSET), self.REV_LENGTH)
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

