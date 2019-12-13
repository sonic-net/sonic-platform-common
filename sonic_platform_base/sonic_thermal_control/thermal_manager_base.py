import json
from .thermal_policy import ThermalPolicy
from .thermal_info_base import ThermalInfoBase


class ThermalManagerBase(object):
    """
    Base class of ThermalManager representing a manager to control all thermal policies.
    """
    # JSON field definition.
    JSON_FIELD_POLICIES = 'policies'
    JSON_FIELD_INFO_TYPES = 'info_types'
    JSON_FIELD_POLICY_NAME = 'name'

    # Dictionary of ThermalPolicy objects.
    _policy_dict = {}

    # Dictionary of thermal information objects. A thermal information object is used by Thermal Policy
    _thermal_info_dict = {}

    @classmethod
    def initialize(cls):
        """
        Initialize thermal manager, including register thermal condition types and thermal action types
        and any other vendor specific initialization. The default behavior of this function is a no-op.
        :return:
        """
        pass

    @classmethod
    def destroy(cls):
        """
        Destroy thermal manager, including any vendor specific cleanup. The default behavior of this function 
        is a no-op.
        :return:
        """
        pass

    @classmethod
    def start_thermal_control_algorithm(cls):
        """
        Start vendor specific thermal control algorithm. The default behavior of this function is a no-op.
        :return:
        """
        pass

    @classmethod
    def stop_thermal_control_algorithm(cls):
        """
        Stop vendor specific thermal control algorithm. The default behavior of this function is a no-op.
        :return:
        """
        pass

    @classmethod
    def load(cls, policy_file_name):
        """
        Load all thermal policies from policy.json file. An example looks like:
        {
          "info_types": [
            {
              "type": "fan_info" # collect fan information for each iteration
            },
            {
              "type": "psu_info" # collect psu information for each iteration
            }
          ],
          "policies": [
            {
              "name": "any fan absence", # if any fan absence, set all fan speed to 100% and disable thermal control algorithm
              "conditions": [
                {
                  "type": "fan.any.absence" # see sonic-platform-daemons.sonic-thermalctld.thermal_policy.thermal_conditions
                }
              ],
              "actions": [
                {
                  "type": "fan.all.set_speed", # see sonic-platform-daemons.sonic-thermalctld.thermal_policy.thermal_actions
                  "speed": "100"
                },
                {
                  "type": "thermal_control.control",
                  "status": "false"
                }
              ]
            },
            {
              "name": "all fan absence", # if all fan absence, shutdown the switch
              "conditions": [
                {
                  "type": "fan.all.absence"
                }
              ],
              "actions": [
                {
                  "type": "switch.shutdown"
                }
              ]
            }
          ]
        }
        :param policy_file_name: Path of policy.json.
        :return:
        """
        with open(policy_file_name, 'r') as policy_file:
            json_obj = json.load(policy_file)
            if cls.JSON_FIELD_POLICIES in json_obj:
                json_policies = json_obj[cls.JSON_FIELD_POLICIES]
                for json_policy in json_policies:
                    cls._load_policy(json_policy)

            if cls.JSON_FIELD_INFO_TYPES in json_obj:
                for json_info in json_obj[cls.JSON_FIELD_INFO_TYPES]:
                    info_type = ThermalInfoBase.get_type(json_info)
                    if info_type:
                        info_obj = info_type()
                        cls._thermal_info_dict[json_info[ThermalInfoBase.JSON_FIELD_INFO_TYPE]] = info_obj
                    else:
                        raise KeyError('Invalid thermal information defined in policy file')

    @classmethod
    def _load_policy(cls, json_policy):
        """
        Load a policy object from a JSON object.
        :param json_policy: A JSON object representing a thermal policy.
        :return:
        """
        if cls.JSON_FIELD_POLICY_NAME in json_policy:
            name = json_policy[cls.JSON_FIELD_POLICY_NAME]
            if name in cls._policy_dict:
                raise KeyError('Policy {} already exists'.format(name))

            policy = ThermalPolicy()
            policy.load_from_json(json_policy)
            cls._policy_dict[name] = policy
        else:
            raise KeyError('{} not found in policy'.format(cls.JSON_FIELD_POLICY_NAME))

    @classmethod
    def run_policy(cls):
        """
        Collect thermal information, run each policy, if one policy matches, execute the policy's action.
        :return:
        """
        if not cls._policy_dict:
            return

        cls._collect_thermal_information()

        for policy in cls._policy_dict.values():
            if policy.is_match(cls._thermal_info_dict):
                policy.do_action(cls._thermal_info_dict)

    @classmethod
    def _collect_thermal_information(cls, chassis):
        """
        Collect thermal information. This function will be called before run_policy.
        :param chassis: The chassis object.
        :return:
        """
        for thermal_info in cls._thermal_info_dict.values():
            thermal_info.collect(chassis)
