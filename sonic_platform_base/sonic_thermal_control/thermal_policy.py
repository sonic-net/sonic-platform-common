from .thermal_json_object import ThermalJsonObject
from collections import OrderedDict


class ThermalPolicy(object):
    """
    Class representing a thermal policy. A thermal policy object is initialized by JSON policy file.
    """
    # JSON field definition.
    JSON_FIELD_NAME = 'name'
    JSON_FIELD_CONDITIONS = 'conditions'
    JSON_FIELD_ACTIONS = 'actions'

    def __init__(self):
        # Name of the policy
        self.name = None

        # Conditions load from JSON policy file
        self.conditions = OrderedDict()

        # Actions load from JSON policy file
        self.actions = OrderedDict()

    def load_from_json(self, json_obj):
        """
        Load thermal policy from JSON policy file.
        :param json_obj: A json object representing a thermal policy.
        :return:
        """
        if self.JSON_FIELD_NAME in json_obj:
            self.name = json_obj[self.JSON_FIELD_NAME]

            if self.JSON_FIELD_CONDITIONS in json_obj:
                for json_condition in json_obj[self.JSON_FIELD_CONDITIONS]:
                    cond_type = ThermalJsonObject.get_type(json_condition)
                    if cond_type in self.conditions:
                        raise Exception('Duplicate thermal condition type detected in policy [{}]!'.format(self.name))
                    cond_obj = cond_type()
                    cond_obj.load_from_json(json_condition)
                    self.conditions[cond_type] = cond_obj

            if self.JSON_FIELD_ACTIONS in json_obj:
                for json_action in json_obj[self.JSON_FIELD_ACTIONS]:
                    action_type = ThermalJsonObject.get_type(json_action)
                    if action_type in self.actions:
                        raise Exception('Duplicate thermal action type detected in policy [{}]!'.format(self.name))
                    action_obj = action_type()
                    action_obj.load_from_json(json_action)
                    self.actions[action_type] = action_obj
                
            if not len(self.conditions) or not len(self.actions):
                raise Exception('A policy requires at least 1 action and 1 condition')
        else:
            raise Exception('name field not found in policy')

    def is_match(self, thermal_info_dict):
        """
        Indicate if this policy is match.
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return: True if all conditions matches else False.
        """
        for condition in self.conditions.values():
            if not condition.is_match(thermal_info_dict):
                return False

        return True

    def do_action(self, thermal_info_dict):
        """
        Execute all actions if is_match returns True.
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return:
        """
        for action in self.actions.values():
            action.execute(thermal_info_dict)

    def validate_duplicate_policy(self, policies):
        """
        Detect this policy with existing policies, if a policy with same conditions exists, raise Exception.
        :param policies: existing policies.
        :return:
        """
        for policy in policies:
            if len(policy.conditions) != len(self.conditions):
                continue

            for cond_type, value in policy.conditions.items():
                if cond_type in self.conditions and policy.conditions[cond_type] == self.conditions[cond_type]:
                    raise Exception('Policy [{}] and policy [{}] have duplicate conditions'.format(policy.name, self.name))
