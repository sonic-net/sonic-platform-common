import json
from .thermal_policy import ThermalPolicy
from .thermal_json_object import ThermalJsonObject


class ThermalManagerBase(object):
    """
    Base class of ThermalManager representing a manager to control all thermal policies.
    """
    # JSON field definition.
    JSON_FIELD_POLICIES = 'policies'
    JSON_FIELD_INFO_TYPES = 'info_types'
    JSON_FIELD_POLICY_NAME = 'name'
    JSON_FIELD_THERMAL_ALGORITHM = "thermal_control_algorithm"
    JSON_FIELD_FAN_SPEED_WHEN_SUSPEND = "fan_speed_when_suspend"
    JSON_FIELD_RUN_AT_BOOT_UP = "run_at_boot_up"
    JSON_FIELD_INTERVAL = "interval"

    # Dictionary of ThermalPolicy objects.
    _policy_dict = {}

    # Dictionary of thermal information objects. A thermal information object is used by Thermal Policy
    _thermal_info_dict = {}

    _fan_speed_when_suspend = None

    _run_thermal_algorithm_at_boot_up = None

    _interval = 60

    @classmethod
    def initialize(cls):
        """
        Initialize thermal manager, including register thermal condition types and thermal action types
        and any other vendor specific initialization.
        :return:
        """
        pass

    @classmethod
    def deinitialize(cls):
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
        Load all thermal policies from JSON policy file. An example looks like:
        {
          "thermal_control_algorithm": {
            "run_at_boot_up": "false",
            "fan_speed_when_suspend": "60"
          },
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
          ],
          "interval": "30",
        }
        :param policy_file_name: Path of JSON policy file.
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
                    info_type = ThermalJsonObject.get_type(json_info)
                    info_obj = info_type()
                    cls._thermal_info_dict[json_info[ThermalJsonObject.JSON_FIELD_TYPE]] = info_obj

            if cls.JSON_FIELD_THERMAL_ALGORITHM in json_obj:
                json_thermal_algorithm_config = json_obj[cls.JSON_FIELD_THERMAL_ALGORITHM]
                if cls.JSON_FIELD_RUN_AT_BOOT_UP in json_thermal_algorithm_config:
                    cls._run_thermal_algorithm_at_boot_up = \
                        True if json_thermal_algorithm_config[cls.JSON_FIELD_RUN_AT_BOOT_UP].lower() == 'true' else False

                if cls.JSON_FIELD_FAN_SPEED_WHEN_SUSPEND in json_thermal_algorithm_config:
                    # if the string is not a valid int, let it raise
                    cls._fan_speed_when_suspend = \
                        int(json_thermal_algorithm_config[cls.JSON_FIELD_FAN_SPEED_WHEN_SUSPEND])

            if cls.JSON_FIELD_INTERVAL in json_obj:
               cls._interval = int(json_obj[cls.JSON_FIELD_INTERVAL])


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
                raise Exception('Policy {} already exists'.format(name))

            policy = ThermalPolicy()
            policy.load_from_json(json_policy)
            policy.validate_duplicate_policy(cls._policy_dict.values())
            cls._policy_dict[name] = policy
        else:
            raise Exception('{} not found in policy'.format(cls.JSON_FIELD_POLICY_NAME))

    @classmethod
    def run_policy(cls, chassis):
        """
        Collect thermal information, run each policy, if one policy matches, execute the policy's action.
        :param chassis: The chassis object.
        :return:
        """
        if not cls._policy_dict:
            return

        cls._collect_thermal_information(chassis)

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

    @classmethod
    def init_thermal_algorithm(cls, chassis):
        """
        Initialize thermal algorithm according to policy file.
        :param chassis: The chassis object.
        :return:
        """
        if cls._run_thermal_algorithm_at_boot_up is not None:
            if cls._run_thermal_algorithm_at_boot_up:
                cls.start_thermal_control_algorithm()
            else:
                cls.stop_thermal_control_algorithm()
                if cls._fan_speed_when_suspend is not None:
                    for fan in chassis.get_all_fans():
                        fan.set_speed(cls._fan_speed_when_suspend)

                    for psu in chassis.get_all_psus():
                        for fan in psu.get_all_fans():
                            fan.set_speed(cls._fan_speed_when_suspend)

    @classmethod
    def get_interval(cls):
        """
        Get the wait interval for executing thermal policies
        """
        return cls._interval
