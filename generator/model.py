"""The intermediate model every back end renders from.

`parse_pyi.py` fills this in from `sonic_platform_api/facade.pyi`; the
templates read it and nothing else.  Keeping the model between them is what
lets the front end be replaced -- the stub is a choice, the model and the
templates are the asset.

Type mapping lives here as well, in `rust_type`, rather than in the templates.
A template that decides types is a template that has to be kept in step with
two other templates.
"""

import string
from dataclasses import dataclass, field
from typing import Any, Optional

# Python spelling -> Rust spelling, for the leaf types the facade uses.
SCALARS = {
    'str': 'String',
    'bool': 'bool',
    'float': 'f64',
    'int': 'i64',
    # `Number` and every unit spelled as one are Union[int, float] in the
    # stub because vendors return both and the daemons publish what they got:
    # not f64, so that the int/float distinction crosses.  See platform-api's
    # Number.
    'Number': 'Number',
    'Celsius': 'Number',
    'Threshold': 'Number',
    'Percent': 'Number',
    'Rpm': 'u32',
    'Watt': 'Number',
    'Volt': 'Number',
    'Ampere': 'Number',
    'PositionInParent': 'i32',
    'Index': 'u32',
    'Count': 'u32',
    # A newtype in platform-api, so rustc rejects a display name passed where
    # a key is expected.
    'DeviceKey': 'DeviceKey',
}


# Rust keywords a column name could collide with.  `r#` keeps the name
# identical to the Python one, which matters: the bridge looks the attribute up
# by that string, and a generator that renamed `type` to `type_` would have to
# remember which side of the boundary it was on.
RUST_KEYWORDS = {
    'as', 'async', 'await', 'box', 'break', 'const', 'continue', 'dyn', 'else',
    'enum', 'extern', 'false', 'fn', 'for', 'if', 'impl', 'in', 'let', 'loop',
    'match', 'mod', 'move', 'mut', 'pub', 'ref', 'return', 'static', 'struct',
    'trait', 'true', 'type', 'union', 'unsafe', 'use', 'where', 'while',
}
# These four cannot be raw identifiers at all.
RUST_RESERVED = {'self', 'Self', 'super', 'crate'}


@dataclass
class FieldSpec:
    """One column of a row."""

    name: str
    py_type: str                      # as written in the stub, e.g. 'Optional[Celsius]'
    base: str                         # the type inside any Optional[...]
    optional: bool
    from_: Optional[str] = None       # 'ThermalBase.get_temperature'
    at: Optional[int] = None          # slot of a tuple return
    is_parent: bool = False           # filled by the flatten plan, not by a call
    is_key: bool = False              # the row's DeviceKey, built by the traversal
    is_parent_key: bool = False       # the parent's DeviceKey, None for the chassis
    sentinels: tuple = ()
    coerce_from: tuple = ()
    truthy: bool = False              # normalise like Python's `if value:`
    narrowed: bool = False            # a vendor may narrow the getter's signature
    with_name: bool = False           # the getter takes the device's own name
    unguarded: bool = False           # read outside a per_row_errors row's guard
    read_if: Optional[str] = None     # read only when this earlier column has a value
    read_if_truthy: bool = False      # ... is truthy, Python's `if column:`
    read_if_absorbing: bool = True    # ... and also when the row is read absorbing
    row_error: Optional[str] = None   # 'str' | 'repr' | 'column': what went wrong reading the row
    secret: bool = False              # never printed by repr / Debug
    unsupported_on: str = 'none'      # none | default
    col_bit: Optional[int] = None     # bit in the row's column set, if projected
    default: Any = None
    doc: str = ''

    @property
    def rust_name(self) -> str:
        """The column, spelled so rustc accepts it."""
        if self.name in RUST_RESERVED:
            raise ValueError(
                '%r cannot be a Rust field name, even raw; rename the column'
                % self.name)
        return 'r#' + self.name if self.name in RUST_KEYWORDS else self.name

    @property
    def getter(self) -> str:
        return self.from_.split('.', 1)[1] if self.from_ else ''

    @property
    def owner(self) -> str:
        return self.from_.split('.', 1)[0] if self.from_ else ''


@dataclass
class SourceSpec:
    """One place a row type is collected from."""

    from_: str = ''
    mapping: str = ''
    provider: str = ''
    via: tuple = ()
    when: Optional[str] = None
    when_unsupported: str = 'absent'  # what an unanswered `when` means: absent | present
    when_chassis: Optional[str] = None
    parent: Optional[str] = None
    parent_missing: tuple = ()        # parent answers that count as no name
    parent_default: tuple = ()        # normalised to one entry per via level
    index_from_previous: bool = False # `{i}` carries on from the source before
    optional: bool = False
    single: bool = False
    reaches: tuple = ()
    sets: tuple = ()                  # ((field, value), ...); '@parent' is the parent name,
                                      # '@parent_raw' what the parent answered

    @property
    def leaf_getter(self) -> str:
        path = self.from_ or self.mapping
        return path.split('.', 1)[1] if path else ''

    @property
    def describes(self) -> str:
        if self.from_:
            return self.from_
        if self.mapping:
            return '%s (mapping)' % self.mapping
        return 'EscapeHatches.%s' % self.provider

    @property
    def via_getters(self) -> list:
        """(getter, single) per hop, outermost first."""
        return [(path.split('.', 1)[1], single) for path, single in self.via]

    @property
    def via_paths(self) -> list:
        return [path for path, _single in self.via]


@dataclass
class RowSpec:
    name: str
    doc: str = ''
    fields: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    singleton: bool = False   # the chassis is the device; nothing to flatten
    nested: bool = False      # appears only as a column of another row
    referenced: bool = False  # returned by a method, e.g. an escape hatch

    @property
    def snake(self) -> str:
        return _snake(self.name)


@dataclass
class MethodSpec:
    name: str
    params: list = field(default_factory=list)   # [(name, py_type)]
    returns: str = 'None'
    kind: str = 'action'                         # snapshot | action | escape
    row: Optional[str] = None                    # row type: the snapshot's, or the
                                                 # row an action addresses by key
    calls: Optional[str] = None                  # 'FanBase.set_status_led'
    calls_at: Optional[int] = None               # slot of a tuple return
    calls_ints: tuple = ()                       # bool parameters passed on as 1 / 0
    pass_key: bool = False                       # the locator is also arg 0
    singleton: bool = False                      # returns one row, not a list
    projected: bool = False                       # caller picks the columns
    skippable: bool = False                       # caller names rows to read in part
    per_row_errors: bool = False                  # a getter's exception costs one row
    absorbs: bool = False                         # a getter's exception costs one column
    absorbable: bool = False                      # the caller says, per call: `absorb`
    escape_reason: str = ''
    reaches: tuple = ()
    doc: str = ''


@dataclass
class EnumSpec:
    """A `Literal[...]` alias, which becomes a Rust enum."""

    name: str
    values: tuple

    @property
    def variants(self) -> list:
        return [(v, _pascal(v)) for v in self.values]


@dataclass
class Model:
    rows: list = field(default_factory=list)
    methods: list = field(default_factory=list)
    enums: list = field(default_factory=list)
    omitted: tuple = ()   # ((base-class path, reason), ...)
    deferred: tuple = ()  # ((base-class path, reason), ...), for a later phase

    def row(self, name):
        for r in self.rows:
            if r.name == name:
                return r
        return None

    @property
    def enum_names(self) -> set:
        return {e.name for e in self.enums}


# --------------------------------------------------------------------------

def _snake(name: str) -> str:
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i:
            out.append('_')
        out.append(ch.lower())
    return ''.join(out)


def _pascal(value: str) -> str:
    """A value as a Rust variant: 'LINE-CARD' is `LineCard`, 'PoweredDown' stays.

    A part already in mixed case keeps its case past the first letter.
    `str.capitalize()` alone lowercases the rest, which made the base class's
    'PoweredDown' the variant `Powereddown`.
    """
    # A '/' separates like a '-' does: 'N/A' becomes `NA`.
    cleaned = value.replace('/', '_').replace('-', '_').replace(' ', '_')
    return ''.join(p.capitalize() if p.isupper() or p.islower() else p[:1].upper() + p[1:]
                   for p in cleaned.split('_') if p)


def rust_type(py_type: str, enums: set) -> str:
    """Python spelling as written in the stub -> Rust spelling.

    Unknown names pass through, which is what makes a row type referring to
    another row type work without the mapping having to enumerate them.
    """
    t = py_type.strip()
    if t.startswith('Optional[') and t.endswith(']'):
        return 'Option<%s>' % rust_type(t[len('Optional['):-1], enums)
    if t.startswith('list[') and t.endswith(']'):
        return 'Vec<%s>' % rust_type(t[len('list['):-1], enums)
    if t in ('None', 'NoneType'):
        return '()'
    if t in enums:
        return t
    return SCALARS.get(t, t)


def key_segment(getter):
    """A key's step for one getter: the collection it answers, `get_` dropped.

    `get_all_fans` is `fans`; a getter answering one object, `get_watchdog`,
    is `watchdog`.  The step names the getter so that `_find_<row>()` can call
    it again without a table.
    """
    for prefix in ('get_all_', 'get_'):
        if getter.startswith(prefix):
            return getter[len(prefix):]
    return getter


def keyed(row):
    return any(f.is_key for f in row.fields)


def strip_optional(py_type: str):
    t = py_type.strip()
    if t.startswith('Optional[') and t.endswith(']'):
        return t[len('Optional['):-1].strip(), True
    return t, False


def template_fields(default):
    """The fields a fallback name formats besides `{parent}` and `{i}`: ones
    every source fixes, like a sensor's `{kind}` (parse_pyi checks that)."""
    out = []
    for _lit, ref, _spec, _conv in string.Formatter().parse(default):
        if ref is not None and ref not in ('parent', 'i') and ref not in out:
            out.append(ref)
    return out
