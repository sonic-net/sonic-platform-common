"""
    page04.py

    C-CMIS Page 04h - Module Configuration Support.
"""

from .page import CmisPage
from .....fields.xcvr_field import NumberRegField
from .....fields import consts


class CCmisModuleConfigSupportPage(CmisPage):
    """C-CMIS Page 04h fields (frequency grid, channel range, output power)."""

    def __init__(self, codes, bank=0, page=0x04):
        super().__init__(codes, page=page, bank=bank)

        self.fields[consts.MODULE_CONFIG_SUPPORT_FIELD] = [
            NumberRegField(consts.SUPPORT_GRID, self.getaddr(128)),
            NumberRegField(consts.LOW_CHANNEL, self.getaddr(158), format=">h", size=2),
            NumberRegField(consts.HIGH_CHANNEL, self.getaddr(160), format=">h", size=2),
            NumberRegField(consts.MIN_PROG_OUTPUT_POWER, self.getaddr(198), format=">h", size=2, scale=100.0),
            NumberRegField(consts.MAX_PROG_OUTPUT_POWER, self.getaddr(200), format=">h", size=2, scale=100.0),
        ]
