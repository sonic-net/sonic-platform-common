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
"""Render the back ends from the model.

The expressions and the traversal bodies are built here rather than in the
templates.  A template that decides how a sentinel is normalised is a template
that has to be kept in step with the two other templates that decide the same
thing; the point of the exercise is that they cannot drift.

Outputs are checked in.  `--check` re-renders and compares, which is what CI
runs: a stub edited without regenerating fails there rather than at the next
person to touch it.
"""

import argparse
import json
import os
import re
import sys

import jinja2

from model import _snake as _snake_of, rust_type
from parse_pyi import parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
TEMPLATES = os.path.join(HERE, 'templates')

_LICENCE = '''SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.'''


def _header(path):
    """The same licence, in the comment syntax of the file it heads."""
    mark = '//' if path.endswith('.rs') else '#'
    lines = [mark] + ['%s %s' % (mark, ln) if ln else mark
                      for ln in _LICENCE.split('\n')] + [mark]
    return '\n'.join(lines)


OUTPUTS = {
    'facade.py.j2': os.path.join(ROOT, 'platform_api', 'facade.py'),
    'trait.rs.j2': os.path.join(ROOT, 'crates', 'platform-api', 'src', 'generated.rs'),
    'trait_sweep.rs.j2': os.path.join(
        ROOT, 'crates', 'platform-api', 'tests', 'generated_sweep.rs'),
    'bridge.rs.j2': os.path.join(ROOT, 'crates', 'platform-pyo3', 'src', 'generated.rs'),
    'provider.rs.j2': os.path.join(ROOT, 'crates', 'platform-provider', 'src', 'generated.rs'),
    'provider_sweep.rs.j2': os.path.join(
        ROOT, 'crates', 'platform-provider', 'tests', 'generated_sweep.rs'),
    'allowlist.txt.j2': os.path.join(ROOT, 'platform_api', 'stubtest_allowlist.txt'),
}

# Semantic integer types.  A vendor is free to return 50.0 where the base class
# documents an int, so the bridge reads every number as f64 and casts here
# rather than asking PyO3 for a u32 and failing on a float that is a whole
# number anyway.
INT_CASTS = {'u32', 'i32', 'i64', 'u64'}

IND = ' ' * 8


# --------------------------------------------------------------------------
# Python expressions, one per field
# --------------------------------------------------------------------------

def _py_base_call(f):
    """The call that produces the field's raw answer, before `at` slices it."""
    call = 'dev'
    hops = f.getter.split('.')
    for i, hop in enumerate(hops):
        # Only the final hop is the one a vendor narrows -- the hops before it
        # walk the object tree and a TypeError there would be a real bug.
        last = i == len(hops) - 1
        call = ('_call_narrowed(_get(%s, %r))' if (last and f.narrowed)
                else '_call(_get(%s, %r))') % (call, hop)
    return call


def _share_calls(row):
    """Columns that slice the same call get one call between them.

    Bug 15.  `ChassisInfo.reboot_cause` and `.reboot_cause_detail` are `at=0`
    and `at=1` of `ChassisBase.get_reboot_cause()`, and each column expanded
    its own call -- so the row asked the platform twice, every polling cycle,
    and pasted one slot of each answer together.

    The two answers need not agree.  mlnx's `Chassis.get_reboot_cause`
    (chassis.py:1421) reads sysfs flags and returns from whichever branch
    matches: the major branch answers `(cause, '')` and the minor one
    `(HARDWARE_OTHER, cause)` -- the halves mean different things.  A flag
    cleared between the two calls yields a row whose cause came from one
    reading and whose detail came from another: both fields legal, the pair
    never produced by anything.  It is silent, because nothing downstream can
    tell a pasted row from a read one.

    The correctness argument is the whole argument; the cost one does not
    hold up.  Measured on a SmartSwitch, that getter answers in 0.00 s and logs
    nothing -- it takes an early return and its INFO lines sit below the
    syslog threshold.  The paths that would make a second call expensive
    (`_wait_reboot_cause_ready()`'s sleep loop, the three `log_info` calls)
    exist, but are not what this switch executes.  Sharing the call is worth
    doing because two readings can disagree, not because two readings are
    slow.

    Grouping is by the generated call expression, not by the getter name, so
    two columns only share when the call really is the same one.
    """
    seen = {}
    row.shared_calls = []
    for f in row.fields:
        f.shared_var = None
        if f.is_parent or f.with_name or f.at is None or not f.getter:
            continue
        seen.setdefault(_py_base_call(f), []).append(f)
    for call, fields in seen.items():
        if len(fields) < 2:
            continue
        var = '_shared%d' % len(row.shared_calls)
        # A shared call has to be declinable too, or a projection buys nothing
        # where it would buy most: `ChassisBase.get_reboot_cause` is shared by
        # two columns and is the getter with the sleep loop, and a caller that
        # wants neither would still wait for it.  The mask is every bit that
        # slices this call; `None` when no bit is set, which is what the
        # columns' own gates already read as absent.
        mask = 0
        for f in fields:
            if f.col_bit is not None:
                mask |= 1 << f.col_bit
        row.shared_calls.append((var, call, mask if row.projected else None))
        for f in fields:
            f.shared_var = var


def _assign_col_bits(row):
    """Number the columns a projected row can be asked for.

    The bit is the column's position among the ones a caller can decline, in
    declaration order.  It is derived, never hand-written, and both sides are
    emitted from this one pass -- `generate.py --check` is what keeps the
    Python mask and the Rust constant from drifting.

    `Parent()` columns come from the traversal rather than a getter, so there
    is nothing to decline; `name` is always read because `_find_<row>()` walks
    the same rows to resolve a name, and a walk that could not see names would
    not find anything.
    """
    bit = 0
    for f in row.fields:
        f.col_bit = None
        if f.is_parent or not f.getter or f.name == 'name':
            continue
        f.col_bit = bit
        bit += 1
    row.col_count = bit
    row.all_cols = (1 << bit) - 1
    if bit > 64:
        raise ValueError('%s: %d projectable columns will not fit a u64'
                         % (row.name, bit))


def _gated(f, expr):
    """The column's expression, behind its projection bit if it has one.

    A column the caller did not ask for is not read at all: running the getter
    is the cost -- and for some of them the log line -- that the projection
    exists to avoid.  Absent reads as whatever the column would hold if the
    platform did not implement it.
    """
    if f.col_bit is None:
        return expr
    absent = repr(f.default) if f.unsupported_on == 'default' else 'None'
    return '(%s) if cols & (1 << %d) else %s' % (expr, f.col_bit, absent)


def _py_field_expr(f, enums=()):
    """How `facade.py` fills one column of one row.

    `enums` are the `Literal` aliases; a column typed as one of them is
    declared to be a string, so whatever the vendor answers with is narrowed
    to that by `_enum()` before it leaves the facade.
    """
    if f.is_parent:
        if f.name == 'parent_name':
            return 'parent'
        return 'fixed[%r]' % f.name

    if f.with_name:
        # One hop only: the getter is on the device itself and takes its name.
        # Falls through to the projection gate below rather than returning
        # here: a `WithName` column is declinable like any other, and an early
        # return would hand the caller a bit it cannot actually turn off.
        assert '.' not in f.getter, '%s: WithName does not compose with a path' % f.name
        expr = "_call_with_name(_get(dev, 'get_name'), _get(dev, %r))" % f.getter
        return _gated(f, expr)

    call = f.shared_var or _py_base_call(f)
    if f.at is not None:
        call = '_at(%s, %d)' % (call, f.at)

    if f.base in enums:
        call = '_enum(%s)' % call

    if f.truthy:
        expr = '_truthy(%s)' % call
    elif f.sentinels or f.coerce_from:
        expr = '_scalar(%s, %r, %r)' % (call, tuple(f.sentinels), tuple(f.coerce_from))
    elif f.unsupported_on == 'default':
        if isinstance(f.default, str) and '{' in f.default:
            expr = '_fmt(%s, %r, parent, i)' % (call, f.default)
        else:
            expr = '_default(%s, %r)' % (call, f.default)
    else:
        expr = call

    return _gated(f, expr)


# --------------------------------------------------------------------------
# Rust expressions, one per field
# --------------------------------------------------------------------------

def _rust_default(f, ty):
    """The Rust literal for a field declared with an `Unsupported` default."""
    if f.default is None:
        return 'Default::default()'
    if isinstance(f.default, bool):
        return 'true' if f.default else 'false'
    if isinstance(f.default, (int, float)):
        return repr(f.default)
    if isinstance(f.default, str):
        # A format string is resolved on the Python side; by the time the row
        # crosses, the field already holds the resolved name.
        return 'String::new()' if ty == 'String' else json.dumps(f.default)
    return 'Default::default()'


def _rust_field_expr(f, enums, rows=()):
    """How the bridge reads one column off a row the facade handed back."""
    ty = f.rust_ty
    if ty.startswith('Vec<') and ty[4:-1] in rows:
        # A column that is a list of rows.  The only one so far is the batch
        # of device changes, whose two-level mapping the facade has already
        # flattened; reading it here is the same loop as a snapshot.
        return 'rows(row, %s, %s)?' % (json.dumps(f.name), _snake_of(ty[4:-1]))
    inner = ty[len('Option<'):-1] if ty.startswith('Option<') else ty
    key = f.name

    if inner in enums:
        base = 'text(row, %s)?.and_then(|s| %s::from_str(&s))' % (json.dumps(key), inner)
        if f.optional:
            return base
        return ('%s.ok_or_else(|| PlatformError::Backend(%s.to_string()))?'
                % (base, json.dumps('%s is missing or not a declared value' % key)))

    if inner == 'String':
        return 'text(row, %s)?' % json.dumps(key) if f.optional else \
            'text(row, %s)?.unwrap_or_default()' % json.dumps(key)

    if inner == 'bool':
        return 'flag(row, %s)?' % json.dumps(key) if f.optional else \
            'flag(row, %s)?.unwrap_or(%s)' % (json.dumps(key), _rust_default(f, inner))

    if inner == 'Threshold':
        return 'threshold(row, %s)?' % json.dumps(key)
    cast = '.map(|v| v as %s)' % inner if inner in INT_CASTS else ''
    got = 'num(row, %s)?%s' % (json.dumps(key), cast)
    if f.optional:
        return got
    return '%s.unwrap_or(%s)' % (got, _rust_default(f, inner))


def _rust_ret_conv(rust_ret, enums, rows=()):
    """How the bridge turns a returned Python value into the declared type.

    Same shape as the field readers, and for the same reason: a generated
    enum has no `FromPyObject`, and asking PyO3 for a u32 fails on a platform
    that answered with a whole-number float.
    """
    inner = rust_ret[len('Option<'):-1] if rust_ret.startswith('Option<') else rust_ret
    optional = rust_ret.startswith('Option<')
    if inner.startswith('Vec<') and inner[4:-1] in rows:
        reader = _snake_of(inner[4:-1])
        return ('let mut out = Vec::new();\n'
                '            for item in v.try_iter().map_err(|e| err(py, e))? {\n'
                '                out.push(%s(&item.map_err(|e| err(py, e))?)?);\n'
                '            }\n'
                '            Ok(out)' % reader)
    if inner in rows:
        return '%s(&v)' % _snake_of(inner)
    if inner in enums:
        conv = ('let s: Option<String> = v.extract().map_err(|e| err(py, e))?;\n'
                '            let out = s.and_then(|s| %s::from_str(&s));' % inner)
        if optional:
            return conv + '\n            Ok(out)'
        return (conv + '\n            out.ok_or_else(|| PlatformError::Backend('
                '%s.to_string()))' % json.dumps('%s is not a declared value' % inner))
    if inner in INT_CASTS:
        conv = 'let n: Option<f64> = v.extract().map_err(|e| err(py, e))?;'
        if optional:
            return conv + '\n            Ok(n.map(|x| x as %s))' % inner
        return (conv + '\n            n.map(|x| x as %s).ok_or_else(|| '
                'PlatformError::Backend(%s.to_string()))'
                % (inner, json.dumps('missing value')))
    return 'v.extract().map_err(|e| err(py, e))'


def _rust_ident(name):
    """A parameter name Rust will accept.

    The column path has escaped keywords since `ModuleInfo.type`; a parameter
    can collide just as easily -- `fn` did -- and produced Rust that did not
    parse rather than an error anyone could read.
    """
    from model import RUST_KEYWORDS
    return 'r#' + name if name in RUST_KEYWORDS else name


_ALL_COLS = {}


def _row_all_cols(name):
    """The mask `<Row>Cols::ALL` carries, for the sweep's Python expectation."""
    return _ALL_COLS[name]


def _sweep_call(m, enums, enum_specs):
    """The arguments to call a forwarder with, and what Python should see.

    Returned as a pair, because the two have to be built together: the point
    of the sweep is that the second is what arrives when the first is passed,
    and a Rust literal list written apart from its Python expectation is two
    lists that can disagree.

    Every value is distinct and carries its own position, which is the only
    reason the expectation is worth asserting.  Eight methods take two or
    three parameters of the same type -- `(component, image_path)`,
    `(task_id, filename, path)`, `(bus, dev, func)` -- and a forwarder that
    passed those on in the wrong order would compile, run, and be wrong.
    Identical placeholders would hide exactly that; `"arg0"` next to `"arg1"`
    does not.
    """
    rust, py = [], []
    if m.kind == 'snapshot' and m.projected:
        # A distinctive set rather than ALL: a forwarder that dropped the
        # column set and let the facade default to every column would still
        # produce rows, and only the expected call text catches it.
        rust.append('%sCols::ALL' % m.row)
        py.append(_row_all_cols(m.row))
    for i, (_name, py_type) in enumerate(m.params):
        t = _rust_param_type(py_type, enums)
        if t == '&str':
            rust.append('"arg%d"' % i)
            py.append('arg%d' % i)
        elif t == 'bool':
            # `true` rather than `false`: a forwarder that dropped the
            # argument and passed the type's default would still be caught.
            rust.append('true')
            py.append(True)
        elif t == 'f64':
            rust.append('%d.0' % (i + 1))
            py.append(float(i + 1))
        elif t == 'Threshold':
            rust.append('Threshold::Int(%d)' % (i + 1))
            py.append(i + 1)
        elif t in enums:
            spec = next(e for e in enum_specs if e.name == t)
            value, variant = spec.variants[0]
            rust.append('%s::%s' % (t, variant))
            # Not the variant name: an enumeration crosses as the spelling
            # the Python side uses, and that crossing is part of what the
            # forwarder has to get right.
            py.append(value)
        else:
            rust.append('%d' % (i + 1))
            py.append(i + 1)
    return ', '.join(rust), '%s%r' % (m.name, tuple(py))


def _rust_param_type(py_type, enums):
    """A parameter as a Rust signature spells it: borrowed strings, owned rest."""
    t = rust_type(py_type, enums)
    return '&str' if t == 'String' else t


def _rust_arg(name, py_type, enums):
    """The same parameter, marshalled into the tuple PyO3 passes."""
    t = rust_type(py_type, enums)
    name = _rust_ident(name)
    if t in enums:
        return '%s.as_str()' % name
    if t == 'Threshold':
        return 'thr_arg(py, %s)' % name
    return name


# --------------------------------------------------------------------------
# Python traversal bodies, one per snapshot / action
# --------------------------------------------------------------------------

def _fixed_literal(src, parent_expr):
    """The `sets` of one source, as a Python dict expression.

    `'@parent'` is the parent name this source resolved, which is how a drawer
    fan gets a drawer_name and a PSU fan gets 'N/A'.  It has to be spliced as
    the expression that holds it at this point in the traversal -- `p0` inside
    a via loop, a literal for a source with none -- rather than by name.
    """
    if not src.sets:
        return '{}'
    parts = []
    for name, value in src.sets:
        if value == '@parent':
            rendered = parent_expr
        elif value == '@key':
            rendered = 'str(k)'
        elif value == '@value':
            rendered = 'None if v is None else str(v)'
        else:
            rendered = repr(value)
        parts.append('%r: %s' % (name, rendered))
    return '{%s}' % ', '.join(parts)


def _snapshot_body(row):
    if row.singleton:
        # The chassis is the device.  Still paired with itself so that the
        # accessor and any by-name lookup share one shape.
        return ("%sout.append((self._row_%s(self._chassis, 'chassis 1', 0, {}%s), "
                "self._chassis))" % (IND, row.snake, ', cols' if row.projected else ''))
    out = []
    for src in row.sources:
        lines = []
        via = src.via_getters
        indent = IND
        parent_expr = "''"

        if src.when_chassis:
            lines.append('%sif _call(_get(self._chassis, %r)):' % (indent, src.when_chassis))
            indent += '    '

        owner = 'self._chassis'
        for level, (getter, single) in enumerate(via):
            iv, ov = 'i%d' % level, 'o%d' % level
            if single:
                # One object, not a list.  Iterating it would be a TypeError
                # on most platforms and one row per character on a string.
                lines.append('%s%s = _call(_get(%s, %r))' % (indent, ov, owner, getter))
                lines.append('%s%s = 0' % (indent, iv))
                lines.append('%sif %s is not None:' % (indent, ov))
            else:
                lines.append('%sfor %s, %s in enumerate(_iter(_call(_get(%s, %r)))):'
                             % (indent, iv, ov, owner, getter))
            indent += '    '
            if src.when and level == len(via) - 1:
                lines.append('%sif not _call(_get(%s, %r)):' % (indent, ov, src.when))
                lines.append('%s    continue' % indent)
            pname = 'p%d' % level
            got = '_call(_get(%s, %r))' % (ov, src.parent) if src.parent else 'None'
            lines.append('%s%s = _fmt(%s, %r, %s, %s)'
                         % (indent, pname, got, src.parent_default[level], parent_expr, iv))
            parent_expr = pname
            owner = ov

        if not via:
            parent_expr = '%r' % src.parent_default[0]

        if src.mapping:
            # One row per entry.  `_pairs` keeps the mapping's own order and
            # yields nothing for a platform that answered something else.
            lines.append('%sfor i, (k, v) in enumerate(_pairs(_call(_get(%s, %r)))):'
                         % (indent, owner, src.leaf_getter))
            lines.append('%s    out.append((self._row_%s(None, %s, i, %s%s), None))'
                         % (indent, row.snake, parent_expr,
                            _fixed_literal(src, parent_expr),
                            ', cols' if row.projected else ''))
            block = '\n'.join(lines)
            if src.optional:
                body = '\n'.join('    ' + ln for ln in block.split('\n'))
                block = ('%stry:\n%s\n%sexcept NotImplementedError:\n%s    pass'
                         % (IND, body, IND, IND))
            out.append('%s# %s' % (IND, _describe(src)))
            out.append(block)
            continue
        if src.provider:
            leaf = 'self._hatch.%s()' % src.provider
        else:
            leaf = '_call(_get(%s, %r))' % (owner, src.leaf_getter)
        if src.single:
            # At most one row: `_one` yields nothing when the platform has
            # none, rather than a row whose every column is None.
            lines.append('%sfor i, dev in enumerate(_one(%s)):' % (indent, leaf))
        else:
            lines.append('%sfor i, dev in enumerate(_iter(%s)):' % (indent, leaf))
        lines.append('%s    out.append((self._row_%s(dev, %s, i, %s%s), dev))'
                     % (indent, row.snake, parent_expr,
                        _fixed_literal(src, parent_expr),
                        ', cols' if row.projected else ''))

        block = '\n'.join(lines)
        if src.optional:
            body = '\n'.join('    ' + ln for ln in block.split('\n'))
            block = ('%stry:\n%s\n%sexcept NotImplementedError:\n%s    pass'
                     % (IND, body, IND, IND))
        out.append('%s# %s' % (IND, _describe(src)))
        out.append(block)
    return '\n'.join(out)


def _describe(src):
    if src.via:
        return '%s via %s' % (src.describes, ' -> '.join(src.via_paths))
    return src.describes


def _at_wrap(call, m):
    """Take one slot of a tuple return, the way a field's `at` does.

    `ModuleBase.get_reboot_cause()` answers `(cause, detail)`, and the method
    that replaced the polled column wants the cause.  Without this the caller
    would have to know the arity -- which is exactly what `From(at=)` exists to
    stop a field from having to know.
    """
    return call if m.calls_at is None else '_at(%s, %d)' % (call, m.calls_at)


def _returned_row(m, model):
    """The row a method hands back, if its return type names one."""
    base = m.returns.strip()
    if base.startswith('Optional[') and base.endswith(']'):
        base = base[len('Optional['):-1].strip()
    return model.row(base)


def _row_from_one_call(m, model):
    """Build the returned row out of the single call the method makes.

    `ModuleBase.get_reboot_cause()` answers `(cause, detail)`, and both halves
    are published: the cause to `REBOOT_CAUSE|<module>|<ts>.cause` and the
    detail to its `comment`.  Taking one slot with `Calls(at=)` and calling
    again for the other would work, but the vendor's getter *logs* -- which is
    why this became a method in the first place -- so asking twice doubles the
    line it was made a method to stop duplicating.  One call, both slots.

    None when the return type is not such a row, so the caller falls back to
    returning the call's value as it stands.
    """
    row = _returned_row(m, model)
    if row is None or not row.fields:
        return None
    if not all(f.from_ == m.calls and f.at is not None for f in row.fields):
        return None
    return row


def _action_body(m, model):
    owner, rest = m.calls.split('.', 1)
    hops = rest.split('.')
    method = hops[-1]
    reach = hops[:-1]
    if m.row:
        # pass_key: the base class takes the device's own name as its first
        # argument as well, so the locator is not consumed by the lookup.
        passed = m.params if m.pass_key else m.params[1:]
    else:
        passed = m.params
    args = ', '.join(p for p, _t in passed)

    if not m.row:
        # On the chassis itself, or on something reached through it.
        target = 'self._chassis'
        lines = []
        for hop in reach:
            lines.append('%starget = _call(_get(%s, %r))' % (IND, target, hop))
            target = 'target'
        lines.append('%sfn = _get(%s, %r)' % (IND, target, method))
        lines.append('%sif fn is None:' % IND)
        lines.append('%s    raise NotImplementedError(%r)'
                     % (IND, '%s is not implemented' % m.calls))
        built = _row_from_one_call(m, model)
        if built is not None:
            lines.append('%sanswer = fn(%s)' % (IND, args))
            lines.append('%sreturn %s(%s)'
                         % (IND, built.name,
                            ', '.join('%s=_at(answer, %d)' % (f.name, f.at)
                                      for f in built.fields)))
        else:
            lines.append('%sreturn %s' % (IND, _at_wrap('fn(%s)' % args, m)))
        return '\n'.join(lines)

    row = model.row(m.row)
    key = m.params[0][0]
    head = ('%sdev = self._find_%s(%s)\n'
            '%sfn = _get(dev, %r)\n'
            '%sif fn is None:\n'
            '%s    raise NotImplementedError(%r)\n'
            % (IND, row.snake, key, IND, method, IND, IND,
               '%s is not implemented' % m.calls))
    built = _row_from_one_call(m, model)
    if built is not None:
        return ('%s%sanswer = fn(%s)\n%sreturn %s(%s)'
                % (head, IND, args, IND, built.name,
                   ', '.join('%s=_at(answer, %d)' % (f.name, f.at)
                             for f in built.fields)))
    return head + '%sreturn %s' % (IND, _at_wrap('fn(%s)' % args, m))


# --------------------------------------------------------------------------

def _required_args(signature):
    """The arguments a caller must supply, from an inventory signature string.

    `scope_scan` renders defaults as `name=...`, so a bare name after `self`
    and before any `*` is one the caller has to pass.
    """
    inner = signature.strip()[1:-1]
    parts = [x.strip() for x in inner.split(',')]
    # Drop the receiver, whatever it is called: `self` on an ordinary method,
    # `cls` on a classmethod -- `SensorBase.get_unit(cls)` is one, and Python
    # binds it, so a zero-argument call is correct there.
    if parts and parts[0] in ('self', 'cls'):
        parts = parts[1:]
    out = []
    for part in parts:
        if not part or part.startswith('*') or '=' in part:
            if part.startswith('*') and part != '*':
                break          # *args / **kwargs: nothing after is positional
            continue
        out.append(part)
    return out


def check_arity(model, inventory_path=os.path.join(HERE, 'inventory.json')):
    """Reject a column whose getter needs an argument the row does not pass.

    This is the check that was missing.  The conformance scan verifies every
    path named in a `From` *exists* on the vendor object; nothing verified that
    a zero-argument call still matched the signature.
    `ModuleBase.get_module_state_transition(self, module_name)` was declared as
    a plain column, the generated call passed nothing, and the TypeError took
    the entire `ModuleInfo` row with it -- on a SmartSwitch NPU that left
    chassisd logging "Failed to read the modules" every cycle and publishing no
    midplane table at all, which is not a shape any unit test reproduces.

    Fields declared `WithName()` are exempt: they pass the device's own name.
    A vendor that *narrows* a signature the base class leaves open is a
    different problem and cannot be seen from here -- that is what `Narrowed()`
    and the on-hardware arity scan are for.
    """
    try:
        with open(inventory_path) as f:
            inv = json.load(f)
    except (OSError, ValueError):
        return []                      # no inventory: nothing to check against
    # The buckets are name -> record for the classes the scan reached and a
    # plain list of names for the ones it did not; tolerate both rather than
    # assume, because an assumption here fails open and the check silently
    # stops checking.
    sigs = {}
    for cls, buckets in inv.get('classes', {}).items():
        if not isinstance(buckets, dict):
            continue
        for bucket in ('reached', 'unreached'):
            b = buckets.get(bucket)
            if isinstance(b, dict):
                for name, rec in b.items():
                    if isinstance(rec, dict):
                        sigs[(cls, name)] = rec.get('signature', '')
    bad = []
    for row in model.rows:
        for f in row.fields:
            if not f.from_ or f.with_name or '.' in (f.getter or ''):
                continue
            cls = f.from_.split('.')[0]
            need = _required_args(sigs.get((cls, f.getter), '(self)'))
            if need:
                bad.append('%s.%s reads %s%s with no arguments; it requires %s'
                           ' -- declare WithName() or pass them'
                           % (row.name, f.name, f.from_,
                              sigs.get((cls, f.getter), ''), ', '.join(need)))
    return bad


def build(model):
    # Rows an action addresses by name need a lookup; the rest do not, and
    # emitting one anyway would be dead code in a generated file.
    addressed = {m.row for m in model.methods if m.kind == 'action' and m.row}
    enums = model.enum_names
    row_names = {r.name for r in model.rows}
    projected_rows = {m.row for m in model.methods
                      if m.kind == 'snapshot' and m.projected}
    for row in model.rows:
        row.projected = row.name in projected_rows
        row.col_count = 0
        row.all_cols = 0
        if row.projected:
            _assign_col_bits(row)
            _ALL_COLS[row.name] = row.all_cols
        else:
            for f in row.fields:
                f.col_bit = None
        _share_calls(row)
        for f in row.fields:
            f.py_expr = _py_field_expr(f, enums)
            f.rust_ty = rust_type(f.py_type, enums)
            f.rust_expr = _rust_field_expr(f, enums, row_names)
        row.walk_body = _snapshot_body(row)
        row.addressed = row.name in addressed
        # A row can derive Default unless a column is a bare enumeration:
        # there is no neutral colour or fan kind, and picking one would be a
        # value nobody declared.  The rows that can are the ones a test
        # fixture or a partial vendor implementation wants to build piecemeal.
        row.can_default = not any(
            f.rust_ty in enums for f in row.fields)
    for m in model.methods:
        if m.kind == 'action':
            m.body = _action_body(m, model)
        m.rust_name = m.name
        if m.kind == 'snapshot':
            m.rust_ret = m.row if m.singleton else 'Vec<%s>' % m.row
        else:
            m.rust_ret = rust_type(m.returns, enums)
        m.rust_params = ''.join(
            ', %s: %s' % (_rust_ident(p), _rust_param_type(t, enums)) for p, t in m.params)
        if m.kind == 'snapshot' and m.projected:
            # The column set is not a stub parameter -- it is the snapshot's
            # own, added by `Snapshot(projected=True)` -- so it is spliced in
            # here rather than declared alongside the others.
            m.rust_params = ', cols: %sCols%s' % (m.row, m.rust_params)
        m.rust_args = ''.join(
            '%s, ' % _rust_arg(p, t, enums) for p, t in m.params)
        # The same parameters passed straight on, with no conversion: what one
        # Rust implementation hands another.  `rust_args` above is the Python
        # call's argument tuple and has conversions baked in, so a forwarder
        # cannot reuse it.
        m.rust_fwd_args = ', '.join(
            (['cols'] if m.kind == 'snapshot' and m.projected else [])
            + [_rust_ident(p) for p, _t in m.params])
        m.rust_sweep_args, call = _sweep_call(m, enums, model.enums)
        # A Rust string literal, not jinja's `tojson`: that one escapes the
        # quote in a Python repr as `\u0027`, which Rust does not spell that
        # way and will not compile.
        m.py_sweep_call = json.dumps(call)
        m.rust_ret_conv = _rust_ret_conv(m.rust_ret, enums, row_names)

    # The names the provider's forwarding impl actually mentions.  It converts
    # nothing, so it needs a type only where one appears in a signature --
    # importing the bridge's full list would leave a third of it unused.
    # `Threshold` is hand-written in platform-api rather than projected from
    # the stub, so it is not in `enums` or `rows`; it still appears in
    # signatures and still has to be imported when it does.
    declared = ([e.name for e in model.enums]
                + [r.name for r in model.rows]
                # A projected snapshot names its column set in the signature,
                # and `\bFanInfo\b` does not match `FanInfoCols`.
                + ['%sCols' % r.name for r in model.rows if r.projected]
                + ['Threshold'])
    mentioned = ' '.join(m.rust_ret + m.rust_params for m in model.methods)
    model.provider_imports = [
        n for n in declared if re.search(r'\b%s\b' % re.escape(n), mentioned)]

    # The sweep names a type only where it has to build one, so it needs the
    # parameter types and none of the return types: it discards every answer.
    taken = ' '.join(m.rust_params for m in model.methods)
    model.sweep_imports = [
        n for n in declared if re.search(r'\b%s\b' % re.escape(n), taken)]
    return model


def _rustdoc(text, indent='    '):
    """Prose as a Rust doc comment, however many lines it runs to.

    Emitting the first line with `///` and trusting the rest is how a
    docstring that grew a second paragraph becomes a compile error in a
    generated file nobody edits.
    """
    lines = _fence_indented(lines_of(text))
    out = [lines[0].rstrip()]
    for ln in lines[1:]:
        ln = ln.rstrip()
        # No trailing space on a blank doc line: rustfmt would strip it and
        # then `generate.py --check` would disagree with the working tree.
        out.append('%s///%s' % (indent, ' ' + ln if ln else ''))
    return '\n'.join(out)


def lines_of(text):
    return (text or '').rstrip().split('\n')


def _fence_indented(lines):
    """Fence an indented block as `text`, not as Rust.

    rustdoc reads a four-space indent as a code block and compiles it.  These
    docstrings indent to show measured output -- `python: 'Non-Hardware'`
    against `rust: 'N/A'` -- and that apostrophe is an unterminated character
    literal, so the doctest fails to compile in a file nobody edits.  The
    crate's doctests had never run (it is a path dependency, not a workspace
    member, and `check.sh` tests the two crates above it), so the breakage sat
    there until something gave platform-api a test target.
    """
    out, i = [], 0
    while i < len(lines):
        if lines[i][:4] == '    ' and lines[i].strip():
            out.append('```text')
            while i < len(lines) and (not lines[i].strip() or lines[i][:4] == '    '):
                out.append(lines[i])
                i += 1
            while out and not out[-1].strip():      # trailing blanks go after
                out.pop()
                lines.insert(i, '')
            out.append('```')
            continue
        out.append(lines[i])
        i += 1
    return out


def render(model):
    # The output is Rust and Python source, not HTML: autoescaping would turn
    # every `<`, `>` and `&` in a type or a doc comment into an entity.
    # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES),
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    env.filters['rustdoc'] = _rustdoc
    env.filters['camel'] = lambda n: ''.join(p.title() for p in n.split('_'))
    env.filters['snake'] = _snake_of
    out = {}
    for tpl, path in OUTPUTS.items():
        text = env.get_template(tpl).render(model=model, header=_header(path))
        # Trailing whitespace once, here, rather than in three templates.  A
        # blank line inside a doc comment is the usual source, and rustfmt and
        # most linters would strip it back out -- at which point `--check`
        # would disagree with the working tree over a space.
        out[path] = '\n'.join(ln.rstrip() for ln in text.split('\n'))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true',
                    help='fail if a checked-in output is stale')
    args = ap.parse_args()

    model = build(parse())
    problems = check_arity(model)
    if problems:
        for p in problems:
            print('arity: %s' % p, file=sys.stderr)
        return 1
    rendered = render(model)

    stale = []
    for path, text in sorted(rendered.items()):
        rel = os.path.relpath(path, ROOT)
        if args.check:
            current = open(path).read() if os.path.exists(path) else None
            if current != text:
                stale.append(rel)
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(text)
        print('wrote %s (%d lines)' % (rel, text.count('\n')))

    if args.check:
        if stale:
            print('stale, re-run generator/generate.py: %s' % ', '.join(stale),
                  file=sys.stderr)
            return 1
        print('generated files up to date')
    return 0


if __name__ == '__main__':
    sys.exit(main())
