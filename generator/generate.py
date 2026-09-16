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
    'bridge.rs.j2': os.path.join(ROOT, 'crates', 'platform-pyo3', 'src', 'generated.rs'),
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

def _py_field_expr(f):
    """How `facade.py` fills one column of one row."""
    if f.is_parent:
        if f.name == 'parent_name':
            return 'parent'
        return 'fixed[%r]' % f.name

    call = 'dev'
    for hop in f.getter.split('.'):
        call = '_call(_get(%s, %r))' % (call, hop)
    if f.at is not None:
        call = '_at(%s, %d)' % (call, f.at)

    if f.sentinels or f.coerce_from:
        return '_scalar(%s, %r, %r)' % (call, tuple(f.sentinels), tuple(f.coerce_from))
    if f.unsupported_on == 'default':
        if isinstance(f.default, str) and '{' in f.default:
            return '_fmt(%s, %r, parent, i)' % (call, f.default)
        return '_default(%s, %r)' % (call, f.default)
    return call


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


def _rust_param_type(py_type, enums):
    """A parameter as a Rust signature spells it: borrowed strings, owned rest."""
    t = rust_type(py_type, enums)
    return '&str' if t == 'String' else t


def _rust_arg(name, py_type, enums):
    """The same parameter, marshalled into the tuple PyO3 passes."""
    t = rust_type(py_type, enums)
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
        return ("%sout.append((self._row_%s(self._chassis, 'chassis 1', 0, {}), "
                "self._chassis))" % (IND, row.snake))
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
            lines.append('%s    out.append((self._row_%s(None, %s, i, %s), None))'
                         % (indent, row.snake, parent_expr,
                            _fixed_literal(src, parent_expr)))
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
        lines.append('%s    out.append((self._row_%s(dev, %s, i, %s), dev))'
                     % (indent, row.snake, parent_expr,
                        _fixed_literal(src, parent_expr)))

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
        lines.append('%sreturn fn(%s)' % (IND, args))
        return '\n'.join(lines)

    row = model.row(m.row)
    key = m.params[0][0]
    return ('%sdev = self._find_%s(%s)\n'
            '%sfn = _get(dev, %r)\n'
            '%sif fn is None:\n'
            '%s    raise NotImplementedError(%r)\n'
            '%sreturn fn(%s)'
            % (IND, row.snake, key, IND, method, IND, IND,
               '%s is not implemented' % m.calls, IND, args))


# --------------------------------------------------------------------------

def build(model):
    # Rows an action addresses by name need a lookup; the rest do not, and
    # emitting one anyway would be dead code in a generated file.
    addressed = {m.row for m in model.methods if m.kind == 'action' and m.row}
    enums = model.enum_names
    row_names = {r.name for r in model.rows}
    for row in model.rows:
        for f in row.fields:
            f.py_expr = _py_field_expr(f)
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
            ', %s: %s' % (p, _rust_param_type(t, enums)) for p, t in m.params)
        m.rust_args = ''.join(
            '%s, ' % _rust_arg(p, t, enums) for p, t in m.params)
        m.rust_ret_conv = _rust_ret_conv(m.rust_ret, enums, row_names)
    return model


def _rustdoc(text, indent='    '):
    """Prose as a Rust doc comment, however many lines it runs to.

    Emitting the first line with `///` and trusting the rest is how a
    docstring that grew a second paragraph becomes a compile error in a
    generated file nobody edits.
    """
    lines = (text or '').rstrip().split('\n')
    out = [lines[0].rstrip()]
    for ln in lines[1:]:
        ln = ln.rstrip()
        # No trailing space on a blank doc line: rustfmt would strip it and
        # then `generate.py --check` would disagree with the working tree.
        out.append('%s///%s' % (indent, ' ' + ln if ln else ''))
    return '\n'.join(out)


def render(model):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES),
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    env.filters['rustdoc'] = _rustdoc
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

    rendered = render(build(parse()))

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
