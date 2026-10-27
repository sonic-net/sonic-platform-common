"""
Thermal policy info types shared by platforms.

Importing this module registers the info types below, so a platform opts in by importing it
from its thermal manager. Nothing imports it implicitly: registering a type name that a
platform also registers itself would raise, so adoption has to stay deliberate.

Most platforms name the attribute INFO_NAME; a few use INFO_TYPE. Both are provided.
"""

from .thermal_info_base import ThermalPolicyInfoBase
from .thermal_json_object import thermal_json_object


@thermal_json_object('fan_info')
class FanInfo(ThermalPolicyInfoBase):
    """Presence and fault state of every chassis fan."""

    INFO_NAME = 'fan_info'
    INFO_TYPE = 'fan_info'

    def __init__(self):
        self._fans = []
        self._absence_fans = set()
        self._presence_fans = set()
        self._fault_fans = set()
        self._presence_changed = False
        self._status_changed = False

    def collect(self, chassis):
        self._presence_changed = False
        self._status_changed = False
        self._fans = chassis.get_all_fans()[:]

        for fan in self._fans:
            present = fan.get_presence()
            healthy = fan.get_status()

            if present and fan not in self._presence_fans:
                self._presence_fans.add(fan)
                self._absence_fans.discard(fan)
                self._presence_changed = True
            elif not present and fan not in self._absence_fans:
                self._absence_fans.add(fan)
                self._presence_fans.discard(fan)
                self._presence_changed = True

            if not healthy and fan not in self._fault_fans:
                self._fault_fans.add(fan)
                self._status_changed = True
            elif healthy and fan in self._fault_fans:
                self._fault_fans.discard(fan)
                self._status_changed = True

    def get_fans(self):
        return self._fans

    def get_absence_fans(self):
        return self._absence_fans

    def get_presence_fans(self):
        return self._presence_fans

    def get_fault_fans(self):
        return self._fault_fans

    def get_num_present_fans(self):
        return len(self._presence_fans)

    def is_presence_changed(self):
        return self._presence_changed

    def is_status_changed(self):
        return self._status_changed


@thermal_json_object('fan_drawer_info')
class FanDrawerInfo(ThermalPolicyInfoBase):
    """Fan drawers and the fans they hold."""

    INFO_NAME = 'fan_drawer_info'
    INFO_TYPE = 'fan_drawer_info'

    def __init__(self):
        self._fans = []
        self._fan_drawers = []

    def collect(self, chassis):
        self._fans = chassis.get_all_fans()[:]
        self._fan_drawers = chassis.get_all_fan_drawers()[:]

    def get_fans(self):
        return self._fans

    def get_fan_drawers(self):
        return self._fan_drawers

    def get_num_present_fan_drawers(self):
        return sum(1 for drawer in self._fan_drawers if drawer.get_presence())


@thermal_json_object('thermal_info')
class ThermalInfo(ThermalPolicyInfoBase):
    """
    Chassis thermals, plus whether any of them is over threshold.

    Carries both the sensor list, for control algorithms that need per-sensor readings, and
    the aggregate threshold flags that simpler policies match on.
    """

    INFO_NAME = 'thermal_info'
    INFO_TYPE = 'thermal_info'

    def __init__(self):
        self._thermals = []
        self._thermal_manager = None
        self._over_high_threshold = False
        self._over_high_critical_threshold = False

    def collect(self, chassis):
        self._thermals = chassis.get_all_thermals()[:]
        for sfp in chassis.get_all_sfps():
            self._thermals.extend(sfp.get_all_thermals())
        self._thermal_manager = chassis.get_thermal_manager()

        self._over_high_threshold = False
        self._over_high_critical_threshold = False
        for thermal in self._thermals:
            temperature = thermal.get_temperature()
            if temperature is None:
                continue
            high = thermal.get_high_threshold()
            critical = thermal.get_high_critical_threshold()
            if high is not None and temperature > high:
                self._over_high_threshold = True
            if critical is not None and temperature > critical:
                self._over_high_critical_threshold = True

    def get_thermals(self):
        return self._thermals

    def get_thermal_manager(self):
        return self._thermal_manager

    def is_over_high_threshold(self):
        return self._over_high_threshold

    def is_over_high_critical_threshold(self):
        return self._over_high_critical_threshold

    def is_over_threshold(self):
        return self._over_high_threshold or self._over_high_critical_threshold


@thermal_json_object('psu_info')
class PsuInfo(ThermalPolicyInfoBase):
    """PSUs, whose fans and thermals are separate from the chassis ones."""

    INFO_NAME = 'psu_info'
    INFO_TYPE = 'psu_info'

    def __init__(self):
        self._psus = []
        self._absence_psus = set()
        self._presence_psus = set()

    def collect(self, chassis):
        self._psus = chassis.get_all_psus()[:]
        self._absence_psus = set()
        self._presence_psus = set()
        for psu in self._psus:
            if psu.get_presence():
                self._presence_psus.add(psu)
            else:
                self._absence_psus.add(psu)

    def get_psus(self):
        return self._psus

    def get_absence_psus(self):
        return self._absence_psus

    def get_presence_psus(self):
        return self._presence_psus

    def get_num_present_psus(self):
        return len(self._presence_psus)

    def get_thermals(self):
        thermals = []
        for psu in self._psus:
            thermals.extend(psu.get_all_thermals())
        return thermals

    def get_fans(self):
        fans = []
        for psu in self._psus:
            fans.extend(psu.get_all_fans())
        return fans


@thermal_json_object('chassis_info')
class ChassisInfo(ThermalPolicyInfoBase):
    """The chassis itself, for actions that need to act on it directly."""

    INFO_NAME = 'chassis_info'
    INFO_TYPE = 'chassis_info'

    def __init__(self):
        self._chassis = None

    def collect(self, chassis):
        self._chassis = chassis

    def get_chassis(self):
        return self._chassis
