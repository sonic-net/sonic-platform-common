from .thermal_action_base import ThermalActionBase, thermal_action


class SetFanSpeedAction(ThermalActionBase):
    """
    Base thermal action class to set speed for fans
    """
    # JSON field definition
    JSON_FIELD_SPEED = 'speed'

    def __init__(self):
        """
        Constructor of SetFanSpeedAction which actually do nothing.
        """
        self.speed = None

    def load_from_json(self, json_obj):
        """
        Construct ControlThermalControlAlgoAction via JSON. JSON example:
            {
                "type": "fan.all.set_speed"
                "speed": "100"
            }
        :param json_obj: A JSON object representing a SetFanSpeedAction action.
        :return:
        """
        if SetFanSpeedAction.JSON_FIELD_SPEED in json_obj:
            self.speed = float(json_obj[SetFanSpeedAction.JSON_FIELD_SPEED])
        else:
            raise ValueError('SetFanSpeedAction missing mandatory field {} in policy.json'.
                             format(SetFanSpeedAction.JSON_FIELD_SPEED))


@thermal_action('fan.all.set_speed')
class SetAllFanSpeedAction(SetFanSpeedAction):
    """
    Action to set speed for all fans
    """
    def execute(self, thermal_info_dict):
        """
        Set speed for all fans
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return:
        """
        from .thermal_infos import FanInfo
        if FanInfo.INFO_NAME in thermal_info_dict and isinstance(thermal_info_dict[FanInfo.INFO_NAME], FanInfo):
            fan_info_obj = thermal_info_dict[FanInfo.INFO_NAME]
            for fan in fan_info_obj.get_present_fans():
                fan.set_speed(self.speed)


@thermal_action('thermal_control.control')
class ControlThermalControlAlgoAction(ThermalActionBase):
    """
    Action to control the thermal control algorithm
    """
    # JSON field definition
    JSON_FIELD_STATUS = 'status'

    def __init__(self):
        self.status = True

    def load_from_json(self, json_obj):
        """
        Construct ControlThermalControlAlgoAction via JSON. JSON example:
            {
                "type": "thermal_control.control"
                "status": "true"
            }
        :param json_obj: A JSON object representing a ControlThermalControlAlgoAction action.
        :return:
        """
        if ControlThermalControlAlgoAction.JSON_FIELD_STATUS in json_obj:
            status_str = json_obj[ControlThermalControlAlgoAction.JSON_FIELD_STATUS].lower()
            if status_str == 'true':
                self.status = True
            elif status_str == 'false':
                self.status = False
            else:
                raise ValueError('Invalid {} field value, please specify true of false'.
                                 format(ControlThermalControlAlgoAction.JSON_FIELD_STATUS))
        else:
            raise ValueError('ControlThermalControlAlgoAction '
                             'missing mandatory field {} in policy.json'.
                             format(ControlThermalControlAlgoAction.JSON_FIELD_STATUS))

    def execute(self, thermal_info_dict):
        """
        Disable thermal control algorithm
        :param thermal_info_dict: A dictionary stores all thermal information.
        :return:
        """
        import sonic_platform.platform
        chassis = sonic_platform.platform.Platform().get_chassis()
        thermal_manager = chassis.get_thermal_manager()
        if self.status:
            thermal_manager.start_thermal_control_algorithm()
        else:
            thermal_manager.stop_thermal_control_algorithm()


