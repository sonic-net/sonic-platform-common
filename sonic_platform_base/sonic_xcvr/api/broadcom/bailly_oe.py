"""CMIS API for a Bailly optical engine, independent of its ELS endpoints."""
from ...cpo.cmis import CpoCmisApi


class BaillyOeApi(CpoCmisApi):
    """Use community banked/non-banked OE APIs with Bailly CMIS workarounds."""

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
