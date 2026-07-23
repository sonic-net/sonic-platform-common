"""
    page00_cdb.py

    CDB-side fields on CMIS Page 00h: CDB1 status byte at offset 37.
"""

from .page import CmisPage
from .....fields.xcvr_field import NumberRegField, RegBitField, RegBitsField
from .....fields.public.cmis import CdbStatusField
from .....fields import cdb_consts


class CdbAdminStatusPage(CmisPage):
    """Page 00h fields relevant to CDB: the CDB1 status byte."""

    def __init__(self, codes):
        super().__init__(codes, page=0x00, bank=0)

        self.fields[cdb_consts.CDB1_CMD_STATUS_FIELD] = [
            NumberRegField(
                cdb_consts.CDB1_CMD_STATUS, self.getaddr(37),
                RegBitField(cdb_consts.CDB1_IS_BUSY, 7),
                RegBitField(cdb_consts.CDB1_HAS_FAILED, 6),
                RegBitsField(cdb_consts.CDB1_STATUS, bitpos=0, size=6),
                bitdecode=True,
            ),
            CdbStatusField(
                cdb_consts.CDB1_COMMAND_RESULT, self.getaddr(37), size=1, format="B",
                deps=[(cdb_consts.CDB1_IS_BUSY, cdb_consts.CDB1_HAS_FAILED, cdb_consts.CDB1_STATUS)],
            ),
        ]

        # CMIS revision (00h:1): major = bits 7-4, minor = bits 3-0. Read as a
        # single byte so the CDB handler can decide whether PasswordCmdResult
        # (00h:42.3-0) is defined for this module (CMIS 5.3+).
        self.fields[cdb_consts.CDB_CMIS_REVISION] = [
            NumberRegField(
                cdb_consts.CDB_CMIS_REVISION, self.getaddr(1), format="B", size=1,
            ),
        ]

        # PasswordCmdResult (00h:42.3-0): result of the most recent password
        # entry/change written to the Password Entry Area (00h:118-125).
        self.fields[cdb_consts.CDB_PASSWORD_CMD_RESULT] = [
            NumberRegField(
                cdb_consts.CDB_PASSWORD_CMD_RESULT, self.getaddr(42),
                RegBitsField(cdb_consts.CDB_PASSWORD_CMD_RESULT_CODE, bitpos=0, size=4),
            ),
        ]
