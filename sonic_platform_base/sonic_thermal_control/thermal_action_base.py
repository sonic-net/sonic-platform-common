from .thermal_json_object import ThermalJsonObject


class ThermalPolicyActionBase(ThermalJsonObject):
    """
    Base class for thermal action. Once all thermal conditions in a thermal policy are matched,
    all predefined thermal action will be executed.
    """
    def execute(self, thermal_info_dict):
        """
        Take action when thermal condition matches. For example, adjust speed of fan or shut
        down the switch.
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return:
        """
        raise NotImplementedError

