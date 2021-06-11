"""
   xcvr_mem_map.py

   Base class for representing xcvr memory maps in SONiC
"""

from  ..fields.xcvr_field import XcvrField

class XcvrMemMap(object):
   def __init__(self, codes):
      self.codes = codes
      self._fields = None
   
   def _get_all_fields(self):
      if self._fields is None:
         self._fields = {}
         for key in dir(self):
            attr = getattr(self, key)
            if isinstance(attr, XcvrField):
               self._fields[attr.name] = attr
               self._fields.update(attr.get_fields())
      return self._fields

   def get_field(self, field_name):
      return self._get_all_fields()[field_name]
