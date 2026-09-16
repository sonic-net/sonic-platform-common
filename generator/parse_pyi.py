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
"""Read `platform_api/facade.pyi` into the model, with `ast`.

The stub is never imported.  `ast` is in the standard library, so the
generator has no build-time dependency on a type checker -- `mypy` gates the
stub in CI, but a build that has to produce the bridge does not need it.

Metadata arrives as `Annotated[...]` arguments on fields and
`@platform_method(...)` decorators on methods.  Both are plain call
expressions in the syntax tree, so reading them is `ast.literal_eval` on the
arguments plus a lookup on the callee's name.  Module-level assignments of
metadata objects (`_MISSING = Observed(...)`) are resolved first so that a
field can refer to one by name rather than repeating it.
"""

import ast
import os

from model import (
    EnumSpec,
    FieldSpec,
    Model,
    MethodSpec,
    RowSpec,
    SourceSpec,
    strip_optional,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FACADE_PYI = os.path.join(HERE, os.pardir, 'platform_api', 'facade.pyi')


class ParseError(Exception):
    pass


def _src(node):
    """The type as written, so the model keeps the stub's own spelling."""
    return ast.unparse(node)


def _literal(node):
    try:
        return ast.literal_eval(node)
    except ValueError:
        # A metadata object used as a value, e.g. Observed(...) nested in a
        # call.  The caller resolves those; here it is not a literal.
        raise ParseError('not a literal: %s' % _src(node))


def _callee(node):
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    return getattr(f, 'id', getattr(f, 'attr', None))


def _kwargs(node, consts):
    """Positional and keyword arguments of a metadata call, as Python values."""
    args, kw = [], {}
    for a in node.args:
        args.append(_resolve(a, consts))
    for k in node.keywords:
        kw[k.arg] = _resolve(k.value, consts)
    return args, kw


def _resolve(node, consts):
    """A literal, a named module-level constant, or a nested metadata call."""
    if isinstance(node, ast.Name) and node.id in consts:
        return consts[node.id]
    if isinstance(node, ast.Call):
        name = _callee(node)
        args, kw = _kwargs(node, consts)
        return (name, args, kw)
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(_resolve(e, consts) for e in node.elts)
    return _literal(node)


def _module_consts(tree):
    """Module-level metadata objects, so a field can name one."""
    consts = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not (len(targets) == 1 and isinstance(targets[0], ast.Name)):
                continue
            if node.value is None or not isinstance(node.value, ast.Call):
                continue
            consts[targets[0].id] = _resolve(node.value, consts)
    return consts


def _omitted(tree):
    """The stub's OMITTED declaration: what the facade deliberately leaves out."""
    for node in tree.body:
        target = getattr(node, 'target', None)
        if isinstance(node, ast.AnnAssign) and getattr(target, 'id', '') == 'OMITTED':
            return tuple(ast.literal_eval(node.value))
    return ()


def _literal_aliases(tree):
    """`LedColor = Literal["green", ...]` -> an enum in the model."""
    out = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        v = node.value
        if isinstance(v, ast.Subscript) and getattr(v.value, 'id', None) == 'Literal':
            sl = v.slice
            elts = sl.elts if isinstance(sl, ast.Tuple) else [sl]
            out.append(EnumSpec(target.id, tuple(e.value for e in elts)))
    return out


# --------------------------------------------------------------------------

def _field(node, consts):
    """One `name: Annotated[T, From(...), ...]` declaration."""
    ann = node.annotation
    if not (isinstance(ann, ast.Subscript) and getattr(ann.value, 'id', None) == 'Annotated'):
        return None
    parts = ann.slice.elts if isinstance(ann.slice, ast.Tuple) else [ann.slice]
    py_type = _src(parts[0])
    base, optional = strip_optional(py_type)

    spec = FieldSpec(name=node.target.id, py_type=py_type, base=base, optional=optional)
    for meta in parts[1:]:
        resolved = _resolve(meta, consts)
        if not isinstance(resolved, tuple) or len(resolved) != 3:
            raise ParseError('%s: unreadable metadata %s' % (spec.name, _src(meta)))
        name, args, kw = resolved
        if name == 'From':
            spec.from_ = args[0] if args else kw['path']
            spec.at = kw.get('at', args[1] if len(args) > 1 else None)
        elif name == 'Parent':
            spec.is_parent = True
        elif name == 'Observed':
            spec.sentinels = tuple(kw.get('sentinels', args[0] if args else ()))
            spec.coerce_from = tuple(kw.get('coerce_from', args[1] if len(args) > 1 else ()))
        elif name == 'Unsupported':
            spec.unsupported_on = kw.get('on', args[0] if args else 'none')
            spec.default = kw.get('default', args[1] if len(args) > 1 else None)
        else:
            raise ParseError('%s: unknown field metadata %r' % (spec.name, name))
    return spec


def _sources(node, consts):
    """The `ORDER: ClassVar[Flatten] = Flatten(sources=(...))` declaration."""
    resolved = _resolve(node.value, consts)
    name, args, kw = resolved
    if name != 'Flatten':
        raise ParseError('ORDER must be a Flatten, got %r' % name)
    raw = kw.get('sources', args[0] if args else ())

    out = []
    for entry in raw:
        sname, sargs, skw = entry
        if sname != 'FlattenSource':
            raise ParseError('Flatten.sources takes FlattenSource, got %r' % sname)
        via = []
        for entry in skw.get('via', ()):
            if isinstance(entry, str):
                via.append((entry, False))
            elif isinstance(entry, tuple) and len(entry) == 3 and entry[0] == 'Via':
                _n, vargs, vkw = entry
                via.append((vargs[0] if vargs else vkw['path'],
                            bool(vkw.get('single', vargs[1] if len(vargs) > 1 else False))))
            else:
                raise ParseError('via takes a path or a Via(), got %r' % (entry,))
        via = tuple(via)
        pd = skw.get('parent_default', '')
        if isinstance(pd, str):
            pd = (pd,)
        levels = max(len(via), 1)
        if len(pd) != levels:
            raise ParseError(
                '%s: parent_default has %d entries for %d via level(s)'
                % (sargs[0], len(pd), levels))
        provider = skw.get('provider', '')
        mapping = skw.get('mapping', '')
        from_ = sargs[0] if sargs else skw.get('from_', '')
        if sum(1 for x in (from_, mapping, provider) if x) != 1:
            raise ParseError(
                'a FlattenSource takes exactly one of from_, mapping or '
                'provider: %r / %r / %r' % (from_, mapping, provider))
        out.append(SourceSpec(
            from_=from_,
            mapping=mapping,
            provider=provider,
            via=via,
            when=skw.get('when'),
            when_chassis=skw.get('when_chassis'),
            parent=skw.get('parent'),
            parent_default=pd,
            optional=bool(skw.get('optional', False)),
            single=bool(skw.get('single', False)),
            reaches=tuple(skw.get('reaches', ())),
            sets=tuple(skw.get('sets', ())),
        ))
    return out


def _method(node, consts):
    spec = MethodSpec(
        name=node.name,
        returns=_src(node.returns) if node.returns else 'None',
        doc=ast.get_docstring(node) or '',
    )
    for arg in node.args.args:
        if arg.arg == 'self':
            continue
        spec.params.append((arg.arg, _src(arg.annotation) if arg.annotation else 'object'))

    for dec in node.decorator_list:
        if _callee(dec) != 'platform_method':
            continue
        for meta in dec.args:
            name, args, kw = _resolve(meta, consts)
            if name == 'Snapshot':
                # An EscapeHatch stays one: the body is hand-written whatever
                # else the declaration says about how often it is read.
                if spec.kind != 'escape':
                    spec.kind = 'snapshot'
                spec.snapshot_scope = kw.get('scope', args[0] if args else 'per_call')
            elif name == 'Unsupported':
                spec.unsupported_on = kw.get('on', args[0] if args else 'none')
            elif name == 'On':
                spec.row = kw.get('row', args[0] if args else None)
                spec.pass_key = bool(kw.get('pass_key', False))
            elif name == 'Calls':
                spec.calls = kw.get('path', args[0] if args else None)
            elif name == 'EscapeHatch':
                spec.kind = 'escape'
                spec.escape_reason = kw.get('reason', args[0] if args else '')
                spec.reaches = tuple(kw.get('reaches', ()))
            else:
                raise ParseError('%s: unknown method metadata %r' % (spec.name, name))

    if spec.kind == 'escape':
        return spec
    if spec.kind == 'snapshot':
        r = spec.returns
        if r.startswith('list[') and r.endswith(']'):
            spec.row = r[len('list['):-1].strip()
        else:
            # A singleton: the chassis is the device.
            spec.row = r
            spec.singleton = True
    return spec


def parse(path=FACADE_PYI):
    tree = ast.parse(open(path).read(), filename=path)
    consts = _module_consts(tree)
    model = Model(enums=_literal_aliases(tree), omitted=_omitted(tree))

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name == 'PlatformApi':
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and not item.name.startswith('__'):
                    model.methods.append(_method(item, consts))
            continue

        row = RowSpec(name=node.name, doc=ast.get_docstring(node) or '')
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                if item.target.id == 'ORDER':
                    row.sources = _sources(item, consts)
                else:
                    f = _field(item, consts)
                    if f:
                        row.fields.append(f)
        if row.fields:
            model.rows.append(row)

    declared_rows = {r.name for r in model.rows}
    for m in model.methods:
        ret = m.returns
        if ret.startswith('list[') and ret.endswith(']'):
            ret = ret[len('list['):-1].strip()
        if ret in declared_rows and m.kind == 'escape':
            m.row = ret
    for row in model.rows:
        for f in row.fields:
            base = f.base
            if base.startswith('list[') and base.endswith(']'):
                inner = base[len('list['):-1].strip()
                if inner in declared_rows:
                    model.row(inner).nested = True
    for m in model.methods:
        if m.kind == 'snapshot' and m.singleton:
            r = model.row(m.row)
            if r is not None:
                r.singleton = True
    # Only an escape hatch excuses a row from declaring how it is flattened.
    # A snapshot returning list[Row] still needs an ORDER -- without one there
    # is nothing for the traversal to walk, and the accessor would answer an
    # empty list on every platform.
    handwritten = {m.row for m in model.methods if m.row and m.kind == 'escape'}
    for row in model.rows:
        row.referenced = row.name in handwritten
    _validate(model)
    return model


def _validate(model):
    """Catch in the model what neither mypy nor stubtest can see."""
    enum_names = model.enum_names
    for row in model.rows:
        names = {f.name for f in row.fields}
        if not row.sources and not (row.singleton or row.nested or row.referenced):
            raise ParseError(
                '%s has no ORDER and nothing returns it: either declare how it '
                'is flattened, or stop declaring it' % row.name)
        if row.sources and (row.singleton or row.nested):
            raise ParseError(
                '%s carries an ORDER but nothing flattens it: it is %s'
                % (row.name,
                   'a singleton' if row.singleton else 'nested in another row'))
        for src in row.sources:
            for fname, _v in src.sets:
                if fname not in names:
                    raise ParseError(
                        '%s: source %s sets unknown field %r'
                        % (row.name, src.from_, fname))
        # A field the flatten plan is supposed to fill must actually be filled
        # by every source, or a row silently carries a hole.
        for f in row.fields:
            if not f.is_parent:
                continue
            if f.name == 'parent_name':
                continue
            for src in row.sources:
                if f.name not in {n for n, _v in src.sets}:
                    raise ParseError(
                        '%s.%s is Parent() but source %s does not set it'
                        % (row.name, f.name, src.from_))
        for f in row.fields:
            if f.from_ and f.is_parent:
                raise ParseError('%s.%s: both From() and Parent()' % (row.name, f.name))
            if not f.from_ and not f.is_parent:
                raise ParseError('%s.%s: neither From() nor Parent()' % (row.name, f.name))
            if f.base in enum_names and f.sentinels:
                raise ParseError(
                    '%s.%s: %s is an enumeration; a sentinel here would delete a value'
                    % (row.name, f.name, f.base))

    declared = {r.name for r in model.rows}
    for m in model.methods:
        if m.kind == 'snapshot' and m.row not in declared:
            raise ParseError('%s returns undeclared row %s' % (m.name, m.row))
        if m.kind == 'action':
            if not m.calls:
                raise ParseError(
                    '%s: an action must declare Calls(), or be an EscapeHatch' % m.name)
            if m.row and m.row not in declared:
                raise ParseError('%s addresses undeclared row %s' % (m.name, m.row))
            if m.row and not m.params:
                raise ParseError('%s: On() needs a first parameter naming the row' % m.name)
            if m.row and model.row(m.row) is not None and model.row(m.row).singleton:
                raise ParseError(
                    '%s addresses %s by name, but it is a singleton'
                    % (m.name, m.row))


if __name__ == '__main__':
    m = parse()
    print('rows    : %d' % len(m.rows))
    for r in m.rows:
        print('   %-16s %2d fields, %d sources' % (r.name, len(r.fields), len(r.sources)))
    print('methods : %d' % len(m.methods))
    for x in m.methods:
        print('   %-22s %-9s -> %s' % (x.name, x.kind, x.returns))
    print('enums   : %s' % ', '.join('%s(%d)' % (e.name, len(e.values)) for e in m.enums))
