from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sonic_platform_base import device_base
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.eeprom_rw import EepromReadWriteMixin


class OeId(Enum):
    BROADCOM_DAVISSON = 1


class ElsfpId(Enum):
    pass


@dataclass
class CpoHardwareInfo:
    oe_id: OeId
    elsfp_id: Optional[ElsfpId]
    elsfp_low_mem_offset: int = 0


class CpoApiFactory(ABC):
    def __init__(self, device: "CpoDeviceBase"):
        self._device = device

    def _create_api(self, codes_class, mem_map_class, api_class):
        mem_map = mem_map_class(codes_class, self._device.bank)
        eeprom = XcvrEeprom(self._device.read_eeprom, self._device.write_eeprom, mem_map)
        return api_class(eeprom)

    @abstractmethod
    def create_api(self):
        raise NotImplementedError


class CpoDeviceBase(device_base.DeviceBase, EepromReadWriteMixin):
    def __init__(self, hardware_id: CpoHardwareInfo, bank: int = 0):
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

    def remove_api(self):
        self._api = None


class CpoBase(device_base.DeviceBase):
    def __init__(self, hardware_id: CpoHardwareInfo, oe: "OeBase", elsfp: "ElsfpBase"):
        self.hardware_id = hardware_id
        self.oe = oe
        self.elsfp = elsfp

    def refresh_xcvr_api(self):
        self.oe.refresh_api()
        self.elsfp.refresh_api()

    def get_xcvr_api(self):
        # We always default to the OE API for CPO. If the ELSFP API is required,
        # then that can be accessed via self.elsfp.get_api() directly.
        return self.oe.get_api()

    def remove_xcvr_api(self):
        self.oe.remove_api()
        self.elsfp.remove_api()
