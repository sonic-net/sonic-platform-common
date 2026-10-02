from dataclasses import dataclass

from sonic_platform_base.sonic_xcvr.api.broadcom.davisson_elsfp import DavissonTh6ElsfpApi
from sonic_platform_base.sonic_xcvr.codes.public.elsfp import ElsfpCodes
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoApiFactory, CpoDeviceBase, OeId
from sonic_platform_base.sonic_xcvr.eeprom_rw import ModuleEepromLowerMemoryInfo
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.davisson_elsfp import DavissonTh6ElsfpMemMap


@dataclass
class ElsfpInfo:
    vendor_name: str
    vendor_part_number: str


class ElsfpApiFactory(CpoApiFactory):
    def _get_elsfp_info(self) -> ElsfpInfo:
        eeprom_info = ModuleEepromLowerMemoryInfo(
            self._device.read_eeprom,
            offset=self._device.hardware_id.elsfp_low_mem_offset
        )
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
            if self._device.hardware_id.oe_id == OeId.BROADCOM_DAVISSON:
                return self._create_api(
                    codes_class=ElsfpCodes,
                    mem_map_class=DavissonTh6ElsfpMemMap,
                    api_class=DavissonTh6ElsfpApi
                )

        # if self._device.hardware_id.elsfp_id == ElsfpId.EXAMPLE:
        #     self._create_api(...)

        raise ValueError(
            f"Could not determine what ELSFP API to use for CPO HW ID. "
            f"OE ID: {self._device.hardware_id.oe_id}, ELSFP ID: {self._device.hardware_id.elsfp_id}"
        )


class ElsfpBase(CpoDeviceBase):
    def _make_api_factory(self) -> CpoApiFactory:
        return ElsfpApiFactory(self)

    def get_reset_status(self) -> bool:
        """
        Retrieves the state of the ELSFP hardware reset pin.

        Returns:
            A Boolean, True if the ELSFP is held in reset, False if not
        """
        raise NotImplementedError

    def reset(self) -> bool:
        """
        Resets the ELSFP by pulsing the hardware reset pin.

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError

    def get_lpmode(self) -> bool:
        """
        Retrieves the state of the ELSFP hardware LPMode pin.

        Returns:
            A Boolean, True if the pin asserts low power mode, False if not
        """
        raise NotImplementedError

    def set_lpmode(self, lpmode: bool) -> bool:
        """
        Sets the ELSFP hardware LPMode pin.

        Args:
            lpmode: A Boolean, True to assert low power mode, False to deassert it

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError
