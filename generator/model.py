#
# SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
# Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""The intermediate model every back end renders from.

`parse_pyi.py` fills this in from `platform_api/facade.pyi`; the templates
read it and nothing else.  Keeping the model between them is what lets the
front end be replaced -- the stub is a choice, the model and the templates are
the asset.

Type mapping lives here as well, in `rust_type`, rather than in the templates.
A template that decides types is a template that has to be kept in step with
two other templates.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

# Python spelling -> Rust spelling, for the leaf types the facade uses.
# Threshold is Union[int, float] in the stub because vendors return both; it
# lands on f64 and the coercion happens at the boundary.
SCALARS = {
    'str': 'String',
    'bool': 'bool',
    'float': 'f64',
    'int': 'i64',
    'Celsius': 'f64',
    # Not f64: the int/float distinction is load-bearing downstream, so it
    # crosses as a type that keeps it.  See platform-api's Threshold.
    'Threshold': 'Threshold',
    'Percent': 'u32',
    'Rpm': 'u32',
    'Watt': 'f64',
    'Volt': 'f64',
    'Ampere': 'f64',
    'PositionInParent': 'i32',
    'Index': 'u32',
    'Count': 'u32',
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
    sentinels: tuple = ()
    coerce_from: tuple = ()
    unsupported_on: str = 'none'      # none | default | error
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
    when_chassis: Optional[str] = None
    parent: Optional[str] = None
    parent_default: tuple = ()        # normalised to one entry per via level
    optional: bool = False
    single: bool = False
    reaches: tuple = ()
    sets: tuple = ()                  # ((field, value), ...); '@parent' is the parent name

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
                                                 # row an action addresses by name
    calls: Optional[str] = None                  # 'FanBase.set_status_led'
    pass_key: bool = False                       # the locator is also arg 0
    singleton: bool = False                      # returns one row, not a list
    snapshot_scope: Optional[str] = None
    unsupported_on: Optional[str] = None
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
    # 'N/A' is a real value of FanDirection, not a separator.
    cleaned = value.replace('/', '_').replace('-', '_').replace(' ', '_')
    return ''.join(p.capitalize() for p in cleaned.split('_') if p)


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


def strip_optional(py_type: str):
    t = py_type.strip()
    if t.startswith('Optional[') and t.endswith(']'):
        return t[len('Optional['):-1].strip(), True
    return t, False
