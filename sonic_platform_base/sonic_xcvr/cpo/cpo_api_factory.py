from abc import ABC, abstractmethod
from typing import Optional
from enum import Enum
from dataclasses import dataclass

from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.eeprom_rw import ModuleEepromInfo


class OeId(Enum):
    pass


class ElsfpId(Enum):
    pass


@dataclass
class CpoHardwareId:
    oe_id: OeId
    elsfp_id: Optional[ElsfpId]


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


class OeApiFactory(CpoApiFactory):
    def create_api(self):
        # if self._device.hardware_id.oe_id == OeId.EXAMPLE:
        #     self._create_api(...)

        raise ValueError(f"Could not determine what OE API to use for OE ID: {self._device.hardware_id.oe_id}")


@dataclass
class ElsfpInfo:
    vendor_name: str
    vendor_part_number: str


class ElsfpApiFactory(CpoApiFactory):
    def _get_elsfp_info(self) -> ElsfpInfo:
        eeprom_info = ModuleEepromInfo(self._device.read_eeprom)
        return ElsfpInfo(
            vendor_name=eeprom_info.get_vendor_name(),
            vendor_part_number=eeprom_info.get_vendor_part_num(),
        )

    def create_api(self):
        if self._device.hardware_id.elsfp_id is None:
            # Read vendor name & part number from EEPROM
            # and determine the correct memory map to use
            # based on that information.
            elsfp_info = self._get_elsfp_info()

        # if self._device.hardware_id.elsfp_id == ElsfpId.EXAMPLE:
        #     self._create_api(...)

        raise ValueError(
            f"Could not determine what ELSFP API to use for CPO HW ID. "
            f"OE ID: {self._device.hardware_id.oe_id}, ELSFP ID: {self._device.hardware_id.elsfp_id}"
        )
