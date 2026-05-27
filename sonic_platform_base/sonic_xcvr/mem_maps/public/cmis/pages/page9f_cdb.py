"""
    page9f_cdb.py

    CDB LPL Message Page (CMIS Page 9Fh). Holds the CDB reply-payload area:
    Query Status, Firmware Info, and Firmware Mgmt Features fields.
"""

from .page import CmisPage
from .....fields.xcvr_field import CodeRegField, NumberRegField, RegBitField
from .....fields import cdb_consts


class CdbLplMessagePage(CmisPage):
    """CDB-side fields on CMIS Page 9Fh (LPL message area)."""

    def __init__(self, codes):
        super().__init__(codes, page=cdb_consts.LPL_PAGE, bank=0)

        # Top-level Query Status field (single CodeRegField, not grouped).
        self.fields[cdb_consts.CDB1_QUERY_STATUS] = [
            CodeRegField(
                cdb_consts.CDB1_QUERY_STATUS, self.getaddr(137), codes.CDB_QUERY_STATUS,
            ),
        ]

        # Firmware info group (bytes 136..212)
        self.fields[cdb_consts.CDB1_FIRMWARE_INFO] = [
            NumberRegField(
                cdb_consts.CDB1_FIRMWARE_STATUS, self.getaddr(136),
                RegBitField(cdb_consts.CDB1_BANKA_OPER_STATUS, 0),
                RegBitField(cdb_consts.CDB1_BANKA_ADMIN_STATUS, 1),
                RegBitField(cdb_consts.CDB1_BANKA_VALID_STATUS, 2),
                RegBitField(cdb_consts.CDB1_BANKB_OPER_STATUS, 4),
                RegBitField(cdb_consts.CDB1_BANKB_ADMIN_STATUS, 5),
                RegBitField(cdb_consts.CDB1_BANKB_VALID_STATUS, 6),
                bitdecode=True,
            ),
            NumberRegField(
                cdb_consts.CDB1_IMAGE_INFO, self.getaddr(137),
                RegBitField(cdb_consts.CDB1_IMAGEA_VERSION_PRESENT, 0),
                RegBitField(cdb_consts.CDB1_IMAGEB_VERSION_PRESENT, 1),
                RegBitField(cdb_consts.CDB1_FACTIMG_VERSION_PRESENT, 2),
            ),
            NumberRegField(cdb_consts.CDB1_BANKA_MAJOR_VERSION, self.getaddr(138), size=1),
            NumberRegField(cdb_consts.CDB1_BANKA_MINOR_VERSION, self.getaddr(139), size=1),
            NumberRegField(cdb_consts.CDB1_BANKA_BUILD_VERSION, self.getaddr(140), size=2, format=">H"),
            NumberRegField(cdb_consts.CDB1_BANKB_MAJOR_VERSION, self.getaddr(174), size=1),
            NumberRegField(cdb_consts.CDB1_BANKB_MINOR_VERSION, self.getaddr(175), size=1),
            NumberRegField(cdb_consts.CDB1_BANKB_BUILD_VERSION, self.getaddr(176), size=2, format=">H"),
            NumberRegField(cdb_consts.CDB1_FACTORY_MAJOR_VERSION, self.getaddr(210), size=1),
            NumberRegField(cdb_consts.CDB1_FACTORY_MINOR_VERSION, self.getaddr(211), size=1),
            NumberRegField(cdb_consts.CDB1_FACTORY_BUILD_VERSION, self.getaddr(212), size=2, format=">H"),
        ]

        # Firmware management features group (bytes 137..142)
        self.fields[cdb_consts.CDB_FIRMWARE_MGMT_FEATURES] = [
            NumberRegField(
                cdb_consts.CDB_FIRMWARE_MGMT_ADV, self.getaddr(137),
                RegBitField(cdb_consts.CDB_MAX_DURATION_ENCODING, 3),
                RegBitField(cdb_consts.CDB_ABORT_CMD_SUPPORTED, 0),
            ),
            NumberRegField(cdb_consts.CDB_START_CMD_PAYLOAD_SIZE, self.getaddr(138)),
            NumberRegField(cdb_consts.CDB_READ_WRITE_LENGTH_EXT, self.getaddr(140), scale=0.125),
            CodeRegField(cdb_consts.CDB_WRITE_MECHANISM, self.getaddr(141), codes.CDB_WRITE_METHOD),
            CodeRegField(cdb_consts.CDB_READ_MECHANISM, self.getaddr(142), codes.CDB_READ_METHOD),
            NumberRegField(cdb_consts.CDB_MAX_DURATION_START, self.getaddr(144), size=2, format=">H"),
            NumberRegField(cdb_consts.CDB_MAX_DURATION_ABORT, self.getaddr(146), size=2, format=">H"),
            NumberRegField(cdb_consts.CDB_MAX_DURATION_WRITE, self.getaddr(148), size=2, format=">H"),
            NumberRegField(cdb_consts.CDB_MAX_DURATION_COMPLETE, self.getaddr(150), size=2, format=">H"),
            NumberRegField(cdb_consts.CDB_MAX_DURATION_COPY, self.getaddr(152), size=2, format=">H"),
        ]
