from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoApiFactory, CpoDeviceBase


class OeApiFactory(CpoApiFactory):
    def create_api(self):
        # if self._device.hardware_id.oe_id == OeId.EXAMPLE:
        #     self._create_api(...)

        raise ValueError(f"Could not determine what OE API to use for OE ID: {self._device.hardware_id.oe_id}")


class OeBase(CpoDeviceBase):
    def _make_api_factory(self) -> CpoApiFactory:
        return OeApiFactory(self)

    # TODO: Implement OE-specific methods
