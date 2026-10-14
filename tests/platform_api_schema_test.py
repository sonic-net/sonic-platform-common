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
    Calls, EscapeHatch, Flatten, FlattenSource, From, Observed, On, Parent,
    Snapshot, Unsupported, Via, platform_method,
)
from .types import Celsius

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
    @platform_method(Snapshot(scope="per_cycle"))
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
    @platform_method(Unsupported(on="error"))
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


def test_an_escape_hatch_stays_one_however_else_it_is_decorated(tmp_path):
    body = GOOD_ROW + GOOD_API + '''
    @platform_method(EscapeHatch(reason="because"), Snapshot(scope="per_call"))
    def do_something(self) -> Foo: ...
'''
    model = parse(tmp_path, body)
    hatch = [m for m in model.methods if m.name == 'do_something'][0]
    assert hatch.kind == 'escape'
    assert hatch.row == 'Foo', 'the row it returns needs no ORDER of its own'


def test_a_via_may_be_singular(tmp_path):
    body = GOOD_ROW.replace(
        'FlattenSource("ChassisBase.get_all_foos", parent_default="chassis 1")',
        'FlattenSource("LiquidCoolingBase.get_all_foos", '
        'via=(Via("ChassisBase.get_liquid_cooling", single=True),), '
        'parent_default="chassis 1")') + GOOD_API
    model = parse(tmp_path, body)
    assert model.rows[0].sources[0].via == (('ChassisBase.get_liquid_cooling', True),)


# -- the type mapping ------------------------------------------------------

@pytest.mark.parametrize('py,rust', [
    ('str', 'String'),
    ('bool', 'bool'),
    ('Celsius', 'f64'),
    # Not f64: the int/float distinction is what `show platform temperature`
    # reads back out of STATE_DB, so it crosses as a type that keeps it.
    ('Threshold', 'Threshold'),
    ('Optional[Threshold]', 'Option<Threshold>'),
    ('Percent', 'u32'),
    ('PositionInParent', 'i32'),
    ('Optional[str]', 'Option<String>'),
    ('Optional[Celsius]', 'Option<f64>'),
    ('list[FanInfo]', 'Vec<FanInfo>'),
    ('Optional[LedColor]', 'Option<LedColor>'),
    ('None', '()'),
    ('SomethingUnknown', 'SomethingUnknown'),
])
def test_the_python_spelling_maps_to_the_rust_one(py, rust):
    assert rust_type(py, {'LedColor'}) == rust
