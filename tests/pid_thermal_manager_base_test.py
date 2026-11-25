"""
Unit tests for sonic_platform_base.sonic_thermal_control.pid_thermal_manager_base.

Registration is checked in a fresh interpreter. The other test files import the common_*
modules at collection time, so in this process the types are already registered and an
in-process check would pass whether or not the new module imported anything.
"""

import json
import logging
import logging.handlers
import os
import subprocess
import sys
import textwrap

import pytest

from sonic_platform_base.sonic_thermal_control import pid_thermal_manager_base
from sonic_platform_base.sonic_thermal_control.pid_thermal_manager_base import (
    PidThermalManagerBase)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMON_LOGGER = 'sonic_platform_base.sonic_thermal_control'
EXAMPLE_POLICY = os.path.join(REPO_ROOT, 'sonic_platform_base', 'sonic_thermal_control',
                              'examples', 'thermal_policy.json')


def run_fresh(code):
    """Run code in a new interpreter that has imported nothing from this test session."""
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [REPO_ROOT, env.get('PYTHONPATH')]))
    return subprocess.run([sys.executable, '-c', textwrap.dedent(code)],
                          cwd=REPO_ROOT, env=env, capture_output=True, text=True)


@pytest.fixture
def common_logger():
    """The shared modules' logger, with its handlers and level restored after the test."""
    logger = logging.getLogger(COMMON_LOGGER)
    saved_handlers, saved_level = logger.handlers[:], logger.level
    logger.handlers = []
    yield logger
    logger.handlers = saved_handlers
    logger.setLevel(saved_level)


class FakeSysLogHandler(logging.handlers.SysLogHandler):
    """Records its address instead of opening a socket."""

    def __init__(self, address):
        logging.Handler.__init__(self)
        self.address = address


class Manager(PidThermalManagerBase):
    SYSLOG_IDENTIFIER = 'testthermal'


# --- registration -----------------------------------------------------------------------

def test_importing_the_module_registers_the_common_types():
    # Given a fresh interpreter in which no common_* module has been imported
    # When only pid_thermal_manager_base is imported
    result = run_fresh("""
        from sonic_platform_base.sonic_thermal_control import pid_thermal_manager_base
        from sonic_platform_base.sonic_thermal_control.thermal_json_object import (
            ThermalJsonObject)
        registered = ThermalJsonObject._object_type_dict
        for name in ('thermal_info', 'fandrawer.presence', 'thermal.control_algo'):
            assert name in registered, name
    """)

    # Then an info, a condition and an action type are all registered
    assert result.returncode == 0, result.stderr


def test_example_policy_loads_through_a_subclass():
    # Given a fresh interpreter and a platform manager that only subclasses the base
    # When it loads the example policy file
    result = run_fresh("""
        from sonic_platform_base.sonic_thermal_control.pid_thermal_manager_base import (
            PidThermalManagerBase)

        class ThermalManager(PidThermalManagerBase):
            pass

        ThermalManager.load(%r)
        assert len(ThermalManager._policy_dict) == 2, ThermalManager._policy_dict
    """ % EXAMPLE_POLICY)

    # Then both policies load without the platform importing any common_* module itself
    assert result.returncode == 0, result.stderr


# --- syslog routing ---------------------------------------------------------------------

def test_initialize_attaches_a_syslog_handler_with_the_identifier(common_logger, monkeypatch):
    # Given a syslog socket is available
    monkeypatch.setattr(logging.handlers, 'SysLogHandler', FakeSysLogHandler)

    # When the manager is initialized
    assert Manager.initialize() is True

    # Then one syslog handler on /dev/log tags messages with the class's identifier
    handlers = [h for h in common_logger.handlers if isinstance(h, FakeSysLogHandler)]
    assert len(handlers) == 1
    assert handlers[0].address == '/dev/log'
    record = logging.LogRecord(COMMON_LOGGER + '.common_actions', logging.INFO, '', 0,
                               'fans at 50%', None, None)
    assert handlers[0].format(record) == \
        'testthermal: sonic_platform_base.sonic_thermal_control.common_actions: fans at 50%'
    assert common_logger.level == logging.INFO


def test_default_identifier_is_thermalctld(common_logger, monkeypatch):
    # Given a platform manager that does not set an identifier
    monkeypatch.setattr(logging.handlers, 'SysLogHandler', FakeSysLogHandler)

    class Plain(PidThermalManagerBase):
        pass

    # When it is initialized
    Plain.initialize()

    # Then messages are tagged thermalctld
    record = logging.LogRecord(COMMON_LOGGER, logging.INFO, '', 0, 'hi', None, None)
    assert common_logger.handlers[0].format(record).startswith('thermalctld: ')


def test_initialize_twice_attaches_one_handler(common_logger, monkeypatch):
    # Given a manager that has already been initialized
    monkeypatch.setattr(logging.handlers, 'SysLogHandler', FakeSysLogHandler)
    Manager.initialize()

    # When it is initialized again
    Manager.initialize()

    # Then there is still only one syslog handler
    assert len(common_logger.handlers) == 1


def test_initialize_without_a_syslog_socket_leaves_handlers_alone(common_logger,
                                                                  monkeypatch):
    # Given no syslog socket, so creating the handler raises OSError
    def no_socket(address):
        raise OSError('no /dev/log')
    monkeypatch.setattr(logging.handlers, 'SysLogHandler', no_socket)

    # When the manager is initialized
    result = Manager.initialize()

    # Then it still succeeds and the logger is untouched
    assert result is True
    assert common_logger.handlers == []


def test_subclass_initialize_can_chain_to_super(common_logger, monkeypatch):
    # Given a platform manager that overrides initialize and calls super()
    monkeypatch.setattr(logging.handlers, 'SysLogHandler', FakeSysLogHandler)

    class Platform(PidThermalManagerBase):
        SYSLOG_IDENTIFIER = 'platformthermal'
        extra_init_ran = False

        @classmethod
        def initialize(cls):
            cls.extra_init_ran = True
            return super().initialize()

    # When it is initialized
    result = Platform.initialize()

    # Then both its own setup and the routing ran, under its identifier
    assert result is True and Platform.extra_init_ran
    record = logging.LogRecord(COMMON_LOGGER, logging.INFO, '', 0, 'hi', None, None)
    assert common_logger.handlers[0].format(record).startswith('platformthermal: ')


# --- fail-safe --------------------------------------------------------------------------

def policy_file(tmp_path, condition='default.operation', speed=40):
    """A one-policy file: on the condition, set every fan to speed."""
    path = tmp_path / 'thermal_policy.json'
    path.write_text(json.dumps({
        'info_types': [{'type': 'fan_info'}],
        'policies': [{
            'name': 'default',
            'conditions': [{'type': condition}],
            'actions': [{'type': 'fan.all.set_speed', 'speed': speed}],
        }],
    }))
    return str(path)


class Fan:
    """A present, healthy fan, or one whose presence read raises."""

    def __init__(self, broken=False):
        self.speed = None
        self._broken = broken

    def get_presence(self):
        if self._broken:
            raise RuntimeError('fan eeprom unreadable')
        return True

    def get_status(self): return True

    def set_speed(self, speed):
        self.speed = speed
        return True


class Chassis:
    def __init__(self, fans): self._fans = fans
    def get_all_fans(self): return self._fans
    def get_all_fan_drawers(self): return []


@pytest.fixture
def manager(monkeypatch):
    """Manager with empty policy state; ThermalManagerBase keeps it on the class."""
    monkeypatch.setattr(Manager, '_policy_dict', {})
    monkeypatch.setattr(Manager, '_thermal_info_dict', {})
    monkeypatch.setattr(Manager, '_load_error', None, raising=False)
    return Manager


def test_failing_info_collect_drives_fans_to_full_and_reraises(manager, tmp_path):
    # Given a healthy policy and a fan whose presence read raises during fan_info collect
    manager.load(policy_file(tmp_path))
    fans = [Fan(), Fan(broken=True)]

    # When the policy runs
    with pytest.raises(RuntimeError, match='eeprom'):
        manager.run_policy(Chassis(fans))

    # Then the error still reaches thermalctld and every fan is at full speed
    assert [fan.speed for fan in fans] == [100, 100]


def test_failed_load_holds_fans_at_full_until_a_good_load(manager, tmp_path):
    # Given a policy file naming a condition type that does not exist
    broken = policy_file(tmp_path, condition='no.such.condition')

    # When it is loaded
    with pytest.raises(Exception, match='no.such.condition'):
        manager.load(broken)

    # Then every run drives the fans to full speed instead of running nothing
    fan = Fan()
    for _ in range(2):
        fan.speed = None
        manager.run_policy(Chassis([fan]))
        assert fan.speed == 100

    # And once a good file loads, its policy runs again
    manager.load(policy_file(tmp_path, speed=40))
    manager.run_policy(Chassis([fan]))
    assert fan.speed == 40


def test_failing_fail_safe_does_not_hide_the_policy_error(manager, tmp_path, monkeypatch):
    # Given a collect that raises and a fail-safe whose fan write also raises
    manager.load(policy_file(tmp_path))

    attempts = []

    def write_fails(*args, **kwargs):
        attempts.append(args)
        raise OSError('fan bus hung')
    monkeypatch.setattr(pid_thermal_manager_base.common_actions, 'set_all_fan_speeds',
                        write_fails)

    # When the policy runs
    # Then the fail-safe was tried and the original error is the one raised
    with pytest.raises(RuntimeError, match='eeprom'):
        manager.run_policy(Chassis([Fan(broken=True)]))
    assert len(attempts) == 1


def test_healthy_policy_leaves_fans_to_the_policy(manager, tmp_path):
    # Given a healthy policy that sets the fans to 40%
    manager.load(policy_file(tmp_path, speed=40))
    fans = [Fan(), Fan()]

    # When the policy runs
    manager.run_policy(Chassis(fans))

    # Then the fans are at the policy's speed, not the fail-safe's
    assert [fan.speed for fan in fans] == [40, 40]
