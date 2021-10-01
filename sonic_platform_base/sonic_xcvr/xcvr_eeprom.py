"""
   xcvr_eeprom.py

   Common API used by all XcvrApis to read and write to various fields that can be found in a xcvr EEPROM
"""
import struct

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

   def read_flexible(self, offset, size, return_raw = False):
      """
      Read values from a field in EEPROM in a more flexible way

      Args:
         offset: an integer indicating the offset of the starting position of the 
         EEPROM byte(s) to read from

         size: an integer indicating how many bytes to read from
      Returns:
         The value(s) of the field, if the read is successful and None otherwise
      """
      raw_data = self.reader(offset, size)
      if return_raw:
         return raw_data
      if raw_data is None:
         return None
      else:
         if size == 1:
            data = struct.unpack("%dB" %size, raw_data)[0]
         else:
            data = struct.unpack("%dB" %size, raw_data)
      return data

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

   def write_flexible(self, offset, size, bytearray_data):
      """
      Write values to a field in EEPROM in a more flexible way

      Args:
         offset: an integer indicating the offset of the starting position of the 
         EEPROM byte(s) to write to

         size: an integer indicating how many bytes to write to

         bytearray_data: a bytearray as write bugger to be written into EEPROM

      Returns:
         Boolean, True if the write is successful and False otherwise
      """      
      return self.writer(offset, size, bytearray_data)
