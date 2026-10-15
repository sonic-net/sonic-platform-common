"""
    cmis_credo.py

    API for Credo transceivers/cables that support the vendor "Get Telemetry
    Info" CDB command (opcode 0x8000). Adds link-quality/FEC/eye telemetry to
    the standard TRANSCEIVER_DOM_REAL_VALUE fields.
"""

import struct

from sonic_py_common.syslogger import SysLogger

from ..public.cmis import CmisApi
from ...cdb.cdb import CdbCmdHandler
from ...codes.public.cdb import CdbCodes
from ...codes.public.cmis import CmisCodes
from ...fields import credo_cdb_consts as consts
from ...mem_maps.credo import cdb_credo

SYSLOG_IDENTIFIER = "CmisCredo"
log = SysLogger(SYSLOG_IDENTIFIER)
log.logger.propagate = False

# Telemetry data is only valid when EEPROM page 0 byte 36 reads back this value,
# and only once the module's CMIS FW has finished booting (ModuleState == ModuleReady).
_TELEMETRY_COMPLIANCE_OFFSET = 36
_TELEMETRY_COMPLIANCE_VALUE = 0x21
_MODULE_STATE_READY = CmisCodes.MODULE_STATE[3]

_POLL_TARGET = 'local'


def _telemetry_na_dict(host_lane_count=0, media_lane_count=0):
    """Fallback shape when telemetry can't be read: 'N/A' for every host/media lane field."""
    na_dict = {}
    for lane in range(1, host_lane_count + 1):
        na_dict.update({consts.host_field(lane, s): 'N/A' for s in consts.COMMON_SUFFIXES})
    for lane in range(1, media_lane_count + 1):
        na_dict.update({consts.media_field(lane, s): 'N/A' for s in consts.COMMON_SUFFIXES})
        na_dict.update({consts.media_field(lane, s): 'N/A' for s in consts.MEDIA_ONLY_SUFFIXES})
    return na_dict


class CredoCdbCmdHandler(CdbCmdHandler):
    """Low-level sender/reader for Credo's vendor CDB opcode (0x8000)."""

    def __init__(self, reader, writer):
        super(CredoCdbCmdHandler, self).__init__(reader, writer, cdb_credo.CmisCdbCredoMemMap(CdbCodes))

    def get_telemetry_info(self, target, side, dport, timeout=None):
        """Run CDB command 0x8000 and return the decoded reply dict, or None on failure."""
        payload = {'target': target, 'side': side, 'dport': dport}
        if not self.send_cmd(cdb_credo.CDB_GET_TELEMETRY_INFO_CMD, payload, timeout=timeout):
            return None
        return self.read(consts.TELEMETRY_INFO_FIELD)

    def access_remote_byte(self, target, side, dport, offset, value=None, timeout=None):
        """Read or write a single byte on the local/remote side via CDB command 0x8001.

        If `value` is None, reads the byte at `offset` and returns it (or None
        on failure). Otherwise writes `value` and returns True/False for success.
        """
        rw = 'read' if value is None else 'write'
        payload = {
            'target': target, 'side': side, 'dport': dport,
            'offset': offset, 'rw': rw, 'value': value if value is not None else 0,
        }
        if not self.send_cmd(cdb_credo.CDB_ACCESS_REMOTE_BYTE_CMD, payload, timeout=timeout):
            return None if rw == 'read' else False
        if rw == 'write':
            return True
        reply = self.read(consts.REMOTE_BYTE_FIELD)
        return reply[consts.REMOTE_BYTE_VALUE] if reply else None

    def access_remote_page(self, target, side, dport, page, data=None, timeout=None):
        """Read or write up to cdb_credo.REMOTE_PAGE_DATA_SIZE bytes on the
        local/remote side via CDB command 0x8002.

        If `data` is None, reads back `page` and returns its bytes (or None on
        failure). Otherwise writes `data` and returns True/False for success.
        """
        rw = 'read' if data is None else 'write'
        payload = {'target': target, 'side': side, 'dport': dport, 'page': page, 'rw': rw, 'data': data}
        if not self.send_cmd(cdb_credo.CDB_ACCESS_REMOTE_PAGE_CMD, payload, timeout=timeout):
            return None if rw == 'read' else False
        if rw == 'write':
            return True
        reply = self.read(consts.REMOTE_PAGE_FIELD)
        return reply[consts.REMOTE_PAGE_DATA] if reply else None

class CmisCredoApi(CmisApi):
    def __init__(self, xcvr_eeprom, init_cdb_fw_handler=False):
        super(CmisCredoApi, self).__init__(xcvr_eeprom, init_cdb_fw_handler=init_cdb_fw_handler)
        self._init_credo_cdb_handler = True
        self._credo_cdb_handler = None

    @property
    def _credo_cdb(self):
        if not self._init_credo_cdb_handler:
            return None
        if self._credo_cdb_handler is None:
            self._credo_cdb_handler = self._create_credo_cdb_handler()
        return self._credo_cdb_handler

    def _create_credo_cdb_handler(self):
        if not self.is_cdb_supported():
            self._init_credo_cdb_handler = False
            return None
        try:
            return CredoCdbCmdHandler(self.xcvr_eeprom.reader, self.xcvr_eeprom.writer)
        except Exception as err:
            log.log_error("Failed to initialize Credo CDB handler: {}".format(err))
        self._init_credo_cdb_handler = False
        return None

    def _is_capability_supported(self):
        """Telemetry data is only valid when EEPROM page 0 byte 36 == 0x21"""
        if not self.is_cdb_supported():
            return False

        compliance = self.xcvr_eeprom.read_raw(_TELEMETRY_COMPLIANCE_OFFSET, 1)
        if compliance != _TELEMETRY_COMPLIANCE_VALUE:
            return False

        return True

    def _get_credo_telemetry_info(self, host_lane_count, media_lane_count):
        """Fetch and decode local telemetry via CDB 0x8000, once per host/media lane.

        Returns a fully-populated dict ('N/A' for lanes/fields that aren't
        queried or fail to read), or None if the module isn't ModuleReady yet.
        """
        if self.get_module_state() != _MODULE_STATE_READY:
            return None

        result = _telemetry_na_dict(host_lane_count, media_lane_count)

        for side, lane_count in ((consts.HOST, host_lane_count), (consts.MEDIA, media_lane_count)):
            field = consts.host_field if side == consts.HOST else consts.media_field
            for lane in range(1, lane_count + 1):
                dport = lane - 1
                try:
                    raw = self._credo_cdb.get_telemetry_info(_POLL_TARGET, side, dport)
                    if raw is None:
                        continue
                    decoded = {field(lane, suffix): raw[suffix] for suffix in consts.COMMON_SUFFIXES}
                    if side == consts.MEDIA:
                        decoded.update({
                            field(lane, suffix): raw[suffix]
                            for suffix in consts.MEDIA_ONLY_SUFFIXES if suffix in raw
                        })
                except Exception as err:
                    log.log_error("Failed to read Credo {}-side lane {} telemetry info: {}".format(side, lane, err))
                    continue
                result.update(decoded)

        return result

    def get_transceiver_dom_real_value(self):
        trans_dom = super(CmisCredoApi, self).get_transceiver_dom_real_value()
        if trans_dom is None:
            return None

        host_lane_count = self.get_host_lane_count() or 0
        media_lane_count = self.get_media_lane_count() or 0
        na_dict = _telemetry_na_dict(host_lane_count, media_lane_count)

        if not self._is_capability_supported():
            trans_dom.update(na_dict)
            return trans_dom

        telemetry = self._get_credo_telemetry_info(host_lane_count, media_lane_count)
        trans_dom.update(telemetry if telemetry is not None else na_dict)
        return trans_dom
