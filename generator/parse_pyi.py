"""Read `sonic_platform_api/facade.pyi` into the model, with `ast`.

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
import string

from model import (
    EnumSpec,
    FieldSpec,
    Model,
    MethodSpec,
    RowSpec,
    SourceSpec,
    rust_type,
    strip_optional,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FACADE_PYI = os.path.join(HERE, os.pardir, 'sonic_platform_api', 'facade.pyi')


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


def _listed(tree, name):
    """One of the stub's (path, reason) declarations: OMITTED, what the facade
    deliberately leaves out, or DEFERRED, what a later phase declares."""
    for node in tree.body:
        target = getattr(node, 'target', None)
        if isinstance(node, ast.AnnAssign) and getattr(target, 'id', '') == name:
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
        elif name == 'Key':
            spec.is_key = True
        elif name == 'ParentKey':
            spec.is_parent_key = True
        elif name == 'Observed':
            spec.sentinels = tuple(kw.get('sentinels', args[0] if args else ()))
            spec.coerce_from = tuple(kw.get('coerce_from', args[1] if len(args) > 1 else ()))
        elif name == 'WithName':
            spec.with_name = True
        elif name == 'Narrowed':
            spec.narrowed = True
        elif name == 'Truthy':
            spec.truthy = True
        elif name == 'Unguarded':
            spec.unguarded = True
        elif name == 'ReadIf':
            spec.read_if = args[0] if args else kw['column']
            spec.read_if_truthy = bool(kw.get('truthy', False))
            spec.read_if_absorbing = bool(kw.get('when_absorbing', True))
        elif name == 'RowError':
            as_repr = kw.get('repr', args[0] if args else False)
            as_column = kw.get('column', args[1] if len(args) > 1 else False)
            if as_repr and as_column:
                raise ParseError('%s: RowError() is the message, its repr or the column,'
                                 ' one of them' % spec.name)
            spec.row_error = 'repr' if as_repr else 'column' if as_column else 'str'
        elif name == 'Secret':
            spec.secret = True
        elif name == 'Unsupported':
            spec.unsupported_on = kw.get('on', args[0] if args else 'none')
            spec.default = kw.get('default', args[1] if len(args) > 1 else None)
            # 'error' was declared and never generated: it read exactly as
            # 'none'.  Refused rather than accepted, because the stub is the
            # contract and a value that changes nothing is a promise nobody keeps.
            if spec.unsupported_on not in ('none', 'default'):
                raise ParseError('%s: Unsupported(on=%r) is not implemented; a field is'
                                 ' "none" or "default"' % (spec.name, spec.unsupported_on))
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
        provider = skw.get('provider', '')
        mapping = skw.get('mapping', '')
        from_ = sargs[0] if sargs else skw.get('from_', '')
        # Named by whichever origin it has.  `sargs[0]` is only the positional
        # `from_`; a `mapping=` or `provider=` source has no positional
        # argument, and indexing for one turned the parent_default error below
        # into an IndexError that named nothing.
        label = from_ or mapping or provider or 'FlattenSource()'
        pd = skw.get('parent_default', '')
        if isinstance(pd, str):
            pd = (pd,)
        levels = max(len(via), 1)
        if len(pd) != levels:
            raise ParseError(
                '%s: parent_default has %d entries for %d via level(s)'
                % (label, len(pd), levels))
        when_unsupported = skw.get('when_unsupported', 'absent')
        if when_unsupported not in ('absent', 'present'):
            raise ParseError('%s: when_unsupported is "absent" or "present", not %r'
                             % (label, when_unsupported))
        if 'when_unsupported' in skw and not skw.get('when'):
            raise ParseError('%s: when_unsupported without a when' % label)
        parent_missing = tuple(skw.get('parent_missing', ()))
        if parent_missing and not (skw.get('parent') and via):
            raise ParseError('%s: parent_missing needs a parent getter to apply to' % label)
        sets = tuple(skw.get('sets', ()))
        if any(v == '@parent_raw' for _f, v in sets) and not (skw.get('parent') and via):
            raise ParseError('%s: "@parent_raw" needs a parent getter to read' % label)
        if sum(1 for x in (from_, mapping, provider) if x) != 1:
            raise ParseError(
                'a FlattenSource takes exactly one of from_, mapping or '
                'provider: %r / %r / %r' % (from_, mapping, provider))
        index_from_previous = bool(skw.get('index_from_previous', False))
        if index_from_previous:
            # One numbering over two lists only makes sense where both hang
            # off the same fixed parent: with a `via`, `{i}` is the position
            # under whichever parent this row came from.
            prev = out[-1] if out else None
            if prev is None:
                raise ParseError('%s: index_from_previous on the first source, which'
                                 ' has nothing before it to count on from' % label)
            for who, s_via, s_mapping, s_single in ((label, via, mapping, skw.get('single')),
                                                     (prev.describes, prev.via, prev.mapping,
                                                      prev.single)):
                if s_via or s_mapping or s_single:
                    raise ParseError('%s: index_from_previous needs it and the source before'
                                     ' it to be plain lists under one fixed parent; %s is not'
                                     % (label, who))
            if '{i}' in pd[0]:
                # The parent would be named by one position and the row by
                # another.
                raise ParseError('%s: index_from_previous under a parent named by'
                                 ' position (%r)' % (label, pd[0]))
            if prev.parent_default != pd:
                raise ParseError('%s: index_from_previous counts on from a source under'
                                 ' another parent (%r, not %r)'
                                 % (label, prev.parent_default[0], pd[0]))
        out.append(SourceSpec(
            from_=from_,
            mapping=mapping,
            provider=provider,
            via=via,
            when=skw.get('when'),
            when_unsupported=when_unsupported,
            when_chassis=skw.get('when_chassis'),
            parent=skw.get('parent'),
            parent_missing=parent_missing,
            parent_default=pd,
            index_from_previous=index_from_previous,
            optional=bool(skw.get('optional', False)),
            single=bool(skw.get('single', False)),
            reaches=tuple(skw.get('reaches', ())),
            sets=sets,
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
        names = [_resolve(meta, consts)[0] for meta in dec.args]
        if 'Snapshot' in names and 'EscapeHatch' in names:
            # A hand-written body reads when it is called and as it is
            # written; nothing a Snapshot says would reach it.
            raise ParseError('%s: an EscapeHatch is not also a Snapshot; its body'
                             ' is hand-written' % spec.name)
        for meta in dec.args:
            name, args, kw = _resolve(meta, consts)
            if name == 'Snapshot':
                if args or 'scope' in kw:
                    # Declared once and never generated: per_cycle and per_call
                    # produced the same code.  Every snapshot reads on call.
                    raise ParseError('%s: Snapshot(scope=...) is not implemented;'
                                     ' a snapshot reads when it is called' % spec.name)
                spec.kind = 'snapshot'
                spec.projected = bool(kw.get('projected', False))
                spec.skippable = bool(kw.get('skippable', False))
                spec.per_row_errors = bool(kw.get('per_row_errors', False))
                spec.absorbs = bool(kw.get('absorbs', False))
                spec.absorbable = bool(kw.get('absorbable', False))
                unknown = set(kw) - {'projected', 'skippable', 'per_row_errors',
                                     'absorbs', 'absorbable'}
                if unknown:
                    raise ParseError('%s: Snapshot(%s) is not implemented'
                                     % (spec.name, ', '.join(sorted(unknown))))
            elif name == 'Unsupported':
                raise ParseError('%s: Unsupported() on a method is not implemented: an'
                                 ' action raises NotImplementedError for a missing method'
                                 ' and passes on anything else; see Calls' % spec.name)
            elif name == 'On':
                spec.row = kw.get('row', args[0] if args else None)
                spec.pass_key = bool(kw.get('pass_key', False))
            elif name == 'Calls':
                spec.calls = kw.get('path', args[0] if args else None)
                spec.calls_at = kw.get('at', args[1] if len(args) > 1 else None)
                spec.calls_ints = tuple(kw.get('ints', ()))
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
    model = Model(enums=_literal_aliases(tree), omitted=_listed(tree, 'OMITTED'),
                  deferred=_listed(tree, 'DEFERRED'))

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
    #
    # A method's *return* type counts too.  `ModuleBase.get_reboot_cause()`
    # answers `(cause, detail)` and both halves are published, so the method
    # hands back a two-column row built from the one call rather than one slot
    # of it.  Such a row is reached only through that method: it has no ORDER
    # and nothing flattens it, which is the same standing an escape hatch's
    # row has.
    handwritten = {m.row for m in model.methods if m.row and m.kind == 'escape'}
    returned = {r for r in (_returned_row(m, declared_rows) for m in model.methods) if r}
    for row in model.rows:
        row.referenced = row.name in handwritten or row.name in returned
    _validate(model)
    return model


def _returned_row(m, declared_rows):
    """The row a method hands back, if its return type names one.

    Not `m.row`: that is the row an action *addresses by key*, which for
    `get_module_reboot_cause(module)` is ModuleInfo.  What it returns is a
    different thing.
    """
    base = m.returns.strip()
    if base.startswith('Optional[') and base.endswith(']'):
        base = base[len('Optional['):-1].strip()
    return base if base in declared_rows else None


def _validate_guard(row, snap):
    """`per_row_errors`, `skippable` and the column metadata they read."""
    errs = {f.row_error: f for f in row.fields if f.row_error}
    guarded = bool(snap and snap.per_row_errors)
    spelled = {'str': ('error', ''), 'repr': ('error_repr', 'repr=True'),
               'column': ('error_column', 'column=True')}
    for f in errs.values():
        want, arg = spelled[f.row_error]
        if (f.name, f.py_type) != (want, 'Optional[str]') or f.from_ or f.is_parent \
                or f.is_key or f.is_parent_key:
            raise ParseError('%s.%s: RowError(%s) is spelled `%s: Optional[str]` and nothing'
                             ' else' % (row.name, f.name, arg, want))
    absorbs = bool(snap and snap.absorbs)
    absorbable = bool(snap and snap.absorbable)
    if absorbs and (guarded or absorbable):
        raise ParseError('%s: absorbs reads every row that way; per_row_errors or absorbable'
                         ' beside it would never be used' % snap.name)
    if absorbable and not guarded:
        raise ParseError('%s: absorbable is a choice between absorbing and per_row_errors;'
                         ' declare per_row_errors too' % snap.name)
    if (absorbs or absorbable) and snap.singleton:
        raise ParseError('%s: a singleton has no rows to read one column at a time'
                         % snap.name)
    if (absorbs or absorbable) and any(f.unguarded for f in row.fields):
        raise ParseError('%s: Unguarded() and absorbing are not one mode any daemon has: a'
                         ' getter either fails the read or costs its own column' % row.name)
    if guarded and set(errs) != set(spelled):
        raise ParseError('%s: its snapshot is per_row_errors, so it declares `error`,'
                         ' `error_repr` and `error_column` as RowError() columns' % row.name)
    if errs and not guarded:
        raise ParseError('%s declares RowError() columns, but no snapshot answering it is'
                         ' per_row_errors: nothing would ever set them' % row.name)
    if snap and snap.singleton and guarded:
        raise ParseError('%s: a singleton has no other rows to keep; per_row_errors is'
                         ' for a list' % row.name)
    skippable = bool(snap and snap.skippable)
    if skippable and not snap.projected:
        raise ParseError('%s: skippable needs projected -- a skipped row is read with'
                         ' fewer columns' % snap.name)
    if skippable and not any(f.is_key for f in row.fields):
        raise ParseError('%s: skippable names rows by key, and %s has no Key()'
                         % (snap.name, row.name))
    earlier = {}
    for f in row.fields:
        if f.unguarded:
            if not (guarded or skippable):
                raise ParseError('%s.%s: Unguarded() means something only on a row whose'
                                 ' snapshot is per_row_errors or skippable' % (row.name, f.name))
            if not f.from_:
                raise ParseError('%s.%s: Unguarded() is for a column read off the device'
                                 % (row.name, f.name))
        # A skipped row reads only its unguarded columns, and `name` is read
        # whatever the column set says; so on a skippable row it has to be one.
        if skippable and f.name == 'name' and f.from_ and not f.unguarded:
            raise ParseError('%s.name: a skipped row still reads its name, so on a'
                             ' skippable row it is Unguarded()' % row.name)
        if f.read_if is not None:
            src = earlier.get(f.read_if)
            if src is None or not src.from_:
                raise ParseError('%s.%s: ReadIf(%r) names no column read before it'
                                 % (row.name, f.name, f.read_if))
            # Not read is absent: None, or the declared default where there is
            # one -- what a declined column holds too.
            if not f.from_ or not (f.optional or f.unsupported_on == 'default'):
                raise ParseError('%s.%s: ReadIf() is for a column read off the device that'
                                 ' is Optional or has a default' % (row.name, f.name))
            if not f.read_if_absorbing and not absorbable:
                raise ParseError('%s.%s: ReadIf(when_absorbing=False) means something only'
                                 ' on a snapshot that is absorbable' % (row.name, f.name))
            if f.unguarded != src.unguarded:
                raise ParseError('%s.%s: ReadIf(%r) across the guard; both sides or neither'
                                 % (row.name, f.name, f.read_if))
        earlier[f.name] = f


def _validate(model):
    """Catch in the model what neither mypy nor stubtest can see."""
    enum_names = model.enum_names
    snapshots = {m.row: m for m in model.methods if m.kind == 'snapshot'}
    for row in model.rows:
        names = {f.name for f in row.fields}
        _validate_guard(row, snapshots.get(row.name))
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
        # A fallback name is formatted over `{parent}`, `{i}` and the fields
        # every source fixes; anything else would only fail when a device
        # without a name turned up.
        fixed_by_all = (set.intersection(*({n for n, _v in src.sets} for src in row.sources))
                        if row.sources else set())
        for f in row.fields:
            if f.unsupported_on != 'default' or not isinstance(f.default, str):
                continue
            for _lit, ref, _spec, _conv in string.Formatter().parse(f.default):
                if ref is not None and ref not in {'parent', 'i'} | fixed_by_all:
                    raise ParseError(
                        '%s.%s: the default %r names {%s}, which is neither {parent},'
                        ' {i} nor a field every source sets'
                        % (row.name, f.name, f.default, ref))
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
            if f.row_error:
                continue
            if f.is_key or f.is_parent_key:
                want = ('key', 'DeviceKey') if f.is_key else ('parent_key', 'Optional[DeviceKey]')
                if (f.name, f.py_type) != want or f.from_ or f.is_parent:
                    raise ParseError('%s.%s: Key()/ParentKey() is spelled `%s: %s` and nothing else'
                                     % (row.name, f.name, want[0], want[1]))
                # The key is the path the traversal took, and an action
                # follows it back with the same calls.  A mapping entry has no
                # device behind it to follow back to.
                for src in row.sources:
                    if src.mapping:
                        raise ParseError('%s: a keyed row cannot come from %s'
                                         % (row.name, src.describes))
                continue
            if f.from_ and f.is_parent:
                raise ParseError('%s.%s: both From() and Parent()' % (row.name, f.name))
            if not f.from_ and not f.is_parent:
                raise ParseError('%s.%s: neither From() nor Parent()' % (row.name, f.name))
            if f.base in enum_names and f.sentinels:
                raise ParseError(
                    '%s.%s: %s is an enumeration; a sentinel here would delete a value'
                    % (row.name, f.name, f.base))
            # A reading or a limit has no neutral value: a missing one cannot
            # fall back to 0 without becoming a reading -- or a limit every
            # reading crosses -- and Rust's `Number` has no Default for the
            # row to derive.  Every one the base classes document can be
            # unreadable, so `Optional` is the only honest spelling.
            if f.base == 'float':
                raise ParseError(
                    '%s.%s: a float column would publish an int the platform answered'
                    ' as a float; declare it Number, or the unit it measures'
                    % (row.name, f.name))
            if rust_type(f.base, enum_names) == 'Number' and not f.optional:
                raise ParseError(
                    '%s.%s: a %s has no neutral value; declare it '
                    'Optional[%s]' % (row.name, f.name, f.base, f.base))

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
                    '%s addresses %s by key, but it is a singleton'
                    % (m.name, m.row))
            params = dict(m.params)
            for p in getattr(m, 'calls_ints', ()):
                if params.get(p) != 'bool':
                    raise ParseError('%s: Calls(ints=...) names %r, which is not a bool'
                                     ' parameter' % (m.name, p))


if __name__ == '__main__':
    m = parse()
    print('rows    : %d' % len(m.rows))
    for r in m.rows:
        print('   %-16s %2d fields, %d sources' % (r.name, len(r.fields), len(r.sources)))
    print('methods : %d' % len(m.methods))
    for x in m.methods:
        print('   %-22s %-9s -> %s' % (x.name, x.kind, x.returns))
    print('enums   : %s' % ', '.join('%s(%d)' % (e.name, len(e.values)) for e in m.enums))
