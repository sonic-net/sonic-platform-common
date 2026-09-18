"""XcvrApi for Co-Packaged Optics (CPO) modules: aggregates an OE bank and an ELS bank."""

from .cmis import CmisApi


class CpoApi(CmisApi):
    """CPO XcvrApi composing an optical-engine API with an external-laser-source API.

    Each ``get_transceiver_*`` method merges OE and ELS results into a freshly
    owned dict (a shallow copy of the OE result) so the backend dicts are never
    mutated; ELS keys win on collisions. ``None`` from either bank is treated as
    no contribution (so a missing CMIS page on one side does not suppress the
    other).
    """

    def __init__(self, optical_engine_xcvr_api, external_laser_source_xcvr_api) -> None:
        super().__init__(optical_engine_xcvr_api.xcvr_eeprom)
        self.optical_engine_xcvr_api = optical_engine_xcvr_api
        self.external_laser_source_xcvr_api = external_laser_source_xcvr_api

    def _merge(self, method_name):
        result = dict(getattr(self.optical_engine_xcvr_api, method_name)() or {})
        els_data = getattr(self.external_laser_source_xcvr_api, method_name)()
        if els_data:
            result.update(els_data)
        return result

    def get_transceiver_info(self):
        return self._merge('get_transceiver_info')

    def get_transceiver_dom_real_value(self):
        return self._merge('get_transceiver_dom_real_value')

    def get_transceiver_threshold_info(self):
        return self._merge('get_transceiver_threshold_info')

    def get_transceiver_dom_flags(self):
        return self._merge('get_transceiver_dom_flags')

    def get_transceiver_status(self):
        return self._merge('get_transceiver_status')

    def get_transceiver_status_flags(self):
        return self._merge('get_transceiver_status_flags')
