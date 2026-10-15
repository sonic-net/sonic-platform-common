
# Get Telemetry Info (CDB 0x8000) reply field group -- page 9Fh, bytes 134-247.
TELEMETRY_INFO_FIELD = "TelemetryInfoField"
RPL_LEN = "TelemetryRplLen"

# Access Remote Byte (CDB 0x8001) reply field -- page 9Fh, byte
# cdb_consts.RPL_DATA_START_OFFSET (136).
REMOTE_BYTE_FIELD = "RemoteByteField"
REMOTE_BYTE_VALUE = "remote_byte_value"

# Access Remote Page (CDB 0x8002) reply field -- page 9Fh, starting at byte
# cdb_consts.RPL_DATA_START_OFFSET (136). Sized to REMOTE_PAGE_DATA_SIZE (see
# cdb_credo.py), the largest chunk that fits in one LPL command alongside its
# target/side/dport/page/rw header -- not a full 128-byte EEPROM page.
REMOTE_PAGE_FIELD = "RemotePageField"
REMOTE_PAGE_DATA = "remote_page_data"

HOST = "host"
MEDIA = "media"

LINK_STATUS = "link_status"
SCORE = "score"
ACTIVE_CATEGORIES = "active_categories"
SERIAL_NUMBER = "serial_number"
LINK_DOWN_CNTR = "link_down_cntr"
LINK_UP_TIME = "link_up_time"
MODULE_FLAGS = "module_flags"
SNR = "snr"
LTP = "ltp"
EYE1 = "eye1"
EYE2 = "eye2"
EYE3 = "eye3"
TEMPERATURE = "temperature"
VOLTAGE = "voltage"
PRE_FEC_BER = "pre_fec_ber"
POST_FEC_ERRORS = "post_fec_errors"
SHUFFLE_DATA_PATH_ID = "shuffle_data_path_id"
SHUFFLE_IB_DETECTION_STATUS = "shuffle_ib_detection_status"
OPTICAL_TX_POWER_MIN = "optical_tx_power_min"
OPTICAL_TX_POWER_MAX = "optical_tx_power_max"

# Media-only: the CDB reply only populates these when queried with side='media'.
OPTICAL_POWER_FLAGS = "optical_power_flags"
OPTICAL_LASER_BIAS_FLAGS = "optical_laser_bias_flags"
MPI = "mpi"
# No CDB reply field is ever decoded for this suffix -- the vendor CDB spec
# doesn't document a distinct byte/bit range for it beyond the single MPI
# flag byte -- so it always stays at its 'N/A' default from _telemetry_na_dict.
MPI_VALUE = "mpi_value"
OPTICAL_RX_POWER_MIN = "optical_rx_power_min"
OPTICAL_RX_POWER_MAX = "optical_rx_power_max"

NUM_FEC_BINS = 16
FEC_BIN_PREFIX = "fec_bin_"

# Suffixes decoded from both a host-side and a media-side query (each side's
# reply gets its own telemetry_host_*/telemetry_media_* key).
COMMON_SUFFIXES = [
    LINK_STATUS, SCORE, ACTIVE_CATEGORIES, SERIAL_NUMBER, LINK_DOWN_CNTR,
    LINK_UP_TIME, MODULE_FLAGS, SNR, LTP, EYE1, EYE2, EYE3, TEMPERATURE,
    VOLTAGE, PRE_FEC_BER, POST_FEC_ERRORS, SHUFFLE_DATA_PATH_ID,
    SHUFFLE_IB_DETECTION_STATUS, OPTICAL_TX_POWER_MIN, OPTICAL_TX_POWER_MAX,
] + ["{}{}".format(FEC_BIN_PREFIX, i) for i in range(NUM_FEC_BINS)]

# Suffixes only ever decoded on a media-side query (no telemetry_host_* key exists).
MEDIA_ONLY_SUFFIXES = [
    OPTICAL_POWER_FLAGS, OPTICAL_LASER_BIAS_FLAGS, MPI, MPI_VALUE,
    OPTICAL_RX_POWER_MIN, OPTICAL_RX_POWER_MAX,
]


def _field(side, lane, suffix):
    return "telemetry_{}_lane{}_{}".format(side, lane, suffix)


def host_field(lane, suffix):
    """Return the TRANSCEIVER_DOM_REAL_VALUE field name for host *lane* (1-based) telemetry *suffix*."""
    return _field(HOST, lane, suffix)


def media_field(lane, suffix):
    """Return the TRANSCEIVER_DOM_REAL_VALUE field name for media *lane* (1-based) telemetry *suffix*."""
    return _field(MEDIA, lane, suffix)


def fec_bin_field(side, lane, index):
    """Return the TRANSCEIVER_DOM_REAL_VALUE field name for RS-FEC bin *index* (0-15) on *side*/*lane*."""
    return _field(side, lane, "{}{}".format(FEC_BIN_PREFIX, index))
