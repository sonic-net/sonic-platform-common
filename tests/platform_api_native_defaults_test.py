"""The native base classes' defaults, against Python's base classes.

`generator/native.py` reads each base class's methods to decide what a native
object overriding nothing answers, and writes that into
`crates/platform-base/tests/generated/object_sweep.rs`, which the Rust defaults
are tested against.  That shows only that Rust agrees with the generator's
reading.  This checks the reading against Python: an instance of each base
class, constructed with its constructor's defaults, asked every method the
table expects an answer from.

A native object carries no base-class instance state.  Where Python's answer
comes from a constructor argument with no default -- a leak sensor's name, a
BMC's address -- there is no default instance to match, and the native
default says the implementation has to provide it.  Those cells are checked
the other way round: Python answers exactly what the constructor was given,
so the value comes from nowhere else.
"""

import inspect
import os
import sys
from unittest import mock

import pytest

try:
    import sonic_py_common  # noqa: F401
except ImportError:
    # The same stub as tests/platform_api_facade_test.py.
    sys.modules['sonic_py_common'] = mock.MagicMock()
    sys.modules['sonic_py_common.logger'] = mock.MagicMock()
    sys.modules['sonic_py_common.syslogger'] = mock.MagicMock()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'generator'))

pytest.importorskip('jinja2')

import generate  # noqa: E402
import native  # noqa: E402
import parse_pyi  # noqa: E402

from sonic_platform_base.bmc_base import BMCBase  # noqa: E402
from sonic_platform_base.chassis_base import ChassisBase  # noqa: E402
from sonic_platform_base.component_base import ComponentBase  # noqa: E402
from sonic_platform_base.fan_base import FanBase  # noqa: E402
from sonic_platform_base.fan_drawer_base import FanDrawerBase  # noqa: E402
from sonic_platform_base.liquid_cooling_base import (  # noqa: E402
    LeakageSensorBase, LeakSensorProfileBase, LiquidCoolingBase)
from sonic_platform_base.module_base import ModuleBase  # noqa: E402
from sonic_platform_base.pdb_base import PdbBase  # noqa: E402
from sonic_platform_base.psu_base import PsuBase  # noqa: E402
from sonic_platform_base.sed_mgmt_base import SedMgmtBase  # noqa: E402
from sonic_platform_base.sensor_base import (  # noqa: E402
    CurrentSensorBase, SensorBase, VoltageSensorBase)
from sonic_platform_base.sonic_eeprom.eeprom_tlvinfo import TlvInfoDecoder  # noqa: E402
from sonic_platform_base.sonic_thermal_control.thermal_manager_base import (  # noqa: E402
    ThermalManagerBase)
from sonic_platform_base.thermal_base import ThermalBase  # noqa: E402
from sonic_platform_base.watchdog_base import WatchdogBase  # noqa: E402

PYTHON = {c.__name__: c for c in (
    ChassisBase, ModuleBase, FanBase, FanDrawerBase, PsuBase, PdbBase, ThermalBase,
    SensorBase, VoltageSensorBase, CurrentSensorBase, LiquidCoolingBase,
    LeakageSensorBase, LeakSensorProfileBase, ComponentBase, WatchdogBase, BMCBase,
    SedMgmtBase, ThermalManagerBase, TlvInfoDecoder)}
PYTHON['Object'] = object

# The base-class bodies checked here.  The others write files, take locks, run
# commands or read the switch, and are tested in `crate::bodies`.
BODIES = {
    ('LeakageSensorBase', 'get_leak_severity'),
    ('LiquidCoolingBase', 'get_all_profiles'),
}

STATE = 'answers base-class state the implementation has to provide'


class Given(object):
    """What a required constructor argument is given."""

    def __repr__(self):
        return 'GIVEN'


GIVEN = Given()


def instance(name):
    """`name`'s base class, constructed with its defaults; GIVEN for each
    argument that has none."""
    base = PYTHON[name]
    cls = type('Sweep', (base,), {})
    # A base class with abstract methods is still a base class to derive from.
    cls.__abstractmethods__ = frozenset()
    if base is object:
        return cls()
    args, kwargs = [], {}
    for p in list(inspect.signature(base.__init__).parameters.values())[1:]:
        if p.default is not p.empty or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        if p.kind == p.KEYWORD_ONLY:
            kwargs[p.name] = GIVEN
        else:
            args.append(GIVEN)
    # ChassisBase.__init__ builds CPO devices if cpo.json says there are any;
    # off a switch there is none.
    with mock.patch('sonic_platform_base.chassis_base.device_info') as device_info:
        device_info.get_cpo_data.return_value = None
        return cls(*args, **kwargs)


def outcome(obj, meth, args):
    """What `obj.meth(*args)` does, spelt as the sweep spells it."""
    fn = getattr(obj, meth, None)
    if fn is None:
        return 'missing'
    try:
        v = fn(*args)
    except NotImplementedError as e:
        return 'raise NotImplementedError: %s' % e
    return 'ok %r' % (v,)


def cells():
    classes = native.read_classes(os.path.join(ROOT, 'sonic_platform_base'))
    table = native.build_object(generate.build(parse_pyi.parse()),
                                os.path.join(ROOT, 'sonic_platform_base'))
    for m in table['methods']:
        args = [native.SWEEP_PY[k] for _p, k in m.params]
        for cls, expected in zip(('Object',) + native.BASES, m.sweep):
            if expected is None:
                continue
            kind = native.default_of(classes, cls, m.name)[0] if cls != 'Object' else 'missing'
            if kind == 'body' and (cls, m.name) not in BODIES:
                continue
            yield pytest.param(cls, m.name, args, expected, id='%s.%s' % (cls, m.name))


@pytest.mark.parametrize('cls, meth, args, expected', list(cells()))
def test_a_native_default_answers_what_a_default_python_instance_answers(cls, meth, args, expected):
    got = outcome(instance(cls), meth, args)
    if STATE in expected:
        # No default instance: Python answers what the constructor was given.
        assert got == 'ok GIVEN', '%s.%s: %s' % (cls, meth, got)
    else:
        assert got == expected


def test_every_stateful_default_with_a_default_instance_is_answered():
    # The leak sensor's type and location default to 'unknown', and the
    # cooling's profiles to none: what the review found the native defaults
    # raising on.  Only state from a required argument is left to vendors.
    stateful = {(c, m) for c, m, _a, e in (p.values for p in cells()) if STATE in e}
    assert {m for _c, m in stateful} <= {'_get_ip_addr', 'get_name', 'is_read_only'}
    assert ('LeakageSensorBase', 'get_leak_sensor_type') not in stateful
