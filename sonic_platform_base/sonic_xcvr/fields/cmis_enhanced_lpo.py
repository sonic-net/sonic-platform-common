import struct

from .xcvr_field import NumberRegField


class _LpoScaledNumberRegField(NumberRegField):
    factor = 1

    def __init__(self, name, offset, *fields, **kwargs):
        super(_LpoScaledNumberRegField, self).__init__(name, offset, *fields, **kwargs)
        self.precision = kwargs.get("precision", 3)

    def decode(self, raw_data, **decoded_deps):
        value = struct.unpack(self.format, raw_data)[0] * self.factor
        return float("{:.{}f}".format(value, self.precision))


class _LpoLowerNibbleScaledRegField(_LpoScaledNumberRegField):
    def decode(self, raw_data, **decoded_deps):
        value = (struct.unpack(self.format, raw_data)[0] & 0x0F) * self.factor
        return float("{:.{}f}".format(value, self.precision))


class LpoVmaField(_LpoScaledNumberRegField):
    factor = 5


class LpoOmaField(_LpoScaledNumberRegField):
    factor = 0.0001


class LpoOerField(_LpoScaledNumberRegField):
    factor = 0.1


class LpoVmaAccuracyField(_LpoLowerNibbleScaledRegField):
    factor = 5


class LpoOmaAccuracyField(_LpoLowerNibbleScaledRegField):
    factor = 0.2


class LpoLaneFlagRegField(NumberRegField):
    def decode(self, raw_data, **decoded_deps):
        value = struct.unpack(self.format, raw_data)[0]
        decoded = {}
        for lane in range(1, 9):
            decoded["{}{}".format(self.name, lane)] = bool((value >> (lane - 1)) & 1)
        return decoded
