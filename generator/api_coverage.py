"""How much of the consumed platform API the facade declares.

Named `api_coverage` rather than `coverage`: a module called `coverage.py` in
this directory shadows the coverage.py package for anything run with this as
its working directory, which quietly breaks `python3 -m coverage`.

Four numbers.  `covered` is what the stub reads or calls; `omitted` is what it
deliberately does not, each entry carrying its reason; `deferred` is what a
later phase declares, each entry naming the phase; `todo` is the rest.
Rolling the first two together is what makes a migration look unfinished
forever -- a count is the length of a list, and declaring it as well would
give a platform two ways to disagree with itself.  Keeping `deferred` apart
from `todo` is what lets the last one be zero.

`--check` fails on any `todo`: everything a consumer reaches is declared,
omitted with a reason, or deferred to a named phase.  It also fails when an
omission or a deferral no longer names anything a consumer reaches, or a
deferral names something the stub now declares, which is how a reason that
has stopped being true gets noticed.
"""

import argparse
import ast
import collections
import json
import os
import sys

from parse_pyi import FACADE_PYI, parse

HERE = os.path.dirname(os.path.abspath(__file__))
INVENTORY = os.path.join(HERE, 'inventory.json')


def listed(name, path=FACADE_PYI):
    """(class, method) -> reason, from one of the stub's declarations."""
    tree = ast.parse(open(path).read(), filename=path)
    for node in tree.body:
        target = getattr(node, 'target', None)
        if isinstance(node, ast.AnnAssign) and getattr(target, 'id', '') == name:
            return {tuple(p.split('.', 1)): reason
                    for p, reason in ast.literal_eval(node.value)}
    return {}


def omitted(path=FACADE_PYI):
    """(class, method) -> reason, from the stub's OMITTED declaration."""
    return listed('OMITTED', path)


def deferred(path=FACADE_PYI):
    """(class, method) -> phase, from the stub's DEFERRED declaration."""
    return listed('DEFERRED', path)


def declared(model):
    """(class, method) the facade reads or calls.

    Chained paths count every hop: a two-hop column reaches the intermediate
    getter as surely as the final one, and a vendor has to implement both.
    """
    out = set()
    for row in model.rows:
        for f in row.fields:
            if not f.from_:
                continue
            cls, rest = f.from_.split('.', 1)
            owner = cls
            for hop in rest.split('.'):
                out.add((owner, hop))
                owner = None   # only the first hop's class is named
            # Later hops belong to a class the stub does not spell; they are
            # covered by whatever declares them, and the scan matches on the
            # method name within the class it found.
        for src in row.sources:
            reached = list(src.via_paths)
            # `mapping=` reaches its base-class method exactly as `from_` does;
            # what differs is the shape of the answer, not whether it is called.
            reached += [p for p in (src.from_, src.mapping) if p]
            for path in reached:
                out.add(tuple(path.split('.', 1)))
            for path in src.reaches:
                out.add(tuple(path.split('.', 1)))
    names = set()
    for m in model.methods:
        for path in m.reaches:
            out.add(tuple(path.split('.', 1)))
        if m.calls:
            cls, rest = m.calls.split('.', 1)
            hops = rest.split('.')
            out.add((cls, hops[0]))
            # A later hop is reached on an object whose class the stub does
            # not spell -- `get_watchdog().arm()`.  The method is implemented
            # all the same, so it counts by name.
            names.update(hops[1:])
    return out, names


def report():
    inv = json.load(open(INVENTORY))
    model = parse()
    skip = omitted()
    later = deferred()
    have, chained = declared(model)

    # A method name the facade reads through a base class counts for every
    # subclass that redeclares it: a vendor implements one of them, and which
    # class the scan attributed the call site to is not something it can know.
    have_names = {m for _c, m in have} | chained

    rows = []
    for cls, entry in inv['classes'].items():
        for meth in entry['reached']:
            key = (cls, meth)
            if key in have:
                state = 'covered'
            elif key in skip:
                state = 'omitted'
            elif meth in have_names:
                state = 'covered'
            elif key in later:
                state = 'deferred'
            else:
                state = 'todo'
            rows.append((cls, meth, state))

    counts = collections.Counter(state for _c, _m, state in rows)
    total = len(rows)
    print('in-scope declarations : %d' % total)
    for state in ('covered', 'omitted', 'deferred', 'todo'):
        n = counts.get(state, 0)
        print('  %-8s %5d  %3.0f%%' % (state, n, 100.0 * n / total if total else 0))
    print()

    by_phase = collections.Counter(later[(c, m)] for c, m, st in rows if st == 'deferred')
    if by_phase:
        print('%-50s %5s' % ('deferred, by phase', ''))
        for phase, n in by_phase.most_common():
            print('  %-48s %5d' % (phase, n))
        print()

    todo = [(c, m) for c, m, st in rows if st == 'todo']
    if todo:
        by_cls = collections.Counter(c for c, _m in todo)
        print('%-24s %5s' % ('remaining, by class', 'todo'))
        for cls, n in by_cls.most_common():
            names = sorted(m for c, m in todo if c == cls)
            print('%-24s %5d  %s' % (cls, n, ', '.join(names)[:70]))

    def reached(k):
        return k[1] in inv['classes'].get(k[0], {}).get('reached', {})

    problems = []
    for name, entries in (('OMITTED', skip), ('DEFERRED', later)):
        stale = sorted(k for k in entries if not reached(k))
        if stale:
            print()
            print('%s entries that no consumer reaches any more (%d):' % (name, len(stale)))
            for cls, meth in stale:
                print('   %s.%s  -- %s' % (cls, meth, entries[(cls, meth)]))
            problems.append('remove them from %s, or say why they are still listed' % name)
    done = sorted(k for k in later if k in have or k[1] in have_names)
    if done:
        print()
        print('DEFERRED entries the stub now declares (%d):' % len(done))
        for cls, meth in done:
            print('   %s.%s' % (cls, meth))
        problems.append('remove them from DEFERRED')
    both = sorted(set(skip) & set(later))
    if both:
        print()
        print('in both OMITTED and DEFERRED (%d): %s'
              % (len(both), ', '.join('%s.%s' % k for k in both)))
        problems.append('keep each in one of OMITTED and DEFERRED')
    if todo:
        problems.append('declare them, or add them to OMITTED or DEFERRED with the reason')
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true',
                    help='fail on a todo, or on an entry that has stopped being true')
    args = ap.parse_args()
    problems = report()
    if args.check and problems:
        for p in problems:
            print('\n' + p, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
