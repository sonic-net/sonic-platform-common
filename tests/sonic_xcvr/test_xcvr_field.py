from sonic_platform_base.sonic_xcvr.fields.xcvr_field import (
    CodeRegField,
    DateField,
    FixedNumberRegField,
    HexRegField,
    ServerFWVersionRegField,
    NumberRegField,
    RegBitField,
    RegBitsField,
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

    SHIFTED_CODE_DICT = {
       0: "Code0",
       1: "Code1",
       2: "Code2",
       3: "Code3",
    }

    DATAPATH_STATE = {
        1: 'DataPathDeactivated',
        2: 'DataPathInit',
        3: 'DataPathDeinit',
        4: 'DataPathActivated',
        5: 'DataPathTxTurnOn',
        6: 'DataPathTxTurnOff',
        7: 'DataPathInitialized',
    }

class MockXcvrMemMap(XcvrMemMap):
    def __init__(self, codes):
        super(MockXcvrMemMap, self).__init__(codes)

        self.CODE_REG = CodeRegField("CodeReg", 5, self.codes.CODE_DICT)
        self.SHIFTED_CODE_REG = CodeRegField("ShiftedCodeReg", 50, self.codes.SHIFTED_CODE_DICT,
            RegBitField("CodeBit7", bitpos=7),
            RegBitField("CodeBit8", bitpos=8),
            size=2, format=">H")
        self.NUM_REG = NumberRegField("NumReg", 100, format=">Q", size=8, ro=False)
        self.SCALE_NUM_REG = NumberRegField("ScaleNumReg", 120, format=">i", size=4, scale=100, ro=False)
        self.FIXED_NUM_REG = FixedNumberRegField("FixedNumReg", 130, 8, format=">f", size=4, ro=False)
        self.NUM_REG_WITH_BIT = NumberRegField("NumRegWithBit", 140,
            RegBitField("NumRegBit", bitpos=20, ro=False),
            format="<I", size=4, ro=False
        )
        self.NUM_REG_2BITS = NumberRegField("MultiBitsReg1", 154,
            RegBitsField("Bits0to1", bitpos=0, ro=False, size=2),
            RegBitsField("Bits2to3", bitpos=2, ro=False, size=2),
            RegBitsField("Bits4to5", bitpos=4, ro=False, size=2),
            RegBitsField("Bits6to7", bitpos=6, ro=False, size=2)
        )
        self.NUM_REG_4BITS = NumberRegField("MultiBitsReg2", 162, 
            RegBitsField("Bits0to3", bitpos=0, ro=False, size=4),
            RegBitsField("Bits4to7", bitpos=4, ro=False, size=4)
        )
        self.STRING_REG = StringRegField("StringReg", 12, size=15)
        self.HEX_REG = HexRegField("HexReg", 30, size=3)
        self.BYTES_REG = ServerFWVersionRegField("BytesReg", 10, size=4)
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

        self.REG_GROUP_NON_CONTIGUOUS = RegGroupField("RegGroupNonContiguous",
            NumberRegField("Field3", 50, format="<I", size=4),
            NumberRegField("Field4", 55, format="<I", size=4)
        )

        self.DATE = DateField("Date", 60, size=8)
        self.combo = RegGroupField("COMBO_ACTIVE_APPL",
                        *(NumberRegField("ACTIVE_APPL%d" % (lane) , offset,
                            *(RegBitField("Bit%d" % bit, bit) for bit in range(0, 4)))
                            for lane, offset in zip(range(1, 9), range(186, 214)))
        )

        self.dp_state = RegGroupField("DATA_PATH_STATE",
                *(CodeRegField("DP%dState" % (lane) , 0, self.codes.DATAPATH_STATE,
                    *(RegBitField("Bit%d" % bit, bit) for bit in [range(4, 8), range(0, 4)][lane%2]))
                 for lane in range(1, 9))
        )

codes = MockXcvrCodes
mem_map = MockXcvrMemMap(codes)

field = mem_map.get_field("COMBO_ACTIVE_APPL")
data = bytearray([0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7])
decoded = field.decode(data)
assert decoded == {
               "ACTIVE_APPL1": 0,
               "ACTIVE_APPL2": 1,
               "ACTIVE_APPL3": 2,
               "ACTIVE_APPL4": 3,
               "ACTIVE_APPL5": 4,
               "ACTIVE_APPL6": 5,
               "ACTIVE_APPL7": 6,
               "ACTIVE_APPL8": 7
            }

field = mem_map.get_field("DATA_PATH_STATE")
data = bytearray([0x47, 0x47, 0x47, 0x47])
decoded = field.decode(data)
assert decoded == {
        "DP1State" : "DataPathInitialized",
        "DP2State" : "DataPathActivated",
        "DP3State" : "DataPathInitialized",
        "DP4State" : "DataPathActivated",
        "DP5State" : "DataPathInitialized",
        "DP6State" : "DataPathActivated",
        "DP7State" : "DataPathInitialized",
        "DP8State" : "DataPathActivated",
}

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

class TestRegBitsField(object):
    def test_encode_decode(self):
        field = mem_map.get_field("Bits0to1")
        encoded_data = field.encode(0x3, bytearray(b'\xfc'))
        assert encoded_data == bytearray(b'\xff')
        decoded_data = field.decode(bytearray(b'\xf2'))
        assert decoded_data == 0x2

        field = mem_map.get_field("Bits2to3")
        encoded_data = field.encode(0x0, bytearray(b'\xff'))
        assert encoded_data == bytearray(b'\xf3')
        decoded_data = field.decode(bytearray(b'\xf4'))
        assert decoded_data == 0x1

        field = mem_map.get_field("Bits4to5")
        encoded_data = field.encode(0x2, bytearray(b'\xff'))
        assert encoded_data == bytearray(b'\xef')
        decoded_data = field.decode(bytearray(b'\xef'))
        assert decoded_data == 0x2

        field = mem_map.get_field("Bits6to7")
        encoded_data = field.encode(0x2, bytearray(b'\xff'))
        assert encoded_data == bytearray(b'\xbf')
        decoded_data = field.decode(bytearray(b'\xbf'))
        assert decoded_data == 0x2

        field = mem_map.get_field("Bits6to7")
        encoded_data = field.encode(0x1, bytearray(b'\xff'))
        assert encoded_data == bytearray(b'\x7f')
        decoded_data = field.decode(bytearray(b'\x7f'))
        assert decoded_data == 0x1

        field = mem_map.get_field("Bits0to3")
        encoded_data = field.encode(0x3, bytearray(b'\xff'))
        assert encoded_data == bytearray(b'\xf3')
        decoded_data = field.decode(bytearray(b'\xf3'))
        assert decoded_data == 3
        field = mem_map.get_field("Bits4to7")
        encoded_data = field.encode(0x3, bytearray(b'\xff'))
        assert encoded_data == bytearray(b'\x3f')
        decoded_data = field.decode(bytearray(b'\xf3'))
        assert decoded_data == 0xf
    
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
        field = mem_map.get_field("NumRegBit")
        assert field.decode(field.encode(True, bytearray(b'\x00')))
        assert not field.decode(field.encode(False, bytearray(b'\xFF')))

        field = mem_map.get_field("NumRegBit")
        assert field.decode(field.encode(True, bytearray(b'\x00')))
        assert not field.decode(field.encode(False, bytearray(b'\xFF')))

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
        assert field.decode(field.encode(val)) == 3
        assert field.decode(field.encode(0)) == 0

class TestFixedNumberRegField(object):
    def test_encode_decode(self):
        field = mem_map.get_field("FixedNumReg")
        val = 1.25
        assert field.decode(field.encode(val)) == val

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

        field = mem_map.get_field("ShiftedCodeReg")
        data = bytearray([0xFE, 0x7F])
        assert field.decode(data) == "Code0"
        data = bytearray([0xFE, 0xFF])
        assert field.decode(data) == "Code1"
        data = bytearray([0xFF, 0x7F])
        assert field.decode(data) == "Code2"
        data = bytearray([0xFF, 0xFF])
        assert field.decode(data) == "Code3"

class TestHexRegField(object):
    def test_decode(self):
        field = mem_map.get_field("HexReg")
        data = bytearray([0xAA, 0xBB, 0xCC])
        assert field.decode(data) == "aa-bb-cc"

class TestServerFWVersionRegField(object):
    def test_decode(self):
        field = mem_map.get_field("BytesReg")
        data = bytearray([0, 0, 0, 1, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 5, 0x8d])
        assert field.decode(data) == (bytearray([0, 0, 0, 1, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 5, 0x8d]), "1.5.0.1421")

class TestRegGroupField(object):
    def test_offset(self):
        field = mem_map.get_field("RegGroup")
        assert field.offset == mem_map.get_field("Field0").offset

    def test_size(self):
        field = mem_map.get_field("RegGroup")
        assert field.get_size() == 5

        field = mem_map.get_field("RegGroupNested")
        assert field.get_size() == 3

        field = mem_map.get_field("RegGroupNonContiguous")
        assert field.get_size() == 9

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

        field = mem_map.get_field("RegGroupNonContiguous")
        data = bytearray(b'\x01\x02\x03\x04\x01\x02\x03\x04\x01')
        decoded = field.decode(data)

        assert decoded == {
            "Field3": 0x04030201,
            "Field4": 0x01040302,
        }

class TestDateField(object):
    def test_decode(self):
        field = mem_map.get_field("Date")
        data = bytearray(b'\x32\x31\x31\x30\x32\x30\x00\x00')
        decoded = field.decode(data)
        assert decoded == "2021-10-20 \0\0"
