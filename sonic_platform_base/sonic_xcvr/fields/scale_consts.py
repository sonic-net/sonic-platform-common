"""Named scale factors for :class:`NumberRegField`.

``NumberRegField.decode()`` returns ``raw / scale``. Names below encode the
*raw LSB* and the *target unit* of the decoded float, so a reader can tell
at a glance which unit the field ends up in.

Convention: ``SCALE_<RAW_LSB>_TO_<DECODED_UNIT>``.

Multiple fields can share the same numeric value with different semantics
(e.g. ``SCALE_100UA_TO_A`` and ``SCALE_100UV_TO_V`` are both ``10000.0``);
use the name that matches the field's physical quantity, not the number.
"""

# ---------- Current ----------
# Raw stored as 1 uA per LSB, decoded in mA (CDB laser MPD).
SCALE_UA_TO_MA = 1000.0

# Raw stored as 100 uA per LSB, decoded in A.
SCALE_100UA_TO_A = 10000.0

# Raw stored as 100 uA per LSB, decoded in mA
# (ELSFP bias thresholds / setpoints / monitors, ELSFP max/min bias).
SCALE_100UA_TO_MA = 10.0

# Raw stored as 200 uA per LSB, decoded in mA (ELSFP module ICC monitor).
SCALE_200UA_TO_MA = 5.0

# ---------- Optical power (linear) ----------
# Raw stored as 10 uW per LSB, decoded in mW
# (ELSFP opt-power thresholds / setpoints / monitors, ELSFP max/min opt power).
SCALE_10UW_TO_MW = 100.0

# ---------- Voltage ----------
# Raw stored as 100 uV per LSB, decoded in V
# (standard CMIS VOLTAGE_FIELD, NVIDIA ELS voltage on page 0x00/0x02).
SCALE_100UV_TO_V = 10000.0

# Raw stored as 15 mV per LSB, decoded in V (ELSFP per-lane VCC monitor).
SCALE_15MV_TO_V = 1000.0 / 15.0

# Raw stored as 5 mV per LSB, decoded in mV
# (NVIDIA CPO ELS laser + TEC health values on CDB 0x9018).
SCALE_5MV_TO_MV = 0.2

# ---------- Module power ----------
# Raw stored as 0.1 W per LSB, decoded in W (CDB module power consumption).
SCALE_0P1W_TO_W = 10.0

# ---------- Temperature ----------
# Raw stored as 1/256 deg C per LSB (signed int16, aka Q8.8 fixed-point:
# upper byte = integer deg C, lower byte = fractional deg C in 1/256 steps),
# decoded in deg C. Used by standard CMIS temperature and NVIDIA ELS
# custom-monitor temperature value + thresholds.
SCALE_1_OVER_256C_TO_C = 256.0

# ---------- Frequency ----------
# Raw stored as 5 GHz per LSB, decoded in GHz (ELSFP per-lane laser frequency).
SCALE_5GHZ_TO_GHZ = 0.2
