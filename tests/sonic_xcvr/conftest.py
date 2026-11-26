from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _no_sleep():
    with patch("time.sleep", autospec=True, return_value=None):
        yield


@pytest.fixture
def cmis_eeprom():
    data = bytearray(512)
    data[0:3] = bytes((0x19, 0x53, 0))
    data[39:41] = bytes((172, 133))
    data[129:145] = b"QUALIFIED".ljust(16, b" ")
    data[148:164] = b"REGISTER-OPTIC".ljust(16, b" ")
    data[256:258] = bytes((171, 132))
    reader = MagicMock(side_effect=lambda offset, size: data[offset:offset + size])
    writer = MagicMock(side_effect=AssertionError("Unexpected EEPROM write"))
    return data, reader, writer
