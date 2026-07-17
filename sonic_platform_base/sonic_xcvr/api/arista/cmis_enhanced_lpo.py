"""
    cmis_enhanced_lpo.py

    API for Arista Enhanced LPO modules.
"""

from ..public.cmis import CmisApi
from ...fields import arista_lpo_consts as lpo

# LPO_CAPABILITY is C1h:128. Bits 2, 3, and 4 advertise OER, VMA, and OMA support.
_OER_CAPABILITY_MASK = 0x04
_VMA_CAPABILITY_MASK = 0x08
_OMA_CAPABILITY_MASK = 0x10

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


_VMA_THRESHOLD_FIELDS = [
    lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_THRESHOLD,
    lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_THRESHOLD,
    lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_THRESHOLD,
    lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_THRESHOLD,
]

_OMA_THRESHOLD_FIELDS = [
    lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_THRESHOLD,
    lpo.LPO_RX_INPUT_OMA_LOW_ALARM_THRESHOLD,
    lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_THRESHOLD,
    lpo.LPO_RX_INPUT_OMA_LOW_WARNING_THRESHOLD,
]


def _value_or_na(value):
    """Return the API fallback for decoded fields that failed to read."""
    return value if value is not None else 'N/A'


def _read_value_or_na(xcvr_eeprom, field):
    """Read an already-decoded EEPROM field and normalize read failures."""
    return _value_or_na(xcvr_eeprom.read(field))


def _set_na(output, fields):
    """Populate unsupported scalar fields without reading optional registers."""
    for field in fields:
        output[field] = 'N/A'


def _set_lane_flag_na(output, fields):
    """Populate unsupported per-lane flag fields with the API fallback value."""
    for field in fields:
        for lane in range(1, 9):
            output["{}{}".format(field, lane)] = 'N/A'


def _lane_flag_na_dict(field):
    """Build the per-lane fallback shape expected by decoded flag fields."""
    flags = {}
    _set_lane_flag_na(flags, [field])
    return flags


def _is_capability_supported(capabilities, mask):
    """Check whether an optional LPO capability bit is advertised."""
    return bool(capabilities & mask)


class CmisEnhancedLpoApi(CmisApi):
    def _read_if_supported(self, field, capabilities, mask):
        """Read optional info fields only when the capability bit is set."""
        if not _is_capability_supported(capabilities, mask):
            return 'N/A'
        return _read_value_or_na(self.xcvr_eeprom, field)

    def get_transceiver_info(self):
        xcvr_info = super().get_transceiver_info()
        if xcvr_info is None:
            return None
        capabilities = self.xcvr_eeprom.read(lpo.LPO_CAPABILITY)
        if capabilities is None:
            return None

        xcvr_info.update({
            lpo.LPO_TX_POLARITY_INVERTED: _read_value_or_na(self.xcvr_eeprom, lpo.LPO_TX_POLARITY_INVERTED),
            lpo.LPO_RX_POLARITY_INVERTED: _read_value_or_na(self.xcvr_eeprom, lpo.LPO_RX_POLARITY_INVERTED),
            lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY: self._read_if_supported(
                lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY, capabilities, _VMA_CAPABILITY_MASK
            ),
            lpo.LPO_RX_INPUT_OMA_MON_ACCURACY: self._read_if_supported(
                lpo.LPO_RX_INPUT_OMA_MON_ACCURACY, capabilities, _OMA_CAPABILITY_MASK
            ),
            lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX: self._read_if_supported(
                lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX, capabilities, _OER_CAPABILITY_MASK
            ),
        })
        return xcvr_info

    def get_transceiver_dom_real_value(self):
        trans_dom = super().get_transceiver_dom_real_value()
        if trans_dom is None:
            return None
        capabilities = self.xcvr_eeprom.read(lpo.LPO_CAPABILITY)
        if capabilities is None:
            return None

        if _is_capability_supported(capabilities, _VMA_CAPABILITY_MASK):
            for field in _VMA_TX_FIELDS:
                trans_dom[field] = _read_value_or_na(self.xcvr_eeprom, field)
        else:
            _set_na(trans_dom, _VMA_TX_FIELDS)

        if _is_capability_supported(capabilities, _OMA_CAPABILITY_MASK):
            for field in _OMA_RX_FIELDS:
                trans_dom[field] = _read_value_or_na(self.xcvr_eeprom, field)
        else:
            _set_na(trans_dom, _OMA_RX_FIELDS)

        return trans_dom

    def get_transceiver_threshold_info(self):
        threshold_dict = super().get_transceiver_threshold_info()
        if threshold_dict is None:
            return None
        capabilities = self.xcvr_eeprom.read(lpo.LPO_CAPABILITY)
        if capabilities is None:
            return None

        if _is_capability_supported(capabilities, _VMA_CAPABILITY_MASK):
            for field in _VMA_THRESHOLD_FIELDS:
                threshold_dict[field] = _read_value_or_na(self.xcvr_eeprom, field)
        else:
            _set_na(threshold_dict, _VMA_THRESHOLD_FIELDS)

        if _is_capability_supported(capabilities, _OMA_CAPABILITY_MASK):
            for field in _OMA_THRESHOLD_FIELDS:
                threshold_dict[field] = _read_value_or_na(self.xcvr_eeprom, field)
        else:
            _set_na(threshold_dict, _OMA_THRESHOLD_FIELDS)

        return threshold_dict

    def get_transceiver_dom_flags(self):
        dom_flag_dict = super().get_transceiver_dom_flags()
        if dom_flag_dict is None:
            return None
        capabilities = self.xcvr_eeprom.read(lpo.LPO_CAPABILITY)
        if capabilities is None:
            return None

        if _is_capability_supported(capabilities, _VMA_CAPABILITY_MASK):
            for field in _VMA_FLAG_FIELDS:
                flags = self.xcvr_eeprom.read(field)
                dom_flag_dict.update(flags if flags is not None else _lane_flag_na_dict(field))
        else:
            _set_lane_flag_na(dom_flag_dict, _VMA_FLAG_FIELDS)

        if _is_capability_supported(capabilities, _OMA_CAPABILITY_MASK):
            for field in _OMA_FLAG_FIELDS:
                flags = self.xcvr_eeprom.read(field)
                dom_flag_dict.update(flags if flags is not None else _lane_flag_na_dict(field))
        else:
            _set_lane_flag_na(dom_flag_dict, _OMA_FLAG_FIELDS)

        return dom_flag_dict
