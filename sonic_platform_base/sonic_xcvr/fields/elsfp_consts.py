# ELSFP-specific field name constants (Pages 1Ah and 1Bh)

# Group name constants (used as group fields)
ELSFP_MODULE_ADVERTISEMENTS_FIELD = "ElsfpModuleAdvertisements"
ELSFP_LANE_FAULTS_WARNINGS_FIELD = "ElsfpLaneFaultsWarnings"
ELSFP_LASER_SAVE_RESTORE_FIELD = "ElsfpLaserSaveRestore"
ELSFP_ALARMS_WARNINGS_MASKS_FIELD = "ElsfpAlarmsWarningsMasks"
ELSFP_LANE_CONTROLS_FIELD = "ElsfpLaneControls"  # Table 8: Bytes 220-222
ELSFP_OUTPUT_FIBER_CHECKED_FIELD = "ElsfpOutputFiberChecked"  # Table 9: Byte 223
ELSFP_LANE_MAPPING_FREQ_POWER_FIELD = "ElsfpLaneMappingFreqPower"  # Table 10: Bytes 224-255
ELSFP_SETPOINTS_FIELD = "ElsfpSetpoints"
ELSFP_MONITORS_FIELD = "ElsfpMonitors"

# Page 1Ah: ELSFP Advertisements, Flags, and Controls

# Module Advertisements (Bytes 128-164)
MAX_OPTICAL_POWER = "MaxOpticalPower"
MIN_OPTICAL_POWER = "MinOpticalPower"
MAX_LASER_BIAS = "MaxLaserBias"
MIN_LASER_BIAS = "MinLaserBias"

# Container byte for ControlModeAPCACC/NumberOfLanes (byte 140)
CONTROL_MODE_AND_LANE_COUNT = "ElsfpControlModeAndLaneCount"

CONTROL_MODE_APC_ACC = "ControlModeAPCACC"
NUMBER_OF_LANES = "NumberOfLanes"
BIAS_HIGH_ALARM = "BiasHighAlarm"
BIAS_LOW_ALARM = "BiasLowAlarm"
BIAS_HIGH_WARN = "BiasHighWarn"
BIAS_LOW_WARN = "BiasLowWarn"
OPT_POWER_HIGH_ALARM = "OptPowerHighAlarm"
OPT_POWER_LOW_ALARM = "OptPowerLowAlarm"
OPT_POWER_HIGH_WARN = "OptPowerHighWarn"
OPT_POWER_LOW_WARN = "OptPowerLowWarn"

# Lane Faults and Warnings (Bytes 165-181)
LANE_SUMMARY_STATUS = "ElsfpLaneSummaryStatus"
LANE_SUMMARY_FAULT = "LaneSummaryFault"
LANE_SUMMARY_WARNING = "LaneSummaryWarning"
FAULT_FLAG_LANE_FIELD = "FaultFlagLanes"
WARN_FLAG_LANE_FIELD = "WarnFlagLanes"

# Laser Setting and Save/Restore (Bytes 182-185)
SAVE_RESTORE_COMMAND = "SaveRestoreCommand"
SAVE_RESTORE_CONFIRM = "SaveRestoreConfirm"

# Laser Alarms, Warnings, Faults, and Masks (Bytes 186-219)
HIGH_BIAS_ALARM_INDEXED_FIELD = "HighBiasAlarmIndexed"
LOW_BIAS_ALARM_INDEXED_FIELD = "LowBiasAlarmIndexed"
HIGH_BIAS_WARN_INDEXED_FIELD = "HighBiasWarnIndexed"
LOW_BIAS_WARN_INDEXED_FIELD = "LowBiasWarnIndexed"
HIGH_POWER_ALARM_INDEXED_FIELD = "HighPowerAlarmIndexed"
LOW_POWER_ALARM_INDEXED_FIELD = "LowPowerAlarmIndexed"
HIGH_POWER_WARN_INDEXED_FIELD = "HighPowerWarnIndexed"
LOW_POWER_WARN_INDEXED_FIELD = "LowPowerWarnIndexed"

HIGH_BIAS_ALARM_MASK_FIELD = "HighBiasAlarmMask"
LOW_BIAS_ALARM_MASK_FIELD = "LowBiasAlarmMask"
HIGH_BIAS_WARN_MASK_FIELD = "HighBiasWarnMask"
LOW_BIAS_WARN_MASK_FIELD = "LowBiasWarnMask"
HIGH_POWER_ALARM_MASK_FIELD = "HighPowerAlarmMask"
LOW_POWER_ALARM_MASK_FIELD = "LowPowerAlarmMask"
HIGH_POWER_WARN_MASK_FIELD = "HighPowerWarnMask"
LOW_POWER_WARN_MASK_FIELD = "LowPowerWarnMask"

GLOBAL_ALARM_MASK_FIELD = "GlobalAlarmMask"
GLOBAL_WARN_MASK_FIELD = "GlobalWarnMask"
FAULT_CODE_FIELD = "FaultCode"
WARNING_CODE_FIELD = "WarningCode"

# Laser Controls, State, and Additional Info (Bytes 220-255)
LANE_ENABLE_FIELD = "LaneEnable"
LANE_STATE_FIELD = "LaneState"
OUTPUT_FIBER_CHECKED_FLAG_LANE_FIELD = "OutputFiberCheckedFlagLane"
LANE_TO_FIBER_MAPPING_FIELD = "LaneToFiberMapping"
LANE_FREQ_FIELD = "LaneFreq"
OPT_CHECK_POWER_SETPOINT = "OptCheckPowerSetpoint"

# Page 1Bh: Laser Setpoints and Monitors

# Laser Current and Optical Power Setpoints (Bytes 128-183)
BIAS_CURRENT_SETPOINT_FIELD = "BiasCurrentSetpoint"
OPT_POWER_SETPOINT_FIELD = "OptPowerSetpoint"

# Laser Current, Optical, and Voltage Monitors (Bytes 184-255)
BIAS_CURRENT_MONITOR_FIELD = "BiasCurrentMonitor"
OPT_POWER_MONITOR_FIELD = "OptPowerMonitor"
VOLTAGE_MONITOR_FIELD = "VoltageMonitor"
ICC_MONITOR = "ICCMonitor"

