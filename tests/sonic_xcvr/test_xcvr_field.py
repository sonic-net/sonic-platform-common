try:
   from sonic_platform_base.sonic_xcvr.fields.xcvr_field import (
      RegBitField,
      RegField,
      RegGroupField,
   )
   from sonic_platform_base.sonic_xcvr.mem_maps.xcvr_mem_map import XcvrMemMap
except ImportError as e:
   raise ImportError("%s - required module not found" % e)

class MockXcvrMemMap(XcvrMemMap):
   REG_GROUP = RegGroupField("RegGroup",
      RegField("Field0", 6, ro=False),
      RegField("Field1", 7,
         RegBitField("BitField0", bitpos=0, ro=False),
         RegBitField("BitField1", bitpos=1, ro=False),
         ro=False
      ),
   )

   REG_GROUP_NESTED = RegGroupField("RegGroupNested",
      RegGroupField("RegGroupNestedInner",
         RegField("NestedField0", 9),
         RegField("NestedField1", 10),
      ),
      RegField("NestedField2", 11)
   )

class TestXcvrField(object):
   mem_map = MockXcvrMemMap(None)

   def test_get_fields(self):
      field = self.mem_map.get_field("RegGroup")
      fields = field.get_fields()
      assert fields == {
         "Field0": self.mem_map.get_field("Field0"),
         "Field1": self.mem_map.get_field("Field1"),
         "BitField0": self.mem_map.get_field("BitField0"),
         "BitField1": self.mem_map.get_field("BitField1")
      }

      field = self.mem_map.get_field("RegGroupNested")
      fields = field.get_fields()
      assert fields == {
         "RegGroupNestedInner": self.mem_map.get_field("RegGroupNestedInner"),
         "NestedField0": self.mem_map.get_field("NestedField0"),
         "NestedField1": self.mem_map.get_field("NestedField1"),
         "NestedField2": self.mem_map.get_field("NestedField2")
      }

class TestRegBitField(TestXcvrField):
   def test_offset(self):
      field = self.mem_map.get_field("BitField0")
      parent_field = self.mem_map.get_field("Field1")
      assert field.get_offset() == parent_field.get_offset()

   def test_size(self):
      field = self.mem_map.get_field("BitField0")
      assert field.get_size() == 1

   def test_read_before_write(self):
      field = self.mem_map.get_field("BitField0")
      assert field.read_before_write

   def test_encode_decode(self):
      field = self.mem_map.get_field("BitField1")
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

class TestRegField(TestXcvrField):
   def test_offset(self):
      field = self.mem_map.get_field("Field0")
      assert field.offset == 6

   def test_size(self):
      field = self.mem_map.get_field("Field1")
      assert field.get_size() == 1

   def test_read_before_write(self):
      field = self.mem_map.get_field("Field0")
      assert not field.read_before_write()

   def test_encode_decode(self):
      field = self.mem_map.get_field("Field1")

      assert field.decode(field.encode(0xFF)) == 0xFF
      assert field.decode(field.encode(0)) == 0

class TestRegGroupField(TestXcvrField):
   def test_offset(self):
      field = self.mem_map.get_field("RegGroup")
      assert field.offset == self.mem_map.get_field("Field0").offset

   def test_size(self):
      field = self.mem_map.get_field("RegGroup")
      assert field.get_size() == 2

      field = self.mem_map.get_field("RegGroupNested")
      assert field.get_size() == 3

   def test_read_before_write(self):
      field = self.mem_map.get_field("RegGroup")
      assert not field.read_before_write()

   def test_decode(self):
      field = self.mem_map.get_field("RegGroup")
      data = bytearray([0, 1])
      decoded = field.decode(data)

      assert decoded == {
         "Field0": 0,
         "Field1": 1
      }

      field = self.mem_map.get_field("RegGroupNested")
      data = bytearray([0, 1, 2])
      decoded = field.decode(data)

      assert decoded == {
         "RegGroupNestedInner": {
            "NestedField0": 0,
            "NestedField1": 1,
         },
         "NestedField2": 2,
      }