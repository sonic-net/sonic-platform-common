"""Public ELSFP API contract for separate and combined OE/ELS devices."""

from ..xcvr_api import XcvrApi


class ElsfpApiBase(XcvrApi):
    """Optional ELS operations raise NotImplementedError until implemented.

    ELS module controls have explicit ELSFP names so a combined OE/ELS API
    cannot accidentally inherit the OE's reset, low-power, or state methods.
    """

    def get_elsfp_info(self):
        """Return a dictionary of ELS module identity fields, or None on read failure."""
        raise NotImplementedError("ELS module information is not implemented")

    def get_elsfp_status(self):
        """Return a dictionary of supported ELS status fields, or None on read failure."""
        raise NotImplementedError("ELS status is not implemented")

    def get_elsfp_module_state(self):
        """Return the independent ELS module state string, or None on read failure."""
        raise NotImplementedError("Independent ELS module state is not implemented")

    def get_elsfp_dom_real_value(self):
        """Return a dictionary of ELS module monitor values, or None on read failure."""
        raise NotImplementedError("ELS module monitors are not implemented")

    def get_elsfp_threshold_info(self):
        """Return a dictionary of ELS monitor thresholds, or None on read failure."""
        raise NotImplementedError("ELS monitor thresholds are not implemented")

    def get_per_lane_bias_current_monitor(self):
        """Return per-lane bias current monitors, or None on read failure."""
        raise NotImplementedError("ELS per-lane bias monitoring is not implemented")

    def get_per_lane_opt_power_monitor(self):
        """Return per-lane optical powers in mW, or None on read failure."""
        raise NotImplementedError("ELS per-lane optical power monitoring is not implemented")

    def get_per_lane_voltage_monitor(self):
        """Return per-lane voltages in volts, or None on read failure."""
        raise NotImplementedError("ELS per-lane voltage monitoring is not implemented")

    def set_elsfp_lpmode(self, low_power):
        """Set ELS low-power mode (True) or full power (False); return success."""
        raise NotImplementedError("ELS low-power control is not implemented")

    def reset_elsfp(self):
        """Reset only the ELS module; return True on success or False on failure."""
        raise NotImplementedError("ELS reset is not implemented")

    def set_per_lane_enable(self, lane_mask, enabled):
        """Enable/disable selected lasers; bit 0 is the first lane in this bank.

        Return True on success or False on failure. Unsupported platforms
        inherit this placeholder, which performs no EEPROM writes.
        """
        raise NotImplementedError("ELS per-lane enable control is not implemented")

    def supports_per_lane_enable(self):
        """Report a control implementation without performing a hardware write.

        This allows callers to reject an unsupported combined OE/ELS operation
        before changing either device. Platforms may override this query when
        support also depends on hardware capabilities.
        """
        return type(self).set_per_lane_enable is not ElsfpApiBase.set_per_lane_enable

    def get_per_lane_state(self):
        """Return a dictionary of ELS laser states, or None on read failure."""
        raise NotImplementedError("ELS per-lane state is not implemented")
