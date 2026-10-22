"""The generator and its omission check, run the way check.sh runs them.

`generate.py --check` is the gate that keeps the checked-in facade and the
three Rust files equal to what the stub says; `api_coverage.py --check` is the
one that notices an omission whose reason has stopped being true.  Both used
to run only as command lines, where nothing measured which of their branches a
change ever took.  They run in process here, so the failures they exist to
report are exercised too, not only the passing run.
"""

import ast
import json
import os
import re
import sys

import pytest

GENERATOR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'generator')
sys.path.insert(0, GENERATOR)

pytest.importorskip('jinja2')

import api_coverage  # noqa: E402
import generate  # noqa: E402
import parse_pyi  # noqa: E402
from model import FieldSpec, MethodSpec, RowSpec, _pascal, rust_type, strip_optional  # noqa: E402

from sonic_platform_api import facade  # noqa: E402

from .platform_api_schema_test import GOOD_API, GOOD_ROW, HEADER  # noqa: E402


def run(monkeypatch, script, *args):
    monkeypatch.setattr(sys, 'argv', [script] + list(args))
    return {'generate.py': generate, 'api_coverage.py': api_coverage}[script].main()


def outputs_under(monkeypatch, root):
    """Point every generated file at the same place under `root`.

    The relative paths are kept, so each file keeps its suffix and the header
    rendered for it -- the text written is byte for byte the checked-in one.
    """
    moved = {tpl: str(root / os.path.relpath(path, generate.ROOT))
             for tpl, path in generate.OUTPUTS.items()}
    monkeypatch.setattr(generate, 'OUTPUTS', moved)
    monkeypatch.setattr(generate, 'ROOT', str(root))
    return moved


# -- generate.py -------------------------------------------------------------

def test_the_checked_in_outputs_are_what_the_generator_produces(monkeypatch, capsys):
    assert run(monkeypatch, 'generate.py', '--check') == 0
    assert 'generated files up to date' in capsys.readouterr().out


def test_a_fresh_tree_is_written_and_then_checks_clean(tmp_path, monkeypatch, capsys):
    moved = outputs_under(monkeypatch, tmp_path)

    assert run(monkeypatch, 'generate.py') == 0
    out = capsys.readouterr().out
    assert 'wrote sonic_platform_api/facade.py' in out
    for path in moved.values():
        assert os.path.exists(path)

    assert run(monkeypatch, 'generate.py', '--check') == 0


def test_an_edited_or_missing_output_is_stale(tmp_path, monkeypatch, capsys):
    moved = outputs_under(monkeypatch, tmp_path)
    assert run(monkeypatch, 'generate.py') == 0
    capsys.readouterr()

    with open(moved['facade.py.j2'], 'a') as f:
        f.write('# edited by hand\n')
    os.remove(moved['trait.rs.j2'])

    assert run(monkeypatch, 'generate.py', '--check') == 1
    err = capsys.readouterr().err
    assert 'stale, re-run generator/generate.py' in err
    assert 'sonic_platform_api/facade.py' in err
    assert 'crates/platform-api/src/generated.rs' in err


def test_an_arity_problem_stops_the_generator_before_it_writes(tmp_path, monkeypatch, capsys):
    moved = outputs_under(monkeypatch, tmp_path)
    monkeypatch.setattr(generate, 'check_arity',
                        lambda model: ['Foo.heat needs a unit'])

    assert run(monkeypatch, 'generate.py') == 1
    assert 'arity: Foo.heat needs a unit' in capsys.readouterr().err
    assert not any(os.path.exists(p) for p in moved.values())


@pytest.mark.parametrize('signature, required', [
    ('(self)', []),
    ('()', []),
    ('(self, unit)', ['unit']),
    # A classmethod's receiver is bound by Python, whatever it is called.
    ('(cls)', []),
    ('(cls, index)', ['index']),
    ('(self, scale=1)', []),
    ('(self, unit, scale=1)', ['unit']),
    ('(self, **kwargs)', []),
    # A keyword-only argument without a default still has to be passed,
    # whether a bare `*` or a `*args` is what made it keyword-only.
    ('(self, *, key)', ['key']),
    ('(self, index, *args, key)', ['index', 'key']),
    ('(self, *a, x)', ['x']),
    ('(self, *args, key=None, **kwargs)', []),
    ('(self, /, unit)', ['unit']),
])
def test_the_arguments_a_caller_must_pass_are_read_from_the_signature(signature, required):
    fn = ast.parse('def f%s: pass' % signature).body[0]
    assert generate._required_args(fn) == required


def test_a_staticmethod_has_no_receiver_to_drop():
    fn = ast.parse('@staticmethod\ndef f(unit): pass').body[0]
    assert generate._required_args(fn) == ['unit']


def model_of(tmp_path):
    path = tmp_path / 'facade.pyi'
    path.write_text(HEADER + GOOD_ROW + GOOD_API)
    return parse_pyi.parse(str(path))


def bases(tmp_path, text):
    path = tmp_path / 'arity_base'
    path.mkdir()
    (path / 'thermal_base.py').write_text(text)
    return str(path)


DEVICE = '''
class DeviceBase(object):
    def get_name(self):
        raise NotImplementedError
'''


def test_a_zero_argument_read_of_a_getter_that_needs_one_is_refused(tmp_path):
    base = bases(tmp_path, DEVICE + '''
class ThermalBase(DeviceBase):
    def get_temperature(self, unit):
        raise NotImplementedError
''')
    assert generate.check_arity(model_of(tmp_path), base_dir=base) == [
        'Foo.heat reads ThermalBase.get_temperature(self, unit) with no arguments;'
        ' it requires unit -- declare WithName() or pass them']


def test_a_getter_that_takes_nothing_passes_the_arity_check(tmp_path):
    # Inherited counts: `name` reads DeviceBase.get_name through ThermalBase's
    # bases, the way Python resolves it.
    base = bases(tmp_path, DEVICE + '''
class ThermalBase(DeviceBase):
    def get_temperature(self, scale=1):
        raise NotImplementedError
''')
    assert generate.check_arity(model_of(tmp_path), base_dir=base) == []


def test_a_getter_the_base_classes_do_not_define_is_refused(tmp_path):
    # The inventory this used to read answered nothing for a getter it had
    # not seen, and the check took that as "takes no arguments".
    base = bases(tmp_path, DEVICE + '''
class ThermalBase(DeviceBase):
    pass
''')
    assert generate.check_arity(model_of(tmp_path), base_dir=base) == [
        'Foo.heat reads ThermalBase.get_temperature, which the base classes do not define']


def test_no_base_classes_to_read_signatures_from_is_a_problem_not_a_pass(tmp_path):
    missing = str(tmp_path / 'nowhere')
    assert generate.check_arity(model_of(tmp_path), base_dir=missing) == [
        'no base classes under %s to check the columns against' % missing]


def test_every_column_the_stub_reads_resolves_against_the_shipped_base_classes():
    assert generate.check_arity(generate.build(parse_pyi.parse())) == []


# -- the stub against the base classes ---------------------------------------

BASE = '''
from enum import Enum


class Colours(Enum):
    GREEN = "green"
    RED = "red"


class Wide(Enum):
    GREEN = "green"
    RED = "red"
    BLUE = "blue"


class DeviceBase(object):
    def set_status_led(self, color):
        """
        Sets the state of the device status LED

        Returns:
            bool: True if status LED state is set successfully, False if not
        """
        raise NotImplementedError


class FanBase(DeviceBase):
    pattern = "\\d"          # not a raw string, like the shipped ones
'''


def base_dir(tmp_path):
    path = tmp_path / 'base'
    path.mkdir()
    (path / 'device_base.py').write_text(BASE)
    (path / 'half_written.py').write_text('def (:\n')
    return str(path)


def contract_model(tmp_path, returns, calls):
    path = tmp_path / 'facade.pyi'
    path.write_text(HEADER + GOOD_ROW + GOOD_API + '''
    @platform_method(On(row="Foo"), Calls("%s"))
    def set_foo_led(self, foo: str, color: Colour) -> %s: ...
''' % (calls, returns))
    return parse_pyi.parse(str(path))


@pytest.mark.parametrize('returns, calls, literals, problems', [
    ('Optional[bool]', 'FanBase.set_status_led', {'Colour': ('Colours', '')}, []),
    # The base class answers a bool, inherited from DeviceBase.
    ('None', 'FanBase.set_status_led', {'Colour': ('Colours', '')},
     ['set_foo_led returns None, but FanBase.set_status_led answers a bool --'
      ' declare Optional[bool], or its False reaches the caller as success']),
    ('Optional[bool]', 'FanBase.set_nothing', {'Colour': ('Colours', '')},
     ['set_foo_led calls FanBase.set_nothing, which the base classes do not define']),
    ('Optional[bool]', 'FanBase.set_status_led', {},
     ['Colour is used at set_foo_led(color), but LITERAL_CONSTANTS does not say'
      ' which base-class constants it stands for']),
    ('Optional[bool]', 'FanBase.set_status_led', {'Colour': ('DeviceBase', 'STATUS_')},
     ['Colour stands for DeviceBase.STATUS_*, which defines no constants']),
    ('Optional[bool]', 'FanBase.set_status_led', {'Colour': ('Wide', '')},
     ['Colour lacks blue, which Wide.* defines -- a vendor answering it would'
      ' read as None']),
])
def test_the_stub_is_held_to_what_the_base_classes_answer(
        tmp_path, returns, calls, literals, problems):
    model = contract_model(tmp_path, returns, calls)
    assert generate.check_contract(
        model, base_dir=base_dir(tmp_path), literals=literals) == problems


def test_no_base_classes_to_check_against_is_a_problem_not_a_pass(tmp_path):
    model = contract_model(tmp_path, 'Optional[bool]', 'FanBase.set_status_led')
    missing = str(tmp_path / 'nowhere')
    assert generate.check_contract(model, base_dir=missing) == [
        'no base classes under %s to check the stub against' % missing]


def test_a_contract_problem_stops_the_generator_before_it_writes(
        tmp_path, monkeypatch, capsys):
    moved = outputs_under(monkeypatch, tmp_path)
    monkeypatch.setattr(generate, 'check_contract',
                        lambda model: ['set_foo_led returns None'])

    assert run(monkeypatch, 'generate.py') == 1
    assert 'contract: set_foo_led returns None' in capsys.readouterr().err
    assert not any(os.path.exists(p) for p in moved.values())


# -- what one column expands to ----------------------------------------------

def column(name, py_type, from_, **kw):
    """One column as the parser would hand it over, before `build` runs."""
    base, optional = strip_optional(py_type)
    f = FieldSpec(name=name, py_type=py_type, base=base, optional=optional,
                  from_=from_, **kw)
    f.shared_var = None
    f.rust_ty = rust_type(py_type, set())
    return f


def facade_eval(expr, **names):
    """Evaluate a generated column expression with the facade's own helpers."""
    return eval(expr, dict(vars(facade)), names)


class Bare:
    """A device that implements nothing, so every getter reads as absent."""


def test_a_declined_column_with_a_named_default_holds_the_name_not_the_template():
    # The read and the decline must agree on what an absent column holds.  The
    # decline used to emit the declared default verbatim, so a caller that
    # turned the column off got the template '{parent} fan {i}' where one whose
    # platform did not implement the getter got 'PSU 1 fan 1'.
    f = column('label', 'str', 'FanBase.get_label',
               unsupported_on='default', default='{parent} fan {i}')
    f.col_bit = 3
    expr = generate._py_field_expr(f)
    where = dict(dev=Bare(), parent='PSU 1', i=0)
    assert facade_eval(expr, cols=1 << 3, **where) == 'PSU 1 fan 1'
    assert facade_eval(expr, cols=0, **where) == 'PSU 1 fan 1'


def test_a_named_default_may_name_a_field_its_source_fixes():
    # sensormond says which kind of sensor an unnamed one is (sensormond:246,
    # 394); the template names the field and the source's value fills it, read
    # or declined alike.
    f = column('label', 'str', 'SensorBase.get_label',
               unsupported_on='default', default='{parent} {kind}_sensor {i}')
    f.col_bit = 2
    assert generate.template_fields(f.default) == ['kind']
    expr = generate._py_field_expr(f)
    where = dict(dev=Bare(), parent='chassis 1', i=2, fixed={'kind': 'current'})
    assert facade_eval(expr, cols=1 << 2, **where) == 'chassis 1 current_sensor 3'
    assert facade_eval(expr, cols=0, **where) == 'chassis 1 current_sensor 3'


def test_a_declined_column_with_a_plain_default_still_holds_the_default():
    f = column('replaceable', 'bool', 'FanBase.is_replaceable',
               unsupported_on='default', default=False)
    f.col_bit = 0
    assert facade_eval(generate._py_field_expr(f), cols=0, dev=Bare(),
                       parent='', i=0) is False


def shared_row(*fields):
    row = RowSpec(name='Foo', fields=list(fields))
    row.projected = True
    generate._assign_col_bits(row)
    generate._share_calls(row)
    return row


def test_a_shared_call_is_gated_on_the_bits_of_the_columns_that_slice_it():
    row = shared_row(
        column('cause', 'Optional[str]', 'ChassisBase.get_reboot_cause', at=0),
        column('detail', 'Optional[str]', 'ChassisBase.get_reboot_cause', at=1))
    [(_var, _call, mask)] = row.shared_calls
    assert mask == 0b11


def test_a_shared_call_one_of_whose_slicers_cannot_be_declined_is_always_made():
    # `name` never gets a bit -- the by-name lookup has to see it -- so a call
    # it shares has to be made whatever the caller asked for.  Gated on the
    # sibling's bit alone, declining the sibling left `_at(None, 0)`: no name.
    row = shared_row(
        column('name', 'str', 'DeviceBase.get_identity', at=0),
        column('serial', 'Optional[str]', 'DeviceBase.get_identity', at=1))
    assert [f.col_bit for f in row.fields] == [None, 0]
    [(_var, _call, mask)] = row.shared_calls
    assert mask is None


@pytest.mark.parametrize('py_type, width', [
    ('Optional[Rpm]', 'u32'),
    ('Optional[Count]', 'u32'),
    ('Optional[PositionInParent]', 'i32'),
    ('Optional[int]', 'i64'),
    ('int', 'i64'),
])
def test_a_number_narrowed_to_an_integer_goes_through_the_checked_read(py_type, width):
    # `as` saturates: -1 crossed as a u32 0 and NaN as 0, each a plausible
    # reading nobody took.  The bridge's `integer` answers None instead, and
    # reads an `int` exactly rather than through f64.
    expr = generate._rust_field_expr(column('n', py_type, 'FanBase.get_n'), set())
    assert 'integer::<%s>' % width in expr
    assert 'num(' not in expr
    assert ' as ' not in expr


@pytest.mark.parametrize('py_type', ['Optional[Percent]', 'Optional[Celsius]',
                                     'Optional[Threshold]', 'Optional[Watt]',
                                     'Optional[Number]'])
def test_a_reading_crosses_keeping_int_or_float(py_type):
    # The daemons publish a reading with `str()`, so 3 and 3.0 are different
    # answers; neither f64 nor an integer width keeps both.
    expr = generate._rust_field_expr(column('n', py_type, 'ThermalBase.get_n'), set())
    assert expr == 'int_or_float(row, "n")?'


@pytest.mark.parametrize('ret', ['Option<i64>', 'u32'])
def test_a_returned_integer_goes_through_the_checked_read(ret):
    conv = generate._rust_ret_conv(ret, set())
    assert 'int_of::<%s>' % ret.replace('Option<', '').rstrip('>') in conv
    assert 'f64' not in conv
    assert ' as ' not in conv


@pytest.mark.parametrize('kw, doc', [
    (dict(row='FanDrawerInfo', calls='FanDrawerBase.set_status_led',
          params=[('drawer', 'str'), ('color', 'LedColor')]),
     'Calls `FanDrawerBase.set_status_led()` on the FanDrawerInfo at `drawer`.'),
    (dict(calls='ChassisBase.get_watchdog.disarm'),
     'Calls `ChassisBase.get_watchdog().disarm()`.'),
])
def test_an_action_the_stub_does_not_describe_is_described_by_its_declaration(kw, doc):
    # Declared with `...`, such an action came out as `""""""` in the facade
    # and as its bare name on the trait.
    assert generate._action_doc(MethodSpec(name='m', **kw)) == doc


# -- api_coverage.py ---------------------------------------------------------

def test_everything_a_consumer_reaches_is_declared_omitted_or_deferred(monkeypatch, capsys):
    assert run(monkeypatch, 'api_coverage.py', '--check') == 0
    out = capsys.readouterr().out
    assert 'in-scope declarations' in out
    assert re.search(r'todo +0 ', out)
    assert 'deferred, by phase' in out
    assert 'no consumer reaches any more' not in out


def inventory_without(tmp_path, monkeypatch, cls, meth):
    """The checked-in inventory, with `cls.meth` no longer reached."""
    with open(api_coverage.INVENTORY) as f:
        inv = json.load(f)
    del inv['classes'][cls]['reached'][meth]
    path = tmp_path / 'inventory.json'
    path.write_text(json.dumps(inv))
    monkeypatch.setattr(api_coverage, 'INVENTORY', str(path))


@pytest.mark.parametrize('name', ['OMITTED', 'DEFERRED'])
def test_an_entry_nothing_reaches_any_more_fails_the_check(tmp_path, monkeypatch, capsys, name):
    cls, meth = sorted(api_coverage.listed(name))[0]
    inventory_without(tmp_path, monkeypatch, cls, meth)

    # Reported either way; only --check turns it into a failure.
    assert run(monkeypatch, 'api_coverage.py') == 0
    assert run(monkeypatch, 'api_coverage.py', '--check') == 1
    captured = capsys.readouterr()
    assert '%s entries that no consumer reaches any more (1)' % name in captured.out
    assert '%s.%s' % (cls, meth) in captured.out
    assert 'remove them from %s' % name in captured.err


def test_a_todo_fails_the_check(monkeypatch, capsys):
    # What a consumer reaches and the stub neither declares, omits nor
    # defers: the check used to report it and pass.
    later = dict(api_coverage.deferred())
    cls, meth = sorted(later)[0]
    del later[(cls, meth)]
    monkeypatch.setattr(api_coverage, 'deferred', lambda path=None: later)
    assert run(monkeypatch, 'api_coverage.py') == 0
    assert run(monkeypatch, 'api_coverage.py', '--check') == 1
    captured = capsys.readouterr()
    assert re.search(r'todo +1 ', captured.out)
    assert '%s ' % cls in captured.out and meth in captured.out
    assert 'add them to OMITTED or DEFERRED' in captured.err


def test_a_deferral_the_stub_now_declares_fails_the_check(monkeypatch, capsys):
    later = dict(api_coverage.deferred())
    later[('FanBase', 'get_speed')] = 'a later phase'
    monkeypatch.setattr(api_coverage, 'deferred', lambda path=None: later)
    assert run(monkeypatch, 'api_coverage.py', '--check') == 1
    captured = capsys.readouterr()
    assert 'DEFERRED entries the stub now declares (1)' in captured.out
    assert 'FanBase.get_speed' in captured.out


def test_an_entry_in_both_lists_fails_the_check(monkeypatch, capsys):
    skip = dict(api_coverage.omitted())
    cls, meth = sorted(api_coverage.deferred())[0]
    skip[(cls, meth)] = 'decided against after all'
    monkeypatch.setattr(api_coverage, 'omitted', lambda path=None: skip)
    assert run(monkeypatch, 'api_coverage.py', '--check') == 1
    captured = capsys.readouterr()
    assert 'in both OMITTED and DEFERRED (1)' in captured.out


def test_a_stub_that_omits_nothing_says_so(tmp_path):
    path = tmp_path / 'facade.pyi'
    path.write_text(HEADER + GOOD_ROW + GOOD_API)
    assert api_coverage.omitted(str(path)) == {}
    assert api_coverage.deferred(str(path)) == {}


# -- enumeration variants ----------------------------------------------------

@pytest.mark.parametrize('value, variant', [
    ('green', 'Green'),
    ('LINE-CARD', 'LineCard'),
    ('N/A', 'NA'),
    ('i2c_stuck', 'I2cStuck'),
    ('module_psu', 'ModulePsu'),
    # Already mixed case: the base class's own spelling survives.
    # `capitalize()` alone made these `Powereddown` and `Provisionready`.
    ('PoweredDown', 'PoweredDown'),
    ('ProvisionReady', 'ProvisionReady'),
])
def test_a_value_becomes_the_variant_its_spelling_suggests(value, variant):
    assert _pascal(value) == variant


def test_no_two_values_of_an_enumeration_become_one_variant():
    for e in parse_pyi.parse().enums:
        variants = [v for _value, v in e.variants]
        assert len(set(variants)) == len(variants), e.name
