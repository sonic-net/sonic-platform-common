"""
    pg_00_administrative_upper.py

    Implementation of CmisAdministrativeUpperPage for CMIS page 0x00 upper memory (offsets 128-255)
"""

from .base import CmisPage
from .cmis_page_consts import ADMINISTRATIVE_PAGE
from ....fields.xcvr_field import (
    CodeRegField,
    NumberRegField,
    RegBitField,
    RegGroupField,
    StringRegField,
    HexRegField,
    DateField,
)
from ....fields.public.cmis import CableLenField
from ....fields import consts


class CmisAdministrativeUpperPage(CmisPage):
    def __init__(self, codes, page=ADMINISTRATIVE_PAGE):
        super().__init__(codes, page=page, bank=0)

        # ADMIN_INFO_FIELD - upper page fields wrapped in EXT_ID_FIELD
        self.fields[consts.ADMIN_INFO_FIELD] = [
            CodeRegField(consts.ID_ABBRV_FIELD, self.getaddr(128), codes.XCVR_IDENTIFIER_ABBRV),
            StringRegField(consts.VENDOR_NAME_FIELD, self.getaddr(129), size=16),
            HexRegField(consts.VENDOR_OUI_FIELD, self.getaddr(145), size=3),
            StringRegField(consts.VENDOR_PART_NO_FIELD, self.getaddr(148), size=16),
            StringRegField(consts.VENDOR_REV_FIELD, self.getaddr(164), size=2),
            StringRegField(consts.VENDOR_SERIAL_NO_FIELD, self.getaddr(166), size=16),
            DateField(consts.VENDOR_DATE_FIELD, self.getaddr(182), size=8),
            RegGroupField(consts.EXT_ID_FIELD,
                CodeRegField(consts.POWER_CLASS_FIELD, self.getaddr(200), codes.POWER_CLASSES,
                    *(RegBitField("%s_%d" % (consts.POWER_CLASS_FIELD, bit), bit) for bit in range(5, 8))
                ),
                NumberRegField(consts.MAX_POWER_FIELD, self.getaddr(201), scale=4.0),
            ),
            NumberRegField(consts.LEN_MULT_FIELD, self.getaddr(202),
                *(RegBitField("%s_%d" % (consts.LEN_MULT_FIELD, bit), bit) for bit in range (6, 8))
            ),
            CableLenField(consts.LENGTH_ASSEMBLY_FIELD, self.getaddr(202),
                *(RegBitField("%s_%d" % (consts.LENGTH_ASSEMBLY_FIELD, bit), bit) for bit in range(0, 6))
            ),
            CodeRegField(consts.CONNECTOR_FIELD, self.getaddr(203), codes.CONNECTORS),
            CodeRegField(consts.MEDIA_INTERFACE_TECH, self.getaddr(212), codes.MEDIA_INTERFACE_TECH),
        ]

