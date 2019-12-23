from .thermal_json_object import ThermalJsonObject


class ThermalPolicyConditionBase(ThermalJsonObject):
    """
    Base class for thermal condition
    """
    def is_match(self, thermal_info_dict):
        """
        Indicate if this condition is matched.
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return: True if condition matched else False.
        """
        raise NotImplementedError
