from sonic_platform_base.sonic_xcvr.optoe_eeprom_rw import OptoeEepromReadWriteMixin
from sonic_platform_base.sonic_xcvr.cpo.oe import OeBase
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpBase

class OptoeOeBase(OeBase, OptoeEepromReadWriteMixin):
    pass

class OptoeElsfpBase(ElsfpBase, OptoeEepromReadWriteMixin):
    pass
