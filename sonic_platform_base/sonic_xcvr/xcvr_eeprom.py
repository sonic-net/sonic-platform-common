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
      self.cache = None # Cache for page 00h

   def get_data(self, offset: int, size: int) -> bytearray :  
      """
      Fetch the bytearray of the eeprom data from the offset specified upto the length
      """
      try:
         if offset + size < 256 and self.cache is not None:
            return self.cache[offset:offset+size]
      except Exception as e:
         pass

      return self.reader(offset, size)

   def read(self, field_name):
      """
      Read a value from a field in EEPROM

      Args:
         field_name: a string denoting the XcvrField to read from

      Returns:
         The value of the field, if the read is successful and None otherwise
      """
      field = self.mem_map.get_field(field_name)
      raw_data = self.get_data(field.get_offset(), field.get_size())
      if raw_data:
         deps = field.get_deps()
         decoded_deps = {dep: self.read(dep) for dep in deps}
         return field.decode(raw_data, **decoded_deps)
      return None

   def read_raw(self, offset, size, return_raw = False):
      """
      Read values from a field in EEPROM in a more flexible way

      Args:
         offset: an integer indicating the offset of the starting position of the
         EEPROM byte(s) to read from

         size: an integer indicating how many bytes to read from
      Returns:
         The value(s) of the field, if the read is successful and None otherwise
      """
      raw_data = self.get_data(offset, size)
      if raw_data is None:
         return None
      if return_raw:
         return raw_data
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

   def write_raw(self, offset, size, bytearray_data):
      """
      Write values to a field in EEPROM in a more flexible way

      Args:
         offset: an integer indicating the offset of the starting position of the
         EEPROM byte(s) to write to

         size: an integer indicating how many bytes to write to

         bytearray_data: a bytearray as write buffer to be written into EEPROM

      Returns:
         Boolean, True if the write is successful and False otherwise
      """
      return self.writer(offset, size, bytearray_data)
   
   def enable_cache(self, **kwargs):
      """
      When enabled, it caches the lower and upper pages of 00h i.e offset 0 to 256
      Any read request made strictly b/w these limits will be read from the cache until disabled

      Returns: 
         None
      """
      # TODO: Use a better mechanism and allow caching for higher pages and more complicated scenarios
      self.cache = self.reader(0, 256)

   def disable_cache(self, **kwargs):
      """
      Clear the Cache

      Returns: 
         None
      """
      self.cache = None

