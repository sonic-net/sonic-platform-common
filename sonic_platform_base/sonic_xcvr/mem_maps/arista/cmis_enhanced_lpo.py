"""
    cmis_enhanced_lpo.py

    Memory map for Arista Enhanced LPO modules
"""

from ..public.cmis import CmisMemMap
from ..public.cmis.pages.page import CmisPage
from ...fields.xcvr_field import NumberRegField
from ...fields.cmis_enhanced_lpo import LpoLaneFlagRegField, LpoOerField, LpoOmaAccuracyField, LpoOmaField
from ...fields.cmis_enhanced_lpo import LpoVmaAccuracyField, LpoVmaField
from ...fields import arista_lpo_consts as lpo


class _CmisEnhancedLpoPage01(CmisPage):
    """Page 01h extension: LPO EEPROM compliance advertisement (bytes 195-196)."""

    def __init__(self, codes):
        super().__init__(codes, page=0x01, bank=0)
        self.fields[lpo.LPO_EEPROM_FIELD] = [
            NumberRegField(lpo.LPO_EEPROM_COMPLIANCE, self.getaddr(195), format="B", size=1),
            NumberRegField(lpo.LPO_ENHANCED_SPEC_VERSION, self.getaddr(196), format="B", size=1),
        ]


class _CmisEnhancedLpoPageC1(CmisPage):
    """Page C1h: capability advertisement, polarity, accuracy, OER max, thresholds."""

    def __init__(self, codes):
        super().__init__(codes, page=0xC1, bank=0)

        # Capability advertisement byte (C1h:128)
        self.fields[lpo.LPO_INFO_FIELD] = [
            NumberRegField(lpo.LPO_CAPABILITY, self.getaddr(128), format="B", size=1),
            # C1h:129 - Tx outer extinction ratio max (U8, 0.1 dB/count)
            LpoOerField(lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX, self.getaddr(129), format="B", size=1),
            # C1h:133 - Tx polarity inversion bitmask (1 bit per lane)
            NumberRegField(lpo.LPO_TX_POLARITY_INVERTED, self.getaddr(133), format="B", size=1),
            # C1h:134 - Rx polarity inversion bitmask (1 bit per lane)
            NumberRegField(lpo.LPO_RX_POLARITY_INVERTED, self.getaddr(134), format="B", size=1),
            # C1h:135 - Tx host input VMA monitoring accuracy (bits 3-0, U4, 5 mV/count)
            LpoVmaAccuracyField(lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY, self.getaddr(135), format="B", size=1),
            # C1h:140 - Rx input OMA monitoring accuracy (bits 3-0, U4, 0.2 dB/count)
            LpoOmaAccuracyField(lpo.LPO_RX_INPUT_OMA_MON_ACCURACY, self.getaddr(140), format="B", size=1),
        ]

        # VMA thresholds (U8, 5 mV/count) - C1h:136-139
        self.fields[lpo.LPO_VMA_THRESHOLDS_FIELD] = [
            LpoVmaField(lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_THRESHOLD, self.getaddr(136), format="B", size=1),
            LpoVmaField(lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_THRESHOLD, self.getaddr(137), format="B", size=1),
            LpoVmaField(lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_THRESHOLD, self.getaddr(138), format="B", size=1),
            LpoVmaField(lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_THRESHOLD, self.getaddr(139), format="B", size=1),
        ]

        # OMA thresholds (U16 big-endian, 0.1 uW/count) - C1h:141-148
        self.fields[lpo.LPO_OMA_THRESHOLDS_FIELD] = [
            LpoOmaField(lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_THRESHOLD, self.getaddr(141), format=">H", size=2),
            LpoOmaField(lpo.LPO_RX_INPUT_OMA_LOW_ALARM_THRESHOLD, self.getaddr(143), format=">H", size=2),
            LpoOmaField(lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_THRESHOLD, self.getaddr(145), format=">H", size=2),
            LpoOmaField(lpo.LPO_RX_INPUT_OMA_LOW_WARNING_THRESHOLD, self.getaddr(147), format=">H", size=2),
        ]


class _CmisEnhancedLpoPageC2(CmisPage):
    """Page C2h: VMA/OMA flags, per-lane measurements, masks."""

    def __init__(self, codes):
        super().__init__(codes, page=0xC2, bank=0)

        # VMA flags (latched bitmasks, 1 bit per lane) - C2h:141-144
        self.fields[lpo.LPO_VMA_FLAGS_FIELD] = [
            LpoLaneFlagRegField(lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG, self.getaddr(141), format="B", size=1),
            LpoLaneFlagRegField(lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_FLAG, self.getaddr(142), format="B", size=1),
            LpoLaneFlagRegField(lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_FLAG, self.getaddr(143), format="B", size=1),
            LpoLaneFlagRegField(lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_FLAG, self.getaddr(144), format="B", size=1),
        ]

        # Per-lane Tx host input VMA measurements (U8, 5 mV/count) - C2h:145-152
        self.fields[lpo.LPO_VMA_DOM_FIELD] = [
            LpoVmaField(lpo.LPO_HOST_INPUT_VMA_TX1, self.getaddr(145), format="B", size=1),
            LpoVmaField(lpo.LPO_HOST_INPUT_VMA_TX2, self.getaddr(146), format="B", size=1),
            LpoVmaField(lpo.LPO_HOST_INPUT_VMA_TX3, self.getaddr(147), format="B", size=1),
            LpoVmaField(lpo.LPO_HOST_INPUT_VMA_TX4, self.getaddr(148), format="B", size=1),
            LpoVmaField(lpo.LPO_HOST_INPUT_VMA_TX5, self.getaddr(149), format="B", size=1),
            LpoVmaField(lpo.LPO_HOST_INPUT_VMA_TX6, self.getaddr(150), format="B", size=1),
            LpoVmaField(lpo.LPO_HOST_INPUT_VMA_TX7, self.getaddr(151), format="B", size=1),
            LpoVmaField(lpo.LPO_HOST_INPUT_VMA_TX8, self.getaddr(152), format="B", size=1),
        ]

        # VMA masks (bitmasks) - C2h:153-156
        self.fields[lpo.LPO_VMA_MASKS_FIELD] = [
            NumberRegField(lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_MASK, self.getaddr(153), format="B", size=1),
            NumberRegField(lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_MASK, self.getaddr(154), format="B", size=1),
            NumberRegField(lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_MASK, self.getaddr(155), format="B", size=1),
            NumberRegField(lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_MASK, self.getaddr(156), format="B", size=1),
        ]

        # OMA flags (latched bitmasks, 1 bit per lane) - C2h:157-160
        self.fields[lpo.LPO_OMA_FLAGS_FIELD] = [
            LpoLaneFlagRegField(lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_FLAG, self.getaddr(157), format="B", size=1),
            LpoLaneFlagRegField(lpo.LPO_RX_INPUT_OMA_LOW_ALARM_FLAG, self.getaddr(158), format="B", size=1),
            LpoLaneFlagRegField(lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_FLAG, self.getaddr(159), format="B", size=1),
            LpoLaneFlagRegField(lpo.LPO_RX_INPUT_OMA_LOW_WARNING_FLAG, self.getaddr(160), format="B", size=1),
        ]

        # Per-lane Rx optical input OMA measurements (U16 big-endian, 0.1 uW/count) - C2h:161-176
        self.fields[lpo.LPO_OMA_DOM_FIELD] = [
            LpoOmaField(lpo.LPO_INPUT_OMA_RX1, self.getaddr(161), format=">H", size=2),
            LpoOmaField(lpo.LPO_INPUT_OMA_RX2, self.getaddr(163), format=">H", size=2),
            LpoOmaField(lpo.LPO_INPUT_OMA_RX3, self.getaddr(165), format=">H", size=2),
            LpoOmaField(lpo.LPO_INPUT_OMA_RX4, self.getaddr(167), format=">H", size=2),
            LpoOmaField(lpo.LPO_INPUT_OMA_RX5, self.getaddr(169), format=">H", size=2),
            LpoOmaField(lpo.LPO_INPUT_OMA_RX6, self.getaddr(171), format=">H", size=2),
            LpoOmaField(lpo.LPO_INPUT_OMA_RX7, self.getaddr(173), format=">H", size=2),
            LpoOmaField(lpo.LPO_INPUT_OMA_RX8, self.getaddr(175), format=">H", size=2),
        ]

        # OMA masks (bitmasks) - C2h:177-180
        self.fields[lpo.LPO_OMA_MASKS_FIELD] = [
            NumberRegField(lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_MASK, self.getaddr(177), format="B", size=1),
            NumberRegField(lpo.LPO_RX_INPUT_OMA_LOW_ALARM_MASK, self.getaddr(178), format="B", size=1),
            NumberRegField(lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_MASK, self.getaddr(179), format="B", size=1),
            NumberRegField(lpo.LPO_RX_INPUT_OMA_LOW_WARNING_MASK, self.getaddr(180), format="B", size=1),
        ]


class CmisEnhancedLpoMemMap(CmisMemMap):
    def __init__(self, codes, bank=0):
        super().__init__(codes, bank=bank)
        # LPO-specific pages are always bank=0 per the Enhanced LPO spec.
        self.add_pages(
            _CmisEnhancedLpoPage01(codes),
            _CmisEnhancedLpoPageC1(codes),
            _CmisEnhancedLpoPageC2(codes),
        )
