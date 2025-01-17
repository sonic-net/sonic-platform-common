import pytest

from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes

from xcvr_emu.transceiver import CMISTransceiver  # type: ignore
from xcvr_emu.proto.emulator_pb2 import (  # type: ignore
    ReadRequest,
    WriteRequest,
)


class XcvrEmuEeprom(XcvrEeprom):
    def __init__(self, config: dict):

        codes = CmisCodes
        mem_map = CmisMemMap(codes)

        self.xcvr = CMISTransceiver(
            0,
            {
                "present": True,
                "defaults": config,
            },
        )

        super().__init__(self._read, self._write, mem_map)

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
    await eeprom.xcvr.plugout()
    assert result == expected
