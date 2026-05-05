"""
    pg_13_module_perf_diag_ctrl.py

    CMIS Page 13h - Module Performance and Diagnostic Control Page
"""

from .base import CmisPage
from .cmis_page_consts import MODULE_PERF_DIAG_CTRL_PAGE
from ....fields.xcvr_field import NumberRegField
from ....fields import consts


class CmisModulePerfDiagCtrlPage(CmisPage):
    def __init__(self, codes, bank=0, page=MODULE_PERF_DIAG_CTRL_PAGE):
        super().__init__(codes, page=page, bank=bank)

        # TRANS_LOOPBACK_FIELD
        self.fields[consts.TRANS_LOOPBACK_FIELD] = [
            NumberRegField(consts.LOOPBACK_CAPABILITY, self.getaddr(128), size=1),
            NumberRegField(consts.MEDIA_OUTPUT_LOOPBACK, offset=self.getaddr(180), size=1,  ro=False),
            NumberRegField(consts.MEDIA_INPUT_LOOPBACK, offset=self.getaddr(181), size=1, ro=False),
            NumberRegField(consts.HOST_OUTPUT_LOOPBACK, self.getaddr(182), size=1, ro=False),
            NumberRegField(consts.HOST_INPUT_LOOPBACK, self.getaddr(183), size=1, ro=False),
        ]
