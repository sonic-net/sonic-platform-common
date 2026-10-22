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
import ast
import json
import os
import re
import sys
import warnings

import jinja2

from model import key_segment, keyed, _snake as _snake_of, rust_type, strip_optional, template_fields
from parse_pyi import parse
import native

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
# The base classes the stub is held to and the native defaults come from:
# the repository's, wherever the outputs are written.
BASE_DIR = os.path.join(ROOT, 'sonic_platform_base')
TEMPLATES = os.path.join(HERE, 'templates')

OUTPUTS = {
    'facade.py.j2': os.path.join(ROOT, 'sonic_platform_api', 'facade.py'),
    'trait.rs.j2': os.path.join(ROOT, 'crates', 'platform-api', 'src', 'generated.rs'),
    'trait_sweep.rs.j2': os.path.join(
        ROOT, 'crates', 'platform-api', 'tests', 'generated', 'sweep.rs'),
    'bridge.rs.j2': os.path.join(ROOT, 'crates', 'platform-pyo3', 'src', 'generated.rs'),
    'provider.rs.j2': os.path.join(ROOT, 'crates', 'platform-provider', 'src', 'generated.rs'),
    'provider_sweep.rs.j2': os.path.join(
        ROOT, 'crates', 'platform-provider', 'tests', 'generated', 'sweep.rs'),
    'allowlist.txt.j2': os.path.join(ROOT, 'sonic_platform_api', 'stubtest_allowlist.txt'),
    'native_object.rs.j2': os.path.join(
        ROOT, 'crates', 'platform-base', 'src', 'generated', 'object.rs'),
    'native_facade.rs.j2': os.path.join(
        ROOT, 'crates', 'platform-base', 'src', 'generated', 'facade.rs'),
    'native_object_sweep.rs.j2': os.path.join(
        ROOT, 'crates', 'platform-base', 'tests', 'generated', 'object_sweep.rs'),
}

# Semantic integer types.  The bridge reads them with platform-pyo3's
# `integer`/`int_of` rather than asking PyO3 for a u32: an `int` crosses
# exactly, a vendor's 50.0 where the base class documents an int is truncated
# rather than failed, and a value the width cannot hold is absent rather than
# saturated as `as` would -- a fan answering -1 for "could not read" crossed as
# a stopped fan.
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
        #
        # Only when every slicer has a bit, though.  A member without one --
        # `name`, which `_assign_col_bits` never numbers, declared with `at=`
        # -- is read whatever the caller asked for, so its slice of a call
        # gated on its siblings' bits would be `_at(None, k)`: a row with no
        # name whenever the caller declined the others.  Such a call is made
        # unconditionally, as it would be for that column alone.
        mask = 0
        for f in fields:
            if f.col_bit is not None:
                mask |= 1 << f.col_bit
        gated = row.projected and all(f.col_bit is not None for f in fields)
        row.shared_calls.append((var, call, mask if gated else None))
        for f in fields:
            f.shared_var = var


def _assign_col_bits(row):
    """Number the columns a projected row can be asked for.

    The bit is the column's position among the ones a caller can decline, in
    declaration order.  It is derived, never hand-written, and both sides are
    emitted from this one pass -- `generate.py --check` is what keeps the
    Python mask and the Rust constant from drifting.

    `Parent()`, `Key()` and `ParentKey()` columns come from the traversal
    rather than a getter, so there is nothing to decline; `name` is always
    read because it is what a caller publishes the row under.
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


def _absent(f):
    """What a column holds when it was not read: as if the platform did not
    implement the getter."""
    if f.unsupported_on != 'default':
        return 'None'
    if _is_template(f.default):
        # The same resolution the read takes when the getter answers nothing,
        # or a declined column would hold the raw `'{parent} fan {i}'` where
        # an unimplemented one holds `'PSU 1 fan 1'`.
        return _fmt_call('None', f.default)
    return repr(f.default)


def _gated(f, expr):
    """The column's expression, behind its projection bit if it has one.

    A column the caller did not ask for is not read at all: running the getter
    is the cost -- and for some of them the log line -- that the projection
    exists to avoid.  Absent reads as whatever the column would hold if the
    platform did not implement it.
    """
    if f.col_bit is None:
        return expr
    return '(%s) if cols & (1 << %d) else %s' % (expr, f.col_bit, _absent(f))


def _is_template(default):
    """A declared default that names its row: `'{parent} fan {i}'`."""
    return isinstance(default, str) and '{' in default


def _fmt_call(got, default):
    extra = ''.join(', %s=fixed[%r]' % (n, n) for n in template_fields(default))
    return '_fmt(%s, %r, parent, i%s)' % (got, default, extra)


def _py_field_expr(f, enums=()):
    """How `facade.py` fills one column of one row.

    `enums` are the `Literal` aliases.  A column typed as one of them, or as
    `str`, is declared to be a string, so whatever the vendor answers with is
    made one by `_text()` before it leaves the facade.
    """
    if f.is_parent:
        if f.name == 'parent_name':
            return 'parent'
        return 'fixed[%r]' % f.name
    if f.is_key:
        return "fixed['key']"
    if f.is_parent_key:
        return "fixed['parent_key']"
    if f.row_error:
        return 'None'

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

    if f.base in enums or f.base == 'str':
        call = '_text(%s)' % call

    if f.truthy:
        expr = '_truthy(%s)' % call
    elif f.sentinels or f.coerce_from:
        expr = '_scalar(%s, %r, %r)' % (call, tuple(f.sentinels), tuple(f.coerce_from))
    elif f.unsupported_on == 'default':
        if _is_template(f.default):
            expr = _fmt_call(call, f.default)
        else:
            expr = '_default(%s, %r)' % (call, f.default)
    else:
        expr = call

    return _gated(f, expr)


def _row_body(row):
    """`_row_<row>()` for a row read column by column rather than in one call.

    Three things need it.  `per_row_errors`: the device's getters run inside
    a `try`, and the first exception ends the reading of that row -- the
    columns not reached keep their absent value and `error`, `error_repr` and
    `error_column` say what happened -- while `Unguarded()` columns are read
    before it and fail the call, as Python reads them outside its own `try`.
    Absorbing (`Snapshot(absorbs=True)`, or `absorb` on an `absorbable`
    snapshot): each getter in a `try` of its own, an exception leaving that
    one column absent, which is psud's `try_get`.  And `ReadIf()`: a column
    read only when an earlier one came back with a value, which a single
    constructor call cannot express.
    """
    def reads(f):
        return bool(f.from_)

    guard = row.guarded or row.absorbs or row.absorbable
    unguarded = [f for f in row.fields if reads(f) and (f.unguarded or not guard)]
    guarded = [f for f in row.fields if reads(f) and not f.unguarded and guard]
    in_try = {f.shared_var for f in guarded if f.shared_var}
    outside = {f.shared_var for f in unguarded if f.shared_var}
    if in_try & outside:
        raise ValueError('%s: a call shared across the guard (%s)'
                         % (row.name, ', '.join(sorted(in_try & outside))))

    def shared(names, indent):
        out = []
        for var, call, mask in row.shared_calls:
            if var not in names:
                continue
            gate = ' if cols & %d else None' % mask if mask is not None else ''
            out.append('%s%s = %s%s' % (indent, var, call, gate))
        return out

    def assign(f, indent, absorbing=False):
        expr = f.py_expr
        if f.read_if and (f.read_if_absorbing or not absorbing):
            cond = ('row.%s' if f.read_if_truthy else 'row.%s is not None') % f.read_if
            expr = '(%s) if %s else %s' % (expr, cond, _absent(f))
        return '%srow.%s = %s' % (indent, f.name, expr)

    def row_errors(indent):
        """One `try` for the row: the first exception ends it, and the
        column being read when it struck is the one named."""
        out = ['%stry:' % indent]
        done = set()
        for f in guarded:
            if f.shared_var and f.shared_var not in done:
                done.add(f.shared_var)
                out.append('%s    _column = %r' % (indent, f.name))
                out += shared({f.shared_var}, indent + '    ')
            out.append('%s    _column = %r' % (indent, f.name))
            out.append(assign(f, indent + '    '))
        out.append('%sexcept Exception as e:' % indent)
        out.append('%s    row.error = str(e)' % indent)
        out.append('%s    row.error_repr = repr(e)' % indent)
        out.append('%s    row.error_column = _column' % indent)
        return out

    def absorbed(indent):
        """A `try` per getter: an exception is that column absent, as
        `try_get` makes it in psud."""
        out = []
        done = set()
        for f in guarded:
            if f.shared_var and f.shared_var not in done:
                done.add(f.shared_var)
                for line in shared({f.shared_var}, ''):
                    out += ['%stry:' % indent, '%s    %s' % (indent, line),
                            '%sexcept Exception:' % indent,
                            '%s    %s = None' % (indent, f.shared_var)]
            out += ['%stry:' % indent, assign(f, indent + '    ', absorbing=True),
                    '%sexcept Exception:' % indent,
                    '%s    row.%s = %s' % (indent, f.name, _absent(f))]
        return out

    lines = []
    if row.skippable:
        lines.append("%sif fixed['key'] in skip:" % IND)
        lines.append('%s    cols &= %d' % (IND, row.unguarded_mask))
    lines += shared(outside, IND)
    # Everything that is not read off the device, and every unguarded column
    # that no ReadIf holds back, goes in the constructor: in declaration
    # order, which is the order Python reads them in.
    later = [f for f in unguarded if f.read_if]
    lines.append('%srow = %s(' % (IND, row.name))
    for f in row.fields:
        if not reads(f) or (f in unguarded and not f.read_if):
            lines.append('%s    %s=%s,' % (IND, f.name, f.py_expr))
        else:
            lines.append('%s    %s=%s,' % (IND, f.name, _absent(f)))
    lines.append('%s)' % IND)
    for f in later:
        lines.append(assign(f, IND))
    if guarded:
        if row.absorbs:
            lines += absorbed(IND)
        elif row.absorbable:
            lines.append('%sif absorb:' % IND)
            lines += absorbed(IND + '    ')
            lines.append('%selse:' % IND)
            lines += row_errors(IND + '    ')
        else:
            lines += row_errors(IND)
    lines.append('%sreturn row' % IND)
    return '\n'.join(lines)


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

    if inner == 'DeviceKey':
        return 'text(row, %s)?.map(DeviceKey::from)%s' % (
            json.dumps(key), '' if f.optional else '.unwrap_or_default()')

    if inner == 'bool':
        return 'flag(row, %s)?' % json.dumps(key) if f.optional else \
            'flag(row, %s)?.unwrap_or(%s)' % (json.dumps(key), _rust_default(f, inner))

    if inner == 'Number':
        # `parse_pyi._validate` refuses a non-Optional number: there is no
        # neutral one to fall back to, and the row could no longer derive
        # Default.  Asserted rather than assumed, so a model built some other
        # way fails here instead of emitting a type mismatch into the bridge.
        assert f.optional, '%s: a Number column must be Optional' % key
        return 'int_or_float(row, %s)?' % json.dumps(key)
    if inner not in INT_CASTS:
        # `parse_pyi._validate` refuses a `float` column: a number read off
        # the platform is a `Number`, which keeps an int an int.
        raise ValueError('%s: no reader for a %s column' % (key, inner))
    got = 'integer::<%s>(row, %s)?' % (inner, json.dumps(key))
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
    if inner == 'DeviceKey':
        conv = ('let s: Option<String> = v.extract().map_err(|e| err(py, e))?;\n'
                '            let out = s.map(DeviceKey::from);')
        if optional:
            return conv + '\n            Ok(out)'
        return (conv + '\n            out.ok_or_else(|| PlatformError::Backend('
                '"missing key".to_string()))')
    if inner in enums:
        conv = ('let s: Option<String> = v.extract().map_err(|e| err(py, e))?;\n'
                '            let out = s.and_then(|s| %s::from_str(&s));' % inner)
        if optional:
            return conv + '\n            Ok(out)'
        return (conv + '\n            out.ok_or_else(|| PlatformError::Backend('
                '%s.to_string()))' % json.dumps('%s is not a declared value' % inner))
    if inner in INT_CASTS:
        conv = 'let n = int_of::<%s>(&v).map_err(|e| err(py, e))?;' % inner
        if optional:
            return conv + '\n            Ok(n)'
        return (conv + '\n            n.ok_or_else(|| '
                'PlatformError::Backend(%s.to_string()))'
                % json.dumps('missing value, or not a %s' % inner))
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
    if m.kind == 'snapshot' and m.skippable:
        # Two keys, so that a forwarder passing an empty list, or only the
        # first, is caught as surely as one dropping the argument.
        rust.append('&[DeviceKey::from("skip0"), DeviceKey::from("skip1")]')
        py.append(['skip0', 'skip1'])
    if m.kind == 'snapshot' and m.absorbable:
        # `true`, not the default: a forwarder that dropped it is caught.
        rust.append('true')
        py.append(True)
    for i, (_name, py_type) in enumerate(m.params):
        t = _rust_param_type(py_type, enums)
        if t == '&str':
            rust.append('"arg%d"' % i)
            py.append('arg%d' % i)
        elif t == '&DeviceKey':
            rust.append('&DeviceKey::from("arg%d")' % i)
            py.append('arg%d' % i)
        elif t == 'bool':
            # `true` rather than `false`: a forwarder that dropped the
            # argument and passed the type's default would still be caught.
            rust.append('true')
            py.append(True)
        elif t == 'f64':
            rust.append('%d.0' % (i + 1))
            py.append(float(i + 1))
        elif t == 'Number':
            rust.append('Number::Int(%d)' % (i + 1))
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
    if t == 'DeviceKey':
        return '&DeviceKey'
    return '&str' if t == 'String' else t


def _rust_arg(name, py_type, enums):
    """The same parameter, marshalled into the tuple PyO3 passes."""
    t = rust_type(py_type, enums)
    name = _rust_ident(name)
    if t in enums or t == 'DeviceKey':
        return '%s.as_str()' % name
    if t == 'Number':
        return 'int_or_float_arg(py, %s)' % name
    return name


# --------------------------------------------------------------------------
# Python traversal bodies, one per snapshot / action
# --------------------------------------------------------------------------

def _fixed_literal(src, parent_expr, key=None, raw_expr=None):
    """The `sets` of one source, as a Python dict expression.

    `'@parent'` is the parent name this source resolved, which is how a PSU
    fan gets its PSU's name.  It has to be spliced as the expression that
    holds it at this point in the traversal -- `p0` inside a via loop, a
    literal for a source with none -- rather than by name.  `'@parent_raw'`
    is what the parent answered before any fallback, which is a drawer fan's
    `drawer_name`.
    """
    parts = []
    if key is not None:
        parts.append("'key': %s" % key[0])
        parts.append("'parent_key': %s" % key[1])
    if not src.sets and not parts:
        return '{}'
    for name, value in src.sets:
        if value == '@parent':
            rendered = parent_expr
        elif value == '@parent_raw':
            rendered = '_raw(%s)' % raw_expr
        elif value == '@key':
            rendered = 'str(k)'
        elif value == '@value':
            rendered = 'None if v is None else str(v)'
        else:
            rendered = repr(value)
        parts.append('%r: %s' % (name, rendered))
    return '{%s}' % ', '.join(parts)


def _when(src, owner):
    """The `when` predicate as a condition on `owner`.

    `when_unsupported="present"` passes True as the unanswered default, which
    is `try_get()`'s truthy 'N/A' in the daemon it reproduces.
    """
    default = ', True' if src.when_unsupported == 'present' else ''
    return '_call(_get(%s, %r)%s)' % (owner, src.when, default)


def _row_args(row):
    """What every `_row_<row>()` call passes after the fixed dict."""
    return ((', cols' if row.projected else '')
            + (', skip' if getattr(row, 'skippable', False) else '')
            + (', absorb' if getattr(row, 'absorbable', False) else ''))


def _snapshot_body(row):
    if row.singleton:
        # The chassis is the device.
        return ("%sout.append(self._row_%s(self._chassis, 'chassis 1', 0, {}%s))"
                % (IND, row.snake, _row_args(row)))
    out = []
    for k, src in enumerate(row.sources):
        lines = []
        via = src.via_getters
        indent = IND
        parent_expr = "''"
        raw_expr = None
        counted = k + 1 < len(row.sources) and row.sources[k + 1].index_from_previous

        if src.when_chassis:
            lines.append('%sif _call(_get(self._chassis, %r)):' % (indent, src.when_chassis))
            indent += '    '

        owner = 'self._chassis'
        kprev = None
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
                lines.append('%sif not %s:' % (indent, _when(src, ov)))
                lines.append('%s    continue' % indent)
            pname = 'p%d' % level
            got = '_call(_get(%s, %r))' % (ov, src.parent) if src.parent else 'None'
            if src.parent and (src.parent_missing
                               or any(v == '@parent_raw' for _f, v in src.sets)):
                # What the parent answered is kept: '@parent_raw' publishes
                # it, and a `parent_missing` answer is only a name for that.
                rname = 'r%d' % level
                lines.append('%s%s = %s' % (indent, rname, got))
                got = ('_present(%s, %r)' % (rname, tuple(src.parent_missing))
                       if src.parent_missing else rname)
                raw_expr = rname
            lines.append('%s%s = _fmt(%s, %r, %s, %s)'
                         % (indent, pname, got, src.parent_default[level], parent_expr, iv))
            if keyed(row):
                seg = key_segment(getter)
                step = repr(seg) if single else '%r %% %s' % (seg + '[%d]', iv)
                lines.append('%sk%d = %s' % (indent, level,
                                             step if kprev is None else '%s + %r + %s' % (kprev, '/', step)))
                kprev = 'k%d' % level
            parent_expr = pname
            owner = ov

        if not via:
            parent_expr = '%r' % src.parent_default[0]
            if '{i}' in src.parent_default[0]:
                # The source's own position, as a via level's would be:
                # 'PSU {i}' names the PSU it falls back for.
                parent_expr = '%r.format(i=i + 1)' % src.parent_default[0]

        if src.mapping:
            # One row per entry.  `_pairs` keeps the mapping's own order and
            # yields nothing for a platform that answered something else.
            lines.append('%sfor i, (k, v) in enumerate(_pairs(_call(_get(%s, %r)))):'
                         % (indent, owner, src.leaf_getter))
            lines.append('%s    out.append(self._row_%s(None, %s, i, %s%s))'
                         % (indent, row.snake, parent_expr,
                            _fixed_literal(src, parent_expr, raw_expr=raw_expr),
                            _row_args(row)))
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
        key = None
        if keyed(row):
            # An escape hatch's list is a step of its own, named after it.
            seg = src.provider or key_segment(src.leaf_getter)
            step = repr(seg) if src.single else '%r %% i' % (seg + '[%d]')
            key = (step if kprev is None else '%s + %r + %s' % (kprev, '/', step),
                   kprev or 'None')
        index = 'i'
        if src.index_from_previous:
            # One numbering with the source before (`index_from_previous`):
            # `{i}` counts on from its rows, the key stays this list's own.
            lines.append('%sn = len(out) - s%d' % (indent, k - 1))
            index = 'n + i'
        if src.single:
            # At most one row: `_one` yields nothing when the platform has
            # none, rather than a row whose every column is None.
            lines.append('%sfor i, dev in enumerate(_one(%s)):' % (indent, leaf))
        else:
            lines.append('%sfor i, dev in enumerate(_iter(%s)):' % (indent, leaf))
        lines.append('%s    out.append(self._row_%s(dev, %s, %s, %s%s))'
                     % (indent, row.snake, parent_expr, index,
                        _fixed_literal(src, parent_expr, key, raw_expr),
                        _row_args(row)))

        block = '\n'.join(lines)
        if src.optional:
            body = '\n'.join('    ' + ln for ln in block.split('\n'))
            block = ('%stry:\n%s\n%sexcept NotImplementedError:\n%s    pass'
                     % (IND, body, IND, IND))
        out.append('%s# %s' % (IND, _describe(src)))
        if counted:
            out.append('%ss%d = len(out)' % (IND, k))
        out.append(block)
    return '\n'.join(out)


def _find_body(row):
    """`_find_<row>(key)`: the walk of each source again, one device per hop.

    A key's shape -- its collections, and which steps carry a position --
    says which source made it, and only a source of this row type is
    followed: a PSU's key passed to a fan action is refused, not obeyed.  The
    same `when_chassis` and `when` gates apply as in the walk, so a key leads
    exactly where a published row would have, and nowhere a row could not.
    """
    out = ['%spath = _parse_key(key)' % IND]
    for src in row.sources:
        shape = [(key_segment(g), not single) for g, single in src.via_getters]
        shape.append((src.provider or key_segment(src.leaf_getter), not src.single))
        lines = ['%sif _shape(path) == %r:' % (IND, tuple(shape))]
        indent = IND + '    '
        if src.when_chassis:
            lines.append('%sif _call(_get(self._chassis, %r)):' % (indent, src.when_chassis))
            indent += '    '
        owner = 'self._chassis'
        via = src.via_getters
        for level, (getter, single) in enumerate(via):
            ov = 'o%d' % level
            if single:
                lines.append('%s%s = _call(_get(%s, %r))' % (indent, ov, owner, getter))
            else:
                lines.append('%s%s = _nth(_call(_get(%s, %r)), path[%d][1])'
                             % (indent, ov, owner, getter, level))
            cond = '%s is not None' % ov
            if src.when and level == len(via) - 1:
                cond += ' and %s' % _when(src, ov)
            lines.append('%sif %s:' % (indent, cond))
            indent += '    '
            owner = ov
        if src.provider:
            leaf = 'self._hatch.%s()' % src.provider
        else:
            leaf = '_call(_get(%s, %r))' % (owner, src.leaf_getter)
        if src.single:
            lines.append('%sdev = %s' % (indent, leaf))
        else:
            lines.append('%sdev = _nth(%s, path[%d][1])' % (indent, leaf, len(via)))
        lines.append('%sif dev is not None:' % indent)
        lines.append('%s    return dev' % indent)
        block = '\n'.join(lines)
        if src.optional:
            body = '\n'.join('    ' + ln for ln in block.split('\n'))
            block = ('%stry:\n%s\n%sexcept NotImplementedError:\n%s    pass'
                     % (IND, body, IND, IND))
        out.append('%s# %s' % (IND, _describe(src)))
        out.append(block)
    out.append("%sraise DeviceNotFound('no %s at %%r' %% key)" % (IND, row.name))
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


def _answer(call, m):
    """What an action hands back: its slot, then, for a bool, its truth.

    A caller acts on these answers the way Python does -- `if not answer:`
    (chassisd:1405) -- and vendors answer with whatever their helper returned:
    an int, or "Executed" (pddf ledutil.py:35).  The bridge extracts a `bool`
    strictly, so without `_truthy()` an answer Python reads as True would
    fail the call.
    """
    call = _at_wrap(call, m)
    if strip_optional(m.returns)[0] == 'bool':
        call = '_truthy(%s)' % call
    return call


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
    def passed(p):
        # `Calls(ints=...)`: the platform gets what the Python caller passes,
        # 1 or 0, not the bool the signature takes.
        return '(1 if %s else 0)' % p if p in m.calls_ints else p

    if m.row:
        # pass_key: the base class takes the device's own name as its first
        # argument as well.  The locator is a key now, so the name is the
        # device's, asked of the device the key led to.
        args = ', '.join((["_text(_call(_get(dev, 'get_name')))"] if m.pass_key else [])
                         + [passed(p) for p, _t in m.params[1:]])
    else:
        args = ', '.join(passed(p) for p, _t in m.params)

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
            lines.append('%sreturn %s' % (IND, _answer('fn(%s)' % args, m)))
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
    return head + '%sreturn %s' % (IND, _answer('fn(%s)' % args, m))


def _action_doc(m):
    """What an action does, for one whose stub has no docstring.

    Most actions are one base-class call on one row, and `Calls` and `On`
    already say which.  Without this the facade method gets an empty
    docstring and the trait method nothing but its own name.
    """
    owner, rest = m.calls.split('.', 1)
    call = '%s.%s()' % (owner, '().'.join(rest.split('.')))
    if not m.row:
        return 'Calls `%s`.' % call
    return 'Calls `%s` on the %s at `%s`.' % (call, m.row, m.params[0][0])


# --------------------------------------------------------------------------

def _required_args(fn):
    """The arguments a caller must supply, from a base-class `def`.

    Positional ones with no default, and keyword-only ones with no default --
    `(self, *, key)` and `(self, *args, key)` alike, since either way the
    caller has to pass `key`.  The receiver is bound by Python whatever it is
    called: `self`, or `cls` on a classmethod -- `SensorBase.get_unit(cls)` is
    one -- unless the method is a staticmethod and has none.
    """
    a = fn.args
    positional = a.posonlyargs + a.args
    required = positional[:len(positional) - len(a.defaults)]
    static = any(getattr(d, 'id', getattr(d, 'attr', None)) == 'staticmethod'
                 for d in fn.decorator_list)
    if required and not static:
        required = required[1:]
    out = [x.arg for x in required]
    out += [x.arg for x, d in zip(a.kwonlyargs, a.kw_defaults) if d is None]
    return out


def _resolve_method(classes, cls, meth):
    """Look `cls.meth` up the way Python does: the class, then its bases.

    The class's entry for `meth`, or None when nothing on the way defines it.
    """
    todo, seen = [cls], set()
    while todo:
        c = todo.pop(0)
        if c in seen or c not in classes:
            continue
        seen.add(c)
        entry = classes[c]
        if meth in entry.methods:
            return entry.methods[meth]
        todo.extend(entry.bases)
    return None


def check_arity(model, base_dir=os.path.join(ROOT, 'sonic_platform_base')):
    """Reject a column whose getter the base classes do not define, or that
    needs an argument the row does not pass.

    `ModuleBase.get_module_state_transition(self, module_name)` was declared as
    a plain column, the generated call passed nothing, and the TypeError took
    the entire `ModuleInfo` row with it -- on a SmartSwitch NPU that left
    chassisd logging "Failed to read the modules" every cycle and publishing no
    midplane table at all, which is not a shape any unit test reproduces.

    The signatures are read from `sonic_platform_base` with `ast`, as
    `check_contract` reads it.  They used to come from `inventory.json`, a
    snapshot taken by `scope_scan.py` against trees CI does not have; with the
    snapshot missing or stale the check passed, and a getter it had not seen
    was assumed to take nothing.  Now a path that does not resolve is a
    problem, not a pass.

    Fields declared `WithName()` are exempt: they pass the device's own name.
    A vendor that *narrows* a signature the base class leaves open is a
    different problem and cannot be seen from here; see `Narrowed()`.
    A path through another object (`LeakageSensorBase.get_leak_profile.
    get_type`) names a class the base package does not spell out, and is
    skipped.
    """
    classes = _base_classes(base_dir)
    if not classes:
        return ['no base classes under %s to check the columns against' % base_dir]
    bad = []
    for row in model.rows:
        for f in row.fields:
            if not f.from_ or f.with_name or '.' in (f.getter or ''):
                continue
            method = _resolve_method(classes, f.owner, f.getter)
            if method is None:
                bad.append('%s.%s reads %s, which the base classes do not define'
                           % (row.name, f.name, f.from_))
                continue
            need = method.required
            if need:
                bad.append('%s.%s reads %s(%s) with no arguments; it requires %s'
                           ' -- declare WithName() or pass them'
                           % (row.name, f.name, f.from_, ', '.join(method.params),
                              ', '.join(need)))
    return bad


# The base-class constants each `Literal` alias stands for: (class, prefix).
# An empty prefix names an `enum.Enum`, whose members are the values.  An
# alias that a vendor's answer is read into, or that a daemon's argument is
# passed from, has to be listed here: a new one cannot skip the check by not
# being named.
LITERAL_CONSTANTS = {
    'LedColor': ('DeviceBase', 'STATUS_LED_COLOR_'),
    'ModuleType': ('ModuleBase', 'MODULE_TYPE_'),
    'ModuleStatus': ('ModuleBase', 'MODULE_STATUS_'),
    'LeakSeverity': ('LeakSeverity', ''),
}

# How a base-class docstring says its method answers a bool: "bool: True if",
# "A bool value", "A boolean, True if", "Boolean False if".
_BOOL_ANSWER = re.compile(r'Returns?:\s*(?:a\s+)?bool(?:ean)?\b', re.I)


class _Method(object):
    """One base-class `def`: what its docstring says, and what it takes."""

    def __init__(self, fn):
        self.doc = ast.get_docstring(fn) or ''
        self.required = _required_args(fn)
        a = fn.args
        self.params = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]


class _Class(object):
    """One base class: its bases, its string constants and its methods."""

    def __init__(self, bases, consts, methods):
        self.bases, self.consts, self.methods = bases, consts, methods


def _base_classes(base_dir):
    """Every class in the base package, by name.

    Read with `ast`, not imported: the base classes import swsscommon, which
    the generator has no business needing.
    """
    out = {}
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames.sort()
        for fn in sorted(filenames):
            if not fn.endswith('.py'):
                continue
            with open(os.path.join(dirpath, fn)) as f, warnings.catch_warnings():
                # Their regexes are not raw strings; that is theirs to fix.
                warnings.simplefilter('ignore', SyntaxWarning)
                try:
                    tree = ast.parse(f.read())
                except SyntaxError:
                    continue
            for node in tree.body:
                if not isinstance(node, ast.ClassDef) or node.name in out:
                    continue
                consts, methods = {}, {}
                for item in node.body:
                    if (isinstance(item, ast.Assign) and len(item.targets) == 1
                            and isinstance(item.targets[0], ast.Name)
                            and isinstance(item.value, ast.Constant)
                            and isinstance(item.value.value, str)):
                        consts[item.targets[0].id] = item.value.value
                    elif isinstance(item, ast.FunctionDef):
                        methods[item.name] = _Method(item)
                bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                out[node.name] = _Class(bases, consts, methods)
    return out


def _docstring(classes, cls, meth):
    """`cls.meth`'s docstring, looked up the way Python resolves the method."""
    method = _resolve_method(classes, cls, meth)
    return None if method is None else method.doc


def check_contract(model, base_dir=BASE_DIR,
                   literals=None):
    """Hold the stub to what the base classes say their methods answer.

    `check_arity` verifies that what a column reads exists and can be called;
    nothing verified what an action *answers*.  Every test is generated from, or
    written against, the same stub, so a declaration narrower than the base
    class passes all of them.  `set_module_state_transition` was declared
    `-> None`: the base class's False -- another operation holds the module --
    reached chassisd as success, so its recovery would power-cycle a DPU an
    operator was shutting down.  `ModuleStatus` lacked the three
    `MODULE_STATUS_PROVISION*`, which would have read as None.

    Two rules:

    - an action whose base-class method documents a bool answer is
      `Optional[bool]`;
    - a `Literal` that a vendor's answer is read into, or that an action's
      argument is passed from, holds every value of the base-class constants
      it stands for (`LITERAL_CONSTANTS`).
    """
    literals = LITERAL_CONSTANTS if literals is None else literals
    classes = _base_classes(base_dir)
    if not classes:
        return ['no base classes under %s to check the stub against' % base_dir]
    bad = []

    for m in model.methods:
        # A path through another object (`ChassisBase.get_watchdog.arm`) names
        # a class the base package does not spell out; skip it.
        if m.kind != 'action' or not m.calls or m.calls.count('.') != 1:
            continue
        cls, meth = m.calls.split('.')
        doc = _docstring(classes, cls, meth)
        if doc is None:
            bad.append('%s calls %s, which the base classes do not define'
                       % (m.name, m.calls))
        elif _BOOL_ANSWER.search(doc) and strip_optional(m.returns)[0] != 'bool':
            bad.append('%s returns %s, but %s answers a bool -- declare'
                       ' Optional[bool], or its False reaches the caller as'
                       ' success' % (m.name, m.returns, m.calls))

    used = {}
    for row in model.rows:
        for f in row.fields:
            if f.from_ and f.base in model.enum_names:
                used.setdefault(f.base, '%s.%s' % (row.name, f.name))
    for m in model.methods:
        if m.kind == 'action':
            for p, t in m.params:
                if strip_optional(t)[0] in model.enum_names:
                    used.setdefault(strip_optional(t)[0], '%s(%s)' % (m.name, p))
    values = {e.name: set(e.values) for e in model.enums}
    for alias, where in sorted(used.items()):
        if alias not in literals:
            bad.append('%s is used at %s, but LITERAL_CONSTANTS does not say'
                       ' which base-class constants it stands for' % (alias, where))
            continue
        cls, prefix = literals[alias]
        consts = classes[cls].consts if cls in classes else {}
        want = {v for k, v in consts.items() if k.startswith(prefix)}
        if not want:
            bad.append('%s stands for %s.%s*, which defines no constants'
                       % (alias, cls, prefix))
            continue
        missing = sorted(want - values[alias])
        if missing:
            bad.append('%s lacks %s, which %s.%s* defines -- a vendor answering'
                       ' it would read as None' % (alias, ', '.join(missing), cls, prefix))
    return bad


def build(model):
    # Rows an action addresses by key need a lookup; the rest do not, and
    # emitting one anyway would be dead code in a generated file.
    addressed = {m.row for m in model.methods if m.kind == 'action' and m.row}
    enums = model.enum_names
    row_names = {r.name for r in model.rows}
    snapshots = {m.row: m for m in model.methods if m.kind == 'snapshot'}
    for row in model.rows:
        snap = snapshots.get(row.name)
        row.projected = bool(snap and snap.projected)
        row.skippable = bool(snap and snap.skippable)
        row.guarded = bool(snap and snap.per_row_errors)
        row.absorbs = bool(snap and snap.absorbs)
        row.absorbable = bool(snap and snap.absorbable)
        row.sequential = (row.guarded or row.absorbs or row.absorbable
                          or any(f.read_if for f in row.fields))
        row.col_count = 0
        row.all_cols = 0
        if row.projected:
            _assign_col_bits(row)
            _ALL_COLS[row.name] = row.all_cols
        else:
            for f in row.fields:
                f.col_bit = None
        # What a skipped row still reads: its unguarded columns.
        row.unguarded_mask = sum(1 << f.col_bit for f in row.fields
                                 if f.unguarded and f.col_bit is not None)
        _share_calls(row)
        for f in row.fields:
            f.py_expr = _py_field_expr(f, enums)
            f.rust_ty = rust_type(f.py_type, enums)
            f.rust_expr = _rust_field_expr(f, enums, row_names)
        row.row_body = _row_body(row) if row.sequential else ''
        row.secrets = [f.name for f in row.fields if f.secret]
        row.secrets_py = repr(tuple(row.secrets))
        row.walk_body = _snapshot_body(row)
        row.addressed = row.name in addressed
        if row.addressed and not keyed(row):
            raise ValueError('%s is addressed by an action but declares no Key() field'
                             % row.name)
        row.find_body = _find_body(row) if row.addressed else ''

        # A row can derive Default unless a column is a bare enumeration:
        # there is no neutral colour or fan kind, and picking one would be a
        # value nobody declared.  The rows that can are the ones a test
        # fixture or a partial vendor implementation wants to build piecemeal.
        # The others get `new()`, taking exactly those columns, so that a
        # column added to the stub does not break every struct literal that
        # builds one: `FanInfo { name, ..FanInfo::new(FanKind::Drawer) }`.
        row.can_default = not any(
            f.rust_ty in enums for f in row.fields)
        row.new_params = [f for f in row.fields if f.rust_ty in enums]
    for m in model.methods:
        if m.kind == 'action':
            m.body = _action_body(m, model)
            if not m.doc:
                m.doc = _action_doc(m)
        m.rust_name = m.name
        if m.kind == 'snapshot':
            m.rust_ret = m.row if m.singleton else 'Vec<%s>' % m.row
        else:
            m.rust_ret = rust_type(m.returns, enums)
        m.rust_params = ''.join(
            ', %s: %s' % (_rust_ident(p), _rust_param_type(t, enums)) for p, t in m.params)
        # The column set and the skip list are not stub parameters -- they
        # are the snapshot's own, added by `Snapshot(projected=True)` and
        # `Snapshot(skippable=True)` -- so they are spliced in here rather
        # than declared alongside the others.
        own = []
        if m.kind == 'snapshot' and m.projected:
            own.append(('cols', '%sCols' % m.row))
        if m.kind == 'snapshot' and m.skippable:
            own.append(('skip', '&[DeviceKey]'))
        if m.kind == 'snapshot' and m.absorbable:
            own.append(('absorb', 'bool'))
        m.rust_params = ''.join(', %s: %s' % p for p in own) + m.rust_params
        m.rust_args = ''.join(
            '%s, ' % _rust_arg(p, t, enums) for p, t in m.params)
        # The same parameters passed straight on, with no conversion: what one
        # Rust implementation hands another.  `rust_args` above is the Python
        # call's argument tuple and has conversions baked in, so a forwarder
        # cannot reuse it.
        fwd = [n for n, _t in own] + [_rust_ident(p) for p, _t in m.params]
        m.rust_fwd_args = ', '.join(fwd)
        # What a default body discards, so that rustc does not call it unused.
        m.rust_unused = '(%s,)' % ', '.join(fwd) if fwd else '()'
        # What the bridge hands the facade for the snapshot's own parameters.
        m.py_snapshot_args = '(%s,)' % ', '.join(
            {'cols': 'cols.bits()',
             'skip': 'skip.iter().map(DeviceKey::as_str).collect::<Vec<_>>()',
             'absorb': 'absorb'}[n]
            for n, _t in own)
        m.rust_sweep_args, call = _sweep_call(m, enums, model.enums)
        # A Rust string literal, not jinja's `tojson`: that one escapes the
        # quote in a Python repr as `\u0027`, which Rust does not spell that
        # way and will not compile.
        m.py_sweep_call = json.dumps(call)
        m.rust_ret_conv = _rust_ret_conv(m.rust_ret, enums, row_names)

    # The names the provider's forwarding impl actually mentions.  It converts
    # nothing, so it needs a type only where one appears in a signature --
    # importing the bridge's full list would leave a third of it unused.
    # `Number` is hand-written in platform-api rather than projected from
    # the stub, so it is not in `enums` or `rows`; it still appears in
    # signatures and still has to be imported when it does.
    declared = ([e.name for e in model.enums]
                + [r.name for r in model.rows]
                # A projected snapshot names its column set in the signature,
                # and `\bFanInfo\b` does not match `FanInfoCols`.
                + ['%sCols' % r.name for r in model.rows if r.projected]
                + ['Number', 'DeviceKey'])
    mentioned = ' '.join(m.rust_ret + m.rust_params for m in model.methods)
    model.provider_imports = [
        n for n in declared if re.search(r'\b%s\b' % re.escape(n), mentioned)]

    # The sweep names a type only where it has to build one, so it needs the
    # parameter types and none of the return types: it discards every answer.
    taken = ' '.join(m.rust_params for m in model.methods)
    model.sweep_imports = [
        n for n in declared if re.search(r'\b%s\b' % re.escape(n), taken)]

    # The native back end reads the same model, after everything above has
    # filled it in: it reuses the column bits, the shared calls and the Rust
    # signatures rather than deciding any of them again.
    native.build_facade(model)
    model.native = native.build_object(model, BASE_DIR)
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
    # A Rust string literal.  Not `tojson`, which escapes `<`, `>` and `'` for
    # HTML as `\u003c`, nor `json.dumps`, whose `\uXXXX`, `\b` and `\f` are
    # no more Rust escapes than that is.
    env.filters['rust_str'] = native.rust_str
    out = {}
    for tpl, path in OUTPUTS.items():
        text = env.get_template(tpl).render(model=model, native=getattr(model, 'native', None))
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
    problems = (['arity: %s' % p for p in check_arity(model)]
                + ['contract: %s' % p for p in check_contract(model)])
    if problems:
        for p in problems:
            print(p, file=sys.stderr)
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
