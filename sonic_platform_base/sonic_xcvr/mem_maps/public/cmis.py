"""
    cmis.py

    Implementation of XcvrMemMap for CMIS Rev 4.0
"""

from ..xcvr_mem_map import XcvrMemMap
from ...fields.xcvr_field import (
    CodeRegField,
    HexRegField,
    NumberRegField,
    RegGroupField,
    StringRegField,
)
from ...fields import consts

PAGE_SIZE = 128

def get_addr(page, offset):
    return PAGE_SIZE * page + offset

class CmisMemMap(XcvrMemMap):
    def __init__(self, codes):
        super(CmisMemMap, self).__init__(codes)

        self.ADMIN_INFO = RegGroupField(consts.ADMIN_INFO_FIELD,
            CodeRegField(consts.ID_FIELD, get_addr(0x0, 128), self.codes.XCVR_IDENTIFIERS),
            StringRegField(consts.VENDOR_NAME_FIELD, get_addr(0x0, 129), size=16),
            HexRegField(consts.VENDOR_OUI_FIELD, get_addr(0x0, 145), size=3),
            StringRegField(consts.VENDOR_PART_NO_FIELD, get_addr(0x0, 148), size=16),
            # TODO: add remaining admin fields
        )

        self.MEDIA_LANE_FEC_PM = RegGroupField(consts.MEDIA_LANE_FEC_PM_FIELD,
            NumberRegField(consts.RX_BITS_PM_FIELD, get_addr(0x34, 128), format=">Q", size=8),
            NumberRegField(consts.RX_BITS_SUB_INT_PM_FIELD, get_addr(0x34, 136), format=">Q", size=8),
            # TODO: add other PMs...
        )

        self.MEDIA_LANE_LINK_PM = RegGroupField(consts.MEDIA_LANE_LINK_PM_FIELD,
            NumberRegField(consts.RX_AVG_CD_PM_FIELD, get_addr(0x35, 128), format=">i", size=4),
            NumberRegField(consts.RX_MIN_CD_PM_FIELD, get_addr(0x35, 132), format=">i", size=4),
            NumberRegField(consts.RX_MAX_CD_PM_FIELD, get_addr(0x35, 136), format=">i", size=4),
            NumberRegField(consts.RX_AVG_DGD_PM_FIELD, get_addr(0x35, 140), format=">H", size=2, scale=100)
            # TODO: add others PMs...
        )

        # TODO: add remaining fields
