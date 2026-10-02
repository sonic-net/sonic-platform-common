from sonic_platform_base.sonic_xcvr.api.broadcom.davisson_oe import DavissonTh6OeApi
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoApiFactory, CpoDeviceBase, OeId
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.davisson_oe import DavissonTh6OeMemMap


class OeApiFactory(CpoApiFactory):
    def create_api(self):
        if self._device.hardware_id.oe_id == OeId.BROADCOM_DAVISSON:
            return self._create_api(
                codes_class=CmisCodes,
                mem_map_class=DavissonTh6OeMemMap,
                api_class=DavissonTh6OeApi
            )

        raise ValueError(f"Could not determine what OE API to use for OE ID: {self._device.hardware_id.oe_id}")


class OeBase(CpoDeviceBase):
    def _make_api_factory(self) -> CpoApiFactory:
        return OeApiFactory(self)

    def get_reset_status(self) -> bool:
        """
        Retrieves the state of the OE hardware reset pin.

        Returns:
            A Boolean, True if the OE is held in reset, False if not
        """
        raise NotImplementedError

    def reset(self) -> bool:
        """
        Resets the OE by pulsing the hardware reset pin.

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError

    def get_lpmode(self) -> bool:
        """
        Retrieves the state of the OE hardware LPMode pin.

        Returns:
            A Boolean, True if the pin asserts low power mode, False if not
        """
        raise NotImplementedError

    def set_lpmode(self, lpmode: bool) -> bool:
        """
        Sets the OE hardware LPMode pin.

        Args:
            lpmode: A Boolean, True to assert low power mode, False to deassert it

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError
