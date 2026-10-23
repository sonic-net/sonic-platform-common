"""The guard rails the stub is read through.

`mypy` checks that the metadata is well typed and `stubtest` checks that the
generated code matches the stub; neither can tell that a `Flatten` names a
field the row does not have, or that a source sets a column no other source
sets.  Those are what `parse_pyi._validate` is for -- and a guard rail nobody
tests is a guard rail that quietly stops holding.

Every case below is a declaration somebody could plausibly write.
"""

import os
import sys

import pytest

GENERATOR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'generator')
sys.path.insert(0, GENERATOR)

import parse_pyi  # noqa: E402
from model import rust_type  # noqa: E402

HEADER = '''
from typing import Annotated, ClassVar, Literal, Optional

from .meta import (
    Calls, EscapeHatch, Flatten, FlattenSource, From, Key, Observed, On, Parent,
    ParentKey, ReadIf, RowError, Snapshot, Unguarded, Unsupported, Via,
    platform_method,
)
from .types import Celsius, DeviceKey

Colour = Literal["green", "red"]
'''

GOOD_ROW = '''
class Foo:
    name: Annotated[str, From("DeviceBase.get_name")]
    parent_name: Annotated[str, Parent()]
    heat: Annotated[Optional[Celsius], From("ThermalBase.get_temperature")]

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1"),)
    )
'''

GOOD_API = '''
class PlatformApi:
    @platform_method(Snapshot())
    def get_foos(self) -> list[Foo]: ...
'''

# A row read device by device: keyed, guarded, skippable.
GUARDED_ROW = '''
class Foo:
    name: Annotated[str, From("DeviceBase.get_name"), Unguarded()]
    parent_name: Annotated[str, Parent()]
    key: Annotated[DeviceKey, Key()]
    parent_key: Annotated[Optional[DeviceKey], ParentKey()]
    heat: Annotated[Optional[Celsius], From("ThermalBase.get_temperature")]
    limit: Annotated[Optional[Celsius], From("ThermalBase.get_high_threshold"), ReadIf("heat")]
    error: Annotated[Optional[str], RowError()]
    error_repr: Annotated[Optional[str], RowError(repr=True)]
    error_column: Annotated[Optional[str], RowError(column=True)]

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1"),)
    )
'''

GUARDED_API = '''
class PlatformApi:
    @platform_method(Snapshot(projected=True, skippable=True, per_row_errors=True))
    def get_foos(self) -> list[Foo]: ...
'''


def parse(tmp_path, body):
    path = tmp_path / 'facade.pyi'
    path.write_text(HEADER + body)
    return parse_pyi.parse(str(path))


def refuses(tmp_path, body, fragment):
    with pytest.raises(parse_pyi.ParseError) as caught:
        parse(tmp_path, body)
    assert fragment in str(caught.value), str(caught.value)


def test_a_well_formed_declaration_parses(tmp_path):
    model = parse(tmp_path, GOOD_ROW + GOOD_API)
    assert [r.name for r in model.rows] == ['Foo']
    assert [m.name for m in model.methods] == ['get_foos']
    assert [e.name for e in model.enums] == ['Colour']


def test_a_row_with_no_order_and_nothing_returning_it_is_refused(tmp_path):
    body = GOOD_ROW.replace('''
    ORDER: ClassVar[Flatten] = Flatten(
        sources=(FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1"),)
    )
''', '') + GOOD_API.replace('list[Foo]', 'list[Foo]')
    refuses(tmp_path, body, 'no ORDER and nothing returns it')


def test_a_singleton_carrying_an_order_is_refused(tmp_path):
    body = GOOD_ROW + GOOD_API.replace('-> list[Foo]', '-> Foo')
    refuses(tmp_path, body, 'nothing flattens it')


def test_a_column_with_neither_from_nor_parent_is_refused(tmp_path):
    body = GOOD_ROW.replace(
        'heat: Annotated[Optional[Celsius], From("ThermalBase.get_temperature")]',
        'heat: Annotated[Optional[Celsius], Observed(sentinels=("N/A",))]') + GOOD_API
    refuses(tmp_path, body, 'neither From() nor Parent()')


def test_a_column_with_both_from_and_parent_is_refused(tmp_path):
    body = GOOD_ROW.replace(
        'parent_name: Annotated[str, Parent()]',
        'parent_name: Annotated[str, From("DeviceBase.get_name"), Parent()]'
    ) + GOOD_API
    refuses(tmp_path, body, 'both From() and Parent()')


def test_a_sentinel_on_an_enumeration_is_refused(tmp_path):
    # A Literal's values are answers; a sentinel there deletes one.
    body = GOOD_ROW.replace(
        'heat: Annotated[Optional[Celsius], From("ThermalBase.get_temperature")]',
        'heat: Annotated[Optional[Colour], From("FanBase.get_direction"), '
        'Observed(sentinels=("red",))]') + GOOD_API
    refuses(tmp_path, body, 'a sentinel here would delete a value')


def test_unknown_field_metadata_is_refused(tmp_path):
    body = GOOD_ROW.replace('From("DeviceBase.get_name")',
                            'Calls("DeviceBase.get_name")') + GOOD_API
    refuses(tmp_path, body, 'unknown field metadata')


def test_a_source_setting_a_column_the_row_lacks_is_refused(tmp_path):
    body = GOOD_ROW.replace('parent_default="chassis 1"',
                            'parent_default="chassis 1", sets=(("nope", 1),)') + GOOD_API
    refuses(tmp_path, body, 'sets unknown field')


def test_a_parent_column_no_source_fills_is_refused(tmp_path):
    body = GOOD_ROW.replace(
        'heat: Annotated[Optional[Celsius], From("ThermalBase.get_temperature")]',
        'kind: Annotated[str, Parent()]') + GOOD_API
    refuses(tmp_path, body, 'does not set it')


def test_a_parent_default_that_does_not_match_the_via_depth_is_refused(tmp_path):
    body = GOOD_ROW.replace(
        'FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1")',
        'FlattenSource("ModuleBase.get_all_foos", '
        'via=("ChassisBase.get_all_modules", "ModuleBase.get_all_bars"), '
        'parent_default="only one")') + GOOD_API
    refuses(tmp_path, body, 'parent_default has 1 entries for 2 via level')


def test_a_parent_default_mismatch_on_a_mapping_source_names_the_mapping(tmp_path):
    # A mapping= source has no positional argument; naming the source by its
    # first one turned this error into an IndexError that named nothing.
    body = GOOD_ROW.replace(
        'FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1")',
        'FlattenSource(mapping="ChassisBase.get_foo_map", '
        'parent_default=("one", "two"))') + GOOD_API
    refuses(tmp_path, body,
            'ChassisBase.get_foo_map: parent_default has 2 entries for 1 via level')


def test_a_parent_default_mismatch_on_a_provider_source_names_the_provider(tmp_path):
    body = GOOD_ROW.replace(
        'FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1")',
        'FlattenSource(provider="foos", parent_default=("one", "two"))') + GOOD_API
    refuses(tmp_path, body, 'foos: parent_default has 2 entries for 1 via level')


def test_a_limit_that_is_not_optional_is_refused(tmp_path):
    # There is no neutral limit to fall back to, and the Rust row could no
    # longer derive Default; the generator used to emit an Option where the
    # field was declared bare, which did not compile.
    body = GOOD_ROW.replace(
        'heat: Annotated[Optional[Celsius], From("ThermalBase.get_temperature")]',
        'heat: Annotated[Threshold, From("ThermalBase.get_high_threshold")]') + GOOD_API
    refuses(tmp_path, body, 'Foo.heat: a Threshold has no neutral value')


def test_an_optional_limit_is_accepted(tmp_path):
    body = GOOD_ROW.replace(
        'heat: Annotated[Optional[Celsius], From("ThermalBase.get_temperature")]',
        'heat: Annotated[Optional[Threshold], From("ThermalBase.get_high_threshold")]'
    ) + GOOD_API
    assert parse(tmp_path, body).rows[0].fields[-1].base == 'Threshold'


def test_a_source_with_two_origins_is_refused(tmp_path):
    body = GOOD_ROW.replace(
        'FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1")',
        'FlattenSource("ChassisBase.get_all_foos", mapping="ChassisBase.get_map", '
        'parent_default="chassis 1")') + GOOD_API
    refuses(tmp_path, body, 'exactly one of from_, mapping or provider')


def test_a_source_with_no_origin_is_refused(tmp_path):
    body = GOOD_ROW.replace(
        'FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1")',
        'FlattenSource(parent_default="chassis 1")') + GOOD_API
    refuses(tmp_path, body, 'exactly one of from_, mapping or provider')


def test_an_order_that_is_not_a_flatten_is_refused(tmp_path):
    body = GOOD_ROW.replace('Flatten(\n        sources=', 'Observed(\n        sources=') \
        + GOOD_API
    refuses(tmp_path, body, 'ORDER must be a Flatten')


def test_a_via_entry_that_is_neither_a_path_nor_a_via_is_refused(tmp_path):
    body = GOOD_ROW.replace(
        'FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1")',
        'FlattenSource("ModuleBase.get_all_foos", via=(3,), parent_default="c")') \
        + GOOD_API
    refuses(tmp_path, body, 'via takes a path or a Via()')


def test_a_snapshot_returning_an_undeclared_row_is_refused(tmp_path):
    body = GOOD_ROW + GOOD_API.replace('list[Foo]', 'list[Nope]')
    refuses(tmp_path, body, 'returns undeclared row')


def test_an_action_without_calls_is_refused(tmp_path):
    body = GOOD_ROW + GOOD_API + '''
    def do_something(self) -> None: ...
'''
    refuses(tmp_path, body, 'must declare Calls(), or be an EscapeHatch')


def test_an_action_addressing_an_undeclared_row_is_refused(tmp_path):
    body = GOOD_ROW + GOOD_API + '''
    @platform_method(On(row="Nope"), Calls("FanBase.set_speed"))
    def do_something(self, who: str) -> None: ...
'''
    refuses(tmp_path, body, 'addresses undeclared row')


def test_an_action_with_on_but_no_locator_parameter_is_refused(tmp_path):
    body = GOOD_ROW + GOOD_API + '''
    @platform_method(On(row="Foo"), Calls("FanBase.set_speed"))
    def do_something(self) -> None: ...
'''
    refuses(tmp_path, body, 'On() needs a first parameter')


def test_unknown_method_metadata_is_refused(tmp_path):
    body = GOOD_ROW + GOOD_API + '''
    @platform_method(Parent())
    def do_something(self) -> None: ...
'''
    refuses(tmp_path, body, 'unknown method metadata')


def test_an_escape_hatch_answers_a_row_that_needs_no_order(tmp_path):
    body = GOOD_ROW + GOOD_API + '''
    @platform_method(EscapeHatch(reason="because"))
    def do_something(self) -> Foo: ...
'''
    model = parse(tmp_path, body)
    hatch = [m for m in model.methods if m.name == 'do_something'][0]
    assert hatch.kind == 'escape'
    assert hatch.row == 'Foo', 'the row it returns needs no ORDER of its own'


def test_an_escape_hatch_that_is_also_a_snapshot_is_refused(tmp_path):
    # Nothing a Snapshot says reaches a hand-written body, so it would be a
    # declaration that changes nothing.
    body = GOOD_ROW + GOOD_API + '''
    @platform_method(EscapeHatch(reason="because"), Snapshot())
    def do_something(self) -> Foo: ...
'''
    refuses(tmp_path, body, 'an EscapeHatch is not also a Snapshot')


# -- metadata that was declared and never generated --------------------------

def test_a_snapshot_scope_is_refused(tmp_path):
    refuses(tmp_path, GOOD_ROW + GOOD_API.replace('Snapshot()', 'Snapshot(scope="per_cycle")'),
            'Snapshot(scope=...) is not implemented')


def test_unsupported_on_a_method_is_refused(tmp_path):
    body = GOOD_ROW + GOOD_API + '''
    @platform_method(Calls("FanBase.set_speed"), Unsupported(on="error"))
    def do_something(self) -> None: ...
'''
    refuses(tmp_path, body, 'Unsupported() on a method is not implemented')


def test_a_field_unsupported_on_error_is_refused(tmp_path):
    body = GOOD_ROW.replace('From("ThermalBase.get_temperature")',
                            'From("ThermalBase.get_temperature"), Unsupported(on="error")') + GOOD_API
    refuses(tmp_path, body, 'Unsupported(on=\'error\') is not implemented')


# -- per_row_errors, skippable, Unguarded and ReadIf --------------------------

def test_a_guarded_skippable_row_parses(tmp_path):
    model = parse(tmp_path, GUARDED_ROW + GUARDED_API)
    snap = model.methods[0]
    assert (snap.projected, snap.skippable, snap.per_row_errors) == (True, True, True)
    fields = {f.name: f for f in model.rows[0].fields}
    assert fields['name'].unguarded and not fields['heat'].unguarded
    assert fields['limit'].read_if == 'heat'
    assert (fields['error'].row_error, fields['error_repr'].row_error,
            fields['error_column'].row_error) == ('str', 'repr', 'column')


@pytest.mark.parametrize('api, fragment', [
    ('Snapshot(projected=True, skippable=True)',
     'declares RowError() columns, but no snapshot answering it is per_row_errors'),
    ('Snapshot(per_row_errors=True, skippable=True)', 'skippable needs projected'),
])
def test_the_guard_and_its_snapshot_have_to_agree(tmp_path, api, fragment):
    body = GUARDED_ROW + GUARDED_API.replace(
        'Snapshot(projected=True, skippable=True, per_row_errors=True)', api)
    refuses(tmp_path, body, fragment)


def test_a_per_row_errors_row_without_its_error_columns_is_refused(tmp_path):
    body = GOOD_ROW + GOOD_API.replace('Snapshot()', 'Snapshot(per_row_errors=True)')
    refuses(tmp_path, body, 'declares `error`, `error_repr` and `error_column` as RowError()')


@pytest.mark.parametrize('old, new, fragment', [
    ('error: Annotated[Optional[str], RowError()]', 'err: Annotated[Optional[str], RowError()]',
     'RowError() is spelled `error: Optional[str]`'),
    ('error_column: Annotated[Optional[str], RowError(column=True)]',
     'failed: Annotated[Optional[str], RowError(column=True)]',
     'RowError(column=True) is spelled `error_column: Optional[str]`'),
    ('error_column: Annotated[Optional[str], RowError(column=True)]',
     'error_column: Annotated[Optional[str], RowError(repr=True, column=True)]',
     'RowError() is the message, its repr or the column'),
    ('error_column: Annotated[Optional[str], RowError(column=True)]\n', '',
     'declares `error`, `error_repr` and `error_column`'),
    ('    key: Annotated[DeviceKey, Key()]\n    parent_key: Annotated[Optional[DeviceKey], ParentKey()]\n',
     '', 'skippable names rows by key'),
    ('From("DeviceBase.get_name"), Unguarded()', 'From("DeviceBase.get_name")',
     'a skipped row still reads its name'),
    ('ReadIf("heat")', 'ReadIf("later")', 'ReadIf(\'later\') names no column read before it'),
    ('heat: Annotated[Optional[Celsius], From("ThermalBase.get_temperature")]',
     'heat: Annotated[Optional[Celsius], From("ThermalBase.get_temperature"), Unguarded()]',
     'ReadIf(\'heat\') across the guard'),
    ('parent_name: Annotated[str, Parent()]', 'parent_name: Annotated[str, Parent(), Unguarded()]',
     'Unguarded() is for a column read off the device'),
])
def test_a_guard_declaration_that_cannot_hold_is_refused(tmp_path, old, new, fragment):
    assert old in GUARDED_ROW
    refuses(tmp_path, GUARDED_ROW.replace(old, new) + GUARDED_API, fragment)


# -- absorbing: psud's try_get ---------------------------------------------------

def test_an_absorbing_snapshot_parses(tmp_path):
    model = parse(tmp_path, GOOD_ROW + GOOD_API.replace('Snapshot()', 'Snapshot(absorbs=True)'))
    assert (model.methods[0].absorbs, model.methods[0].absorbable) == (True, False)
    body = GUARDED_ROW + GUARDED_API.replace('per_row_errors=True', 'per_row_errors=True,'
                                             ' absorbable=True')
    body = body.replace(', Unguarded()', '').replace('skippable=True, ', '')
    assert parse(tmp_path, body).methods[0].absorbable


@pytest.mark.parametrize('snapshot, fragment', [
    ('Snapshot(absorbs=True, per_row_errors=True)', 'would never be used'),
    ('Snapshot(absorbable=True)', 'declare per_row_errors too'),
    ('Snapshot(absorb=True)', 'Snapshot(absorb) is not implemented'),
])
def test_an_absorbing_snapshot_that_cannot_hold_is_refused(tmp_path, snapshot, fragment):
    refuses(tmp_path, GOOD_ROW + GOOD_API.replace('Snapshot()', snapshot), fragment)


def test_an_absorbing_row_has_no_error_columns_to_set(tmp_path):
    body = GUARDED_ROW.replace(', Unguarded()', '') + GUARDED_API.replace(
        'Snapshot(projected=True, skippable=True, per_row_errors=True)', 'Snapshot(absorbs=True)')
    refuses(tmp_path, body, 'no snapshot answering it is per_row_errors')


def test_absorbing_and_unguarded_are_not_one_mode(tmp_path):
    body = GUARDED_ROW + GUARDED_API.replace(
        'Snapshot(projected=True, skippable=True, per_row_errors=True)',
        'Snapshot(projected=True, per_row_errors=True, absorbable=True)')
    refuses(tmp_path, body, 'Unguarded() and absorbing are not one mode')


# -- ReadIf(truthy=..., when_absorbing=...) ---------------------------------------

ABSORBABLE_FANS = '''
class Foo:
    name: Annotated[str, From("DeviceBase.get_name")]
    parent_name: Annotated[str, Parent()]
    key: Annotated[DeviceKey, Key()]
    parent_key: Annotated[Optional[DeviceKey], ParentKey()]
    here: Annotated[bool, From("DeviceBase.get_presence"), Unsupported(on="default", default=False)]
    speed: Annotated[Optional[Celsius], From("FanBase.get_speed"),
                     ReadIf("here", truthy=True, when_absorbing=False)]
    ok: Annotated[bool, From("DeviceBase.get_status"), Unsupported(on="default", default=False),
                  ReadIf("here", truthy=True, when_absorbing=False)]
    error: Annotated[Optional[str], RowError()]
    error_repr: Annotated[Optional[str], RowError(repr=True)]
    error_column: Annotated[Optional[str], RowError(column=True)]

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1"),)
    )

class PlatformApi:
    @platform_method(Snapshot(projected=True, per_row_errors=True, absorbable=True))
    def get_foos(self) -> list[Foo]: ...
'''


def test_a_truthy_gate_lifted_when_absorbing_parses(tmp_path):
    fields = {f.name: f for f in parse(tmp_path, ABSORBABLE_FANS).rows[0].fields}
    assert (fields['speed'].read_if, fields['speed'].read_if_truthy,
            fields['speed'].read_if_absorbing) == ('here', True, False)
    # A column with a default may be gated: not read is its default.
    assert fields['ok'].read_if == 'here'


@pytest.mark.parametrize('old, new, fragment', [
    ('Snapshot(projected=True, per_row_errors=True, absorbable=True)',
     'Snapshot(projected=True, per_row_errors=True)',
     'ReadIf(when_absorbing=False) means something only on a snapshot that is absorbable'),
    ('ok: Annotated[bool, From("DeviceBase.get_status"), Unsupported(on="default", default=False),',
     'ok: Annotated[bool, From("DeviceBase.get_status"),',
     'ReadIf() is for a column read off the device that is Optional or has a default'),
])
def test_a_gate_that_cannot_hold_is_refused(tmp_path, old, new, fragment):
    assert old in ABSORBABLE_FANS
    refuses(tmp_path, ABSORBABLE_FANS.replace(old, new), fragment)


# -- Calls(ints=...) ------------------------------------------------------------

def test_a_bool_passed_on_as_an_int_parses(tmp_path):
    body = GOOD_ROW + '''
class PlatformApi:
    @platform_method(Snapshot())
    def get_foos(self) -> list[Foo]: ...
    @platform_method(Calls("ChassisBase.set_state", ints=("up",)))
    def set_state(self, up: bool) -> Optional[bool]: ...
'''
    m = [m for m in parse(tmp_path, body).methods if m.name == 'set_state'][0]
    assert m.calls_ints == ('up',)


@pytest.mark.parametrize('param', ['up: int', 'down: bool'])
def test_ints_names_a_bool_parameter(tmp_path, param):
    body = GOOD_ROW + '''
class PlatformApi:
    @platform_method(Snapshot())
    def get_foos(self) -> list[Foo]: ...
    @platform_method(Calls("ChassisBase.set_state", ints=("up",)))
    def set_state(self, %s) -> Optional[bool]: ...
''' % param
    refuses(tmp_path, body, "Calls(ints=...) names 'up', which is not a bool parameter")


def test_a_float_column_is_refused(tmp_path):
    body = GOOD_ROW.replace('Optional[Celsius]', 'Optional[float]') + GOOD_API
    refuses(tmp_path, body, 'Foo.heat: a float column would publish an int')


def test_a_reading_that_is_not_optional_is_refused(tmp_path):
    body = GOOD_ROW.replace('Optional[Celsius]', 'Celsius') + GOOD_API
    refuses(tmp_path, body, 'Foo.heat: a Celsius has no neutral value')


def test_unguarded_on_a_row_read_in_one_go_is_refused(tmp_path):
    body = GOOD_ROW.replace('From("ThermalBase.get_temperature")',
                            'From("ThermalBase.get_temperature"), Unguarded()') + GOOD_API
    refuses(tmp_path, body, 'Unguarded() means something only on a row whose snapshot')


def test_a_singleton_cannot_keep_other_rows(tmp_path):
    body = '''
class Foo:
    name: Annotated[str, From("DeviceBase.get_name")]
    error: Annotated[Optional[str], RowError()]
    error_repr: Annotated[Optional[str], RowError(repr=True)]
    error_column: Annotated[Optional[str], RowError(column=True)]

class PlatformApi:
    @platform_method(Snapshot(per_row_errors=True))
    def get_foo(self) -> Foo: ...
'''
    refuses(tmp_path, body, 'a singleton has no other rows to keep')


# -- what a source may say about its parent ------------------------------------

@pytest.mark.parametrize('source, fragment', [
    ('FlattenSource("ChassisBase.get_all_foos", when_unsupported="present", '
     'parent_default="chassis 1")', 'when_unsupported without a when'),
    ('FlattenSource("FanDrawerBase.get_all_foos", via=("ChassisBase.get_all_fan_drawers",), '
     'when="get_presence", when_unsupported="maybe", parent="get_name", '
     'parent_default="chassis 1")', 'when_unsupported is "absent" or "present"'),
    ('FlattenSource("ChassisBase.get_all_foos", parent_missing=("N/A",), '
     'parent_default="chassis 1")', 'parent_missing needs a parent getter'),
    ('FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1", '
     'sets=(("parent_name", "@parent_raw"),))', '"@parent_raw" needs a parent getter'),
])
def test_a_parent_option_with_nothing_to_apply_to_is_refused(tmp_path, source, fragment):
    body = GOOD_ROW.replace(
        'FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1")', source) + GOOD_API
    refuses(tmp_path, body, fragment)


def test_a_via_may_be_singular(tmp_path):
    body = GOOD_ROW.replace(
        'FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1")',
        'FlattenSource("LiquidCoolingBase.get_all_foos", '
        'via=(Via("ChassisBase.get_liquid_cooling", single=True),), '
        'parent_default="chassis 1")') + GOOD_API
    model = parse(tmp_path, body)
    assert model.rows[0].sources[0].via == (('ChassisBase.get_liquid_cooling', True),)


# -- one numbering over two sources, and what a fallback name may name --------

ONE = 'FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1")'


def two_sources(first, second):
    return GOOD_ROW.replace(ONE, '%s, %s' % (first, second)) + GOOD_API


def test_a_source_may_count_on_from_the_one_before(tmp_path):
    model = parse(tmp_path, two_sources(
        ONE, 'FlattenSource("ChassisBase.get_all_bars", parent_default="chassis 1", '
             'index_from_previous=True)'))
    assert [s.index_from_previous for s in model.rows[0].sources] == [False, True]


@pytest.mark.parametrize('first, second, fragment', [
    (ONE.replace(')', ', index_from_previous=True)'), None, 'on the first source'),
    (ONE, 'FlattenSource("ModuleBase.get_all_bars", via=("ChassisBase.get_all_modules",), '
          'parent="get_name", parent_default="Module {i}", index_from_previous=True)',
     'plain lists under one fixed parent'),
    ('FlattenSource("ModuleBase.get_all_foos", via=("ChassisBase.get_all_modules",), '
     'parent="get_name", parent_default="Module {i}")',
     'FlattenSource("ChassisBase.get_all_bars", parent_default="Module {i}", '
     'index_from_previous=True)', 'plain lists under one fixed parent'),
    (ONE, 'FlattenSource("ChassisBase.get_all_bars", parent_default="chassis 2", '
          'index_from_previous=True)', 'under another parent'),
    ('FlattenSource("ChassisBase.get_all_foos", parent_default="PSU {i}")',
     'FlattenSource("ChassisBase.get_all_bars", parent_default="PSU {i}", '
     'index_from_previous=True)', 'a parent named by position'),
])
def test_counting_on_where_there_is_no_one_list_is_refused(tmp_path, first, second, fragment):
    body = (GOOD_ROW.replace(ONE, first) + GOOD_API if second is None
            else two_sources(first, second))
    refuses(tmp_path, body, fragment)


KINDED_ROW = GOOD_ROW.replace(
    'name: Annotated[str, From("DeviceBase.get_name")]',
    'name: Annotated[str, From("DeviceBase.get_name"), '
    'Unsupported(on="default", default="{parent} {kind}_foo {i}")]\n'
    '    kind: Annotated[str, Parent()]')


def test_a_fallback_name_may_name_a_field_every_source_sets(tmp_path):
    body = KINDED_ROW.replace(ONE, ONE.replace(')', ', sets=(("kind", "big"),))')) + GOOD_API
    assert parse(tmp_path, body).rows[0].sources[0].sets == (('kind', 'big'),)


@pytest.mark.parametrize('default, second_sets, ref', [
    # `kind` is a field, but the second source does not set it.
    ('{parent} {kind}_foo {i}', '', 'kind'),
    # `colour` is not a field at all.
    ('{parent} {colour} {i}', ', sets=(("kind", "small"),)', 'colour'),
])
def test_a_fallback_name_naming_what_not_every_source_sets_is_refused(
        tmp_path, default, second_sets, ref):
    first = ONE.replace(')', ', sets=(("kind", "big"),))')
    second = 'FlattenSource("ChassisBase.get_all_bars", parent_default="chassis 1"%s)' % second_sets
    body = KINDED_ROW.replace('{parent} {kind}_foo {i}', default).replace(
        ONE, '%s, %s' % (first, second)) + GOOD_API
    refuses(tmp_path, body, 'names {%s}' % ref)


# -- the type mapping ------------------------------------------------------

@pytest.mark.parametrize('py,rust', [
    ('str', 'String'),
    ('bool', 'bool'),
    # Not f64: the int/float distinction is what `show platform temperature`
    # reads back out of STATE_DB, so a reading or a limit crosses as a type
    # that keeps it.
    ('Number', 'Number'),
    ('Celsius', 'Number'),
    ('Threshold', 'Number'),
    ('Optional[Threshold]', 'Option<Number>'),
    ('Percent', 'Number'),
    ('Watt', 'Number'),
    ('Volt', 'Number'),
    ('Ampere', 'Number'),
    ('float', 'f64'),
    ('PositionInParent', 'i32'),
    ('Optional[str]', 'Option<String>'),
    ('Optional[Celsius]', 'Option<Number>'),
    ('list[FanInfo]', 'Vec<FanInfo>'),
    ('Optional[LedColor]', 'Option<LedColor>'),
    ('None', '()'),
    ('SomethingUnknown', 'SomethingUnknown'),
])
def test_the_python_spelling_maps_to_the_rust_one(py, rust):
    assert rust_type(py, {'LedColor'}) == rust
