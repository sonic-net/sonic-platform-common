"""
   xcvr_field.py

   Classes for representing types of fields found in xcvr memory maps.
"""

class XcvrField(object):
   def __init__(self, name, offset, ro):
      self.name = name
      self.offset = offset
      self.ro = ro

   def get_fields(self):
      fields = {}
      if hasattr(self, 'fields'):
         for field in self.fields:
            fields[field.name] = field
            fields.update(field.get_fields())
      return fields

   def get_offset(self):
      return self.offset

   def get_size(self):
      raise NotImplementedError

   def read_before_write(self):
      raise NotImplementedError

   def decode(self, raw_data):
      raise NotImplementedError

   def encode(self, val, raw_state=None):
      raise NotImplementedError

class RegBitField(XcvrField):
   def __init__(self, name, bitpos, parent=None, ro=True, offset=None):
      super(RegBitField, self).__init__(name, offset, ro)
      self.bitpos = bitpos
      self.parent = parent

   def get_size(self):
      return 1

   def read_before_write(self):
      return True

   def decode(self, raw_data):
      return (raw_data[0] >> self.bitpos) & 1

   def encode(self, val, raw_state=None):
      assert not self.ro and raw_state is not None
      curr_state = raw_state[0]
      if val:
         curr_state |= (1 << self.bitpos)
      else:
         curr_state &= ~(1 << self.bitpos)
      return bytearray([curr_state])

class RegField(XcvrField):
   def __init__(self, name, offset, *fields, **kwargs):
      super(RegField, self).__init__(name, offset, kwargs.get('ro', True))
      self.fields = fields
      self._updateBitOffsets()

   def _updateBitOffsets(self):
      for field in self.fields:
         field.offset = self.offset

   def get_size(self):
      return 1

   def read_before_write(self):
      return False

   def decode(self, raw_data):
      return raw_data[0]

   def encode(self, val, raw_state=None):
      assert not self.ro
      return bytearray([val])

class RegGroupField(XcvrField):
   def __init__(self, name, *fields, **kwargs):
      super(RegGroupField, self).__init__(name, fields[0].offset, kwargs.get('ro', True))
      self.fields = fields

   def get_size(self):
      size = 0
      for field in self.fields:
         size += field.get_size()
      return size

   def read_before_write(self):
      return False

   def decode(self, raw_data):
      result = {}
      index = 0
      for field in self.fields:
         result[field.name] = field.decode(raw_data[index : index + field.get_size()])
         index += field.get_size()
      return result
