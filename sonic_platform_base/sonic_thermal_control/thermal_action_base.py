class ThermalPolicyActionBase(object):
    """
    Base class for thermal action. Once all thermal conditions in a thermal policy are matched,
    all predefined thermal action would be executed.
    """
    # JSON field definition
    JSON_FIELD_ACTION_TYPE = 'type'

    # Dictionary of ThermalPolicyActionBase-derived class representing all thermal action types
    _action_type_dict = {}

    def execute(self, thermal_info_dict):
        """
        Take action when thermal condition matches. For example, adjust speed of fan or shut
        down the switch.
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return:
        """
        raise NotImplementedError

    def load_from_json(self, json_obj):
        """
        Initialize this object by a json object. The json object is read from policy.json section 'actions'.
        Derived class can define any field in policy.json and interpret them in this function.
        :param json_obj: A json object representing an action.
        :return:
        """
        pass

    @classmethod
    def register_concrete_action_type(cls, type_name, action_type):
        """
        Register a concrete action class by type name. The concrete action class must derive from
        ThermalPolicyActionBase or have exactly the same member function 'execute' and 'load_from_json'.
        For any concrete action class, it must be registered explicitly.
        :param type_name: Type name of the action class which corresponding to the 'type' field of
        an action in policy.json.
        :param action_type: A concrete action class.
        :return:
        """
        if type_name not in cls._action_type_dict:
            cls._action_type_dict[type_name] = action_type
        else:
            raise KeyError('ThermalAction type {} already exists'.format(type_name))

    @classmethod
    def get_type(cls, json_obj):
        """
        Get a concrete action class by json object. The json object represents a action object and must
        have a 'type' field. This function returns a pre-registered concrete action class if the specific
        'type' is found.
        :param json_obj: A json object representing an action.
        :return: A concrete action class if requested type exists; Otherwise None.
        """
        if ThermalPolicyActionBase.JSON_FIELD_ACTION_TYPE in json_obj:
            type_str = json_obj[ThermalPolicyActionBase.JSON_FIELD_ACTION_TYPE]
            return cls._action_type_dict[type_str] if type_str in cls._action_type_dict else None

        return None


def thermal_action(type_name):
    """
    Decorator to auto register a ThermalPolicyActionBase-derived class
    :param type_name: Type name of the action class which corresponding to the 'type' field of
    a action in policy.json.
    :return: Wrapper function
    """
    def wrapper(action_type):
        ThermalPolicyActionBase.register_concrete_action_type(type_name, action_type)
        return action_type
    return wrapper
