from sonic_platform_base.sonic_xcvr.api.broadcom.davisson_oe import DavissonTh6OeApi
from sonic_platform_base.sonic_xcvr.codes.broadcom.davisson_oe import DavissonTh6OeCodes
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_oe import NvidiaCpoOeCmisApi
from sonic_platform_base.sonic_xcvr.codes.nvidia.cpo_oe import NvidiaCpoOeCodes
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoApiFactory, CpoDeviceBase, OeId
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.davisson_oe import DavissonTh6OeMemMap
from sonic_platform_base.sonic_xcvr.codes.broadcom.bailly import BaillyCodes
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly_oe import BaillyOeMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.api.broadcom.bailly_oe import BaillyOeApi
from sonic_platform_base.sonic_xcvr.mem_maps.nvidia.cpo_oe import NvidiaCpoOeMemMap


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
            mem_map = BaillyOeMemMap(BaillyCodes, bank=device.bank)
            eeprom = XcvrEeprom(device.read_eeprom, device.write_eeprom, mem_map)
            return BaillyOeApi(eeprom)
        if self._device.hardware_id.oe_id == OeId.NVIDIA_SPC6_CPO:
            return self._create_api(
                codes_class=NvidiaCpoOeCodes,
                mem_map_class=NvidiaCpoOeMemMap,
                api_class=NvidiaCpoOeCmisApi
            )

        raise ValueError(f"Could not determine what OE API to use for OE ID: {self._device.hardware_id.oe_id}")


class OeBase(CpoDeviceBase):
    def _make_api_factory(self) -> CpoApiFactory:
        return OeApiFactory(self)

    def get_reset_status(self) -> bool:
        """Return whether the OE is held in reset; platforms provide readback."""
        raise NotImplementedError

    def get_lpmode(self) -> bool:
        """Return OE low-power status; platforms provide readback."""
        raise NotImplementedError

    def set_lpmode(self, lpmode: bool) -> bool:
        """Request OE low-power mode through its API; platforms may override.

        Low-power control applies to the entire OE, including all banks and
        associated ports, rather than only the bank used to access this object.
        """
        return self.get_api().set_lpmode(lpmode)

    def reset(self) -> bool:
        """Reset the OE through its API; platforms may override.

        Reset affects the entire OE, including all banks and associated ports.
        """
        return self.get_api().reset()
