from sonic_platform_base.sonic_xcvr.eeprom_rw import EepromReadWriteMixin
from sonic_platform_base.sonic_xcvr.cpo.cpo_api_factory import OeApiFactory, ElsfpApiFactory, CpoHardwareId


class OeBase(EepromReadWriteMixin):
    def __init__(self, hardware_id: CpoHardwareId, bank: int = 0):
        self.bank = bank
        self._oe_api = None
        self.hardware_id = hardware_id
        self._oe_api_factory = OeApiFactory(self)

    def refresh_oe_api(self):
        self._oe_api = self._oe_api_factory.create_oe_api()

    def get_oe_api(self):
        """Return a cached OE API instance, creating it on first access."""
        if self._oe_api is None:
            self.refresh_oe_api()
        return self._oe_api

    # TODO: Implement OE-specific methods


class ElsfpBase(EepromReadWriteMixin):
    def __init__(self, hardware_id: CpoHardwareId, bank: int = 0):
        self.bank = bank
        self._elsfp_api = None
        self.hardware_id = hardware_id
        self._elsfp_api_factory = ElsfpApiFactory(self)

    def refresh_elsfp_api(self):
        self._elsfp_api = self._elsfp_api_factory.create_elsfp_api()

    def get_elsfp_api(self):
        """Return a cached ELSFP API instance, creating it on first access."""
        if self._elsfp_api is None:
            self.refresh_elsfp_api()
        return self._elsfp_api

    # TODO: Implement ELSFP-specific methods


class CpoBase:
    def __init__(self, hardware_id: CpoHardwareId, oe: OeBase, elsfp: ElsfpBase):
        self.hardware_id = hardware_id
        self.oe = oe
        self.elsfp = elsfp

# TODO: Implement CPO-specific methods
#     def do_fiber_check(self, lane):
#         oe_api = self.oe.get_oe_api()
#         oe_api.do_fiber_check(lane)
#
#     def tx_disable(self, lane):
#         elsp_api = self.elsfp.get_elsp_api()
#         elsp_api.tx_disable(lane)
