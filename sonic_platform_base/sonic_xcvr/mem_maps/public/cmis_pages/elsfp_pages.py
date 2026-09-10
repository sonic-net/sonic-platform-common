"""
CMIS pages 0x1A and 0x1B for the ELSFP (External Laser Source) device.
Field layout follows OIF-ELSFP-CMIS-01.0 Tables 4-12.
"""

from .base import CmisPage
from .cmis_page_consts import (
    ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE,
    ELSFP_SETPOINTS_MON_PAGE,
)
from ....fields.xcvr_field import (
    NumberRegField,
    CodeRegField,
    RegBitField,
    RegBitsField,
    RegGroupField,
)
from ....fields import elsfp_consts
from ....fields.scale_consts import (
    SCALE_100UA_TO_MA,
    SCALE_10UW_TO_MW,
    SCALE_15MV_TO_V,
    SCALE_200UA_TO_MA,
    SCALE_5GHZ_TO_GHZ,
)

NUM_ELSFP_LANES = 8


def _per_lane_bit_field(const, addr, bit_prefix, ro=True, num_lanes=NUM_ELSFP_LANES):
    """Build a 1-byte NumberRegField whose 8 bits map to per-lane RegBitFields.

    Bit ``(lane - 1)`` is exposed as ``f"{bit_prefix}{lane}"`` for ``lane`` in
    ``1..num_lanes``. ``ro`` is applied uniformly to the outer NumberRegField
    and each inner RegBitField, matching the ELSFP alarm/warn/mask convention.
    """
    return NumberRegField(
        const, addr,
        *(RegBitField(f"{bit_prefix}{lane}", lane - 1, ro=ro)
          for lane in range(1, num_lanes + 1)),
        size=1, ro=ro,
    )


class ElsfpAdvertisementsFlagsCtrlPage(CmisPage):
    """ELSFP Page 1Ah (advertisements, flags, controls) -- Tables 4-10."""

    def __init__(self, codes, bank=0):
        super().__init__(codes, page=ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, bank=bank)

        self.fields[elsfp_consts.ELSFP_MODULE_ADVERTISEMENTS_FIELD] = [
            NumberRegField(elsfp_consts.MAX_OPTICAL_POWER, self.getaddr(128), size=2, format=">H", scale=SCALE_10UW_TO_MW),
            NumberRegField(elsfp_consts.MIN_OPTICAL_POWER, self.getaddr(130), size=2, format=">H", scale=SCALE_10UW_TO_MW),
            NumberRegField(elsfp_consts.MAX_LASER_BIAS,    self.getaddr(132), size=2, format=">H", scale=SCALE_100UA_TO_MA),
            NumberRegField(elsfp_consts.MIN_LASER_BIAS,    self.getaddr(134), size=2, format=">H", scale=SCALE_100UA_TO_MA),

            # Byte 140: control mode (bit 0) and number of lanes (bits 7-1)
            RegGroupField(
                elsfp_consts.CONTROL_MODE_AND_LANE_COUNT,
                CodeRegField(
                    elsfp_consts.CONTROL_MODE_APC_ACC,
                    self.getaddr(140),
                    self.codes.CONTROL_MODE,
                    RegBitsField("ControlModeBit", bitpos=0, size=1),
                ),
                NumberRegField(
                    elsfp_consts.NUMBER_OF_LANES,
                    self.getaddr(140),
                    RegBitsField("LaneCountBits", bitpos=1, size=7),
                    size=1,
                    format="B",
                ),
            ),

            NumberRegField(elsfp_consts.BIAS_HIGH_ALARM, self.getaddr(141), size=2, format=">H", scale=SCALE_100UA_TO_MA),
            NumberRegField(elsfp_consts.BIAS_LOW_ALARM,  self.getaddr(143), size=2, format=">H", scale=SCALE_100UA_TO_MA),
            NumberRegField(elsfp_consts.BIAS_HIGH_WARN,  self.getaddr(145), size=2, format=">H", scale=SCALE_100UA_TO_MA),
            NumberRegField(elsfp_consts.BIAS_LOW_WARN,   self.getaddr(147), size=2, format=">H", scale=SCALE_100UA_TO_MA),

            NumberRegField(elsfp_consts.OPT_POWER_HIGH_ALARM, self.getaddr(149), size=2, format=">H", scale=SCALE_10UW_TO_MW),
            NumberRegField(elsfp_consts.OPT_POWER_LOW_ALARM,  self.getaddr(151), size=2, format=">H", scale=SCALE_10UW_TO_MW),
            NumberRegField(elsfp_consts.OPT_POWER_HIGH_WARN,  self.getaddr(153), size=2, format=">H", scale=SCALE_10UW_TO_MW),
            NumberRegField(elsfp_consts.OPT_POWER_LOW_WARN,   self.getaddr(155), size=2, format=">H", scale=SCALE_10UW_TO_MW),
        ]

        self.fields[elsfp_consts.ELSFP_LANE_FAULTS_WARNINGS_FIELD] = [
            NumberRegField(
                elsfp_consts.LANE_SUMMARY_STATUS,
                self.getaddr(165),
                RegBitField(elsfp_consts.LANE_SUMMARY_FAULT, 2),
                RegBitField(elsfp_consts.LANE_SUMMARY_WARNING, 3),
                size=1,
                format="B",
            ),

            # Bytes 166-169: per-lane fault flags for lanes 1-32
            RegGroupField(
                elsfp_consts.FAULT_FLAG_LANE_FIELD,
                *(
                    NumberRegField(
                        f"FaultFlagLane{lane}",
                        self.getaddr(166 + (lane - 1) // 8),
                        RegBitField(f"Bit{(lane - 1) % 8}", (lane - 1) % 8),
                    )
                    for lane in range(1, 33)
                ),
            ),

            # Bytes 174-177: per-lane warning flags for lanes 1-32
            RegGroupField(
                elsfp_consts.WARN_FLAG_LANE_FIELD,
                *(
                    NumberRegField(
                        f"WarnFlagLane{lane}",
                        self.getaddr(174 + (lane - 1) // 8),
                        RegBitField(f"Bit{(lane - 1) % 8}", (lane - 1) % 8),
                    )
                    for lane in range(1, 33)
                ),
            ),
        ]

        self.fields[elsfp_consts.ELSFP_LASER_SAVE_RESTORE_FIELD] = [
            NumberRegField(elsfp_consts.SAVE_RESTORE_COMMAND, self.getaddr(184), size=1, ro=False),
            NumberRegField(elsfp_consts.SAVE_RESTORE_CONFIRM, self.getaddr(185), size=1),
        ]

        self.fields[elsfp_consts.ELSFP_ALARMS_WARNINGS_MASKS_FIELD] = [
            # Per-lane indexed alarm/warn flags (RO, bytes 186-193).
            _per_lane_bit_field(elsfp_consts.HIGH_BIAS_ALARM_INDEXED_FIELD,   self.getaddr(186), "HighBiasAlarmIndexed"),
            _per_lane_bit_field(elsfp_consts.LOW_BIAS_ALARM_INDEXED_FIELD,    self.getaddr(187), "LowBiasAlarmIndexed"),
            _per_lane_bit_field(elsfp_consts.HIGH_BIAS_WARN_INDEXED_FIELD,    self.getaddr(188), "HighBiasWarnIndexed"),
            _per_lane_bit_field(elsfp_consts.LOW_BIAS_WARN_INDEXED_FIELD,     self.getaddr(189), "LowBiasWarnIndexed"),
            _per_lane_bit_field(elsfp_consts.HIGH_POWER_ALARM_INDEXED_FIELD,  self.getaddr(190), "HighPowerAlarmIndexed"),
            _per_lane_bit_field(elsfp_consts.LOW_POWER_ALARM_INDEXED_FIELD,   self.getaddr(191), "LowPowerAlarmIndexed"),
            _per_lane_bit_field(elsfp_consts.HIGH_POWER_WARN_INDEXED_FIELD,   self.getaddr(192), "HighPowerWarnIndexed"),
            _per_lane_bit_field(elsfp_consts.LOW_POWER_WARN_INDEXED_FIELD,    self.getaddr(193), "LowPowerWarnIndexed"),

            # Per-lane alarm/warn masks (RW, bytes 198-205).
            _per_lane_bit_field(elsfp_consts.HIGH_BIAS_ALARM_MASK_FIELD,      self.getaddr(198), "HighBiasAlarmMask",  ro=False),
            _per_lane_bit_field(elsfp_consts.LOW_BIAS_ALARM_MASK_FIELD,       self.getaddr(199), "LowBiasAlarmMask",   ro=False),
            _per_lane_bit_field(elsfp_consts.HIGH_BIAS_WARN_MASK_FIELD,       self.getaddr(200), "HighBiasWarnMask",   ro=False),
            _per_lane_bit_field(elsfp_consts.LOW_BIAS_WARN_MASK_FIELD,        self.getaddr(201), "LowBiasWarnMask",    ro=False),
            _per_lane_bit_field(elsfp_consts.HIGH_POWER_ALARM_MASK_FIELD,     self.getaddr(202), "HighPowerAlarmMask", ro=False),
            _per_lane_bit_field(elsfp_consts.LOW_POWER_ALARM_MASK_FIELD,      self.getaddr(203), "LowPowerAlarmMask",  ro=False),
            _per_lane_bit_field(elsfp_consts.HIGH_POWER_WARN_MASK_FIELD,      self.getaddr(204), "HighPowerWarnMask",  ro=False),
            _per_lane_bit_field(elsfp_consts.LOW_POWER_WARN_MASK_FIELD,       self.getaddr(205), "LowPowerWarnMask",   ro=False),

            # Global alarm/warn masks (RW, bytes 210-211).
            _per_lane_bit_field(elsfp_consts.GLOBAL_ALARM_MASK_FIELD,         self.getaddr(210), "GlobalAlarmMask",    ro=False),
            _per_lane_bit_field(elsfp_consts.GLOBAL_WARN_MASK_FIELD,          self.getaddr(211), "GlobalWarnMask",     ro=False),

            # Bytes 212-219: 4-bit fault and warning codes packed two per byte
            RegGroupField(
                elsfp_consts.FAULT_CODE_FIELD,
                *(
                    CodeRegField(
                        f"{elsfp_consts.FAULT_CODE_FIELD}{lane}",
                        self.getaddr(212 + (lane - 1)),
                        self.codes.LANE_FAULT_CODE,
                        RegBitsField(f"FaultCodeBits{lane}", bitpos=0, size=4),
                    )
                    for lane in range(1, 9)
                ),
            ),
            RegGroupField(
                elsfp_consts.WARNING_CODE_FIELD,
                *(
                    CodeRegField(
                        f"{elsfp_consts.WARNING_CODE_FIELD}{lane}",
                        self.getaddr(212 + (lane - 1)),
                        self.codes.LANE_WARNING_CODE,
                        RegBitsField(f"WarningCodeBits{lane}", bitpos=4, size=4),
                    )
                    for lane in range(1, 9)
                ),
            ),
        ]

        self.fields[elsfp_consts.ELSFP_LANE_CONTROLS_FIELD] = [
            _per_lane_bit_field(elsfp_consts.LANE_ENABLE_FIELD, self.getaddr(220), "LaneEnable", ro=False),
            # Bytes 221-222: 2-bit per-lane state, packed 4-per-byte
            RegGroupField(
                elsfp_consts.LANE_STATE_FIELD,
                *(
                    CodeRegField(
                        f"{elsfp_consts.LANE_STATE_FIELD}{lane}",
                        self.getaddr(221 if lane < 5 else 222),
                        self.codes.LANE_STATE,
                        RegBitsField(f"LaneState{lane}", bitpos=2 * ((lane - 1) % 4), size=2),
                    )
                    for lane in range(1, 9)
                ),
            ),
        ]

        self.fields[elsfp_consts.ELSFP_OUTPUT_FIBER_CHECKED_FIELD] = [
            NumberRegField(
                elsfp_consts.OUTPUT_FIBER_CHECKED_FLAG_LANE_FIELD, self.getaddr(223),
                *(
                    RegBitField(
                        f"{elsfp_consts.OUTPUT_FIBER_CHECKED_FLAG_LANE_FIELD}{lane}",
                        lane - 1,
                    )
                    for lane in range(1, 9)
                ),
                size=1, ro=False,
            ),
        ]

        self.fields[elsfp_consts.ELSFP_LANE_MAPPING_FREQ_POWER_FIELD] = [
            RegGroupField(
                elsfp_consts.LANE_TO_FIBER_MAPPING_FIELD,
                *(
                    NumberRegField(
                        f"{elsfp_consts.LANE_TO_FIBER_MAPPING_FIELD}{lane}",
                        self.getaddr(224 + (lane - 1)),
                        size=1, ro=True,
                    )
                    for lane in range(1, 9)
                ),
            ),
            RegGroupField(
                elsfp_consts.LANE_FREQ_FIELD,
                *(
                    NumberRegField(
                        f"{elsfp_consts.LANE_FREQ_FIELD}{lane}",
                        self.getaddr(232 + 2 * (lane - 1)),
                        size=2, format=">H", scale=SCALE_5GHZ_TO_GHZ, ro=True,
                    )
                    for lane in range(1, 9)
                ),
            ),
            NumberRegField(
                elsfp_consts.OPT_CHECK_POWER_SETPOINT, self.getaddr(248),
                size=1, format="B", scale=1.0, ro=True,
            ),
        ]


class ElsfpSetpointsMonitorsPage(CmisPage):
    """ELSFP Page 1Bh (setpoints, monitors) -- Tables 11-12."""

    def __init__(self, codes, bank=0):
        super().__init__(codes, page=ELSFP_SETPOINTS_MON_PAGE, bank=bank)

        self.fields[elsfp_consts.ELSFP_SETPOINTS_FIELD] = [
            RegGroupField(
                elsfp_consts.BIAS_CURRENT_SETPOINT_FIELD,
                *(
                    NumberRegField(
                        f"{elsfp_consts.BIAS_CURRENT_SETPOINT_FIELD}{lane}",
                        self.getaddr(128 + 2 * (lane - 1)),
                        size=2, format=">H", scale=SCALE_100UA_TO_MA, ro=False,
                    )
                    for lane in range(1, 9)
                ),
            ),
            RegGroupField(
                elsfp_consts.OPT_POWER_SETPOINT_FIELD,
                *(
                    NumberRegField(
                        f"{elsfp_consts.OPT_POWER_SETPOINT_FIELD}{lane}",
                        self.getaddr(144 + 2 * (lane - 1)),
                        size=2, format=">H", scale=SCALE_10UW_TO_MW, ro=False,
                    )
                    for lane in range(1, 9)
                ),
            ),
        ]

        self.fields[elsfp_consts.ELSFP_MONITORS_FIELD] = [
            RegGroupField(
                elsfp_consts.BIAS_CURRENT_MONITOR_FIELD,
                *(
                    NumberRegField(
                        f"{elsfp_consts.BIAS_CURRENT_MONITOR_FIELD}{lane}",
                        self.getaddr(184 + 2 * (lane - 1)),
                        size=2, format=">H", scale=SCALE_100UA_TO_MA,
                    )
                    for lane in range(1, 9)
                ),
            ),
            RegGroupField(
                elsfp_consts.OPT_POWER_MONITOR_FIELD,
                *(
                    NumberRegField(
                        f"{elsfp_consts.OPT_POWER_MONITOR_FIELD}{lane}",
                        self.getaddr(200 + 2 * (lane - 1)),
                        size=2, format=">H", scale=SCALE_10UW_TO_MW,
                    )
                    for lane in range(1, 9)
                ),
            ),
            RegGroupField(
                elsfp_consts.VOLTAGE_MONITOR_FIELD,
                *(
                    NumberRegField(
                        f"{elsfp_consts.VOLTAGE_MONITOR_FIELD}{lane}",
                        self.getaddr(232 + (lane - 1)),
                        size=1, format="B", scale=SCALE_15MV_TO_V,
                    )
                    for lane in range(1, 9)
                ),
            ),
            NumberRegField(
                elsfp_consts.ICC_MONITOR, self.getaddr(240),
                size=2, format=">H", scale=SCALE_200UA_TO_MA,
            ),
        ]
