"""
   xcvr_field.py

   Classes for representing types of fields found in xcvr memory maps.
"""

import struct


class XcvrField(object):
    def __init__(self, name, offset, ro):
        self.name = name
        self.offset = offset
        self.ro = ro

    def get_fields(self):
        """
        Return: dict containing all fields nested within this field
        """
        fields = {}
        if hasattr(self, "fields"):
            for field in self.fields:
                fields[field.name] = field
                fields.update(field.get_fields())
        return fields

    def get_offset(self):
        """
        Return: absolute byte offset of field in memory map
        """
        return self.offset

    def get_size(self):
        """
        Return: size of field in bytes (min. 1)
        """
        raise NotImplementedError

    def read_before_write(self):
        """
        Return: True if a field needs to be read before written to, False otherwise
        """
        raise NotImplementedError

    def decode(self, raw_data):
        """
        raw_data: bytearray of length equal to size of field
        Return: decoded data (high level meaning)
        """
        raise NotImplementedError

    def encode(self, val, raw_state=None):
        """
        val: data with high level meaning
        raw_state: bytearray denoting the current state of memory corresponding to this field
        Return: bytearray of length equal to size of field

        Not implemented if not appropriate for the field (e.g. read-only)
        """
        raise NotImplementedError


class RegBitField(XcvrField):
    """
    Field denoting a single bit. Must be defined under a parent RegField
    """
    def __init__(self, name, bitpos, parent=None, ro=True, offset=None):
        super(RegBitField, self).__init__(name, offset, ro)
        self.bitpos = bitpos
        self.parent = parent

    def get_size(self):
        return 1

    def read_before_write(self):
        return True

    def decode(self, raw_data):
        return bool((raw_data[0] >> self.bitpos) & 1)

    def encode(self, val, raw_state=None):
        assert not self.ro and raw_state is not None
        curr_state = raw_state[0]
        if val:
            curr_state |= (1 << self.bitpos)
        else:
            curr_state &= ~(1 << self.bitpos)
        return bytearray([curr_state])


class RegField(XcvrField):
    """
    Field denoting one or more bytes, but logically interpreted as one unit (e.g. a 4-byte integer)
    """
    def __init__(self, name, offset, *fields, **kwargs):
        super(RegField, self).__init__(name, offset, kwargs.get("ro", True))
        self.fields = fields
        self.size = kwargs.get("size", 1)
        self._updateBitOffsets()

    def _updateBitOffsets(self):
        for field in self.fields:
            field.offset = self.offset + field.bitpos // 8

    def get_size(self):
        return self.size

    def read_before_write(self):
        return False

class NumberRegField(RegField):
    """
    Interprets byte(s) as a number
    """
    def __init__(self, name, offset, *fields, **kwargs):
        super(NumberRegField, self).__init__( name, offset, *fields, **kwargs)
        self.scale = kwargs.get("scale")
        self.format = kwargs.get("format", "B")

    def decode(self, raw_data):
        decoded = struct.unpack(self.format, raw_data)[0]
        if self.scale is not None:
            assert self.scale != 0
            return decoded / self.scale
        return decoded 

    def encode(self, val, raw_state=None):
        assert not self.ro
        if self.scale is not None:
            return bytearray(struct.pack(self.format, val * self.scale))
        return bytearray(struct.pack(self.format, val))

class StringRegField(RegField):
    """
    Interprets byte(s) as a string
    """
    def __init__(self, name, offset, *fields, **kwargs):
        super(StringRegField, self).__init__(name, offset, *fields, **kwargs)
        self.encoding = kwargs.get("encoding", "ascii")
        self.format = kwargs.get("format", ">%ds" % self.size)

    def decode(self, raw_data):
        return struct.unpack(self.format, raw_data)[0].decode(self.encoding)

class CodeRegField(RegField):
    """
    Interprets byte(s) as a code
    """
    def __init__(self, name, offset, code_dict, *fields, **kwargs):
        super(CodeRegField, self).__init__(name, offset, *fields, **kwargs)
        self.code_dict = code_dict
        self.format = kwargs.get("format", "B")

    def _get_bitmask(self):
        if not self.fields:
            return None
        mask = 0
        for field in self.fields:
            mask |= 1 << field.bitpos
        return mask

    def decode(self, raw_data):
        code = struct.unpack(self.format, raw_data)[0]
        mask = self._get_bitmask()
        if mask is not None:
            code &= mask
        return self.code_dict.get(code, "Unknown")

class HexRegField(RegField):
    """
    Interprets bytes as a series of hex pairs
    """
    def __init__(self, name, offset, *fields, **kwargs):
        super(HexRegField, self).__init__(name, offset, *fields, **kwargs)

    def decode(self, raw_data):
        return '-'.join([ "%02x" % byte for byte in raw_data])

class RegGroupField(XcvrField):
    """
    Field denoting one or more bytes, logically interpreted as one or more contiguous RegFields
    (e.g. a 4-byte integer followed by a 16-byte string) or RegGroupFields
    """
    def __init__(self, name, *fields, **kwargs):
        super(RegGroupField, self).__init__(
            name, fields[0].get_offset(), kwargs.get("ro", True))
        self.fields = fields

    def get_size(self):
        start = self.offset
        end = start
        for field in self.fields:
            end = max(end, field.get_offset() + field.get_size())
        return end - start

    def read_before_write(self):
        return False

    def decode(self, raw_data):
        """
            Return: a dict mapping member field names to their decoded results
        """
        result = {}
        start = self.offset
        for field in self.fields:
            offset = field.get_offset()
            result[field.name] = field.decode(
                raw_data[offset - start: offset + field.get_size() - start])
        return result
