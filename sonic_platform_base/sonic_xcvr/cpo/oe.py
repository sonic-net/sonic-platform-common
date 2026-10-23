from sonic_platform_base.sonic_xcvr.api.broadcom.davisson_oe import DavissonTh6OeApi
from sonic_platform_base.sonic_xcvr.codes.broadcom.davisson_oe import DavissonTh6OeCodes
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoApiFactory, CpoDeviceBase, OeId
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.davisson_oe import DavissonTh6OeMemMap
from sonic_platform_base.sonic_xcvr.codes.broadcom.bailly import BaillyCodes
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly import BaillyMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.api.broadcom.bailly import BaillyApi


class OeApiFactory(CpoApiFactory):
    def create_api(self):
        if self._device.hardware_id.oe_id == OeId.BROADCOM_DAVISSON:
            return self._create_api(
                codes_class=DavissonTh6OeCodes,
                mem_map_class=DavissonTh6OeMemMap,
                api_class=DavissonTh6OeApi
            )

        if self._device.hardware_id.oe_id == OeId.BROADCOM_BAILLY:
            device = self._device
            mem_map = BaillyMemMap(
                BaillyCodes, bank=device.bank, base_page=device.base_page)
            eeprom = XcvrEeprom(device.read_eeprom, device.write_eeprom, mem_map)
            return BaillyApi(eeprom)

        raise ValueError(f"Could not determine what OE API to use for OE ID: {self._device.hardware_id.oe_id}")


class OeBase(CpoDeviceBase):
    def _make_api_factory(self) -> CpoApiFactory:
        return OeApiFactory(self)

    # Platform hooks for low-power mode and reset. Platforms implement them with
    # whatever their hardware provides, such as dedicated pins or EEPROM
    # controls. Client code that wants the software path can call the CMIS API
    # from get_api() directly.
    def get_reset_status(self) -> bool:
        """
        Retrieves the reset state of the OE

        Returns:
            A Boolean, True if the OE is held in reset, False if not
        """
        raise NotImplementedError

    def reset(self) -> bool:
        """
        Resets the OE

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError

    def get_lpmode(self) -> bool:
        """
        Retrieves the low-power mode of the OE

        Returns:
            A Boolean, True if the OE is in low-power mode, False if not
        """
        raise NotImplementedError

    def set_lpmode(self, lpmode: bool) -> bool:
        """
        Puts the OE in low-power or full-power mode

        Args:
            lpmode: A Boolean, True to enter low-power mode, False to leave it

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError
