"""
    cmis_enhanced_lpo.py

    API for Arista Enhanced LPO modules.
"""

from ..public.cmis import CmisApi
from ...fields import arista_lpo_consts as lpo

# VMA: U8 raw count -> mV
_VMA_MV_PER_COUNT = 5
# OMA: U16 raw count -> mW (0.1 uW per count = 0.0001 mW per count)
_OMA_MW_PER_COUNT = 0.0001
# OER max: U8 raw count -> dB
_OER_DB_PER_COUNT = 0.1
# VMA accuracy: U4 (bits 3-0) -> mV
_VMA_ACC_MV_PER_COUNT = 5
# OMA accuracy: U4 (bits 3-0) -> dB
_OMA_ACC_DB_PER_COUNT = 0.2

_VMA_FLAG_FIELDS = [
    lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG,
    lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_FLAG,
    lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_FLAG,
    lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_FLAG,
]

_OMA_FLAG_FIELDS = [
    lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_FLAG,
    lpo.LPO_RX_INPUT_OMA_LOW_ALARM_FLAG,
    lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_FLAG,
    lpo.LPO_RX_INPUT_OMA_LOW_WARNING_FLAG,
]

_VMA_TX_FIELDS = [
    lpo.LPO_HOST_INPUT_VMA_TX1,
    lpo.LPO_HOST_INPUT_VMA_TX2,
    lpo.LPO_HOST_INPUT_VMA_TX3,
    lpo.LPO_HOST_INPUT_VMA_TX4,
    lpo.LPO_HOST_INPUT_VMA_TX5,
    lpo.LPO_HOST_INPUT_VMA_TX6,
    lpo.LPO_HOST_INPUT_VMA_TX7,
    lpo.LPO_HOST_INPUT_VMA_TX8,
]

_OMA_RX_FIELDS = [
    lpo.LPO_INPUT_OMA_RX1,
    lpo.LPO_INPUT_OMA_RX2,
    lpo.LPO_INPUT_OMA_RX3,
    lpo.LPO_INPUT_OMA_RX4,
    lpo.LPO_INPUT_OMA_RX5,
    lpo.LPO_INPUT_OMA_RX6,
    lpo.LPO_INPUT_OMA_RX7,
    lpo.LPO_INPUT_OMA_RX8,
]


def _scale(raw, factor, precision=3):
    """Return raw * factor as a rounded float, or 'N/A' if raw is None."""
    if raw is None:
        return 'N/A'
    return float("{:.{}f}".format(raw * factor, precision))


def _lower_nibble(raw):
    """Mask to lower 4 bits (U4 field), propagating None."""
    return None if raw is None else raw & 0x0F


def _unpack_flags(field_name, raw):
    """Unpack a bitmask byte into a dict of per-lane boolean keys (lane 1-8)."""
    result = {}
    for lane in range(1, 9):
        key = "{}{}".format(field_name, lane)
        result[key] = bool((raw >> (lane - 1)) & 1) if raw is not None else 'N/A'
    return result


class CmisEnhancedLpoApi(CmisApi):
    def get_transceiver_info(self):
        xcvr_info = super().get_transceiver_info()
        if xcvr_info is None:
            return None

        tx_pol = self.xcvr_eeprom.read(lpo.LPO_TX_POLARITY_INVERTED)
        rx_pol = self.xcvr_eeprom.read(lpo.LPO_RX_POLARITY_INVERTED)

        vma_acc_raw = self.xcvr_eeprom.read(lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY)
        vma_acc = _scale(_lower_nibble(vma_acc_raw), _VMA_ACC_MV_PER_COUNT)

        oma_acc_raw = self.xcvr_eeprom.read(lpo.LPO_RX_INPUT_OMA_MON_ACCURACY)
        oma_acc = _scale(_lower_nibble(oma_acc_raw), _OMA_ACC_DB_PER_COUNT)

        oer_raw = self.xcvr_eeprom.read(lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX)
        oer_max = _scale(oer_raw, _OER_DB_PER_COUNT)

        xcvr_info.update({
            lpo.LPO_TX_POLARITY_INVERTED: tx_pol if tx_pol is not None else 'N/A',
            lpo.LPO_RX_POLARITY_INVERTED: rx_pol if rx_pol is not None else 'N/A',
            lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY: vma_acc,
            lpo.LPO_RX_INPUT_OMA_MON_ACCURACY: oma_acc,
            lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX: oer_max,
        })
        return xcvr_info

    def get_transceiver_dom_real_value(self):
        trans_dom = super().get_transceiver_dom_real_value()
        if trans_dom is None:
            return None

        for field in _VMA_TX_FIELDS:
            trans_dom[field] = _scale(self.xcvr_eeprom.read(field), _VMA_MV_PER_COUNT)

        for field in _OMA_RX_FIELDS:
            trans_dom[field] = _scale(self.xcvr_eeprom.read(field), _OMA_MW_PER_COUNT)

        return trans_dom

    def get_transceiver_threshold_info(self):
        threshold_dict = super().get_transceiver_threshold_info()
        if threshold_dict is None:
            return None

        vma_threshold_fields = [
            (lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_THRESHOLD, _VMA_MV_PER_COUNT),
            (lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_THRESHOLD, _VMA_MV_PER_COUNT),
            (lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_THRESHOLD, _VMA_MV_PER_COUNT),
            (lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_THRESHOLD, _VMA_MV_PER_COUNT),
        ]
        oma_threshold_fields = [
            (lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_THRESHOLD, _OMA_MW_PER_COUNT),
            (lpo.LPO_RX_INPUT_OMA_LOW_ALARM_THRESHOLD, _OMA_MW_PER_COUNT),
            (lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_THRESHOLD, _OMA_MW_PER_COUNT),
            (lpo.LPO_RX_INPUT_OMA_LOW_WARNING_THRESHOLD, _OMA_MW_PER_COUNT),
        ]

        for field, factor in vma_threshold_fields + oma_threshold_fields:
            raw = self.xcvr_eeprom.read(field)
            threshold_dict[field] = _scale(raw, factor)

        return threshold_dict

    def get_transceiver_dom_flags(self):
        dom_flag_dict = super().get_transceiver_dom_flags()
        if dom_flag_dict is None:
            return None

        for field in _VMA_FLAG_FIELDS + _OMA_FLAG_FIELDS:
            raw = self.xcvr_eeprom.read(field)
            dom_flag_dict.update(_unpack_flags(field, raw))

        return dom_flag_dict
