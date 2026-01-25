import pytest
import logging

from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes

from xcvr_emu.transceiver import CMISTransceiver  # type: ignore
from xcvr_emu.proto.emulator_pb2 import (  # type: ignore
    ReadRequest,
    WriteRequest,
)
from cmis import MemMap
from cmis.optoe import EEPROM

logger = logging.getLogger(__name__)



class XcvrEmuEeprom(XcvrEeprom):
    def __init__(self, config: dict, mem_map=None):

        codes = CmisCodes

        self.xcvr = CMISTransceiver(
            0,
            {
                "present": True,
                "defaults": config,
            },
            mem_map,
        )

        super().__init__(self._read, self._write, CmisMemMap(codes))

    def _read(self, offset, num_bytes):
        if not self.xcvr.present:
            return None
        # convert optoe offset to SFF page and offset
        # optoe maps the SFF 2D address to a linear address
        page = offset // 128
        if page > 0:
            page = page - 1

        if offset > 128:
            offset = (offset % 128) + 128

        return self.xcvr.read(
            ReadRequest(index=0, offset=offset, page=page, length=num_bytes)
        )

    def _write(self, offset, num_bytes, write_buffer):
        assert len(write_buffer) <= num_bytes
        # convert optoe offset to SFF page and offset
        # optoe maps the SFF 2D address to a linear address
        page = offset // 128
        if page > 0:
            page = page - 1

        if offset > 128:
            offset = (offset % 128) + 128

        return self.xcvr.write(
            WriteRequest(
                index=0,
                page=page,
                offset=offset,
                length=num_bytes,
                data=bytes(write_buffer),
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "emu_response, expected", [("1234567890", "1234567890"), ("ABCD", "ABCD")]
)
async def test_get_model(emu_response, expected):
    eeprom = XcvrEmuEeprom(
        {
            "VendorPN": emu_response,
        },
    )
    api = CmisApi(eeprom)
    result = api.get_model()
    result = result.rstrip("\x00")
    await eeprom.xcvr.plugout()
    assert result == expected

# hexdump taken from https://github.com/sonic-net/sonic-platform-common/issues/489#issue-2445591891
EEPROM_HEXDUMP = """00000000 18 40 00 07 00 00 00 00  00 00 00 00 00 00 17 00 |.@..............|
00000010 82 00 00 00 00 00 00 00  17 80 00 00 00 00 00 00 |................|
00000020 00 00 00 00 00 00 00 01  00 00 00 00 00 00 00 00 |................|
00000030 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
00000040 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
00000050 00 00 00 00 00 03 00 00  00 00 00 00 00 00 00 00 |................|
00000060 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
00000070 00 00 11 00 88 00 00 00  00 00 00 00 00 00 00 00 |................|
00000080 18 43 49 53 43 4f 20 20  20 20 20 20 20 20 20 20 |.CISCO          |
00000090 20 00 06 f6 36 38 2d 31  30 33 32 30 35 2d 30 32 | ...68-103205-02|
000000a0 20 20 20 20 32 20 46 41  42 32 36 31 31 30 30 43 |    2 FAB261100C|
000000b0 51 20 20 20 20 20 32 32  31 30 31 38 20 20 00 00 |Q     221018  ..|
000000c0 00 00 00 00 00 00 00 00  e0 78 00 00 00 00 00 00 |.........x......|
000000d0 00 00 00 00 00 00 00 00  00 00 00 00 00 00 f9 00 |................|
000000e0 1b 00 07 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
000000f0 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|"""

@pytest.mark.asyncio
async def test_get_application_advertisement():
    e = EEPROM()
    e.load(EEPROM_HEXDUMP)
    m = MemMap(e)
    eeprom = XcvrEmuEeprom({}, m)
    api = CmisApi(eeprom)

    data = e.read(0, 0, 0, 256)
    for f, v in m.decode(0, 0, data):
        logger.info(f.to_str(value=v))

    result = api.get_application_advertisement()
    logger.info(f"Application Advertisement: {result}")

    app_id = list(result.keys())[0]

    with pytest.raises(KeyError):
        result = api.get_media_lane_count()

    result = api.get_media_lane_count(app_id)
    logger.info(f"Media Lane Count: {result}")

    await eeprom.xcvr.plugout()
