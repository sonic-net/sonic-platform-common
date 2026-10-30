"""CMIS API for a Bailly optical engine, independent of its ELS endpoints."""
import time

from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_py_common import syslogger

from ...cpo.cmis import CpoCmisApi

SYSLOG_IDENTIFIER = "bailly_api"
# Global logger instance
helper_logger = syslogger.SysLogger(SYSLOG_IDENTIFIER)


def log_debug(message):
    helper_logger.log_debug(message)


def log_notice(message):
    helper_logger.log_notice(message)


def log_error(message):
    helper_logger.log_error(message)


def _to_hex(data):
    """
    Format a raw register buffer as a space separated hex string for logging.

    Args:
        data:
            bytes/bytearray/tuple/list of integers, or None

    Returns:
        String, e.g. "00 01 0f"; "None" if data is None
    """
    if data is None:
        return "None"
    return " ".join("{:02x}".format(byte) for byte in bytearray(data))


class BaillyOeApi(CpoCmisApi):
    """Use community banked/non-banked OE APIs with Bailly CMIS workarounds."""

    # Bailly CPO Staged Control Set (Page 10h) programming.
    # StagedCtrlApSel holds one byte per host lane with this layout:
    #   bit 7-4: application code
    #   bit 3  : lane group selector (see _appl_sel_lane_group)
    #   bit 0  : EC (Explicit Control)
    APPL_SEL_CODE_SHIFT = 4
    APPL_SEL_LANE_GROUP_SHIFT = 1
    APPL_SEL_CODE_MAX = 0xf
    # Number of host lanes per lane group (lane0-3 / lane4-7)
    LANES_PER_LANE_GROUP = 4
    # Application code of the 800G application, where the lane group bit stays 0
    APPL_CODE_800G = 6
    # Policy of the ApSel block read-back verification
    APPLY_VERIFY_MAX_RETRY = 3
    APPLY_VERIFY_RETRY_DELAY_SEC = 0.1
    # Settle time after applying DataPathInit
    DPINIT_SETTLE_DELAY_SEC = 0.01

    def get_dpinit_pending(self):
        # Bailly does not report DPInitPending; preserve its provisioning behavior.
        return {"DPInitPending{}".format(lane + 1): True for lane in range(self.NUM_CHANNELS)}

    def get_active_apsel_hostlane(self):
        # A configured AppSel 0 is not supported by Bailly's active-AppSel report.
        current = {"ActiveAppSelLane{}".format(lane + 1): self.get_application(lane)
                   for lane in range(self.NUM_CHANNELS)}
        if 0 in current.values():
            return current
        return super().get_active_apsel_hostlane()

    def get_laser_temperature(self):
        # No OE laser-temperature monitor is provided by Bailly.
        return None

    def get_non_banked_transceiver_dom_real_value(self):
        # The generic CPO aggregate expects an auxiliary laser temperature;
        # Bailly has no such OE monitor and must not substitute ELS temperature.
        temperature = self.get_module_temperature()
        voltage = self.get_voltage()
        if temperature is None or voltage is None:
            return None
        return {"temperature": temperature, "voltage": voltage}

    def _get_appl_sel_field(self, lane_id):
        """
        Get the STAGED_CTRL_APSEL field object of one host lane.

        Args:
            lane_id:
                Integer, one-based host lane id (1 .. NUM_CHANNELS)

        Returns:
            Field object, or None if it is not present in the memory map
        """
        field_name = "{}_{}_{}".format(consts.STAGED_CTRL_APSEL_FIELD, 0, lane_id)
        try:
            return self.xcvr_eeprom.mem_map.get_field(field_name)
        except KeyError:
            return None

    def _get_appl_sel_block(self):
        """
        Locate the whole STAGED_CTRL_APSEL block (one byte per host lane).

        Returns:
            Tuple (start_offset, size) on success, (None, None) on failure
        """
        first_field = self._get_appl_sel_field(1)
        last_field = self._get_appl_sel_field(self.NUM_CHANNELS)
        if first_field is None or last_field is None:
            log_error("_get_appl_sel_block: '{}' field not found in memory map".format(
                consts.STAGED_CTRL_APSEL_FIELD))
            return None, None

        start_offset = first_field.get_offset()
        size = last_field.get_offset() + last_field.get_size() - start_offset
        if size != self.NUM_CHANNELS:
            log_error("_get_appl_sel_block: unexpected block size {} (expect {}) at offset {}".format(
                size, self.NUM_CHANNELS, start_offset))
            return None, None

        return start_offset, size

    def _get_all_application_raw(self):
        """
        Read all lanes STAGED_CTRL_APSEL register block once via read_raw.

        Returns:
            bytearray: raw register bytes for all lanes, None on failure
        """
        if self.is_flat_memory():
            log_error("_get_all_application_raw: flat memory, no lane datapath page")
            return None

        start_offset, size = self._get_appl_sel_block()
        if start_offset is None:
            return None

        try:
            raw_buf = self.xcvr_eeprom.read_raw(start_offset, size)
        except Exception as error:
            log_error("_get_all_application_raw: read_raw({}, {}) failed: {}".format(
                start_offset, size, repr(error)))
            return None

        if raw_buf is None:
            log_error("_get_all_application_raw: read_raw({}, {}) returned None".format(
                start_offset, size))
            return None

        raw_buf = bytearray(raw_buf)
        log_debug("_get_all_application_raw: start_addr {}, raw_buf: {}".format(
            start_offset, _to_hex(raw_buf)))
        return raw_buf

    def _appl_sel_lane_group(self, lane, appl_code):
        """
        Compute the lane group bit of one host lane.

        The host lanes are split into groups of LANES_PER_LANE_GROUP lanes
        (lane0-3 / lane4-7); the second group sets the lane group bit, except
        for the 800G application where the bit stays 0 on every lane.

        Args:
            lane:
                Integer, zero-based host lane id
            appl_code:
                Integer, the application code being programmed

        Returns:
            Integer, 0 or LANES_PER_LANE_GROUP
        """
        if lane < self.LANES_PER_LANE_GROUP or appl_code == self.APPL_CODE_800G:
            return 0
        return self.LANES_PER_LANE_GROUP

    def _build_appl_sel_buffer(self, appl_code, ec):
        """
        Build the whole STAGED_CTRL_APSEL block content for one application.

        Args:
            appl_code:
                Integer, the application code
            ec:
                Integer, EC (Explicit Control) bit value

        Returns:
            bytearray, one byte per host lane
        """
        return bytearray(
            (appl_code << self.APPL_SEL_CODE_SHIFT)
            | (self._appl_sel_lane_group(lane, appl_code) << self.APPL_SEL_LANE_GROUP_SHIFT)
            | ec
            for lane in range(self.NUM_CHANNELS)
        )

    def set_application(self, channel, appl_code, ec=0):
        """
        Update the selected application code to the specified lanes on the host side

        Bailly programs the StagedCtrlApSel block as a whole (one byte per host
        lane), so every lane is written with the same appl_code instead of only
        the lanes selected in channel. channel is therefore used to validate the
        request only; the CPO caller (cmis_manager_task) passes the full lane
        mask of the module.

        Args:
            channel:
                Integer, a bitmask of the lanes on the host side
                e.g. 0x5 for lane 0 and lane 2.
            appl_code:
                Integer, the desired application code
            ec:
                Integer, EC bit value

        Returns:
            Boolean, true if success otherwise false
        """
        log_debug("set_application channel {:#x}, appl_code {}, ec {}".format(channel, appl_code, ec))

        if (channel & ((1 << self.NUM_CHANNELS) - 1)) == 0:
            log_error("set_application: no host lane selected for channel {:#x}, appl_code {}".format(
                channel, appl_code))
            return False

        if not 0 <= appl_code <= self.APPL_SEL_CODE_MAX:
            log_error("set_application: invalid appl_code {} for channel {:#x}".format(
                appl_code, channel))
            return False

        start_offset, size = self._get_appl_sel_block()
        if start_offset is None:
            return False

        # Read the whole block first: it validates that page 10h is reachable
        # and logs the state before the update.
        if self._get_all_application_raw() is None:
            log_error("set_application: unable to read ApSel block for channel {:#x}, appl_code {}".format(
                channel, appl_code))
            return False

        write_buf = self._build_appl_sel_buffer(appl_code, ec)
        log_notice("set_application start_offset {}, channel {:#x}, appl_code {}, ec {}, write_buffer: {}".format(
            start_offset, channel, appl_code, ec, _to_hex(write_buf)))

        try:
            if not self.xcvr_eeprom.write_raw(start_offset, size, write_buf):
                log_error("set_application: write_raw failed for channel {:#x}, appl_code {}".format(
                    channel, appl_code))
                return False

            # retry read-back to verify write result
            new_data = None
            for retry_cnt in range(self.APPLY_VERIFY_MAX_RETRY):
                new_data = self._get_all_application_raw()
                if new_data is None:
                    log_error("set_application: verify read failed, retry {}, channel {:#x}, appl_code {}".format(
                        retry_cnt, channel, appl_code))
                    time.sleep(self.APPLY_VERIFY_RETRY_DELAY_SEC)
                    continue

                if new_data == write_buf:
                    log_debug("set_application: verify ok at retry {}, channel {:#x}, appl_code {}".format(
                        retry_cnt, channel, appl_code))
                    return True

                log_debug("set_application: verify retry {}, start_offset {}, raw_buf: {}".format(
                    retry_cnt, start_offset, _to_hex(new_data)))
                time.sleep(self.APPLY_VERIFY_RETRY_DELAY_SEC)

            log_error("set_application: verify failed for channel {:#x}, appl_code {}, expect: {}, actual: {}".format(
                channel, appl_code, _to_hex(write_buf), _to_hex(new_data)))
            return False
        except Exception as error:
            log_error("set_application: unexpected error for channel {:#x}, appl_code {}, {}".format(
                channel, appl_code, repr(error)))
            return False

    def scs_apply_datapath_init(self, channel):
        """
        Apply DataPathInit via the Page 10h staged control set.

        Bailly applies DataPathInit to the whole bank: as soon as any lane is
        selected in channel the full lane mask is written, and 0 is written when
        channel is 0.

        Note:
            The applied bit is a trigger, it is not read back for verification
            because the hardware may self-clear it.

        Args:
            channel:
                Integer, a bitmask of the lanes on the host side

        Returns:
            Boolean, true if the register write succeeded otherwise false
        """
        data = 0 if channel == 0 else (1 << self.NUM_CHANNELS) - 1
        field_name = "%s_%d" % (consts.STAGED_CTRL_APPLY_DPINIT_FIELD, 0)

        try:
            ret = self.xcvr_eeprom.write(field_name, data)
        except Exception as error:
            log_error("scs_apply_datapath_init: write {} failed: {}".format(field_name, repr(error)))
            return False

        if not ret:
            log_error("scs_apply_datapath_init: write {} = {:#x} failed, channel {:#x}".format(
                field_name, data, channel))
            return False

        log_notice("scs_apply_datapath_init: {} set to {:#x}, channel {:#x}".format(
            field_name, data, channel))
        time.sleep(self.DPINIT_SETTLE_DELAY_SEC)
        return True
