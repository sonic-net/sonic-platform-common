from ..xcvr_field import NumberRegField
from .. import consts

class CableLenField(NumberRegField):
    def __init__(self, name, offset, *fields, **kwargs):
        kwargs["deps"] = [consts.LEN_MULT_FIELD]
        super(CableLenField, self).__init__(name, offset, *fields, **kwargs)

    def decode(self, raw_data, **decoded_deps):
        base_len = super(CableLenField, self).decode(raw_data, **decoded_deps)
        len_mult = decoded_deps.get(consts.LEN_MULT_FIELD)
        mult = 10 ** (len_mult - 1)
        return base_len * mult
