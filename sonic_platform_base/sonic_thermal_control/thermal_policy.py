from .thermal_json_object import ThermalJsonObject


class ThermalPolicy(object):
    """
    Class representing a thermal policy. A thermal policy object is initialized by policy.json.
    """
    # JSON field definition.
    JSON_FIELD_NAME = 'name'
    JSON_FIELD_CONDITIONS = 'conditions'
    JSON_FIELD_ACTIONS = 'actions'

    def __init__(self):
        # Name of the policy
        self.name = None

        # Conditions load from policy.json
        self.conditions = []

        # Actions load from policy.json
        self.actions = []

    def load_from_json(self, json_obj):
        """
        Load thermal policy from policy.json.
        :param json_obj: A json object representing a thermal policy.
        :return:
        """
        if self.JSON_FIELD_NAME in json_obj:
            self.name = json_obj[self.JSON_FIELD_NAME]

            if self.JSON_FIELD_CONDITIONS in json_obj:
                for json_condition in json_obj[self.JSON_FIELD_CONDITIONS]:
                    cond_type = ThermalJsonObject.get_type(json_condition)
                    cond_obj = cond_type()
                    cond_obj.load_from_json(json_condition)
                    self.conditions.append(cond_obj)

            if self.JSON_FIELD_ACTIONS in json_obj:
                for json_action in json_obj[self.JSON_FIELD_ACTIONS]:
                    action_type = ThermalJsonObject.get_type(json_action)
                    action_obj = action_type()
                    action_obj.load_from_json(json_action)
                    self.actions.append(action_obj)
        else:
            raise Exception('name field not found in policy')

    def is_match(self, thermal_info_dict):
        """
        Indicate if this policy is match.
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return: True if all conditions matches else False.
        """
        for condition in self.conditions:
            if not condition.is_match(thermal_info_dict):
                return False

        return True

    def do_action(self, thermal_info_dict):
        """
        Execute all actions if is_match returns True.
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return:
        """
        for action in self.actions:
            action.execute(thermal_info_dict)
