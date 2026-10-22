"""The native back end: the base classes as a Rust trait, and the facade over it.

`platform-base` is what a native implementation is written against.  Two
files of it are generated here, from the same model the Python facade and the
bridge come from:

- `object.rs` -- `PyObject`, one trait every platform object implements.  Its
  methods are the base-class methods the facade and the escape hatches reach,
  by their Python names.  Each default is what the object's *base class*
  answers -- found by walking `sonic_platform_base` with `ast` the way Python
  resolves the method -- so a native fan that overrides nothing answers exactly
  what a Python fan that overrides nothing answers, and a method its base class
  does not define is missing, as `getattr(obj, name, None)` would find it.

- `facade.rs` -- `PlatformApi` over a chassis of such objects.  Every helper,
  every traversal and every column expression below is the Rust spelling of a
  line `generate.py` writes into `facade.py`, followed by the read the bridge
  makes of the result.  The two back ends are kept side by side on purpose: a
  change to one here is a change to the other, or the native implementation
  stops answering what the Python one does.
"""

import ast
import os
import re
import warnings

from model import _snake, key_segment, keyed, rust_type, strip_optional, template_fields

# Methods the hand-written parts of platform-base call that no declaration in
# the stub names: the escape hatches (`_escape_hatch.py`) and the base-class
# bodies.  (base class, method, ((param, python type), ...)).  `object` is a
# platform object passed back in, as the thermal manager is handed the chassis.
EXTRA = (
    ('ChassisBase', 'get_thermal_manager', ()),
    # What `get_module_key` resolves a module name with, as chassisd does.
    ('ChassisBase', 'get_module_index', (('module_name', 'str'),)),
    ('ChassisBase', 'get_eeprom', ()),
    ('ChassisBase', 'get_change_event', (('timeout', 'int'),)),
    ('ModuleBase', 'get_all_asics', ()),
    # What ModuleBase's PCI handling calls, and a DPU module overrides.
    ('ModuleBase', 'get_pci_bus_info', ()),
    ('ModuleBase', 'pci_detach', ()),
    ('ModuleBase', 'pci_reattach', ()),
    # What SedMgmtBase's password changes ask the vendor.
    ('SedMgmtBase', 'get_min_sed_password_len', ()),
    ('SedMgmtBase', 'get_max_sed_password_len', ()),
    ('SedMgmtBase', 'get_default_sed_password', ()),
    ('SedMgmtBase', 'get_tpm_bank_a_address', ()),
    ('SedMgmtBase', 'get_tpm_bank_b_address', ()),
    # What the base-class bodies call: PdbBase answers its PSU-shaped
    # readings from its output ones, FanBase judges speed with a tolerance.
    ('PdbBase', 'get_output_voltage', ()),
    ('PdbBase', 'get_output_current', ()),
    ('PdbBase', 'get_output_power', ()),
    ('FanBase', 'get_speed_tolerance', ()),
    ('ThermalManagerBase', 'initialize', ()),
    ('ThermalManagerBase', 'load', (('policy_file_name', 'str'),)),
    ('ThermalManagerBase', 'init_thermal_algorithm', (('chassis', 'object'),)),
    ('ThermalManagerBase', 'run_policy', (('chassis', 'object'),)),
    ('ThermalManagerBase', 'get_interval', ()),
    ('ThermalManagerBase', 'stop', ()),
    ('ThermalManagerBase', 'deinitialize', ()),
    ('TlvInfoDecoder', 'read_eeprom', ()),
    ('TlvInfoDecoder', 'update_eeprom_db', (('e', 'object'),)),
    ('BMCBase', 'open_session', ()),
    ('BMCBase', 'close_session', (('session_id', 'str'),)),
    ('BMCBase', 'reset_root_password', ()),
    ('BMCBase', 'request_bmc_reset', (('graceful', 'bool'),)),
    ('BMCBase', 'update_firmware', (('fw_image', 'str'),)),
    ('BMCBase', 'trigger_bmc_debug_log_dump', ()),
    ('BMCBase', 'get_bmc_debug_log_dump', (('task_id', 'str'), ('filename', 'str'), ('path', 'str'))),
)

# The base classes a platform object can derive from, as `BaseClass` names
# them.  `object` derives from none: every method is missing on it.
BASES = (
    'ChassisBase', 'ModuleBase', 'FanBase', 'FanDrawerBase', 'PsuBase', 'PdbBase',
    'ThermalBase', 'SensorBase', 'VoltageSensorBase', 'CurrentSensorBase',
    'LiquidCoolingBase', 'LeakageSensorBase', 'LeakSensorProfileBase',
    'ComponentBase', 'WatchdogBase', 'BMCBase', 'SedMgmtBase',
    'ThermalManagerBase', 'TlvInfoDecoder',
)

# A Python int is as wide as PyVal::Int: a fan speed from a policy file is
# whatever the file says, not a C long.
RUST_PARAM = {'str': '&str', 'bool': 'bool', 'int': 'i128', 'float': 'f64', 'object': 'PyVal'}

# The arguments the generated sweep (`tests/generated/object_sweep.rs`) calls
# every default with.  A default that raises or returns a literal does not
# look at them; the bodies below that read one are noted.
SWEEP_ARG = {'str': '"sweep"', 'bool': 'false', 'int': '0', 'float': '0.0', 'object': 'PyVal::None'}
# The same, as the Python values a `DynObject` hands its handler.
SWEEP_PY = {'str': 'sweep', 'bool': False, 'int': 0, 'float': 0.0, 'object': None}

# The base-class bodies the sweep calls, with what each answers for an object
# of that class overriding nothing, as Python would (or, for what is not
# ported, as the native code says so).  The others are left out: they write
# files, take locks, run commands, talk Redfish, or keep the PSU master LED
# in process-wide state.  Their own tests are in `crate::bodies`.
SWEEP_BODIES = {
    # `device_info.is_switch_bmc()` is false off a BMC, so the base class raises.
    ('ChassisBase', 'get_status_led'): 'raise NotImplementedError: ',
    ('ChassisBase', 'set_status_led'): 'raise NotImplementedError: ',
    ('ChassisBase', 'initizalize_system_led'): 'raise NotImplementedError: ',
    # `get_speed()` is the first reading, and it raises.
    ('FanBase', 'is_under_speed'): 'raise NotImplementedError: ',
    ('FanBase', 'is_over_speed'): 'raise NotImplementedError: ',
    # `return self.get_output_voltage()`, which raises.
    ('PdbBase', 'get_voltage'): 'raise NotImplementedError: ',
    ('PdbBase', 'get_current'): 'raise NotImplementedError: ',
    ('PdbBase', 'get_power'): 'raise NotImplementedError: ',
    # What a base instance constructed with its defaults answers: no leak
    # recorded, and no profiles passed in.
    ('LeakageSensorBase', 'get_leak_severity'): 'ok None',
    ('LiquidCoolingBase', 'get_all_profiles'): 'ok []',
    # No /etc/sonic/sed_config.conf off a switch: None.
    ('SedMgmtBase', 'get_tpm_bank_a_address'): 'ok None',
    ('SedMgmtBase', 'get_tpm_bank_b_address'): 'ok None',
    # The class-level defaults: no policy, nothing to run at boot, 60 s.
    ('ThermalManagerBase', 'get_interval'): 'ok 60',
    ('ThermalManagerBase', 'init_thermal_algorithm'): 'ok None',
    ('ThermalManagerBase', 'load'):
        "raise FileNotFoundError: [Errno 2] No such file or directory: 'sweep'",
    ('ThermalManagerBase', 'run_policy'): 'ok None',
    ('ThermalManagerBase', 'stop'): 'ok None',
    ('TlvInfoDecoder', 'read_eeprom'):
        'raise RuntimeError: not ported to the native platform API: TlvInfoDecoder.read_eeprom',
    ('TlvInfoDecoder', 'update_eeprom_db'):
        'raise RuntimeError: not ported to the native platform API: TlvInfoDecoder.update_eeprom_db',
}


def _param_kind(py_type, enums):
    """A stub parameter type as the trait method takes it."""
    t = strip_optional(py_type)[0]
    if t == 'str' or t in enums:
        return 'str'
    if t == 'bool':
        return 'bool'
    if rust_type(t, enums) == 'Number':
        return 'object'
    if rust_type(t, enums) == 'f64':
        return 'float'
    return 'int'


# ── the base classes, read with ast ─────────────────────────────────────────

def read_classes(base_dir):
    """name -> (bases, {method: FunctionDef}, {attr: value node from __init__})."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames.sort()
        for fn in sorted(filenames):
            if not fn.endswith('.py'):
                continue
            with open(os.path.join(dirpath, fn)) as f, warnings.catch_warnings():
                warnings.simplefilter('ignore', SyntaxWarning)
                try:
                    tree = ast.parse(f.read())
                except SyntaxError:
                    continue
            for node in tree.body:
                if not isinstance(node, ast.ClassDef) or node.name in out:
                    continue
                bases = []
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        bases.append(b.id)
                    elif isinstance(b, ast.Attribute):
                        bases.append(b.attr)
                methods = {m.name: m for m in node.body if isinstance(m, ast.FunctionDef)}
                inits = {}
                init = methods.get('__init__')
                for stmt in (init.body if init else ()):
                    # `self.x = v` and `self.x: T = v` alike.
                    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                        target = stmt.targets[0]
                    elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                        target = stmt.target
                    else:
                        continue
                    if (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                            and target.value.id == 'self'):
                        inits.setdefault(target.attr, stmt.value)
                out[node.name] = (bases, methods, inits)
    return out


def mro(classes, cls):
    """The classes Python searches for a method, most derived first."""
    out = [cls]
    for b in classes.get(cls, ((), {}, {}))[0]:
        for c in mro(classes, b):
            if c not in out:
                out.append(c)
    return out


def _body(fn):
    """The statements of a method, its docstring dropped."""
    body = list(fn.body)
    if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    return body


def _literal_rust(value):
    """A Python literal as a PyVal expression, or None if it is not one."""
    if value is None:
        return 'PyVal::None'
    if isinstance(value, bool):
        return 'PyVal::Bool(%s)' % ('true' if value else 'false')
    if isinstance(value, int):
        return 'PyVal::Int(%d)' % value
    if isinstance(value, float):
        return 'PyVal::Float(%r_f64)' % value
    if isinstance(value, str):
        return 'PyVal::Str(%s.to_string())' % rust_str(value)
    if isinstance(value, (list, tuple)):
        inner = [_literal_rust(v) for v in value]
        if any(i is None for i in inner):
            return None
        kind = 'List' if isinstance(value, list) else 'Tuple'
        return 'PyVal::%s(vec![%s])' % (kind, ', '.join(inner))
    if isinstance(value, dict):
        items = [(_literal_rust(k), _literal_rust(v)) for k, v in value.items()]
        if any(a is None or b is None for a, b in items):
            return None
        return 'PyVal::Dict(vec![%s])' % ', '.join('(%s, %s)' % kv for kv in items)
    return None


# What `state` answers when the base class's `__init__` does not set the
# attribute to a literal: the implementation has to provide it.
NOT_PORTED = object()


def constructed(init, expr):
    """What `expr` in `init` evaluates to for an instance constructed with the
    constructor's defaults.

    `self.leak_type = type or 'unknown'` is `'unknown'` when `type` keeps its
    default of None.  A native object carries no base-class instance state, so
    this is what its default answers: what Python's base class answers when
    nothing passed it anything.  ValueError where the value depends on an
    argument with no default -- a leak sensor's name, a BMC's address -- or on
    anything that is not a literal: there is no such default instance, and
    the implementation has to provide the answer.
    """
    a = init.args
    defaults = {}
    positional = a.posonlyargs + a.args
    for arg, d in zip(positional[len(positional) - len(a.defaults):], a.defaults):
        defaults[arg.arg] = d
    for arg, d in zip(a.kwonlyargs, a.kw_defaults):
        if d is not None:
            defaults[arg.arg] = d

    def ev(n):
        if isinstance(n, ast.Name):
            if n.id not in defaults:
                raise ValueError('%s has no default' % n.id)
            return ev(defaults[n.id])
        if isinstance(n, ast.BoolOp):
            v = None
            for x in n.values:
                v = ev(x)
                if bool(v) == isinstance(n.op, ast.Or):
                    return v
            return v
        if isinstance(n, ast.IfExp):
            return ev(n.body) if ev(n.test) else ev(n.orelse)
        if (isinstance(n, ast.Compare) and len(n.ops) == 1
                and isinstance(n.ops[0], (ast.Is, ast.IsNot))):
            same = ev(n.left) is ev(n.comparators[0])
            return same if isinstance(n.ops[0], ast.Is) else not same
        return ast.literal_eval(n)

    return ev(expr)


def default_of(classes, cls, meth):
    """How `cls.meth` answers when nothing overrides it.

    (kind, rust, where, value): kind is missing | raise | notimpl | literal |
    state | body, `rust` the expression for the literal kinds, `where` the
    class that defines it, `value` what Python answers -- the message raised,
    the value returned, or NOT_PORTED -- for every kind but body and missing.
    """
    for c in mro(classes, cls):
        if c not in classes:
            continue
        methods = classes[c][1]
        if meth not in methods:
            continue
        body = _body(methods[meth])
        if len(body) == 1:
            s = body[0]
            if isinstance(s, ast.Raise) and s.exc is not None:
                exc = s.exc.func if isinstance(s.exc, ast.Call) else s.exc
                if isinstance(exc, ast.Name) and exc.id == 'NotImplementedError':
                    args = s.exc.args if isinstance(s.exc, ast.Call) else []
                    if args and isinstance(args[0], ast.Constant):
                        return ('raise', 'PyErr::not_implemented_msg(%s)'
                                % rust_str(args[0].value), c, str(args[0].value))
                    return ('raise', 'PyErr::not_implemented()', c, '')
            if isinstance(s, ast.Pass):
                return ('literal', 'PyVal::None', c, None)
            if isinstance(s, ast.Return):
                v = s.value
                if v is None:
                    return ('literal', 'PyVal::None', c, None)
                if isinstance(v, ast.Name) and v.id == 'NotImplementedError':
                    return ('notimpl', 'PyVal::NotImplementedClass', c, NotImplementedError)
                try:
                    value = ast.literal_eval(v)
                    lit = _literal_rust(value)
                except (ValueError, SyntaxError):
                    lit = None
                if lit is not None:
                    return ('literal', lit, c, value)
                if (isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name)
                        and v.value.id == 'self'):
                    # `return self._psu_list`: what the base class's own
                    # __init__ set it to, which is what Python answers when
                    # the vendor never filled it in.
                    for c2 in mro(classes, cls):
                        init = classes.get(c2, ((), {}, {}))[2].get(v.attr)
                        if init is None:
                            continue
                        try:
                            value = constructed(classes[c2][1]['__init__'], init)
                            lit = _literal_rust(value)
                        except (ValueError, SyntaxError):
                            lit = None
                        return ('state', lit, c, value) if lit else ('state', None, c, NOT_PORTED)
                    return ('state', None, c, NOT_PORTED)
        return ('body', None, c, None)
    return ('missing', None, None, None)


def module_of(cls):
    """The `bodies` module a base class's hand-written methods live in:
    `BMCBase` -> `bmc_base`, `TlvInfoDecoder` -> `tlv_info_decoder`."""
    return re.sub(r'(?<=.)([A-Z][a-z])', r'_\1', cls).lower()


# ── the method table ────────────────────────────────────────────────────────

class Method(object):
    def __init__(self, name):
        self.name = name
        self.params = None           # [(name, kind)]
        self.owners = []             # where it is reached from, for the docs

    def sig(self):
        return ''.join(', %s: %s' % (p, RUST_PARAM[k]) for p, k in self.params)

    def args(self):
        return ''.join(', %s' % p for p, _k in self.params)

    def sweep_args(self):
        """The arguments the sweep calls the method with."""
        return ', '.join(SWEEP_ARG[k] for _p, k in self.params)

    def sweep_echo(self):
        """`repr((name, args))`: what a handler echoing its call answers."""
        return 'ok %r' % ((self.name, [SWEEP_PY[k] for _p, k in self.params]),)

    def as_pyvals(self):
        """The parameters as a `&[PyVal]`, for `DynObject`'s handler."""
        conv = {'str': 'PyVal::Str(%s.to_string())', 'bool': 'PyVal::Bool(%s)',
                'int': 'PyVal::Int(%s)', 'float': 'PyVal::Float(%s)',
                'object': '%s.clone()'}
        if len(self.params) == 1 and self.params[0][1] == 'object':
            return 'std::slice::from_ref(&%s)' % self.params[0][0]
        return '&[%s]' % ', '.join(conv[k] % p for p, k in self.params)


def method_table(model, classes):
    """Every method the generated and hand-written native code calls."""
    enums = model.enum_names
    table = {}

    def add(owner, name, params):
        m = table.setdefault(name, Method(name))
        if m.params is None:
            m.params = list(params)
        elif [k for _p, k in m.params] != [k for _p, k in params]:
            raise ValueError('%s is called with (%s) and with (%s)'
                             % (name, m.params, params))
        if owner and owner not in m.owners:
            m.owners.append(owner)

    def arg_names(owner, name, n):
        """The base class's own parameter names, where it defines the method."""
        for c in mro(classes, owner):
            fn = classes.get(c, ((), {}, {}))[1].get(name)
            if fn is not None:
                names = [a.arg for a in fn.args.args[1:]]
                if len(names) >= n:
                    return names[:n]
        return ['arg%d' % i for i in range(n)]

    def reached_through(name):
        """The base class a method comes from when it is called on what
        another getter answered -- `chassis.get_watchdog().arm` -- which the
        stub does not type: the class that defines it and derives from no
        other class that does.  '' if that is not one class."""
        definers = [c for c, (_b, fns, _a) in classes.items() if name in fns]
        roots = [c for c in definers
                 if not any(d != c and d in mro(classes, c) for d in definers)]
        return roots[0] if len(roots) == 1 else ''

    for row in model.rows:
        for src in row.sources:
            for path, _single in src.via:
                owner, getter = path.split('.', 1)
                add(owner, getter, ())
            for path in (src.from_, src.mapping):
                if path:
                    owner, getter = path.split('.', 1)
                    add(owner, getter, ())
            for g in (src.when, src.parent):
                if g:
                    add('', g, ())
            if src.when_chassis:
                add('ChassisBase', src.when_chassis, ())
        for f in row.fields:
            if not f.from_:
                continue
            hops = f.getter.split('.')
            for h in hops[:-1]:
                add(f.owner, h, ())
            if f.with_name:
                # Whatever `get_name()` answered, passed on as it is: Python
                # does not make it a string first.
                add(f.owner, hops[-1], [(arg_names(f.owner, hops[-1], 1)[0], 'object')])
            else:
                add(f.owner, hops[-1], ())
            if f.with_name:
                add(f.owner, 'get_name', ())
    for m in model.methods:
        if not m.calls:
            continue
        owner, rest = m.calls.split('.', 1)
        hops = rest.split('.')
        for h in hops[:-1]:
            add(owner, h, ())
        if not m.row:
            passed = m.params
        else:
            # The locator is a key, consumed by the lookup.
            passed = m.params[1:]
        # `Calls(ints=...)`: the platform is handed what the Python caller
        # hands it -- chassisd 1 or 0, the base class's own graceful path
        # True or False -- so the parameter is a Python value, not a bool.
        kinds = ['object' if p in m.calls_ints else _param_kind(t, enums) for p, t in passed]
        if m.row and m.pass_key:
            # The base class takes the device's own name in its place, as
            # get_name() answered it: None too.
            kinds = ['object'] + kinds
        target = owner if len(hops) == 1 else reached_through(hops[-1])
        names = arg_names(target or owner, hops[-1], len(kinds))
        add(target, hops[-1], list(zip(names, kinds)))
    for owner, name, params in EXTRA:
        add(owner, name, [(p, t) for p, t in params])
    return [table[k] for k in sorted(table)]


# ── object.rs ───────────────────────────────────────────────────────────────

def _expected(cls, meth, kind, where, value):
    """What the sweep expects `cls.meth` to answer, as its `outcome()` spells
    an answer; None where it does not call it."""
    if kind == 'missing':
        return 'missing'
    if kind == 'raise':
        return 'raise NotImplementedError: %s' % value
    if kind == 'body':
        return SWEEP_BODIES.get((cls, meth))
    if value is NOT_PORTED:
        return ('raise RuntimeError: not ported to the native platform API: %s.%s answers'
                ' base-class state the implementation has to provide' % (where, meth))
    return 'ok %r' % (value,)


def build_object(model, base_dir):
    classes = read_classes(base_dir)
    methods = method_table(model, classes)
    bodies = {}
    body_arms = set()
    for m in methods:
        m.arms = []
        m.sweep = [_expected('Object', m.name, 'missing', None, None)]
        for cls in BASES:
            kind, rust, where, value = default_of(classes, cls, m.name)
            m.sweep.append(_expected(cls, m.name, kind, where, value))
            if kind == 'body':
                body_arms.add((cls, m.name))
            if kind == 'missing':
                continue
            if kind == 'state' and rust is None:
                rust = ('Err(PyErr::not_ported(%s))'
                        % rust_str('%s.%s answers base-class state the'
                                     ' implementation has to provide' % (where, m.name)))
            elif kind == 'body':
                fn = 'crate::bodies::%s::%s' % (module_of(where), m.name)
                bodies.setdefault(module_of(where), set()).add(m.name)
                rust = '%s(s%s)' % (fn, m.args())
            elif kind == 'raise':
                rust = 'Err(%s)' % rust
            else:
                rust = 'Ok(%s)' % rust
            m.arms.append((cls, kind, where, rust))
    stale = sorted(set(SWEEP_BODIES) - body_arms)
    if stale:
        raise ValueError('SWEEP_BODIES names no base-class body: %s' % stale)
    return {
        'methods': methods,
        'bases': BASES,
        'bodies': {k: sorted(v) for k, v in sorted(bodies.items())},
    }


# ── facade.rs ───────────────────────────────────────────────────────────────
#
# Each function below is the Rust spelling of the generate.py function its
# docstring names.  Read them side by side.

INT_CASTS = {'u32', 'i32', 'i64', 'u64'}
IND = ' ' * 8


def rust_str(s):
    """A Rust string literal for `s`.

    Not `json.dumps`: its `\\uXXXX`, `\\b` and `\\f` are not Rust escapes, so
    a control character in a docstring or a default would generate code that
    does not compile.  Everything else is written as it is -- a Rust source
    file is UTF-8.
    """
    out = ['"']
    for ch in s:
        if ch in '"\\':
            out.append('\\' + ch)
        elif ch in '\n\r\t\0':
            out.append({'\n': '\\n', '\r': '\\r', '\t': '\\t', '\0': '\\0'}[ch])
        elif ch < ' ' or ch == '\x7f':
            out.append('\\u{%x}' % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


_q = rust_str


def _pyval_literal(v):
    lit = _literal_rust(v)
    if lit is None:
        raise ValueError('no PyVal literal for %r' % (v,))
    return lit


def _base_call(f, dev='dev'):
    """`_py_base_call`: `_call(_get(dev, hop))` for each hop."""
    call = dev
    hops = f.getter.split('.')
    for i, hop in enumerate(hops):
        last = i == len(hops) - 1
        wrap = 'call_narrowed' if (last and f.narrowed) else 'call'
        ref = call if i == 0 else '&' + call
        call = '%s(get(%s, |o| o.%s()))?' % (wrap, ref, hop)
    return call


def _is_template(default):
    return isinstance(default, str) and '{' in default


def _fmt_call(got, default):
    """`_fmt_call`: `fmt_name`, or `fmt_name_with` for a template that also
    names fields the source fixes."""
    names = template_fields(default)
    if names:
        return 'fmt_name_with(&%s, %s, parent, i, fixed, &[%s])?' % (
            got, _q(default), ', '.join(_q(n) for n in names))
    return 'fmt_name(&%s, %s, parent, i)' % (got, _q(default))


def _absent(f):
    """`_absent`."""
    if f.unsupported_on != 'default':
        return 'PyVal::None'
    if _is_template(f.default):
        return _fmt_call('PyVal::None', f.default)
    return _pyval_literal(f.default)


def _gated(f, expr):
    """`_gated`."""
    if f.col_bit is None:
        return expr
    return 'if cols & (1 << %d) != 0 { %s } else { %s }' % (f.col_bit, expr, _absent(f))


def field_expr(f, enums):
    """`_py_field_expr`."""
    if f.is_parent:
        if f.name == 'parent_name':
            return 'PyVal::Str(parent.to_string())'
        return 'fixed_get(fixed, %s)?' % _q(f.name)
    if f.is_key:
        return 'fixed_get(fixed, "key")?'
    if f.is_parent_key:
        return 'fixed_get(fixed, "parent_key")?'
    if f.row_error:
        return 'PyVal::None'
    if f.with_name:
        expr = ('call_with_name(dev, |o| o.get_name(), |o, n| o.%s(n))?' % f.getter)
        return _gated(f, expr)
    call = '%s.clone()' % f.shared_var if f.shared_var else _base_call(f)
    if f.at is not None:
        call = 'at(&%s, %d)' % (call, f.at)
    if f.base in enums or f.base == 'str':
        call = 'text(%s)' % call
    if f.truthy:
        expr = 'truthy(%s)' % call
    elif f.sentinels or f.coerce_from:
        expr = 'scalar(%s, &[%s], &[%s])?' % (
            call, ', '.join(_pyval_literal(s) for s in f.sentinels),
            ', '.join(_q(c) for c in f.coerce_from))
    elif f.unsupported_on == 'default':
        if _is_template(f.default):
            expr = _fmt_call(call, f.default)
        else:
            expr = 'default(%s, %s)' % (call, _pyval_literal(f.default))
    else:
        expr = call
    return _gated(f, expr)


def shared_lets(row):
    """The `_shared<n>` lines `_row_<row>` opens with."""
    out = []
    for var, _pycall, mask in row.shared_calls:
        f = next(x for x in row.fields if x.shared_var == var)
        call = _base_call(f)
        if mask is not None:
            out.append('let %s = if cols & %d != 0 { %s } else { PyVal::None };'
                       % (var, mask, call))
        else:
            out.append('let %s = %s;' % (var, call))
    return out


def row_body(row):
    """`_row_body`: a row read column by column, for `per_row_errors`,
    absorbing and `ReadIf()`.

    Unguarded columns, and everything not read off the device, go in the
    struct literal in declaration order, as Python's constructor reads its
    keyword arguments.  Per row, the guarded ones are read in a closure
    standing for the `try`, and the first error ends it with `error`,
    `error_repr` and `error_column` set; absorbing, each one in a closure of
    its own, an error leaving that column absent.
    """
    def reads(f):
        return bool(f.from_)

    def among(f, fs):
        return any(f is x for x in fs)

    guard = row.guarded or row.absorbs or row.absorbable
    unguarded = [f for f in row.fields if reads(f) and (f.unguarded or not guard)]
    guarded = [f for f in row.fields if reads(f) and not f.unguarded and guard]
    in_try = {f.shared_var for f in guarded if f.shared_var}
    outside = {f.shared_var for f in unguarded if f.shared_var}
    by_name = {f.name: f for f in row.fields}

    def shared_call(var):
        for v, _pycall, mask in row.shared_calls:
            if v == var:
                f = next(x for x in row.fields if x.shared_var == var)
                call = _base_call(f)
                if mask is not None:
                    return 'if cols & %d != 0 { %s } else { PyVal::None }' % (mask, call)
                return call
        raise ValueError(var)

    def shared(names, indent):
        return ['%slet %s = %s;' % (indent, var, shared_call(var))
                for var, _c, _m in row.shared_calls if var in names]

    def value(f, absorbing=False):
        expr = f.native_expr
        if f.read_if and (f.read_if_absorbing or not absorbing):
            gate = by_name[f.read_if].rust_name
            cond = ('row.%s.truthy()' if f.read_if_truthy else '!row.%s.is_none()') % gate
            expr = 'if %s { %s } else { %s }' % (cond, expr, _absent(f))
        return expr

    def assign(f, indent):
        return '%srow.%s = %s;' % (indent, f.rust_name, value(f))

    def row_errors(indent):
        out = ['%s// try: ... except Exception as e -- the first getter that raises' % indent,
               '%s// ends the reading, and the row is still a row; `column` is the' % indent,
               '%s// one being read when it struck.' % indent,
               '%slet mut column = "";' % indent,
               '%slet r: PyResult<()> = (|| {' % indent]
        done = set()
        for f in guarded:
            if f.shared_var and f.shared_var not in done:
                done.add(f.shared_var)
                out.append('%s    column = %s;' % (indent, _q(f.name)))
                out += shared({f.shared_var}, indent + '    ')
            out.append('%s    column = %s;' % (indent, _q(f.name)))
            out.append(assign(f, indent + '    '))
        out.append('%s    Ok(())' % indent)
        out.append('%s})();' % indent)
        out.append('%sif let Err(e) = r {' % indent)
        for f in row.fields:
            if f.row_error == 'column':
                out.append('%s    row.%s = PyVal::Str(column.to_string());' % (indent, f.rust_name))
            elif f.row_error:
                out.append('%s    row.%s = PyVal::Str(e.%s());'
                           % (indent, f.rust_name, 'repr' if f.row_error == 'repr' else 'str'))
        out.append('%s}' % indent)
        return out

    def absorbed(indent):
        out = ['%s// Each getter in a `try` of its own: an exception is that column' % indent,
               '%s// absent, as psud\'s `try_get` makes it.' % indent]
        done = set()
        for f in guarded:
            if f.shared_var and f.shared_var not in done:
                done.add(f.shared_var)
                out.append('%slet %s = (|| -> PyResult<PyVal> { Ok(%s) })().unwrap_or(PyVal::None);'
                           % (indent, f.shared_var, shared_call(f.shared_var)))
            out.append('%srow.%s = match (|| -> PyResult<PyVal> { Ok(%s) })() {'
                       % (indent, f.rust_name, value(f, absorbing=True)))
            out.append('%s    Ok(v) => v,' % indent)
            out.append('%s    Err(_) => %s,' % (indent, _absent(f)))
            out.append('%s};' % indent)
        return out

    lines = []
    if row.skippable:
        lines.append('let mut cols = cols;')
        lines.append('if skipped(fixed, skip)? {')
        lines.append('    cols &= %d;' % row.unguarded_mask)
        lines.append('}')
    lines += shared(outside, '')
    later = [f for f in unguarded if f.read_if]
    lines.append('let %srow = Py%s {' % ('mut ' if (later or guarded) else '', row.name))
    for f in row.fields:
        if not reads(f) or (among(f, unguarded) and not f.read_if):
            lines.append('    %s: %s,' % (f.rust_name, f.native_expr))
        else:
            lines.append('    %s: %s,' % (f.rust_name, _absent(f)))
    lines.append('};')
    for f in later:
        lines.append(assign(f, ''))
    if guarded:
        if row.absorbs:
            lines += absorbed('')
        elif row.absorbable:
            lines.append('if absorb {')
            lines += absorbed('    ')
            lines.append('} else {')
            lines += row_errors('    ')
            lines.append('}')
        else:
            lines += row_errors('')
    lines.append('Ok(row)')
    return lines


def _when(src, owner):
    """`_when`: the predicate on `owner`, True where unanswered if the source
    says `when_unsupported="present"`."""
    got = 'call(get(%s, |o| o.%s()))?' % (owner, src.when)
    if src.when_unsupported == 'present':
        got = 'default(%s, PyVal::Bool(true))' % got
    return got


def _row_args(row):
    """`_row_args`."""
    return ((', cols' if row.projected else '')
            + (', skip' if getattr(row, 'skippable', False) else '')
            + (', absorb' if getattr(row, 'absorbable', False) else ''))


def _key_step(seg, var):
    """One step of a key, as the `format!` arguments that spell it."""
    return ('%s[{}]' % seg, var) if var else (seg, None)


def _key_expr(prev, seg, var):
    """The Rust expression for a key: `prev` and one more step."""
    text, arg = _key_step(seg, var)
    args = ([prev] if prev else []) + ([arg] if arg else [])
    fmt = ('{}/' if prev else '') + text
    return 'format!(%s%s)' % (_q(fmt), ''.join(', ' + a for a in args))


def _fixed(src, parent_expr, key=None, raw_expr=None):
    """`_fixed_literal`, as a slice of (name, value)."""
    parts = []
    if key is not None:
        parts.append('("key", PyVal::Str(%s))' % key[0])
        parts.append('("parent_key", %s)' % (
            'PyVal::Str(%s.clone())' % key[1] if key[1] else 'PyVal::None'))
    for name, value in src.sets:
        if value == '@parent':
            rendered = 'PyVal::Str((%s).to_string())' % parent_expr
        elif value == '@parent_raw':
            rendered = 'raw(&%s)' % raw_expr
        elif value == '@key':
            rendered = 'PyVal::Str(k.py_str())'
        elif value == '@value':
            rendered = 'if v.is_none() { PyVal::None } else { PyVal::Str(v.py_str()) }'
        else:
            rendered = _pyval_literal(value)
        parts.append('(%s, %s)' % (_q(name), rendered))
    return '&[%s]' % ', '.join(parts)


def walk_body(row):
    """`_snapshot_body`."""
    cols = _row_args(row)
    if row.singleton:
        return ('%sout.push(self.row_%s(&self.chassis, "chassis 1", 0, &[]%s)?);'
                % (IND, row.snake, cols))
    out = []
    for k, src in enumerate(row.sources):
        lines, depth = [], 0
        ind = lambda: IND + '    ' * depth  # noqa: E731
        parent_expr = '""'
        raw_expr = None
        counted = k + 1 < len(row.sources) and row.sources[k + 1].index_from_previous
        if src.when_chassis:
            lines.append('%sif call(get(&self.chassis, |o| o.%s()))?.truthy() {'
                         % (ind(), src.when_chassis))
            depth += 1
        owner = '&self.chassis'
        via = src.via_getters
        kprev = None
        for level, (getter, single) in enumerate(via):
            iv, ov = 'i%d' % level, 'o%d' % level
            if single:
                if src.when and level == len(via) - 1:
                    raise ValueError('%s: `when` on a single via has no loop to skip'
                                     % row.name)
                lines.append('%slet %s = call(get(%s, |o| o.%s()))?;' % (ind(), ov, owner, getter))
                lines.append('%slet %s: usize = 0;' % (ind(), iv))
                lines.append('%sif !%s.is_none() {' % (ind(), ov))
            else:
                lines.append('%sfor (%s, %s) in iter(call(get(%s, |o| o.%s()))?)?.into_iter().enumerate() {'
                             % (ind(), iv, ov, owner, getter))
            depth += 1
            if src.when and level == len(via) - 1:
                lines.append('%sif !%s.truthy() {' % (ind(), _when(src, '&' + ov)))
                lines.append('%s    continue;' % ind())
                lines.append('%s}' % ind())
            got = ('call(get(&%s, |o| o.%s()))?' % (ov, src.parent)) if src.parent else 'PyVal::None'
            if src.parent and (src.parent_missing
                               or any(v == '@parent_raw' for _f, v in src.sets)):
                rname = 'r%d' % level
                lines.append('%slet %s = %s;' % (ind(), rname, got))
                got = ('present(&%s, &[%s])' % (rname, ', '.join(_q(m) for m in src.parent_missing))
                       if src.parent_missing else rname)
                raw_expr = rname
            pname = 'p%d' % level
            lines.append('%slet %s: String = fmt_name(&%s, %s, %s, %s).py_str();'
                         % (ind(), pname, got, _q(src.parent_default[level]),
                            parent_expr if parent_expr == '""' else '&' + parent_expr, iv))
            if keyed(row):
                lines.append('%slet k%d: String = %s;' % (
                    ind(), level, _key_expr(kprev, key_segment(getter), None if single else iv)))
                kprev = 'k%d' % level
            parent_expr = pname
            owner = '&' + ov
        if not via:
            parent_expr = _q(src.parent_default[0])
            if '{i}' in src.parent_default[0]:
                # The source's own position, as a via level's would be.
                parent_expr = 'fmt_name(&PyVal::None, %s, "", i).py_str()' % _q(src.parent_default[0])
        pref = parent_expr if parent_expr.startswith('"') else '&' + parent_expr

        if src.mapping:
            lines.append('%sfor (i, (k, v)) in pairs(call(get(%s, |o| o.%s()))?).into_iter().enumerate() {'
                         % (ind(), owner, src.leaf_getter))
            lines.append('%s    out.push(self.row_%s(&PyVal::None, %s, i, %s%s)?);'
                         % (ind(), row.snake, pref, _fixed(src, pref, raw_expr=raw_expr), cols))
            lines.append('%s}' % ind())
        else:
            if src.provider:
                leaf = 'self.hatch.%s()?' % src.provider
            else:
                leaf = 'call(get(%s, |o| o.%s()))?' % (owner, src.leaf_getter)
            key = None
            if keyed(row):
                seg = src.provider or key_segment(src.leaf_getter)
                key = (_key_expr(kprev, seg, None if src.single else 'i'), kprev)
            index = 'i'
            if src.index_from_previous:
                # `{i}` counts on from the source before; the key stays this
                # list's own.
                lines.append('%slet n = out.len() - s%d;' % (ind(), k - 1))
                index = 'n + i'
            if src.single:
                lines.append('%sfor (i, dev) in one(%s).into_iter().enumerate() {' % (ind(), leaf))
            else:
                lines.append('%sfor (i, dev) in iter(%s)?.into_iter().enumerate() {' % (ind(), leaf))
            lines.append('%s    out.push(self.row_%s(&dev, %s, %s, %s%s)?);'
                         % (ind(), row.snake, pref, index, _fixed(src, pref, key, raw_expr), cols))
            lines.append('%s}' % ind())
        while depth:
            depth -= 1
            lines.append('%s}' % ind())

        desc = '%s// %s' % (IND, src.describes + (' via %s' % ' -> '.join(src.via_paths) if src.via else ''))
        block = '\n'.join(lines)
        if src.optional:
            body = '\n'.join('    ' + ln for ln in block.split('\n'))
            block = ('%s// try: ... except NotImplementedError: pass -- rows already\n'
                     '%s// collected stay collected.\n'
                     '%slet r: PyResult<()> = (|| {\n%s\n%s    Ok(())\n%s})();\n'
                     '%smatch r {\n'
                     '%s    Err(e) if e.exc == Exc::NotImplementedError => {}\n'
                     '%s    other => other?,\n'
                     '%s}'
                     % (IND, IND, IND, body, IND, IND, IND, IND, IND, IND))
        out.append(desc)
        if counted:
            out.append('%slet s%d = out.len();' % (IND, k))
        out.append(block)
    return '\n'.join(out)


def find_body(row):
    """`_find_body`: each source's walk again, one device per step of the key.

    Each source is a closure answering the device or None, so an optional
    source can swallow its `NotImplementedError` as the Python `try` does.
    """
    out = ['let path = parse_key(key)?;']
    for src in row.sources:
        shape = [(key_segment(g), not single) for g, single in src.via_getters]
        shape.append((src.provider or key_segment(src.leaf_getter), not src.single))
        want = '[%s]' % ', '.join('(%s, %s)' % (_q(n), 'true' if p else 'false') for n, p in shape)
        lines = ['// %s' % (src.describes + (' via %s' % ' -> '.join(src.via_paths) if src.via else '')),
                 'let found = (|| -> PyResult<Option<PyVal>> {',
                 '    if shape(&path) != %s {' % want,
                 '        return Ok(None);',
                 '    }']
        depth = 1
        ind = lambda: '    ' * depth  # noqa: E731
        if src.when_chassis:
            lines.append('%sif !call(get(&self.chassis, |o| o.%s()))?.truthy() {'
                         % (ind(), src.when_chassis))
            lines.append('%s    return Ok(None);' % ind())
            lines.append('%s}' % ind())
        owner = '&self.chassis'
        via = src.via_getters
        for level, (getter, single) in enumerate(via):
            ov = 'o%d' % level
            if single:
                lines.append('%slet %s = call(get(%s, |o| o.%s()))?;' % (ind(), ov, owner, getter))
                lines.append('%sif %s.is_none() {' % (ind(), ov))
                lines.append('%s    return Ok(None);' % ind())
                lines.append('%s}' % ind())
            else:
                lines.append('%slet Some(%s) = nth(call(get(%s, |o| o.%s()))?, path[%d].1)? else {'
                             % (ind(), ov, owner, getter, level))
                lines.append('%s    return Ok(None);' % ind())
                lines.append('%s};' % ind())
            if src.when and level == len(via) - 1:
                lines.append('%sif !%s.truthy() {' % (ind(), _when(src, '&' + ov)))
                lines.append('%s    return Ok(None);' % ind())
                lines.append('%s}' % ind())
            owner = '&' + ov
        if src.provider:
            leaf = 'self.hatch.%s()?' % src.provider
        else:
            leaf = 'call(get(%s, |o| o.%s()))?' % (owner, src.leaf_getter)
        if src.single:
            lines.append('%slet dev = %s;' % (ind(), leaf))
            lines.append('%sOk(if dev.is_none() { None } else { Some(dev) })' % ind())
        else:
            lines.append('%snth(%s, path[%d].1)' % (ind(), leaf, len(via)))
        lines.append('})();')
        lines.append('match found {')
        lines.append('    Ok(Some(dev)) => return Ok(dev),')
        lines.append('    Ok(None) => {}')
        if src.optional:
            lines.append('    Err(e) if e.exc == Exc::NotImplementedError => {}')
        lines.append('    Err(e) => return Err(e),')
        lines.append('}')
        out.extend(lines)
    out.append('Err(not_found(%s, key))' % _q(row.name))
    return out


def read_expr(f, enums, rows):
    """`_rust_field_expr`: how the bridge reads one column, over a PyVal."""
    ty = f.rust_ty
    key = _q(f.name)
    v = '&row.%s' % f.rust_name
    if ty.startswith('Vec<') and ty[4:-1] in rows:
        return ('row.%s.iter().map(%s).collect::<Result<Vec<_>, _>>()?'
                % (f.rust_name, 'read_' + _snake(ty[4:-1])))
    inner = ty[len('Option<'):-1] if ty.startswith('Option<') else ty
    if inner in enums:
        base = 'rd_text(%s, %s)?.and_then(|s| %s::from_str(&s))' % (key, v, inner)
        if f.optional:
            return base
        return ('%s.ok_or_else(|| PlatformError::Backend(%s.to_string()))?'
                % (base, _q('%s is missing or not a declared value' % f.name)))
    if inner == 'String':
        return ('rd_text(%s, %s)?' % (key, v)) if f.optional else \
            'rd_text(%s, %s)?.unwrap_or_default()' % (key, v)
    if inner == 'DeviceKey':
        return 'rd_text(%s, %s)?.map(DeviceKey::from)%s' % (
            key, v, '' if f.optional else '.unwrap_or_default()')
    if inner == 'bool':
        if f.optional:
            return 'rd_flag(%s)?' % v
        dflt = 'true' if f.default is True else 'false'
        return 'rd_flag(%s)?.unwrap_or(%s)' % (v, dflt)
    if inner == 'Number':
        return 'rd_number(%s)?' % v
    if inner not in INT_CASTS:
        # `parse_pyi._validate` refuses a `float` column; see `Number`.
        raise ValueError('%s: no reader for a %s column' % (f.name, inner))
    got = 'rd_int::<%s>(%s)?' % (inner, v)
    if f.optional:
        return got
    d = f.default
    lit = 'Default::default()' if d is None or isinstance(d, str) else repr(d)
    return '%s.unwrap_or(%s)' % (got, lit)


def py_field_type(f, rows):
    ty = f.rust_ty
    if ty.startswith('Vec<') and ty[4:-1] in rows:
        return 'Vec<Py%s>' % ty[4:-1]
    return 'PyVal'


def _arg(name, py_type, enums):
    """A trait method's parameter as the object method takes it."""
    t = strip_optional(py_type)[0]
    ident = 'r#' + name if name in ('type', 'fn') else name
    rt = rust_type(t, enums)
    if t in enums:
        return '%s.as_str()' % ident
    if rt == 'Number':
        return 'number_val(%s)' % ident
    if rt in ('u32', 'i32', 'u64', 'i64'):
        return 'i128::from(%s)' % ident
    return ident


def _built(m, model):
    """`_row_from_one_call`."""
    base = m.returns.strip()
    if base.startswith('Optional[') and base.endswith(']'):
        base = base[len('Optional['):-1].strip()
    row = model.row(base)
    if row is None or not row.fields:
        return None
    if not all(f.from_ == m.calls and f.at is not None for f in row.fields):
        return None
    return row


def action_body(m, model):
    """`_action_body`: the closure body, answering the PyVal (or Py row)."""
    enums = model.enum_names
    owner, rest = m.calls.split('.', 1)
    hops = rest.split('.')
    method, reach = hops[-1], hops[:-1]
    def passed(p, t):
        # `Calls(ints=...)`: the platform gets 1 or 0, as the Python caller
        # passes it.
        if p in m.calls_ints:
            return 'PyVal::Int(i128::from(%s))' % p
        return _arg(p, t, enums)

    if m.row:
        args = ', '.join((['name'] if m.pass_key else [])
                         + [passed(p, t) for p, t in m.params[1:]])
    else:
        args = ', '.join(passed(p, t) for p, t in m.params)
    lines = []
    if not m.row:
        target = 'self.chassis'
        for n, hop in enumerate(reach):
            lines.append('let t%d = call(get(&%s, |o| o.%s()))?;' % (n, target, hop))
            target = 't%d' % n
    else:
        row = model.row(m.row)
        key = m.params[0][0]
        lines.append('let dev = self.find_%s(%s.as_str())?;' % (row.snake, key))
        if m.pass_key:
            # The base class takes the device's own name; the key found it.
            lines.append('let name = text(call(get(&dev, |o| o.get_name()))?);')
        target = 'dev'
    lines.append('let answer = action(get(&%s, |o| o.%s(%s)), %s)?;'
                 % (target, method, args, _q(m.calls)))
    built = _built(m, model)
    if built is not None:
        lines.append('Ok(Py%s { %s })' % (built.name, ', '.join(
            '%s: at(&answer, %d)' % (f.rust_name, f.at) for f in built.fields)))
        return built, lines
    expr = 'answer' if m.calls_at is None else 'at(&answer, %d)' % m.calls_at
    if strip_optional(m.returns)[0] == 'bool':
        expr = 'truthy(%s)' % expr
    lines.append('Ok(%s)' % expr)
    return None, lines


def ret_conv(rust_ret, enums):
    """`_rust_ret_conv`, for what an action answers."""
    inner = rust_ret[len('Option<'):-1] if rust_ret.startswith('Option<') else rust_ret
    optional = rust_ret.startswith('Option<')
    if inner in enums:
        conv = 'ret_str(&v)?.and_then(|s| %s::from_str(&s))' % inner
        return 'Ok(%s)' % conv if optional else \
            '%s.ok_or_else(|| PlatformError::Backend(%s.to_string()))' % (
                conv, _q('%s is not a declared value' % inner))
    if inner in INT_CASTS:
        conv = 'ret_int::<%s>(&v)' % inner
        return conv if optional else \
            '%s?.ok_or_else(|| PlatformError::Backend(%s.to_string()))' % (
                conv, _q('missing value, or not a %s' % inner))
    if rust_ret == 'Option<bool>':
        return 'ret_bool(&v)'
    if rust_ret == 'Option<String>':
        return 'ret_str(&v)'
    if rust_ret == 'Option<f64>':
        return 'ret_num(&v)'
    raise ValueError('no native conversion for an action answering %s' % rust_ret)


def build_facade(model):
    enums = model.enum_names
    rows = {r.name for r in model.rows}
    for row in model.rows:
        row.native_lets = shared_lets(row) if (row.sources or row.singleton) else []
        for f in row.fields:
            f.native_expr = field_expr(f, enums) if (row.sources or row.singleton) else None
            f.native_read = read_expr(f, enums, rows)
            f.native_pytype = py_field_type(f, rows)
        row.native_body = (row_body(row) if getattr(row, 'sequential', False)
                           and (row.sources or row.singleton) else [])
        row.native_walk = walk_body(row) if (row.sources or row.singleton) else ''
        row.native_find = find_body(row) if getattr(row, 'addressed', False) else []
    for m in model.methods:
        if m.kind == 'action':
            built, lines = action_body(m, model)
            m.native_built = built.name if built else None
            m.native_body = lines
            m.native_conv = ('read_%s(&v)' % _snake(built.name)) if built else ret_conv(m.rust_ret, enums)
        if m.kind == 'snapshot':
            # The snapshot's own parameters, as its walk takes them: the
            # column bits, and the skip list as the set `frozenset(skip)` is.
            m.native_walk_args = ', '.join(
                (['cols.bits()'] if m.projected else []) + (['&skip'] if m.skippable else [])
                + (['absorb'] if m.absorbable else []))
        # An escape hatch takes the trait method's own parameters, unconverted.
        m.native_fwd = ', '.join('r#' + p if p in ('type', 'fn') else p for p, _t in m.params)
    return model
