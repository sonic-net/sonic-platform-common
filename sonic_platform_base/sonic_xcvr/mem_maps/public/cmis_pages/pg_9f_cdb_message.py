"""
    pg_9f_cdb_message.py

    CMIS Page 9Fh - CDB Message Page
"""

from .base import CmisPage
from .cmis_page_consts import CDB_MESSAGE_PAGE
from ....fields.xcvr_field import NumberRegField
from ....fields import consts


class CmisCdbMessagePage(CmisPage):
    def __init__(self, codes, bank=0):
        super().__init__(codes, page=CDB_MESSAGE_PAGE, bank=bank)

        # TRANS_CDB_FIELD (partial - page 9F fields only)
        self.fields[consts.TRANS_CDB_FIELD] = [
            NumberRegField(consts.CDB_RPL_LENGTH, self.getaddr(134), size=1, ro=False),
            NumberRegField(consts.CDB_RPL_CHKCODE, self.getaddr(135), size=1, ro=False),
        ]
