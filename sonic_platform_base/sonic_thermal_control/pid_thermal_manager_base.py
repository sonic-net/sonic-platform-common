"""
Thermal manager base for platforms that use the shared PID policy types.

A platform subclasses PidThermalManagerBase, sets SYSLOG_IDENTIFIER if the default does not
suit, and ships a thermal_policy.json and thermal_config.json. Subclassing is the opt-in that
common_infos describes: importing this module registers the common info, condition and action
types, so a platform built on it must not register the same type names itself.

If the policy file fails to load, or a policy pass raises, the manager drives every fan to
full speed: thermalctld only logs these errors and never sets fan speeds itself.
"""

import logging
import logging.handlers

from . import common_actions  # also registers the action types
from . import common_conditions  # noqa: F401  (registers the condition types)
from . import common_infos  # noqa: F401  (registers the info types)
from .thermal_manager_base import ThermalManagerBase

# The shared modules log through loggers under this package's name.
COMMON_LOGGER = __package__

SYSLOG_ADDRESS = '/dev/log'

# Fan speed in percent when the policies cannot run.
FAIL_SAFE_SPEED = 100

_logger = logging.getLogger(__name__)


class PidThermalManagerBase(ThermalManagerBase):
    """
    ThermalManagerBase that registers the common policy types, sends the shared modules'
    logging to syslog, and runs the fans at full speed when the policies cannot run.
    """
    # Tag put in front of the shared modules' syslog messages.
    SYSLOG_IDENTIFIER = 'thermalctld'

    # The exception from the last load(), or None if it succeeded.
    _load_error = None

    @classmethod
    def initialize(cls):
        """
        Route the shared thermal modules' logging to syslog. Subclasses that override this
        should call super().initialize().
        :return: True
        """
        cls._route_common_logging_to_syslog()
        return True

    @classmethod
    def _route_common_logging_to_syslog(cls):
        """
        The shared modules log through the standard library rather than a vendor logger, so
        point that namespace at syslog under SYSLOG_IDENTIFIER to keep fan and PID messages
        with the rest of the platform's logs. The handler is added only once.
        """
        logger = logging.getLogger(COMMON_LOGGER)
        if any(isinstance(h, logging.handlers.SysLogHandler) for h in logger.handlers):
            return
        try:
            handler = logging.handlers.SysLogHandler(address=SYSLOG_ADDRESS)
        except OSError:
            # No syslog socket, as in a unit test container. Leave the default handlers.
            return
        handler.setFormatter(
            logging.Formatter(cls.SYSLOG_IDENTIFIER + ': %(name)s: %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    @classmethod
    def load(cls, policy_file_name):
        """
        Load the policy file. On failure, remember it so run_policy() holds the fans at full
        speed rather than running no or partial policies, then re-raise for thermalctld to log.
        """
        cls._load_error = None
        try:
            super().load(policy_file_name)
        except Exception as exc:
            cls._load_error = exc
            _logger.error('failed to load %s, holding fans at %d%%: %s',
                          policy_file_name, FAIL_SAFE_SPEED, exc)
            raise

    @classmethod
    def run_policy(cls, chassis):
        """
        Run the policies, or drive the fans to full speed if the policy file did not load. If a
        pass raises, drive the fans to full speed and re-raise for thermalctld to log.
        """
        if cls._load_error is not None:
            cls._set_fail_safe_speed(chassis)
            return
        try:
            super().run_policy(chassis)
        except Exception as exc:
            _logger.error('thermal policy failed, going to %d%%: %s', FAIL_SAFE_SPEED, exc)
            cls._set_fail_safe_speed(chassis)
            raise

    @classmethod
    def _set_fail_safe_speed(cls, chassis):
        """
        Set every fan to full speed. Errors are logged, not raised, so they never replace the
        error that led here.
        """
        try:
            common_actions.set_all_fan_speeds(chassis.get_all_fans(), FAIL_SAFE_SPEED, _logger)
        except Exception as exc:
            _logger.error('fail-safe fan speed also failed: %s', exc)
