"""Mixin granting an XcvrApi subclass a lazy ``cdb_handler`` backed by an injected CdbMemMap.

Subclasses must call ``self._init_cdb_mem_map(cdb_mem_map)`` from their own ``__init__``;
the mixin does not own ``__init__`` so it composes cleanly with any primary base.
"""

from ..cdb.cdb import CdbCmdHandler


class CdbCapableMixin(object):
    _cdb_mem_map = None
    _cdb_handler = None

    def _init_cdb_mem_map(self, cdb_mem_map=None):
        self._cdb_mem_map = cdb_mem_map
        self._cdb_handler = None

    @property
    def cdb_handler(self):
        if getattr(self, '_cdb_mem_map', None) is None:
            return None
        if self._cdb_handler is None:
            self._cdb_handler = CdbCmdHandler(self.xcvr_eeprom.reader,
                                              self.xcvr_eeprom.writer,
                                              self._cdb_mem_map)
        return self._cdb_handler
