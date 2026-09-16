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
"""Which platform API methods the four consumer groups actually reach.

The facade declared in ``platform_api/facade.pyi`` covers the union of what
the PMON daemons, healthd, the CLI and the platform API conformance suite
call -- not the whole abstract base class.  This scan computes that union and
writes it to ``generator/inventory.json``, which is checked in so that a
change in the surface shows up as a reviewable diff rather than as a number
someone re-derived by hand.

Run ``--check`` in CI: it re-scans and fails if the checked-in inventory has
drifted from the trees.

The consumer scan looks for ABC method names appearing as *attributes*, not as
call sites.  Roughly forty methods are only ever reached through a bound
reference handed to a daemon's ``try_get()`` helper, and a call-site scan
misses every one of them.  The conformance suite is scanned exactly instead,
by reading the method name each of its client shims puts in the URL.
"""

import argparse
import ast
import collections
import glob
import json
import os
import re
import subprocess
import sys
import warnings

BUILD = os.environ.get('SONIC_BUILDIMAGE', '/work/code/sonic-buildimage-spc6')
MGMT = os.environ.get('SONIC_MGMT', '/work/code/sonic-mgmt')

ABC_DIR = os.path.join(BUILD, 'src/sonic-platform-common/sonic_platform_base')
DAEMON_ROOT = os.path.join(BUILD, 'src/sonic-platform-daemons')

# The ten daemons in scope.  ledd is excluded: it reaches hardware through the
# older sonic_led plugin interface, which the facade does not model.
DAEMONS = [
    'sonic-thermalctld/scripts', 'sonic-psud/scripts', 'sonic-chassisd/scripts',
    'sonic-xcvrd/xcvrd', 'sonic-ycabled/ycable', 'sonic-bmcctld/scripts',
    'sonic-sensormond/scripts', 'sonic-stormond/scripts',
    'sonic-syseepromd/scripts', 'sonic-pcied/scripts',
]

# healthd is its own consumer, not part of the CLI.  It runs on the host rather
# than in pmon and reaches the platform API through exactly one method, so
# folding it into the CLI roots would hide that fact.
HEALTHD_ROOTS = [os.path.join(BUILD, 'src/system-health')]

CLI_ROOTS = [
    os.path.join(BUILD, 'src/sonic-utilities'),
    os.path.join(BUILD, 'src/sonic-host-services'),
]

API_TESTS = os.path.join(MGMT, 'tests/platform_tests/api')
SHIMS = os.path.join(MGMT, 'tests/common/helpers/platform_api')

INVENTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.json')

# The scanned repos contain files with invalid escape sequences; ast.parse
# reports each as a SyntaxWarning against a line number in a file this script
# never names, which buries the actual output.
warnings.filterwarnings('ignore', category=SyntaxWarning)

SKIP_DIRS = {'build', 'tests', 'test', '__pycache__', 'proto_out', '.git', 'target'}

CONSUMERS = ('daemon', 'healthd', 'cli', 'test')


# --------------------------------------------------------------------------
# The declaring side: what the base classes offer
# --------------------------------------------------------------------------

def _default_kind(fn):
    """What the ABC's own body does, which is what the facade falls back to.

    ``raise``   -- raise NotImplementedError; the facade yields None
    ``literal`` -- pass, or return a constant; the facade can inline it
    ``body``    -- anything longer; a real implementation has to be written
    """
    body = [n for n in fn.body if not (isinstance(n, ast.Expr)
                                       and isinstance(n.value, ast.Constant)
                                       and isinstance(n.value.value, str))]
    if not body:
        return 'literal'
    if len(body) == 1:
        only = body[0]
        if isinstance(only, ast.Raise):
            return 'raise'
        if isinstance(only, ast.Pass):
            return 'literal'
        if isinstance(only, ast.Return):
            if only.value is None or isinstance(only.value, ast.Constant):
                return 'literal'
            # `return NotImplementedError` (no raise) returns a truthy class
            # object.  Five declarations do this; they are not `raise` and they
            # are not a usable literal either.
            if isinstance(only.value, ast.Name) and only.value.id == 'NotImplementedError':
                return 'returns-notimplementederror'
    return 'body'


def _signature(fn):
    a = fn.args
    parts = [x.arg for x in a.posonlyargs + a.args]
    if a.vararg:
        parts.append('*' + a.vararg.arg)
    if a.kwonlyargs:
        if not a.vararg:
            parts.append('*')
        parts.extend(x.arg for x in a.kwonlyargs)
    if a.kwarg:
        parts.append('**' + a.kwarg.arg)
    return '(%s)' % ', '.join(parts)


def _decorators(fn):
    out = []
    for d in fn.decorator_list:
        if isinstance(d, ast.Name):
            out.append(d.id)
        elif isinstance(d, ast.Attribute):
            out.append(d.attr)
        elif isinstance(d, ast.Call):
            out.append(getattr(d.func, 'id', getattr(d.func, 'attr', '?')))
    return out


def abc_declarations():
    """(class, method) -> facts about the declaration."""
    decls = {}
    class_names = set()
    trees = {}
    for fn in sorted(glob.glob(os.path.join(ABC_DIR, '*.py'))):
        try:
            trees[fn] = ast.parse(open(fn, errors='ignore').read())
        except SyntaxError:
            continue
        for node in ast.walk(trees[fn]):
            if isinstance(node, ast.ClassDef):
                class_names.add(node.name)

    for fn, tree in trees.items():
        module = os.path.basename(fn)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, ast.FunctionDef) or item.name.startswith('_'):
                    continue
                doc = ast.get_docstring(item) or ''
                returns = ''
                m = re.search(r'Returns?:\s*\n(.*?)(?:\n\s*\n|$)', doc, re.S)
                if m:
                    returns = ' '.join(m.group(1).split())
                decs = _decorators(item)
                a = item.args
                decls[(node.name, item.name)] = {
                    'module': module,
                    'line': item.lineno,
                    'signature': _signature(item),
                    'default': _default_kind(item),
                    'decorators': decs,
                    # The three shapes that cannot be generated as written.
                    'returns_object': any(c in returns for c in class_names),
                    'varargs': bool(a.vararg or a.kwarg),
                    'classmethod': 'classmethod' in decs or 'staticmethod' in decs,
                    'returns_doc': returns[:160],
                }
    return decls


# --------------------------------------------------------------------------
# The consuming side
# --------------------------------------------------------------------------

def py_files(roots):
    for root in roots:
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in files:
                p = os.path.join(dirpath, fn)
                if fn.endswith('.py'):
                    yield p
                elif '.' not in fn:
                    # A daemon's entry point is an extensionless script.
                    try:
                        if open(p, errors='ignore').read(2) == '#!':
                            yield p
                    except OSError:
                        pass


def attrs_used(roots, names):
    """Method names appearing as an attribute anywhere under roots.

    ``self.<name>`` is skipped.  A consumer never reaches the platform API
    through itself -- it goes through a chassis, a device object, or a stored
    reference such as ``self.chassis.get_all_thermals()``, whose attribute
    node has ``self.chassis`` rather than ``self`` as its value.  Without this
    a checker's own ``self.reset()`` is scored as ``SfpBase.reset``.
    """
    found = collections.defaultdict(set)
    for p in py_files(roots):
        try:
            tree = ast.parse(open(p, errors='ignore').read())
        except (SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Attribute) and node.attr in names):
                continue
            if isinstance(node.value, ast.Name) and node.value.id == 'self':
                continue
            found[node.attr].add(os.path.relpath(p, BUILD))
    return found


def test_methods(names):
    """Method names the conformance suite can issue, through its client shims.

    Exact rather than heuristic: each shim function names the API method it
    puts in the URL, and the server getattr()s that name off the object it
    walked to.
    """
    shim = {}
    for f in glob.glob(os.path.join(SHIMS, '*.py')):
        fam = os.path.basename(f)[:-3]
        if fam == '__init__':
            continue
        src = open(f).read()
        table = {}
        for m in re.finditer(
                r"def ([a-z_0-9]+)\(conn[^)]*\):\s*\n\s*return \w+_api\("
                r"[^)]*?'([a-z_0-9]+)'", src):
            table[m.group(1)] = m.group(2)
        shim[fam] = table

    found = collections.defaultdict(set)
    files = sorted(glob.glob(os.path.join(API_TESTS, 'test_*.py')))
    files.append(os.path.join(API_TESTS, 'power_api_test_base.py'))
    for p in files:
        if not os.path.exists(p):
            continue
        src = open(p).read()
        for fam, table in shim.items():
            for fn in re.findall(r"\b%s\.([a-z_0-9]+)\(" % fam, src):
                api = table.get(fn, fn)
                if api in names:
                    found[api].add(os.path.basename(p))
        # power_api_test_base binds its family at class level.
        for fn in re.findall(r"power_unit_api\.([a-z_0-9]+)\(", src):
            api = shim.get('psu', {}).get(fn, fn)
            if api in names:
                found[api].add(os.path.basename(p))
    return found


# --------------------------------------------------------------------------

def _sha(path):
    try:
        return subprocess.check_output(
            ['git', '-C', path, 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return 'unknown'


def _require_trees():
    """Fail loudly when the consumer trees are not here.

    They live in other repositories, so this scan only runs in a checkout that
    has them.  Without this the walk finds nothing, every method scores as
    unreached, and the result looks like a surface that shrank rather than
    like a scan that could not see.
    """
    missing = [p for p in [ABC_DIR, DAEMON_ROOT, API_TESTS] + CLI_ROOTS + HEALTHD_ROOTS
               if not os.path.isdir(p)]
    if missing:
        raise SystemExit(
            'cannot scan: not present\n  %s\n'
            'Set SONIC_BUILDIMAGE and SONIC_MGMT to a checkout that has them.'
            % '\n  '.join(missing))


def build_inventory():
    _require_trees()
    decls = abc_declarations()
    names = {m for (_c, m) in decls}

    reached = {
        'daemon': attrs_used([os.path.join(DAEMON_ROOT, d) for d in DAEMONS], names),
        'healthd': attrs_used(HEALTHD_ROOTS, names),
        'cli': attrs_used(CLI_ROOTS, names),
        'test': test_methods(names),
    }
    union = set().union(*(set(r) for r in reached.values()))

    classes = collections.defaultdict(lambda: {'reached': {}, 'unreached': []})
    for (cls, method), facts in sorted(decls.items()):
        if method in union:
            entry = dict(facts)
            entry['consumers'] = sorted(c for c in CONSUMERS if method in reached[c])
            # Keep the hit files.  The consumer scan is name-level -- it cannot
            # tell ThermalBase.get_temperature from PsuBase.get_temperature --
            # so every attribution here is reviewable rather than trusted.
            entry['sites'] = {
                c: sorted(reached[c][method])[:6]
                for c in CONSUMERS if method in reached[c]
            }
            classes[cls]['reached'][method] = entry
        else:
            classes[cls]['unreached'].append(method)

    by_consumer = {c: sorted(reached[c]) for c in CONSUMERS}
    blocked = {
        '%s.%s' % k: v for k, v in sorted(decls.items())
        if k[1] in union and (v['returns_object'] or v['varargs'])
    }

    return {
        'note': 'Generated by generator/scope_scan.py. Do not edit by hand.',
        'source': {
            'sonic-platform-common': _sha(os.path.join(BUILD, 'src/sonic-platform-common')),
            'sonic-platform-daemons': _sha(os.path.join(BUILD, 'src/sonic-platform-daemons')),
            'sonic-utilities': _sha(os.path.join(BUILD, 'src/sonic-utilities')),
            'sonic-mgmt': _sha(MGMT),
        },
        'counts': {
            'abc_methods': len(names),
            'abc_declarations': len(decls),
            'abc_classes': len({c for (c, _m) in decls}),
            'union': len(union),
            'unreached': len(names - union),
            'declarations_in_scope': sum(len(v['reached']) for v in classes.values()),
            'blocked_declarations': len(blocked),
            **{'reached_by_' + c: len(reached[c]) for c in CONSUMERS},
        },
        'by_consumer': by_consumer,
        'blocked': blocked,
        'classes': {k: v for k, v in sorted(classes.items())},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true',
                    help='fail if the checked-in inventory has drifted')
    ap.add_argument('-o', '--out', default=INVENTORY)
    args = ap.parse_args()

    inv = build_inventory()
    text = json.dumps(inv, indent=2, sort_keys=False) + '\n'

    if args.check:
        if not os.path.exists(args.out):
            print('missing %s -- run generator/scope_scan.py' % args.out, file=sys.stderr)
            return 1
        if open(args.out).read() != text:
            print('%s is stale -- re-run generator/scope_scan.py' % args.out, file=sys.stderr)
            return 1
        print('inventory up to date')
        return 0

    with open(args.out, 'w') as f:
        f.write(text)

    c = inv['counts']
    print('ABC: %d methods / %d declarations across %d classes'
          % (c['abc_methods'], c['abc_declarations'], c['abc_classes']))
    print()
    print('%-10s %8s' % ('consumer', 'methods'))
    for name in CONSUMERS:
        print('%-10s %8d' % (name, c['reached_by_' + name]))
    print('%-10s %8d   <- the facade covers this' % ('union', c['union']))
    print('%-10s %8d' % ('unreached', c['unreached']))
    print()
    print('declarations in scope : %d' % c['declarations_in_scope'])
    print('of which blocked      : %d  (return an object, or are variadic)'
          % c['blocked_declarations'])
    print()
    print('wrote %s' % args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
