"""page1a.py

CMIS Page 1Ah - ELSFP Advertisements, Flags, and Controls.

Layout follows OIF-ELSFP-CMIS-01.0 Tables 4-10 for:
  * Module advertisements (bytes 128-164)
  * Lane faults and warnings (bytes 165-181)
  * Laser save/restore (bytes 182-185)
  * Alarms, warnings, masks, and codes (bytes 186-219)
  * Controls, state, and additional info (bytes 220-255)
"""

from .page import CmisPage
from .consts import ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE
from .....fields.xcvr_field import (
    NumberRegField,
    CodeRegField,
    RegBitField,
    RegBitsField,
    RegGroupField,
)
from .....fields import elsfp_consts


class ElsfpAdvertisementsFlagsCtrlPage(CmisPage):
    """ELSFP-specific CMIS Page 1Ah implementation."""

    def __init__(self, codes, bank=0, page=ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE):
        super().__init__(codes, page=page, bank=bank)

        # ------------------------------------------------------------------
        # ELSFP_MODULE_ADVERTISEMENTS_FIELD (Bytes 128-164, Table 4)
        # ------------------------------------------------------------------
        self.fields[elsfp_consts.ELSFP_MODULE_ADVERTISEMENTS_FIELD] = [
            # Max/min optical output power per lane (U16, 10 uW increments)
            NumberRegField(
                elsfp_consts.MAX_OPTICAL_POWER,
                self.getaddr(128),
                size=2,
                format=">H",
                scale=100.0,  # decode in mW (10 uW steps)
            ),
            NumberRegField(
                elsfp_consts.MIN_OPTICAL_POWER,
                self.getaddr(130),
                size=2,
                format=">H",
                scale=100.0,  # decode in mW (10 uW steps)
            ),

            # Max/min laser bias current per lane (U16, 100 uA increments)
            NumberRegField(
                elsfp_consts.MAX_LASER_BIAS,
                self.getaddr(132),
                size=2,
                format=">H",
                scale=10000.0,
            ),
            NumberRegField(
                elsfp_consts.MIN_LASER_BIAS,
                self.getaddr(134),
                size=2,
                format=">H",
                scale=10000.0,
            ),

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

            # Bias current thresholds (U16, 100 uA increments)
            NumberRegField(
                elsfp_consts.BIAS_HIGH_ALARM,
                self.getaddr(141),
                size=2,
                format=">H",
                scale=10000.0,
            ),
            NumberRegField(
                elsfp_consts.BIAS_LOW_ALARM,
                self.getaddr(143),
                size=2,
                format=">H",
                scale=10000.0,
            ),
            NumberRegField(
                elsfp_consts.BIAS_HIGH_WARN,
                self.getaddr(145),
                size=2,
                format=">H",
                scale=10000.0,
            ),
            NumberRegField(
                elsfp_consts.BIAS_LOW_WARN,
                self.getaddr(147),
                size=2,
                format=">H",
                scale=10000.0,
            ),

            # Optical power thresholds (U16, 10 uW increments)
            NumberRegField(
                elsfp_consts.OPT_POWER_HIGH_ALARM,
                self.getaddr(149),
                size=2,
                format=">H",
                scale=100.0,  # decode in mW (10 uW steps)
            ),
            NumberRegField(
                elsfp_consts.OPT_POWER_LOW_ALARM,
                self.getaddr(151),
                size=2,
                format=">H",
                scale=100.0,  # decode in mW (10 uW steps)
            ),
            NumberRegField(
                elsfp_consts.OPT_POWER_HIGH_WARN,
                self.getaddr(153),
                size=2,
                format=">H",
                scale=100.0,  # decode in mW (10 uW steps)
            ),
            NumberRegField(
                elsfp_consts.OPT_POWER_LOW_WARN,
                self.getaddr(155),
                size=2,
                format=">H",
                scale=100.0,  # decode in mW (10 uW steps)
            ),
        ]

        # ------------------------------------------------------------------
        # ELSFP_LANE_FAULTS_WARNINGS_FIELD (Bytes 165-181, Table 5)
        # ------------------------------------------------------------------
        self.fields[elsfp_consts.ELSFP_LANE_FAULTS_WARNINGS_FIELD] = [
            # Byte 165: lane summary fault/warning bits
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
                        "%s%d" % ("FaultFlagLane", lane),
                        self.getaddr(166 + (lane - 1) // 8),
                        RegBitField(
                            "Bit%d" % ((lane - 1) % 8),
                            (lane - 1) % 8,
                        ),
                    )
                    for lane in range(1, 33)
                ),
            ),

            # Bytes 174-177: per-lane warning flags for lanes 1-32
            RegGroupField(
                elsfp_consts.WARN_FLAG_LANE_FIELD,
                *(
                    NumberRegField(
                        "%s%d" % ("WarnFlagLane", lane),
                        self.getaddr(174 + (lane - 1) // 8),
                        RegBitField(
                            "Bit%d" % ((lane - 1) % 8),
                            (lane - 1) % 8,
                        ),
                    )
                    for lane in range(1, 33)
                ),
            ),
        ]

        # ------------------------------------------------------------------
        # ELSFP_LASER_SAVE_RESTORE_FIELD (Bytes 182-185, Table 6)
        # ------------------------------------------------------------------
        self.fields[elsfp_consts.ELSFP_LASER_SAVE_RESTORE_FIELD] = [
            # 184: SaveRestoreCommand (RW), 185: SaveRestoreConfirm (RO)
            NumberRegField(
                elsfp_consts.SAVE_RESTORE_COMMAND,
                self.getaddr(184),
                size=1,
                ro=False,
            ),
            NumberRegField(
                elsfp_consts.SAVE_RESTORE_CONFIRM,
                self.getaddr(185),
                size=1,
            ),
        ]

        # ------------------------------------------------------------------
        # ELSFP_ALARMS_WARNINGS_MASKS_FIELD (Bytes 186-219, Table 7)
        # ------------------------------------------------------------------
        self.fields[elsfp_consts.ELSFP_ALARMS_WARNINGS_MASKS_FIELD] = [
            # 186-193: per-lane alarm/warn bits (1 bit per indexed lane)
            NumberRegField(
                elsfp_consts.HIGH_BIAS_ALARM_INDEXED_FIELD,
                self.getaddr(186),
                *(
                    RegBitField("HighBiasAlarmIndexed%d" % lane, lane - 1)
                    for lane in range(1, 9)
                ),
                size=1,
            ),
            NumberRegField(
                elsfp_consts.LOW_BIAS_ALARM_INDEXED_FIELD,
                self.getaddr(187),
                *(
                    RegBitField("LowBiasAlarmIndexed%d" % lane, lane - 1)
                    for lane in range(1, 9)
                ),
                size=1,
            ),
            NumberRegField(
                elsfp_consts.HIGH_BIAS_WARN_INDEXED_FIELD,
                self.getaddr(188),
                *(
                    RegBitField("HighBiasWarnIndexed%d" % lane, lane - 1)
                    for lane in range(1, 9)
                ),
                size=1,
            ),
            NumberRegField(
                elsfp_consts.LOW_BIAS_WARN_INDEXED_FIELD,
                self.getaddr(189),
                *(
                    RegBitField("LowBiasWarnIndexed%d" % lane, lane - 1)
                    for lane in range(1, 9)
                ),
                size=1,
            ),
            NumberRegField(
                elsfp_consts.HIGH_POWER_ALARM_INDEXED_FIELD,
                self.getaddr(190),
                *(
                    RegBitField("HighPowerAlarmIndexed%d" % lane, lane - 1)
                    for lane in range(1, 9)
                ),
                size=1,
            ),
            NumberRegField(
                elsfp_consts.LOW_POWER_ALARM_INDEXED_FIELD,
                self.getaddr(191),
                *(
                    RegBitField("LowPowerAlarmIndexed%d" % lane, lane - 1)
                    for lane in range(1, 9)
                ),
                size=1,
            ),
            NumberRegField(
                elsfp_consts.HIGH_POWER_WARN_INDEXED_FIELD,
                self.getaddr(192),
                *(
                    RegBitField("HighPowerWarnIndexed%d" % lane, lane - 1)
                    for lane in range(1, 9)
                ),
                size=1,
            ),
            NumberRegField(
                elsfp_consts.LOW_POWER_WARN_INDEXED_FIELD,
                self.getaddr(193),
                *(
                    RegBitField("LowPowerWarnIndexed%d" % lane, lane - 1)
                    for lane in range(1, 9)
                ),
                size=1,
            ),

            # 198-205: per-lane alarm/warn masks (1 bit per lane)
            NumberRegField(
                elsfp_consts.HIGH_BIAS_ALARM_MASK_FIELD,
                self.getaddr(198),
                *(
                    RegBitField("HighBiasAlarmMask%d" % lane, lane - 1, ro=False)
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),
            NumberRegField(
                elsfp_consts.LOW_BIAS_ALARM_MASK_FIELD,
                self.getaddr(199),
                *(
                    RegBitField("LowBiasAlarmMask%d" % lane, lane - 1, ro=False)
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),
            NumberRegField(
                elsfp_consts.HIGH_BIAS_WARN_MASK_FIELD,
                self.getaddr(200),
                *(
                    RegBitField("HighBiasWarnMask%d" % lane, lane - 1, ro=False)
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),
            NumberRegField(
                elsfp_consts.LOW_BIAS_WARN_MASK_FIELD,
                self.getaddr(201),
                *(
                    RegBitField("LowBiasWarnMask%d" % lane, lane - 1, ro=False)
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),
            NumberRegField(
                elsfp_consts.HIGH_POWER_ALARM_MASK_FIELD,
                self.getaddr(202),
                *(
                    RegBitField("HighPowerAlarmMask%d" % lane, lane - 1, ro=False)
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),
            NumberRegField(
                elsfp_consts.LOW_POWER_ALARM_MASK_FIELD,
                self.getaddr(203),
                *(
                    RegBitField("LowPowerAlarmMask%d" % lane, lane - 1, ro=False)
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),
            NumberRegField(
                elsfp_consts.HIGH_POWER_WARN_MASK_FIELD,
                self.getaddr(204),
                *(
                    RegBitField("HighPowerWarnMask%d" % lane, lane - 1, ro=False)
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),
            NumberRegField(
                elsfp_consts.LOW_POWER_WARN_MASK_FIELD,
                self.getaddr(205),
                *(
                    RegBitField("LowPowerWarnMask%d" % lane, lane - 1, ro=False)
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),

            # 210-211: global alarm/warn masks per lane
            NumberRegField(
                elsfp_consts.GLOBAL_ALARM_MASK_FIELD,
                self.getaddr(210),
                *(
                    RegBitField("GlobalAlarmMask%d" % lane, lane - 1, ro=False)
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),
            NumberRegField(
                elsfp_consts.GLOBAL_WARN_MASK_FIELD,
                self.getaddr(211),
                *(
                    RegBitField("GlobalWarnMask%d" % lane, lane - 1, ro=False)
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),

            # 212-219: per-lane 4-bit fault and warning codes
            RegGroupField(
                elsfp_consts.FAULT_CODE_FIELD,
                *(
                    CodeRegField(
                        "%s%d" % (elsfp_consts.FAULT_CODE_FIELD, lane),
                        self.getaddr(212 + (lane - 1)),
                        self.codes.LANE_FAULT_CODE,
                        RegBitsField(
                            "FaultCodeBits%d" % lane,
                            bitpos=0,
                            size=4,
                        ),
                    )
                    for lane in range(1, 9)
                ),
            ),
            RegGroupField(
                elsfp_consts.WARNING_CODE_FIELD,
                *(
                    CodeRegField(
                        "%s%d" % (elsfp_consts.WARNING_CODE_FIELD, lane),
                        self.getaddr(212 + (lane - 1)),
                        self.codes.LANE_WARNING_CODE,
                        RegBitsField(
                            "WarningCodeBits%d" % lane,
                            bitpos=4,
                            size=4,
                        ),
                    )
                    for lane in range(1, 9)
                ),
            ),
        ]

        # ------------------------------------------------------------------
        # ELSFP_LANE_CONTROLS_FIELD (Bytes 220-222, Table 8)
        # Per-lane enable and state
        # ------------------------------------------------------------------
        self.fields[elsfp_consts.ELSFP_LANE_CONTROLS_FIELD] = [
            # 220: Per-lane enable (1 bit per lane)
            NumberRegField(
                elsfp_consts.LANE_ENABLE_FIELD,
                self.getaddr(220),
                *(
                    RegBitField("LaneEnable%d" % lane, lane - 1, ro=False)
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),
            # 221-222: Per-lane 2-bit lane state (packed as LaneState1-4 at byte 221 and
            # LaneState5-8 at byte 222). 4 lanes per byte, 2 bits each.
            RegGroupField(
                elsfp_consts.LANE_STATE_FIELD,
                *(
                    CodeRegField(
                        "%s%d" % (elsfp_consts.LANE_STATE_FIELD, lane),
                        self.getaddr(221 if lane < 5 else 222),
                        self.codes.LANE_STATE,
                        RegBitsField(
                            "LaneState%d" % lane,
                            bitpos=2 * ((lane - 1) % 4),
                            size=2,
                        ),
                    )
                    for lane in range(1, 9)
                ),
            ),
        ]

        # ------------------------------------------------------------------
        # ELSFP_OUTPUT_FIBER_CHECKED_FIELD (Byte 223, Table 9)
        # Output fiber checked flag
        # ------------------------------------------------------------------
        self.fields[elsfp_consts.ELSFP_OUTPUT_FIBER_CHECKED_FIELD] = [
            # 223: Output fiber checked flag (1 bit per lane)
            NumberRegField(
                elsfp_consts.OUTPUT_FIBER_CHECKED_FLAG_LANE_FIELD,
                self.getaddr(223),
                *(
                    RegBitField(
                        "%s%d" % (elsfp_consts.OUTPUT_FIBER_CHECKED_FLAG_LANE_FIELD, lane),
                        lane - 1,
                    )
                    for lane in range(1, 9)
                ),
                size=1,
                ro=False,
            ),
        ]

        # ------------------------------------------------------------------
        # ELSFP_LANE_MAPPING_FREQ_POWER_FIELD (Bytes 224-255, Table 10)
        # Lane-to-fiber mapping, lane frequency, and optical power setpoint
        # ------------------------------------------------------------------
        self.fields[elsfp_consts.ELSFP_LANE_MAPPING_FREQ_POWER_FIELD] = [
            # 224-231: lane-to-fiber mapping, 1 byte per lane
            RegGroupField(
                elsfp_consts.LANE_TO_FIBER_MAPPING_FIELD,
                *(
                    NumberRegField(
                        "%s%d" % (elsfp_consts.LANE_TO_FIBER_MAPPING_FIELD, lane),
                        self.getaddr(224 + (lane - 1)),
                        size=1,
                        ro=True,
                    )
                    for lane in range(1, 9)
                ),
            ),

            # 232-247: lane frequency, 2 bytes per lane, 5 GHz increments
            RegGroupField(
                elsfp_consts.LANE_FREQ_FIELD,
                *(
                    NumberRegField(
                        "%s%d" % (elsfp_consts.LANE_FREQ_FIELD, lane),
                        self.getaddr(232 + 2 * (lane - 1)),
                        size=2,
                        format=">H",
                        scale=0.2,  # decode in GHz (5 GHz steps = 5e9 Hz, stored as value * 5 GHz)
                        ro=True,
                    )
                    for lane in range(1, 9)
                ),
            ),

            # 248: optical power setpoint for fiber check (1 mW increments)
            NumberRegField(
                elsfp_consts.OPT_CHECK_POWER_SETPOINT,
                self.getaddr(248),
                size=1,
                format="B",
                scale=1.0,  # decode in mW (1 mW steps)
                ro=True,
            ),
        ]
