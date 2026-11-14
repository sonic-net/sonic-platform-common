import math
import struct

from .xcvr_field import NumberRegField

# Link report category bitmask -> name (CDB 0x8000 reply, bits 0-6).
_CATEGORY_BITS = {
    0: "LINK_DOWN_COUNTER",
    1: "FEC_BIN_COUNTER",
    2: "PRE_FEC_BER",
    3: "MPI",
    4: "SNR",
    5: "EYE_HEIGHT",
    6: "FLAGS",
}

_RAW_UNITS_PER_MW = 10000.0  # raw optical power registers are 0.1uW/LSB


def _mw_to_dbm_or_floor(mw):
    """Convert mW to dBm, flooring non-positive readings to -40 dBm (module "no light" value)."""
    if mw <= 0:
        return -40.0
    return round(10 * math.log10(mw), 3)


class CredoLinkStatusField(NumberRegField):
    """Decodes the link status byte (bit 0) into a bool."""
    def decode(self, raw_data, **decoded_deps):
        return bool(struct.unpack(self.format, raw_data)[0] & 0x1)


class CredoActiveCategoriesField(NumberRegField):
    """Decodes the 2-byte link report category bitmask into a comma-joined
    string of active category names."""
    def decode(self, raw_data, **decoded_deps):
        mask = struct.unpack(self.format, raw_data)[0]
        return ','.join(name for bit, name in _CATEGORY_BITS.items() if mask & (1 << bit))


class CredoOpticalPowerDbmField(NumberRegField):
    """Decodes a raw 0.1uW/LSB optical power register into dBm. Reused for
    OPTICAL_TX_POWER_MIN/MAX and OPTICAL_RX_POWER_MIN/MAX."""
    def decode(self, raw_data, **decoded_deps):
        raw_units = struct.unpack(self.format, raw_data)[0]
        return _mw_to_dbm_or_floor(raw_units / _RAW_UNITS_PER_MW)
