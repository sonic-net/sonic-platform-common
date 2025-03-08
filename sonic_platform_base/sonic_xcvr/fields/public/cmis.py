from ..xcvr_field import NumberRegField, RegBitsField
from .. import consts

from ...codes.public.cdb import CdbCodes
from ...fields import cdb_consts
class CableLenField(NumberRegField):
    def __init__(self, name, offset, *fields, **kwargs):
        kwargs["deps"] = [consts.LEN_MULT_FIELD]
        super(CableLenField, self).__init__(name, offset, *fields, **kwargs)

    def decode(self, raw_data, **decoded_deps):
        base_len = super(CableLenField, self).decode(raw_data, **decoded_deps)
        len_mult = decoded_deps.get(consts.LEN_MULT_FIELD)
        mult = 10 ** (len_mult - 1)
        return base_len * mult

class CdbStatusField(NumberRegField):
    def __init__(self, name, offset, *fields, **kwargs):
        kwargs["deps"] = [cdb_consts.CDB1_IS_BUSY, cdb_consts.CDB1_HAS_FAILED, cdb_consts.CDB1_STATUS]
        super(CdbStatusField, self).__init__(name, offset, *fields, **kwargs)

    def get_status(self, codes, status):
        """
        Get the status of a CDB command
        """
        return codes[status] if status in codes else "Unknown"

    def decode(self, raw_data, **decoded_deps):
        is_busy = decoded_deps.get(cdb_consts.CDB1_CMD_STATUS_FIELD)
        failed = decoded_deps.get(cdb_consts.CDB1_HAS_FAILED)
        cmd_status = decoded_deps.get(cdb_consts.CDB1_STATUS)
       
        if is_busy:
            status = self.get_status(CdbCodes.CDB_IN_PROGRESS, cmd_status)
        elif failed:
            status = self.get_status(CdbCodes.CDB_CMD_FAILED, cmd_status)
        else:
            status = self.get_status(CdbCodes.CDB_CMD_SUCCESS, cmd_status)
        
        return status