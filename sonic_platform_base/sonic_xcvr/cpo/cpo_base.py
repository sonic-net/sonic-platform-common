from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sonic_platform_base import device_base
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.eeprom_rw import EepromReadWriteMixin


class OeId(Enum):
    BROADCOM_DAVISSON = 1
    BROADCOM_BAILLY = 2


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

    # Platform hooks for the CPO virtual module. Low-power mode and reset act
    # through its module controller; a controller may serve several ports, in
    # which case every port it serves is affected. Tx-disable acts on the
    # virtual module's channels. Platforms implement these hooks with whatever
    # their hardware provides, such as dedicated pins or EEPROM controls.
    # Client code that wants the software path can call the module API from
    # get_xcvr_api() directly.
    def get_reset_status(self) -> bool:
        """
        Retrieves the reset state of the CPO virtual module

        Returns:
            A Boolean, True if the module is held in reset, False if not
        """
        raise NotImplementedError

    def reset(self) -> bool:
        """
        Resets the CPO virtual module

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError

    def get_lpmode(self) -> bool:
        """
        Retrieves the low-power mode of the CPO virtual module

        Returns:
            A Boolean, True if the module is in low-power mode, False if not
        """
        raise NotImplementedError

    def set_lpmode(self, lpmode: bool) -> bool:
        """
        Puts the CPO virtual module in low-power or full-power mode

        Args:
            lpmode: A Boolean, True to enter low-power mode, False to leave it

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError

    def get_tx_disable(self) -> list:
        """
        Retrieves the Tx-disable state of the CPO virtual module

        Returns:
            A list of Booleans, one per channel, True if the channel is
            Tx-disabled, False if not
        """
        raise NotImplementedError

    def tx_disable(self, tx_disable: bool) -> bool:
        """
        Disables or enables Tx on all channels of the CPO virtual module

        Args:
            tx_disable: A Boolean, True to disable Tx, False to enable it

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError
