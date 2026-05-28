from sonic_platform_base.sonic_xcvr.eeprom_rw import EepromReadWriteMixin
from abc import ABC, abstractmethod

SFP_OPTOE_PAGE_SELECT_OFFSET = 127
SFP_OPTOE_UPPER_PAGE0_OFFSET = 128
SFP_OPTOE_PAGE_SIZE = 128

CMIS_MODULE_IDS = (0x18, 0x19, 0x1b, 0x1e)
# Lower-memory byte 2 bit 7: 1 = flat memory (lower + upper page 00h only), 0 = paged.
CMIS_FLAT_MEM_FILE_OFFSET = 2
CMIS_FLAT_MEM_BIT_MASK = 0x80
# Page 01h byte 142 in the optoe linear EEPROM file at bank-0 stride.
CMIS_BANKS_SUPPORTED_FILE_OFFSET = 270
# CMIS AdvBnkSupport (page 01h byte 142, bits 0-1): 00b->1, 01b->2, 10b->4 banks.
CMIS_BANKS_SUPPORTED_TO_MAX_BANK_SIZE = {0: 0, 1: 2, 2: 4}

class OptoeEepromReadWriteMixin(EepromReadWriteMixin, ABC):
    @abstractmethod
    def get_eeprom_path(self) -> str:
        pass

    def set_optoe_write_max(self, write_max):
        sys_path = self.get_eeprom_path()
        sys_path = sys_path.replace("eeprom", "write_max")
        try:
            with open(sys_path, mode='w') as f:
                f.write(str(write_max))
        except (OSError, IOError):
            pass

    def set_optoe_max_bank_size(self, max_bank_size):
        """Write max_bank_size to the optoe driver's sysfs entry; required before banked EEPROM offsets are accessible"""
        sys_path = self.get_eeprom_path().replace("eeprom", "max_bank_size")
        try:
            with open(sys_path) as f:
                if int(f.read().strip()) == max_bank_size:
                    return
            with open(sys_path, mode='w') as f:
                f.write(str(max_bank_size))
        except FileNotFoundError:
            # Some platforms/drivers do not expose max_bank_size in sysfs.
            return

    def set_optoe_write_timeout(self, write_timeout):
        sys_path = self.get_eeprom_path()
        sys_path = sys_path.replace("eeprom", "write_timeout")
        try:
            with open(sys_path, mode='w') as f:
                f.write(str(write_timeout))
        except (OSError, IOError):
            pass

    def set_page0(self):
        self.write_eeprom(SFP_OPTOE_PAGE_SELECT_OFFSET, 1, bytearray([0x00]))

    def get_optoe_current_page(self):
        return self.read_eeprom(SFP_OPTOE_PAGE_SELECT_OFFSET, 1)[0]

    def read_eeprom(self, offset, num_bytes):
        try:
            with open(self.get_eeprom_path(), mode='rb', buffering=0) as f:
                if offset >= SFP_OPTOE_UPPER_PAGE0_OFFSET  and \
                    offset < (SFP_OPTOE_UPPER_PAGE0_OFFSET+SFP_OPTOE_PAGE_SIZE) and \
                        self.get_optoe_current_page() != 0:
                    # Restoring the page to 0 helps in cases where the optoe driver failed to restore
                    # the page when say the module was busy with CDB command processing
                   self.set_page0()
                f.seek(offset)
                return bytearray(f.read(num_bytes))
        except (OSError, IOError):
            return None

    def write_eeprom(self, offset, num_bytes, write_buffer):
        try:
            with open(self.get_eeprom_path(), mode='r+b', buffering=0) as f:
                f.seek(offset)
                f.write(write_buffer[0:num_bytes])
        except (OSError, IOError):
            return False
        return True
