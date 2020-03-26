from .thermal_json_object import ThermalJsonObject


class ThermalPolicyInfoBase(object):
    """
    Base class for thermal information
    """
    def collect(self, chassis):
        """
        Collect thermal information for thermal policy.
        :param chassis: The chassis object.
        :return:
        """
        raise NotImplementedError

