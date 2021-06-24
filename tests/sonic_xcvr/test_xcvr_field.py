from sonic_platform_base.sonic_xcvr.fields.xcvr_field import (
    CodeRegField,
    HexRegField,
    NumberRegField,
    RegBitField,
    RegGroupField,
    StringRegField,
)
from sonic_platform_base.sonic_xcvr.codes.xcvr_codes import XcvrCodes
from sonic_platform_base.sonic_xcvr.mem_maps.xcvr_mem_map import XcvrMemMap

class MockXcvrCodes(XcvrCodes):
    CODE_DICT = {
        0: "Code0",
        1: "Code1"

    }

    LARGE_CODE_DICT = {
       0: "Code0",
       128: "Code128",
       256: "Code256",
       384: "Code384"
    }

class MockXcvrMemMap(XcvrMemMap):
    def __init__(self, codes):
        super(MockXcvrMemMap, self).__init__(codes)

        self.CODE_REG = CodeRegField("CodeReg", 5, self.codes.CODE_DICT)
        self.LARGE_CODE_REG = CodeRegField("LargeCodeReg", 50, self.codes.LARGE_CODE_DICT,
            RegBitField("CodeBit7", bitpos=7),
            RegBitField("CodeBit8", bitpos=8),
            size=2, format=">H")
        self.NUM_REG = NumberRegField("NumReg", 100, format=">Q", size=8, ro=False)
        self.SCALE_NUM_REG = NumberRegField("ScaleNumReg", 120, format=">i", size=4, scale=100, ro=False)
        self.STRING_REG = StringRegField("StringReg", 12, size=15)
        self.HEX_REG = HexRegField("HexReg", 30, size=3)
        self.REG_GROUP = RegGroupField("RegGroup",
            NumberRegField("Field0", 6, ro=False),
            NumberRegField("Field1", 7,
                RegBitField("BitField0", bitpos=0, ro=False),
                RegBitField("BitField1", bitpos=1, ro=False),
                ro=False
            ),
            NumberRegField("Field2", 7, format=">I", size=4),
        )

        self.REG_GROUP_NESTED = RegGroupField("RegGroupNested",
            RegGroupField("RegGroupNestedInner",
                NumberRegField("NestedField0", 9),
                NumberRegField( "NestedField1", 10),
            ),
            NumberRegField("NestedField2", 11)
        )

codes = MockXcvrCodes
mem_map = MockXcvrMemMap(codes)

class TestXcvrField(object):
    def test_get_fields(self):
        field = mem_map.get_field("RegGroup")
        fields = field.get_fields()
        assert fields == {
            "Field0": mem_map.get_field("Field0"),
            "Field1": mem_map.get_field("Field1"),
            "BitField0": mem_map.get_field("BitField0"),
            "BitField1": mem_map.get_field("BitField1"),
            "Field2": mem_map.get_field("Field2")
        }

        field = mem_map.get_field("RegGroupNested")
        fields = field.get_fields()
        assert fields == {
            "RegGroupNestedInner": mem_map.get_field("RegGroupNestedInner"),
            "NestedField0": mem_map.get_field("NestedField0"),
            "NestedField1": mem_map.get_field("NestedField1"),
            "NestedField2": mem_map.get_field("NestedField2")
        }

class TestRegBitField(object):
    def test_offset(self):
        field = mem_map.get_field("BitField0")
        parent_field = mem_map.get_field("Field1")
        assert field.get_offset() == parent_field.get_offset()

    def test_size(self):
        field = mem_map.get_field("BitField0")
        assert field.get_size() == 1

    def test_read_before_write(self):
        field = mem_map.get_field("BitField0")
        assert field.read_before_write

    def test_encode_decode(self):
        field = mem_map.get_field("BitField1")
        encoded_data = field.encode(True, bytearray(b'\x01'))
        assert encoded_data == bytearray(b'\x03')

        encoded_data = field.encode(False, bytearray(b'\x03'))
        assert encoded_data == bytearray(b'\x01')

        decoded_data = field.decode(bytearray(b'\x02'))
        assert decoded_data

        decoded_data = field.decode(bytearray(b'\x00'))
        assert not decoded_data

        assert field.decode(field.encode(True, bytearray(b'\x00')))
        assert not field.decode(field.encode(False, bytearray(b'\x00')))

class TestRegField(object):
    def test_offset(self):
        field = mem_map.get_field("Field0")
        assert field.offset == 6

    def test_size(self):
        field = mem_map.get_field("Field1")
        assert field.get_size() == 1

    def test_read_before_write(self):
        field = mem_map.get_field("Field0")
        assert not field.read_before_write()

class TestNumberRegField(object):
    def test_encode_decode(self):
        field = mem_map.get_field("NumReg")
        val = 0xFFFFFFFFFFFFFFFF
        assert field.decode(field.encode(val)) == val

        field = mem_map.get_field("ScaleNumReg")
        val = -100
        assert field.decode(field.encode(val)) == val

        field = mem_map.get_field("Field1")
        val = 0xFF
        assert field.decode(field.encode(val)) == val
        assert field.decode(field.encode(0)) == 0

class TestStringRegField(object):
    def test_decode(self):
        field = mem_map.get_field("StringReg")
        data = bytearray("Arista Networks".encode("ascii"))
        assert field.decode(data) == "Arista Networks"

class TestCodeRegField(object):
    def test_decode(self):
        field = mem_map.get_field("CodeReg")
        data = bytearray([0])
        assert field.decode(data) == "Code0"

        data = bytearray([1])
        assert field.decode(data) == "Code1"

        field = mem_map.get_field("LargeCodeReg")
        data = bytearray([0xFE, 0x7F])
        assert field.decode(data) == "Code0"
        data = bytearray([0xFE, 0xFF])
        assert field.decode(data) == "Code128"
        data = bytearray([0xFF, 0x7F])
        assert field.decode(data) == "Code256"
        data = bytearray([0xFF, 0xFF])
        assert field.decode(data) == "Code384"

class TestHexRegField(object):
    def test_decode(self):
        field = mem_map.get_field("HexReg")
        data = bytearray([0xAA, 0xBB, 0xCC])
        assert field.decode(data) == "aa-bb-cc"

class TestRegGroupField(object):
    def test_offset(self):
        field = mem_map.get_field("RegGroup")
        assert field.offset == mem_map.get_field("Field0").offset

    def test_size(self):
        field = mem_map.get_field("RegGroup")
        assert field.get_size() == 5

        field = mem_map.get_field("RegGroupNested")
        assert field.get_size() == 3

    def test_read_before_write(self):
        field = mem_map.get_field("RegGroup")
        assert not field.read_before_write()

    def test_decode(self):
        field = mem_map.get_field("RegGroup")
        data = bytearray([0, 1, 2, 0, 0])
        decoded = field.decode(data)

        assert decoded == {
            "Field0": 0,
            "Field1": 1,
            "Field2": 0x01020000,
        }

        field = mem_map.get_field("RegGroupNested")
        data = bytearray([0, 1, 2])
        decoded = field.decode(data)

        assert decoded == {
            "RegGroupNestedInner": {
                "NestedField0": 0,
                "NestedField1": 1,
            },
            "NestedField2": 2,
        }
