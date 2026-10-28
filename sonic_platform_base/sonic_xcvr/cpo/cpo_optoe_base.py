from sonic_platform_base.sonic_xcvr.optoe_eeprom_rw import OptoeEepromReadWriteMixin
from sonic_platform_base.sonic_xcvr.cpo.oe import OeBase
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpBase


class OptoeOeBase(OeBase, OptoeEepromReadWriteMixin):
    # Default to software controls supplied by the endpoint API. Platforms may
    # override these methods to use hardware pins or other board-specific logic.
    # An API that does not support an operation may raise NotImplementedError.
    def set_lpmode(self, lpmode: bool) -> bool:
        """Request OE low-power mode through its API by default."""
        return self.get_api().set_lpmode(lpmode)

    def reset(self) -> bool:
        """Request an OE software reset through its API by default."""
        return self.get_api().reset()


class OptoeElsfpBase(ElsfpBase, OptoeEepromReadWriteMixin):
    # Default to software controls supplied by the endpoint API. Platforms may
    # override these methods to use hardware pins or other board-specific logic.
    # Unsupported API controls propagate; no OE or CPO-controller fallback is used.
    def set_lpmode(self, lpmode: bool) -> bool:
        """Request ELSFP low-power mode through its API by default."""
        return self.get_api().set_lpmode(lpmode)

    def reset(self) -> bool:
        """Request an ELSFP software reset through its API by default."""
        return self.get_api().reset()
