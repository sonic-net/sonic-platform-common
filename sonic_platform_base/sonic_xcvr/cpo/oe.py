from sonic_platform_base.sonic_xcvr.api.broadcom.davisson_oe import DavissonTh6OeApi
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_oe import NvidiaCpoOeCmisApi
from sonic_platform_base.sonic_xcvr.codes.nvidia.cpo_oe import NvidiaCpoOeCodes
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoApiFactory, CpoDeviceBase, OeId
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.davisson_oe import DavissonTh6OeMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.nvidia.cpo_oe import NvidiaCpoOeMemMap


class OeApiFactory(CpoApiFactory):
    def create_api(self):
        if self._device.hardware_id.oe_id == OeId.BROADCOM_DAVISSON:
            return self._create_api(
                codes_class=CmisCodes,
                mem_map_class=DavissonTh6OeMemMap,
                api_class=DavissonTh6OeApi
            )

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

    # TODO: Implement OE-specific methods
