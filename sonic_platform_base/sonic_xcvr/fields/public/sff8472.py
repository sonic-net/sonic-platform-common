import struct

from ..xcvr_field import NumberRegField
from .. import consts

class TempField(NumberRegField):
    def __init__(self, name, offset, *fields, **kwargs):
        kwargs["deps"] = [consts.INT_CAL_FIELD, consts.EXT_CAL_FIELD, consts.T_SLOPE_FIELD, consts.T_OFFSET_FIELD]
        super(TempField, self).__init__(name, offset, *fields, **kwargs)

    def decode(self, raw_data, **decoded_deps):
        int_cal = decoded_deps.get(consts.INT_CAL_FIELD)
        ext_cal = decoded_deps.get(consts.EXT_CAL_FIELD)
        measured_val = struct.unpack(self.format, raw_data)[0]
        if int_cal:
            return measured_val / self.scale
        elif ext_cal:
            t_slope = decoded_deps.get(consts.T_SLOPE_FIELD)
            t_offset = decoded_deps.get(consts.T_OFFSET_FIELD)
            result = t_slope * measured_val + t_offset
            return result / self.scale
        return float('NaN')

class VoltageField(NumberRegField):
    def __init__(self, name, offset, *fields, **kwargs):
        kwargs["deps"] = [consts.INT_CAL_FIELD, consts.EXT_CAL_FIELD, consts.V_SLOPE_FIELD, consts.V_OFFSET_FIELD]
        super(VoltageField, self).__init__(name, offset, *fields, **kwargs)

    def decode(self, raw_data, **decoded_deps):
        int_cal = decoded_deps.get(consts.INT_CAL_FIELD)
        ext_cal = decoded_deps.get(consts.EXT_CAL_FIELD)
        measured_val = struct.unpack(self.format, raw_data)[0]
        if int_cal:
            return measured_val / self.scale
        elif ext_cal:
            v_slope = decoded_deps.get(consts.V_SLOPE_FIELD)
            v_offset = decoded_deps.get(consts.V_OFFSET_FIELD)
            result = v_slope * measured_val + v_offset
            return result / self.scale
        return float('NaN')

class TxBiasField(NumberRegField):
    def __init__(self, name, offset, *fields, **kwargs):
        kwargs["deps"] = [consts.INT_CAL_FIELD, consts.EXT_CAL_FIELD, consts.TX_I_SLOPE_FIELD, consts.TX_I_OFFSET_FIELD]
        super(TxBiasField, self).__init__(name, offset, *fields, **kwargs)

    def decode(self, raw_data, **decoded_deps):
        int_cal = decoded_deps.get(consts.INT_CAL_FIELD)
        ext_cal = decoded_deps.get(consts.EXT_CAL_FIELD)
        measured_val = struct.unpack(self.format, raw_data)[0]
        if int_cal:
            return measured_val / self.scale
        elif ext_cal:
            tx_i_slope = decoded_deps.get(consts.TX_I_SLOPE_FIELD)
            tx_i_offset = decoded_deps.get(consts.TX_I_OFFSET_FIELD)
            result = tx_i_slope * measured_val + tx_i_offset
            return result / self.scale
        return float('NaN')

class TxPowerField(NumberRegField):
    def __init__(self, name, offset, *fields, **kwargs):
        kwargs["deps"] = [consts.INT_CAL_FIELD, consts.EXT_CAL_FIELD, consts.TX_PWR_SLOPE_FIELD, consts.TX_PWR_OFFSET_FIELD]
        super(TxPowerField, self).__init__(name, offset, *fields, **kwargs)

    def decode(self, raw_data, **decoded_deps):
        int_cal = decoded_deps.get(consts.INT_CAL_FIELD)
        ext_cal = decoded_deps.get(consts.EXT_CAL_FIELD)
        measured_val = struct.unpack(self.format, raw_data)[0]
        if int_cal:
            return measured_val / self.scale
        elif ext_cal:
            tx_pwr_slope = decoded_deps.get(consts.TX_PWR_SLOPE_FIELD)
            tx_pwr_offset = decoded_deps.get(consts.TX_PWR_OFFSET_FIELD)
            result = tx_pwr_slope * measured_val + tx_pwr_offset
            return result / self.scale
        return float('NaN')

class RxPowerField(NumberRegField):
    def __init__(self, name, offset, *fields, **kwargs):
        kwargs["deps"] = [consts.INT_CAL_FIELD, consts.EXT_CAL_FIELD, consts.RX_PWR_0_FIELD, consts.RX_PWR_1_FIELD,
                          consts.RX_PWR_2_FIELD, consts.RX_PWR_3_FIELD, consts.RX_PWR_4_FIELD]
        super(RxPowerField, self).__init__(name, offset, *fields, **kwargs)

    def decode(self, raw_data, **decoded_deps):
        int_cal = decoded_deps.get(consts.INT_CAL_FIELD)
        ext_cal = decoded_deps.get(consts.EXT_CAL_FIELD)
        measured_val = struct.unpack(self.format, raw_data)[0]
        if int_cal:
            return measured_val / self.scale
        elif ext_cal:
            rx_pwr_4 = decoded_deps.get(consts.RX_PWR_4_FIELD)
            rx_pwr_3 = decoded_deps.get(consts.RX_PWR_3_FIELD)
            rx_pwr_2 = decoded_deps.get(consts.RX_PWR_2_FIELD)
            rx_pwr_1 = decoded_deps.get(consts.RX_PWR_1_FIELD)
            rx_pwr_0 = decoded_deps.get(consts.RX_PWR_0_FIELD)

            result = rx_pwr_4 * measured_val * 1e4 + \
                     rx_pwr_3 * measured_val * 1e3 + \
                     rx_pwr_2 * measured_val * 1e2 + \
                     rx_pwr_1 * measured_val + \
                     rx_pwr_0
            return result / self.scale
        return float('NaN')
