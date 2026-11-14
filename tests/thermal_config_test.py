"""Unit tests for sonic_platform_base.sonic_thermal_control.thermal_config."""

import json
import os

import pytest

from sonic_platform_base.sonic_thermal_control import thermal_config
from sonic_platform_base.sonic_thermal_control.thermal_config import (
    ThermalConfigError,
    get_domain_setpoint,
    get_fan_limits,
    get_pid_domains,
    load_thermal_config,
)

VALID = {
    "fan_limits": {"min": 30, "max": 100},
    "pid_domains": {
        "asic": {"KP": 10, "KI": 0.1, "KD": 5, "setpoint": 85},
        "main": {"KP": 5, "KI": 0.05, "KD": 2.5},
    },
}


def write_config(tmp_path, config):
    path = tmp_path / thermal_config.CONFIG_FILE_NAME
    path.write_text(config if isinstance(config, str) else json.dumps(config))
    return str(tmp_path)


def test_missing_file_returns_empty_dict(tmp_path):
    # Given a directory with no thermal_config.json
    # When the config is loaded from it
    config = load_thermal_config(str(tmp_path))

    # Then the result is an empty config
    assert config == {}


def test_missing_file_is_not_an_error(tmp_path):
    # Given a directory with no thermal_config.json
    # When the config is loaded from it
    config = load_thermal_config(str(tmp_path))

    # Then the fan limits and PID domains fall back to their defaults
    assert get_fan_limits(config) == (thermal_config.DEFAULT_FAN_MIN_SPEED,
                                      thermal_config.DEFAULT_FAN_MAX_SPEED)
    assert get_pid_domains(config) == {}


def test_loads_a_valid_config(tmp_path):
    # Given a valid config file
    # When it is loaded
    config = load_thermal_config(write_config(tmp_path, VALID))

    # Then its fan limits and PID domains are available
    assert get_fan_limits(config) == (30, 100)
    assert sorted(get_pid_domains(config)) == ["asic", "main"]


def test_setpoint_override_and_absence(tmp_path):
    # Given a valid config where only the asic domain sets a target
    # When it is loaded
    config = load_thermal_config(write_config(tmp_path, VALID))

    # Then only asic reports a setpoint, and unknown domains report none
    assert get_domain_setpoint(config, "asic") == 85
    assert get_domain_setpoint(config, "main") is None
    assert get_domain_setpoint(config, "nonexistent") is None


def test_config_path_uses_default_dir():
    # Given no explicit config directory
    # When the config path is resolved
    path = thermal_config.config_path()

    # Then it lies under the default platform directory
    assert path.startswith(thermal_config.DEFAULT_CONFIG_DIR)


def test_malformed_json_is_an_error(tmp_path):
    # Given a config file that is not valid JSON
    # When it is loaded
    # Then it is rejected
    with pytest.raises(ThermalConfigError):
        load_thermal_config(write_config(tmp_path, "{not json"))


def test_top_level_must_be_an_object(tmp_path):
    # Given a config file whose top level is a list
    # When it is loaded
    # Then it is rejected
    with pytest.raises(ThermalConfigError):
        load_thermal_config(write_config(tmp_path, [1, 2, 3]))


def test_rejects_inverted_fan_limits(tmp_path):
    # Given a config whose fan minimum is above its maximum
    # When it is loaded
    # Then it is rejected
    with pytest.raises(ThermalConfigError):
        load_thermal_config(write_config(tmp_path, {"fan_limits": {"min": 90, "max": 40}}))


def test_rejects_non_numeric_fan_limit(tmp_path):
    # Given a config with a non-numeric fan limit
    # When it is loaded
    # Then it is rejected
    with pytest.raises(ThermalConfigError):
        load_thermal_config(write_config(tmp_path, {"fan_limits": {"min": "low"}}))


def test_rejects_missing_gain(tmp_path):
    # Given a PID domain with no KD gain
    bad = {"pid_domains": {"asic": {"KP": 1, "KI": 1}}}

    # When the config is loaded
    # Then it is rejected
    with pytest.raises(ThermalConfigError):
        load_thermal_config(write_config(tmp_path, bad))


def test_rejects_negative_gain(tmp_path):
    # Given a PID domain with a negative gain
    bad = {"pid_domains": {"asic": {"KP": -1, "KI": 1, "KD": 1}}}

    # When the config is loaded
    # Then it is rejected
    with pytest.raises(ThermalConfigError):
        load_thermal_config(write_config(tmp_path, bad))


def test_rejects_all_zero_gains(tmp_path):
    # Given a PID domain whose gains are all zero
    bad = {"pid_domains": {"asic": {"KP": 0, "KI": 0, "KD": 0}}}

    # When the config is loaded
    # Then it is rejected
    with pytest.raises(ThermalConfigError):
        load_thermal_config(write_config(tmp_path, bad))


def test_rejects_non_numeric_setpoint(tmp_path):
    # Given a PID domain with a non-numeric setpoint
    bad = {"pid_domains": {"asic": {"KP": 1, "KI": 1, "KD": 1, "setpoint": "hot"}}}

    # When the config is loaded
    # Then it is rejected
    with pytest.raises(ThermalConfigError):
        load_thermal_config(write_config(tmp_path, bad))


def test_partial_config_keeps_defaults_for_absent_keys(tmp_path):
    # Given a config that sets only the fan minimum
    # When it is loaded
    config = load_thermal_config(write_config(tmp_path, {"fan_limits": {"min": 40}}))

    # Then the minimum is taken from it and the maximum and PID domains keep their defaults
    assert get_fan_limits(config) == (40, thermal_config.DEFAULT_FAN_MAX_SPEED)
    assert get_pid_domains(config) == {}


@pytest.mark.parametrize("config, message", [
    ({"fan_limits": [30, 100]}, "fan_limits must be an object"),
    ({"pid_domains": ["asic"]}, "pid_domains must be an object"),
    ({"pid_domains": {"asic": 10}}, "pid_domains.asic must be an object"),
])
def test_rejects_non_object_sections(tmp_path, config, message):
    # Given a config where a section is not a JSON object
    # When it is loaded
    # Then it is rejected with an error naming the section
    with pytest.raises(ThermalConfigError, match=message):
        load_thermal_config(write_config(tmp_path, config))


def test_error_names_the_file(tmp_path):
    # Given a config file whose fan minimum is above its maximum
    config_dir = write_config(tmp_path, {"fan_limits": {"min": 90, "max": 40}})

    # When it is loaded
    # Then it is rejected with an error that names the file
    with pytest.raises(ThermalConfigError, match=thermal_config.CONFIG_FILE_NAME):
        load_thermal_config(config_dir)


# JSON true/false load as Python bool, which is a subclass of int; a typo like "KP": true
# must not pass for the number 1.

@pytest.mark.parametrize("config", [
    {"fan_limits": {"min": False, "max": 100}},
    {"fan_limits": {"min": 30, "max": True}},
    {"pid_domains": {"asic": {"KP": True, "KI": 0.1, "KD": 5}}},
    {"pid_domains": {"asic": {"KP": True, "KI": False, "KD": False}}},
    {"pid_domains": {"asic": {"KP": 10, "KI": 0.1, "KD": 5, "setpoint": True}}},
], ids=["fan-min", "fan-max", "one-gain", "all-gains", "setpoint"])
def test_rejects_booleans_where_numbers_are_expected(tmp_path, config):
    # Given a config with a JSON boolean where a number belongs
    # When it is loaded
    # Then it is rejected
    with pytest.raises(ThermalConfigError):
        load_thermal_config(write_config(tmp_path, config))


@pytest.mark.parametrize("limits", [
    {"min": -10, "max": 100},
    {"min": 30, "max": 150},
    {"min": -10, "max": 150},
], ids=["min-below-0", "max-above-100", "both"])
def test_rejects_fan_limits_outside_0_to_100(tmp_path, limits):
    # Given fan limits outside the 0-100 percent range
    # When the config is loaded
    # Then it is rejected
    with pytest.raises(ThermalConfigError):
        load_thermal_config(write_config(tmp_path, {"fan_limits": limits}))


def test_accepts_fan_limits_at_the_bounds(tmp_path):
    # Given fan limits of exactly 0 and 100
    # When the config is loaded
    config = load_thermal_config(write_config(tmp_path, {"fan_limits": {"min": 0, "max": 100}}))

    # Then they are accepted as given
    assert get_fan_limits(config) == (0, 100)


@pytest.mark.parametrize("config, key", [
    ({"interval": 5}, "interval"),
    ({"fan_limits": {"min": 30, "maximum": 100}}, "maximum"),
    ({"pid_domains": {"asic": {"KP": 1, "KI": 0, "KD": 0, "set_point": 80}}}, "set_point"),
], ids=["top-level", "fan_limits", "pid-domain"])
def test_rejects_unknown_keys(tmp_path, config, key):
    # Given a config with a misspelled or unsupported key
    # When it is loaded
    # Then it is rejected with an error naming the key, rather than silently ignored
    with pytest.raises(ThermalConfigError, match=key):
        load_thermal_config(write_config(tmp_path, config))
