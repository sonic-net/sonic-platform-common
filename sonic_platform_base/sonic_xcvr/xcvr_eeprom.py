"""
   xcvr_eeprom.py

   Common API used by all XcvrApis to read and write to various fields that can be found in a xcvr EEPROM
"""

class XcvrEeprom(object):
   def __init__(self, reader, writer, mem_map):
      self.reader = reader
      self.writer = writer
      self.mem_map = mem_map

   def read(self, field_name):
      """
      Read a value from a field in EEPROM

      Args:
         field_name: a string denoting the XcvrField to read from

      Returns:
         The value of the field, if the read is successful and None otherwise
      """
      field = self.mem_map.get_field(field_name)
      raw_data = self.reader(field.get_offset(), field.get_size())
      return field.decode(raw_data) if raw_data is not None else None

   def write(self, field_name, value):
      """
      Write a value to a field in EEPROM

      Args:
         field_name: a string denoting the XcvrField to write to

         value:
            The value to write to the EEPROM, appropriate for the given field_name

      Returns:
         Boolean, True if the write is successful and False otherwise
      """
      field = self.mem_map.get_field(field_name)
      if field.read_before_write():
         encoded_data = field.encode(value, self.reader(field.get_offset(), field.get_size()))
      else:
         encoded_data = field.encode(value)
      return self.writer(field.get_offset(), field.get_size(), encoded_data)
