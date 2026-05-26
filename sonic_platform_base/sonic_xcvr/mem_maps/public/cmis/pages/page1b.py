"""page1b.py

CMIS Page 1Bh - Laser Setpoints and Monitors for ELSFP.

Layout based on OIF-ELSFP-CMIS-01.0 Tables 11-12:
  * BiasCurrentSetpoint1-8 (bytes 128-143), 2 bytes per lane, 100 uA increments
  * OptPowerSetpoint1-8   (bytes 144-159), 2 bytes per lane, 10 uW increments
  * BiasCurrentMonitor1-8 (bytes 184-199), 2 bytes per lane, 100 uA increments
  * OptPowerMonitor1-8    (bytes 200-215), 2 bytes per lane, 10 uW increments
  * VoltageMonitor1-8     (bytes 232-239), 1 byte per lane, 15 mV increments
  * ICCMonitor            (bytes 240-241), 2 bytes, 200 uA increments

Per-lane values are exposed via RegGroupField containing per-lane
NumberRegField entries with appropriate scaling to physical units.
"""

from .page import CmisPage
from .consts import ELSFP_SETPOINTS_MON_PAGE
from .....fields.xcvr_field import (
    NumberRegField,
    RegGroupField,
)
from .....fields import elsfp_consts


class ElsfpSetpointsMonitorsPage(CmisPage):
    """ELSFP-specific CMIS Page 1Bh implementation."""

    def __init__(self, codes, bank=0, page=ELSFP_SETPOINTS_MON_PAGE):
        super().__init__(codes, page=page, bank=bank)

        # ------------------------------------------------------------------
        # ELSFP_SETPOINTS_FIELD (Bytes 128-183, Table 11)
        # ------------------------------------------------------------------
        self.fields[elsfp_consts.ELSFP_SETPOINTS_FIELD] = [
            # 128-143: BiasCurrentSetpoint per lane, 2 bytes per lane, 100 uA increments
            RegGroupField(
                elsfp_consts.BIAS_CURRENT_SETPOINT_FIELD,
                *(
                    NumberRegField(
                        "%s%d" % (elsfp_consts.BIAS_CURRENT_SETPOINT_FIELD, lane),
                        self.getaddr(128 + 2 * (lane - 1)),
                        size=2,
                        format=">H",
                        scale=10000.0,  # decode in Amps (100 uA steps)
                        ro=False,
                    )
                    for lane in range(1, 9)
                ),
            ),

            # 144-159: OptPowerSetpoint per lane, 2 bytes per lane, 10 uW increments
            RegGroupField(
                elsfp_consts.OPT_POWER_SETPOINT_FIELD,
                *(
                    NumberRegField(
                        "%s%d" % (elsfp_consts.OPT_POWER_SETPOINT_FIELD, lane),
                        self.getaddr(144 + 2 * (lane - 1)),
                        size=2,
                        format=">H",
                        scale=100.0,  # decode in mW (10 uW steps)
                        ro=False,
                    )
                    for lane in range(1, 9)
                ),
            ),
        ]

        # ------------------------------------------------------------------
        # ELSFP_MONITORS_FIELD (Bytes 184-255, Table 12)
        # ------------------------------------------------------------------
        self.fields[elsfp_consts.ELSFP_MONITORS_FIELD] = [
            # 184-199: BiasCurrentMonitor per lane, 2 bytes per lane, 100 uA increments
            RegGroupField(
                elsfp_consts.BIAS_CURRENT_MONITOR_FIELD,
                *(
                    NumberRegField(
                        "%s%d" % (elsfp_consts.BIAS_CURRENT_MONITOR_FIELD, lane),
                        self.getaddr(184 + 2 * (lane - 1)),
                        size=2,
                        format=">H",
                        scale=10000.0,  # decode in Amps (100 uA steps)
                    )
                    for lane in range(1, 9)
                ),
            ),

            # 200-215: OptPowerMonitor per lane, 2 bytes per lane, 10 uW increments
            RegGroupField(
                elsfp_consts.OPT_POWER_MONITOR_FIELD,
                *(
                    NumberRegField(
                        "%s%d" % (elsfp_consts.OPT_POWER_MONITOR_FIELD, lane),
                        self.getaddr(200 + 2 * (lane - 1)),
                        size=2,
                        format=">H",
                        scale=100.0,  # decode in mW (10 uW steps)
                    )
                    for lane in range(1, 9)
                ),
            ),

            # 232-239: VoltageMonitor per lane, 1 byte per lane, 15 mV increments
            RegGroupField(
                elsfp_consts.VOLTAGE_MONITOR_FIELD,
                *(
                    NumberRegField(
                        "%s%d" % (elsfp_consts.VOLTAGE_MONITOR_FIELD, lane),
                        self.getaddr(232 + (lane - 1)),
                        size=1,
                        format="B",
                        scale=(1000.0 / 15.0),  # (15 mV steps)
                    )
                    for lane in range(1, 9)
                ),
            ),

            # 240-241: ICCMonitor, 2-byte VCC current monitor, 200 uA increments
            NumberRegField(
                elsfp_consts.ICC_MONITOR,
                self.getaddr(240),
                size=2,
                format=">H",
                scale=5000.0,  # decode in Amps (200 uA steps)
            ),
        ]
