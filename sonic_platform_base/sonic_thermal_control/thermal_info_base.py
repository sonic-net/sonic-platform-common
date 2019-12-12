class ThermalInfoBase(object):
    """
    Base class for thermal information
    """
    # JSON field definition
    JSON_FIELD_INFO_TYPE = 'type'

    # Dictionary of ThermalActionBase-derived class representing all thermal action types
    _info_type_dict = {}

    def collect(self, chassis):
        """
        Collect thermal information for thermal policy.
        :param chassis: The chassis object.
        :return:
        """
        raise NotImplementedError

    def load_from_json(self, json_obj):
        """
        Initialize this object by a json object. The json object is read from policy.json section 'info_types'.
        Derived class can define any field in policy.json and interpret them in this function.
        :param json_obj: A json object representing an thermal information.
        :return:
        """
        pass

    @classmethod
    def register_type(cls, type_name, info_type):
        """
        Register a concrete information class by type name. The concrete information class must derive from
        ThermalInfoBase or have exactly the same member function 'collect'
        For any concrete information class, it must be registered explicitly.
        :param type_name: Type name of the information class.
        :param info_type: A concrete information class.
        :return:
        """
        if type_name not in cls._info_type_dict:
            cls._info_type_dict[type_name] = info_type
        else:
            raise KeyError('ThermalInfo type {} already exists'.format(type_name))

    @classmethod
    def get_type(cls, json_obj):
        """
        Get a concrete information class by json object. The json object represents an information object and must
        have a 'type' field. This function returns a pre-registered concrete information class if the specific
        'type' is found.
        :param json_obj: A json object representing an information.
        :return: A concrete information class if requested type exists; Otherwise None.
        """
        if ThermalInfoBase.JSON_FIELD_INFO_TYPE in json_obj:
            type_str = json_obj[ThermalInfoBase.JSON_FIELD_INFO_TYPE]
            return cls._info_type_dict[type_str] if type_str in cls._info_type_dict else None

        return None


def thermal_info(type_name):
    """
    Decorator to auto register a ThermalInfoBase-derived class
    :param type_name: Type name of the information class
    :return: Wrapper function
    """
    def wrapper(info_type):
        ThermalInfoBase.register_type(type_name, info_type)
        return info_type
    return wrapper
