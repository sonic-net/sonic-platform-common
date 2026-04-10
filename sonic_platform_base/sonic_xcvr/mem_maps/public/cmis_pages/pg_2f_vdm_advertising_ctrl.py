"""
    pg_2f_vdm_advertising_ctrl.py

    CMIS Page 2Fh - VDM Advertising and Control Page
"""

from .base import CmisPage
from .cmis_page_consts import VDM_ADVERTISING_CTRL_PAGE
from ....fields.xcvr_field import (
    NumberRegField,
    RegBitField,
)
from ....fields import consts


class CmisVdmAdvertisingCtrlPage(CmisPage):
    def __init__(self, codes, bank=0):
        super().__init__(codes, page=VDM_ADVERTISING_CTRL_PAGE, bank=bank)

        # TRANS_PM_FIELD
        self.fields[consts.TRANS_PM_FIELD] = [
            NumberRegField(consts.VDM_SUPPORTED_PAGE, self.getaddr(128),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 2))
            ),
            NumberRegField(consts.VDM_CONTROL, self.getaddr(144), size=1, ro=False),
            NumberRegField(consts.VDM_STATUS, self.getaddr(145),
                RegBitField(consts.VDM_UNFREEZE_DONE, 6),
                RegBitField(consts.VDM_FREEZE_DONE, 7),
            ),
        ]
