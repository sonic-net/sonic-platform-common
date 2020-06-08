class ThermalJsonObject(object):
    """
    Base class for thermal json object. 
    """
    # JSON field definition
    JSON_FIELD_TYPE = 'type'

    # Dictionary of ThermalJsonObject-derived class representing all thermal json types
    _object_type_dict = {}

    def load_from_json(self, json_obj):
        """
        Initialize this object by a json object. The json object is read from policy json file.
        Derived class can define any field in policy json file and interpret them in this function.
        :param json_obj: A json object representing an object.
        :return:
        """
        pass

    def __eq__(self, other):
        """
        Compare input object with this object, return True if equal. Subclass should override this
        if necessary.
        :param other: Object to compare with.
        :return: True if equal else False
        """
        return self.__class__ == other.__class__

    @classmethod
    def register_concrete_type(cls, type_name, object_type):
        """
        Register a concrete class by type name. The concrete class must derive from
        ThermalJsonObject.
        :param type_name: Name of the class.
        :param object_type: A concrete class.
        :return:
        """
        if type_name not in cls._object_type_dict:
            cls._object_type_dict[type_name] = object_type
        else:
            raise Exception('ThermalJsonObject type {} already exists'.format(type_name))

    @classmethod
    def get_type(cls, json_obj):
        """
        Get a concrete class by json object. The json object represents an object and must
        have a 'type' field. This function returns a pre-registered concrete class if the specific
        'type' is found.
        :param json_obj: A json object representing an action.
        :return: A concrete class if requested type exists; Otherwise None.
        """
        if ThermalJsonObject.JSON_FIELD_TYPE in json_obj:
            type_str = json_obj[ThermalJsonObject.JSON_FIELD_TYPE]
            if type_str in cls._object_type_dict:
                return cls._object_type_dict[type_str]
            else:
                raise Exception('ThermalJsonObject type {} not found'.format(type_str) )

        raise Exception('Invalid policy file, {} field must be presented'.format(ThermalJsonObject.JSON_FIELD_TYPE))


def thermal_json_object(type_name):
    """
    Decorator to auto register a ThermalJsonObject-derived class
    :param type_name: Type name of the concrete class which corresponding to the 'type' field of
    a condition, action or info.
    :return: Wrapper function
    """
    def wrapper(object_type):
        ThermalJsonObject.register_concrete_type(type_name, object_type)
        return object_type
    return wrapper
