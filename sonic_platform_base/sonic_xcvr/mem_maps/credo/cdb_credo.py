
import struct

from ..public.cmis.cdb import CDBCommand, CdbMemMap
from ..public.cmis.pages.page import CmisPage
from ...fields.xcvr_field import FixedNumberRegField, NumberRegField, StringRegField
from ...fields.cmis_credo import CredoActiveCategoriesField, CredoLinkStatusField, CredoOpticalPowerDbmField
from ...fields import cdb_consts
from ...fields import credo_cdb_consts as consts

# Credo vendor CDB opcodes (0x8000 range)
CDB_GET_TELEMETRY_INFO_CMD = 0x8000
CDB_ACCESS_REMOTE_BYTE_CMD = 0x8001
CDB_ACCESS_REMOTE_PAGE_CMD = 0x8002

TARGET_CODE = {'local': 0, 'remote': 1}
SIDE_CODE = {'host': 0, 'media': 1}
RW_CODE = {'read': 0, 'write': 1}

# Largest chunk CdbCredoAccessRemotePage can move in one LPL command: the
# LPL payload ceiling (cdb_consts.LPL_MAX_PAYLOAD_SIZE) minus its 5-byte
# target/side/dport/page/rw header. Not a full 128-byte EEPROM page.
REMOTE_PAGE_DATA_SIZE = cdb_consts.LPL_MAX_PAYLOAD_SIZE - 5


class _CmisCdbCredoPage9f(CmisPage):

    def __init__(self, codes):
        super().__init__(codes, page=cdb_consts.LPL_PAGE, bank=0)

        # Get Telemetry Info (0x8000) reply layout, page 9Fh bytes 134-247.
        self.fields[consts.TELEMETRY_INFO_FIELD] = [
            NumberRegField(consts.RPL_LEN, self.getaddr(134), size=1),

            # Link status byte (bit 0) - byte 136
            CredoLinkStatusField(consts.LINK_STATUS, self.getaddr(136), size=1),

            # Link report category mask, score, serial number - bytes 137-155
            CredoActiveCategoriesField(consts.ACTIVE_CATEGORIES, self.getaddr(137), format=">H", size=2),
            NumberRegField(consts.SCORE, self.getaddr(139), size=1),
            StringRegField(consts.SERIAL_NUMBER, self.getaddr(140), size=16),

            # Link/module counters and flags - bytes 156-165
            NumberRegField(consts.LINK_DOWN_CNTR, self.getaddr(156), format=">H", size=2),
            NumberRegField(consts.LINK_UP_TIME, self.getaddr(158), format=">I", size=4),
            NumberRegField(consts.MODULE_FLAGS, self.getaddr(162), size=1),
            NumberRegField(consts.OPTICAL_POWER_FLAGS, self.getaddr(163), size=1),
            NumberRegField(consts.OPTICAL_LASER_BIAS_FLAGS, self.getaddr(164), size=1),
            NumberRegField(consts.MPI, self.getaddr(165), size=1),

            # Link quality/eye/environment measurements - bytes 166-183
            NumberRegField(consts.SNR, self.getaddr(166), format=">H", size=2, scale=256),
            NumberRegField(consts.LTP, self.getaddr(168), format=">H", size=2, scale=256),
            NumberRegField(consts.EYE1, self.getaddr(170), format=">H", size=2),
            NumberRegField(consts.EYE2, self.getaddr(172), format=">H", size=2),
            NumberRegField(consts.EYE3, self.getaddr(174), format=">H", size=2),
            FixedNumberRegField(consts.TEMPERATURE, self.getaddr(176), 8, format=">h", size=2),
            NumberRegField(consts.VOLTAGE, self.getaddr(178), format=">H", size=2, scale=10000),
            CredoOpticalPowerDbmField(consts.OPTICAL_RX_POWER_MIN, self.getaddr(180), format=">H", size=2),
            CredoOpticalPowerDbmField(consts.OPTICAL_RX_POWER_MAX, self.getaddr(182), format=">H", size=2),

            # FEC stats - bytes 184-241 (post-FEC error/bin counters are wider
            # than the pre-FEC BER/RS-FEC bin fields they follow)
            NumberRegField(consts.PRE_FEC_BER, self.getaddr(184), format=">H", size=2),
            NumberRegField(consts.POST_FEC_ERRORS, self.getaddr(186), format=">I", size=4),
            *self._fec_bin_fields(),

            # Shuffle/optical Tx power - bytes 242-247
            NumberRegField(consts.SHUFFLE_DATA_PATH_ID, self.getaddr(242), size=1),
            NumberRegField(consts.SHUFFLE_IB_DETECTION_STATUS, self.getaddr(243), size=1),
            CredoOpticalPowerDbmField(consts.OPTICAL_TX_POWER_MIN, self.getaddr(244), format=">H", size=2),
            CredoOpticalPowerDbmField(consts.OPTICAL_TX_POWER_MAX, self.getaddr(246), format=">H", size=2),
        ]

        # Access Remote Byte (0x8001) reply -- single byte at the LPL reply start.
        self.fields[consts.REMOTE_BYTE_FIELD] = [
            NumberRegField(consts.REMOTE_BYTE_VALUE, self.getaddr(cdb_consts.RPL_DATA_START_OFFSET), size=1),
        ]

        # Access Remote Page (0x8002) reply -- REMOTE_PAGE_DATA_SIZE bytes
        # starting at the LPL reply start.
        self.fields[consts.REMOTE_PAGE_FIELD] = [
            NumberRegField(
                consts.REMOTE_PAGE_DATA, self.getaddr(cdb_consts.RPL_DATA_START_OFFSET),
                format=">{}s".format(REMOTE_PAGE_DATA_SIZE), size=REMOTE_PAGE_DATA_SIZE,
            ),
        ]

    def _fec_bin_fields(self):
        """RS-FEC bin counters, bytes 190-241: bin 0 is 8 bytes, bins 1-7 are
        4 bytes each, bins 8-15 are 2 bytes each."""
        fields = []
        offset = 190
        index = 0
        for count, fmt, size in ((1, ">Q", 8), (7, ">I", 4), (8, ">H", 2)):
            for _ in range(count):
                fields.append(NumberRegField(
                    "{}{}".format(consts.FEC_BIN_PREFIX, index), self.getaddr(offset), format=fmt, size=size,
                ))
                offset += size
                index += 1
        return fields

class CdbCredoTelemetry(CDBCommand):
    """
    Credo vendor CDB command 0x8000 to get per-lane telemetry info (link
    quality/FEC/eye/optical power stats).

    Args:
        id: 2 bytes identifier
        epl: 2 bytes extended payload length
        lpl: 1 byte length of payload
        checksum: 1 byte checksum
    """
    def __init__(self, cmd_id=CDB_GET_TELEMETRY_INFO_CMD):
        super(CdbCredoTelemetry, self).__init__(cmd_id, epl=0, lpl=3)

    def encode(self, payload):
        target = payload.get("target")
        side = payload.get("side")
        dport = payload.get("dport")
        lpl_data = struct.pack("BBB", TARGET_CODE[target], SIDE_CODE[side], dport)
        return super(CdbCredoTelemetry, self).encode(payload=lpl_data)


class CdbCredoAccessRemoteByte(CDBCommand):
    """
    Credo vendor CDB command 0x8001 to read or write a single byte on the
    local/remote side (see TARGET_CODE/SIDE_CODE).

    Args:
        id: 2 bytes identifier
        epl: 2 bytes extended payload length
        lpl: 1 byte length of payload
        checksum: 1 byte checksum
    """
    def __init__(self, cmd_id=CDB_ACCESS_REMOTE_BYTE_CMD):
        super(CdbCredoAccessRemoteByte, self).__init__(cmd_id, epl=0, lpl=6)

    def encode(self, payload):
        target = payload.get("target")
        side = payload.get("side")
        dport = payload.get("dport")
        offset = payload.get("offset")
        rw = payload.get("rw")
        value = payload.get("value", 0)
        lpl_data = struct.pack(
            "BBBBBB", TARGET_CODE[target], SIDE_CODE[side], dport, offset, RW_CODE[rw], value,
        )
        return super(CdbCredoAccessRemoteByte, self).encode(payload=lpl_data)


class CdbCredoAccessRemotePage(CDBCommand):
    """
    Credo vendor CDB command 0x8002 to read or write up to
    REMOTE_PAGE_DATA_SIZE bytes on the local/remote side (see
    TARGET_CODE/SIDE_CODE) -- not a full 128-byte EEPROM page, see
    REMOTE_PAGE_DATA_SIZE.

    Args:
        id: 2 bytes identifier
        epl: 2 bytes extended payload length
        lpl: 1 byte length of payload
        checksum: 1 byte checksum
    """
    def __init__(self, cmd_id=CDB_ACCESS_REMOTE_PAGE_CMD):
        super(CdbCredoAccessRemotePage, self).__init__(cmd_id, epl=0, lpl=5)

    def encode(self, payload):
        target = payload.get("target")
        side = payload.get("side")
        dport = payload.get("dport")
        page = payload.get("page")
        rw = payload.get("rw")
        data = payload.get("data")
        hdr = struct.pack("BBBBB", TARGET_CODE[target], SIDE_CODE[side], dport, page, RW_CODE[rw])
        if data is not None:
            assert len(data) <= REMOTE_PAGE_DATA_SIZE, \
                "data length exceeds REMOTE_PAGE_DATA_SIZE ({})".format(REMOTE_PAGE_DATA_SIZE)
            hdr += data
        return super(CdbCredoAccessRemotePage, self).encode(payload=hdr)


class CmisCdbCredoMemMap(CdbMemMap):
    """CdbMemMap with Credo's vendor CDB commands (0x8000-0x8002) registered
    alongside the standard cdb1_* commands."""

    def __init__(self, codes):
        super().__init__(codes)

        self.cdb_credo_get_telemetry_cmd = CdbCredoTelemetry()
        self.cdb_credo_access_remote_byte_cmd = CdbCredoAccessRemoteByte()
        self.cdb_credo_access_remote_page_cmd = CdbCredoAccessRemotePage()

        self.add_pages(
            _CmisCdbCredoPage9f(codes)
        )
