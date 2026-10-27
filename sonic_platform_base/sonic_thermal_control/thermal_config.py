"""
Per-platform thermal tunables, loaded separately from the policy file.

The policy file describes structure - which conditions trigger which actions - and changes
rarely. Gains, limits and setpoints are tuned per platform and change often, so they live
here instead of inline in the policy's action blocks.
"""

import json
import os

DEFAULT_CONFIG_DIR = '/usr/share/sonic/platform'
CONFIG_FILE_NAME = 'thermal_config.json'

DEFAULT_FAN_MIN_SPEED = 30.0
DEFAULT_FAN_MAX_SPEED = 100.0

KEY_FAN_LIMITS = 'fan_limits'
KEY_FAN_MIN = 'min'
KEY_FAN_MAX = 'max'
KEY_PID_DOMAINS = 'pid_domains'
KEY_SETPOINT = 'setpoint'

_REQUIRED_GAINS = ('KP', 'KI', 'KD')


class ThermalConfigError(ValueError):
    """Raised when a thermal config file is present but unusable."""


def config_path(config_dir=None):
    return os.path.join(config_dir or DEFAULT_CONFIG_DIR, CONFIG_FILE_NAME)


def load_thermal_config(config_dir=None):
    """
    Return the platform's thermal tunables, or an empty dict when no config file exists.

    An absent file is not an error: callers fall back to whatever the policy file or their
    own defaults provide. A file that exists but is malformed is an error, since silently
    running on defaults would hide a mistuned platform.

    Raises:
        ThermalConfigError: On unreadable JSON or a failed validation check.
    """
    path = config_path(config_dir)
    if not os.path.isfile(path):
        return {}

    try:
        with open(path) as config_file:
            config = json.load(config_file)
    except (OSError, ValueError) as exc:
        raise ThermalConfigError('{}: {}'.format(path, exc))

    if not isinstance(config, dict):
        raise ThermalConfigError('{}: top level must be an object'.format(path))

    _validate(config, path)
    return config


def get_fan_limits(config):
    return _fan_limits(config.get(KEY_FAN_LIMITS, {}))


def get_pid_domains(config):
    return config.get(KEY_PID_DOMAINS, {})


def get_domain_setpoint(config, domain):
    """Explicit target temperature for a domain, or None to derive it from the sensors."""
    return get_pid_domains(config).get(domain, {}).get(KEY_SETPOINT)


def _fan_limits(limits):
    return (limits.get(KEY_FAN_MIN, DEFAULT_FAN_MIN_SPEED),
            limits.get(KEY_FAN_MAX, DEFAULT_FAN_MAX_SPEED))


def _validate(config, path):
    try:
        _reject_unknown_keys(config, (KEY_FAN_LIMITS, KEY_PID_DOMAINS), 'the config')
        _validate_fan_limits(config.get(KEY_FAN_LIMITS))
        _validate_pid_domains(config.get(KEY_PID_DOMAINS))
    except _Invalid as exc:
        raise ThermalConfigError('{}: {}'.format(path, exc)) from None


class _Invalid(Exception):
    """A validation failure, before the file path is attached."""


def _is_number(value):
    # JSON true/false load as bool, which is a subclass of int and would pass for 1 and 0.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _reject_unknown_keys(obj, allowed, where):
    unknown = sorted(set(obj) - set(allowed))
    if unknown:
        raise _Invalid('{} has unknown key(s): {}'.format(where, ', '.join(unknown)))


def _validate_fan_limits(limits):
    if limits is None:
        return
    if not isinstance(limits, dict):
        raise _Invalid('fan_limits must be an object')
    _reject_unknown_keys(limits, (KEY_FAN_MIN, KEY_FAN_MAX), 'fan_limits')
    low, high = _fan_limits(limits)
    for name, value in ((KEY_FAN_MIN, low), (KEY_FAN_MAX, high)):
        if not _is_number(value):
            raise _Invalid('fan_limits.{} must be a number, got {!r}'.format(name, value))
        if not 0 <= value <= 100:
            raise _Invalid('fan_limits.{} must be a percentage within [0, 100], got {}'.format(
                name, value))
    if low > high:
        raise _Invalid('fan_limits.min {} exceeds fan_limits.max {}'.format(low, high))


def _validate_pid_domains(domains):
    if domains is None:
        return
    if not isinstance(domains, dict):
        raise _Invalid('pid_domains must be an object')
    for domain, domain_config in domains.items():
        _validate_pid_domain(domain, domain_config)


def _validate_pid_domain(domain, domain_config):
    if not isinstance(domain_config, dict):
        raise _Invalid("pid_domains.{} must be an object".format(domain))
    _reject_unknown_keys(domain_config, _REQUIRED_GAINS + (KEY_SETPOINT,),
                         'pid_domains.{}'.format(domain))
    for gain in _REQUIRED_GAINS:
        if gain not in domain_config:
            raise _Invalid("pid_domains.{} is missing {}".format(domain, gain))
        value = domain_config[gain]
        if not _is_number(value) or value < 0:
            raise _Invalid("pid_domains.{}.{} must be a non-negative number, got {!r}".format(
                domain, gain, value))
    if not any(domain_config[gain] for gain in _REQUIRED_GAINS):
        raise _Invalid("pid_domains.{} has all-zero gains".format(domain))
    setpoint = domain_config.get(KEY_SETPOINT)
    if setpoint is not None and not _is_number(setpoint):
        raise _Invalid("pid_domains.{}.setpoint must be a number, got {!r}".format(
            domain, setpoint))
