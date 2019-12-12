class ThermalConditionBase(object):
    """
    Base class for thermal condition
    """
    # JSON field definition
    JSON_FIELD_CONDITION_TYPE = 'type'

    # Dictionary of ThermalConditionBase-derived class representing all thermal condition types.
    _condition_type_dict = {}

    def is_match(self, thermal_info_dict):
        """
        Indicate if this condition is matched.
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return: True if condition matched else False.
        """
        raise NotImplementedError

    def load_from_json(self, json_obj):
        """
        Initialize this object by a json object. The json object is read from policy.json section 'conditions'.
        Derived class can define any field in policy.json and interpret them in this function.
        :param json_obj: A json object representing a condition.
        :return:
        """
        pass

    @classmethod
    def get_type(cls, json_obj):
        """
        Get a concrete condition class by json object. The json object represents a condition object and must
        have a 'type' field. This function returns a pre-registered concrete condition class if the specific
        'type' is found.
        :param json_obj: A json object representing a condition.
        :return: A concrete condition class if requested type exists; Otherwise None.
        """
        if ThermalConditionBase.JSON_FIELD_CONDITION_TYPE in json_obj:
            type_name = json_obj[ThermalConditionBase.JSON_FIELD_CONDITION_TYPE]
            return cls._condition_type_dict[type_name] if type_name in cls._condition_type_dict else None

        return None

    @classmethod
    def register_type(cls, type_name, condition_type):
        """
        Register a concrete condition class by type name. The concrete condition class must derive from
        ThermalConditionBase or have exactly the same member function 'is_match' and 'load_from_json'.
        For any concrete condition class, it must be registered explicitly.
        :param type_name: Type name of the condition class which corresponding to the 'type' field of
        a condition in policy.json.
        :param condition_type: A concrete condition class.
        :return:
        """
        if type_name not in cls._condition_type_dict:
            cls._condition_type_dict[type_name] = condition_type
        else:
            raise KeyError('ThermalCondition type {} already exists'.format(type_name))


def thermal_condition(type_name):
    """
    Decorator to auto register a ThermalConditionBase-derived class
    :param type_name: Type name of the condition class which corresponding to the 'type' field of
    a condition in policy.json.
    :return: Wrapper function
    """
    def wrapper(condition_type):
        ThermalConditionBase.register_type(type_name, condition_type)
        return condition_type
    return wrapper
