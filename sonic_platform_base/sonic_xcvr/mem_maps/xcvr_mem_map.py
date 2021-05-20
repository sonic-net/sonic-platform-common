from  ..fields.xcvr_field import XcvrField

class XcvrMemMap(object):
   def __init__(self, codes):
      self.codes = codes
      self._fields = {}
      for key in dir(self):
         attr = getattr(self, key)
         if isinstance(attr, XcvrField):
            self._fields[attr.name] = attr
            self._fields.update(attr.get_fields())

   def get_field(self, field_name):
      return self._fields[field_name]
