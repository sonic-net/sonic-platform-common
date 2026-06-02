from abc import abstractmethod

from sonic_platform_base.sonic_xcvr.eeprom_rw import EepromReadWriteMixin
from sonic_platform_base.sonic_xcvr.cpo.cpo_api_factory import (
    CpoApiFactory,
    OeApiFactory,
    ElsfpApiFactory,
    CpoHardwareId,
)


class CpoDeviceBase(EepromReadWriteMixin):
    def __init__(self, hardware_id: CpoHardwareId, bank: int = 0):
        self.bank = bank
        self.hardware_id = hardware_id
        self._api = None
        self._api_factory = self._make_api_factory()

    @abstractmethod
    def _make_api_factory(self) -> CpoApiFactory:
        raise NotImplementedError

    def refresh_api(self):
        self._api = self._api_factory.create_api()

    def get_api(self):
        if self._api is None:
            self.refresh_api()
        return self._api


class OeBase(CpoDeviceBase):
    def _make_api_factory(self) -> CpoApiFactory:
        return OeApiFactory(self)

    # TODO: Implement OE-specific methods


class ElsfpBase(CpoDeviceBase):
    def _make_api_factory(self) -> CpoApiFactory:
        return ElsfpApiFactory(self)

    # TODO: Implement ELSFP-specific methods


class CpoBase:
    def __init__(self, hardware_id: CpoHardwareId, oe: OeBase, elsfp: ElsfpBase):
        self.hardware_id = hardware_id
        self.oe = oe
        self.elsfp = elsfp

# TODO: Implement CPO-specific methods
#     def do_fiber_check(self, lane):
#         self.oe.get_api().do_fiber_check(lane)
#
#     def tx_disable(self, lane):
#         self.elsfp.get_api().tx_disable(lane)
