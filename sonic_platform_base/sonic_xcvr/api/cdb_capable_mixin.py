"""Mixin granting an XcvrApi subclass a lazy ``cdb_handler`` backed by an injected CdbMemMap.

Subclasses must call ``self._init_vendor_cdb_mem_map(cdb_mem_map)`` from their own
``__init__``; the mixin does not own ``__init__`` so it composes cleanly with any
primary base.

The attributes are prefixed ``_vendor_`` to stay clear of ``CmisApi._cdb_mem_map``,
which holds the standard CDB map used by the firmware-upgrade path.
"""

from ..cdb.cdb import CdbCmdHandler


class CdbCapableMixin(object):
    def _init_vendor_cdb_mem_map(self, cdb_mem_map=None):
        self._vendor_cdb_mem_map = cdb_mem_map
        self._vendor_cdb_handler = None

    @property
    def cdb_handler(self):
        if getattr(self, '_vendor_cdb_mem_map', None) is None:
            return None
        if self._vendor_cdb_handler is None:
            self._vendor_cdb_handler = CdbCmdHandler(self.xcvr_eeprom.reader,
                                                     self.xcvr_eeprom.writer,
                                                     self._vendor_cdb_mem_map)
        return self._vendor_cdb_handler
