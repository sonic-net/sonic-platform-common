from dataclasses import dataclass

from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoApiFactory, CpoDeviceBase
from sonic_platform_base.sonic_xcvr.eeprom_rw import ModuleEepromInfo


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


class ElsfpBase(CpoDeviceBase):
    def _make_api_factory(self) -> CpoApiFactory:
        return ElsfpApiFactory(self)

    # TODO: Implement ELSFP-specific methods
