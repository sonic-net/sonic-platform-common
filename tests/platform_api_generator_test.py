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
"""The generator and its omission check, run the way check.sh runs them.

`generate.py --check` is the gate that keeps the checked-in facade and the
three Rust files equal to what the stub says; `api_coverage.py --check` is the
one that notices an omission whose reason has stopped being true.  Both used
to run only as command lines, where nothing measured which of their branches a
change ever took.  They run in process here, so the failures they exist to
report are exercised too, not only the passing run.
"""

import json
import os
import sys

import pytest

GENERATOR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'generator')
sys.path.insert(0, GENERATOR)

pytest.importorskip('jinja2')

import api_coverage  # noqa: E402
import generate  # noqa: E402
import parse_pyi  # noqa: E402

from .platform_api_schema_test import GOOD_API, GOOD_ROW, HEADER  # noqa: E402


def run(monkeypatch, script, *args):
    monkeypatch.setattr(sys, 'argv', [script] + list(args))
    return {'generate.py': generate, 'api_coverage.py': api_coverage}[script].main()


def outputs_under(monkeypatch, root):
    """Point every generated file at the same place under `root`.

    The relative paths are kept, so each file keeps its suffix and the header
    rendered for it -- the text written is byte for byte the checked-in one.
    """
    moved = {tpl: str(root / os.path.relpath(path, generate.ROOT))
             for tpl, path in generate.OUTPUTS.items()}
    monkeypatch.setattr(generate, 'OUTPUTS', moved)
    monkeypatch.setattr(generate, 'ROOT', str(root))
    return moved


# -- generate.py -------------------------------------------------------------

def test_the_checked_in_outputs_are_what_the_generator_produces(monkeypatch, capsys):
    assert run(monkeypatch, 'generate.py', '--check') == 0
    assert 'generated files up to date' in capsys.readouterr().out


def test_a_fresh_tree_is_written_and_then_checks_clean(tmp_path, monkeypatch, capsys):
    moved = outputs_under(monkeypatch, tmp_path)

    assert run(monkeypatch, 'generate.py') == 0
    out = capsys.readouterr().out
    assert 'wrote platform_api/facade.py' in out
    for path in moved.values():
        assert os.path.exists(path)

    assert run(monkeypatch, 'generate.py', '--check') == 0


def test_an_edited_or_missing_output_is_stale(tmp_path, monkeypatch, capsys):
    moved = outputs_under(monkeypatch, tmp_path)
    assert run(monkeypatch, 'generate.py') == 0
    capsys.readouterr()

    with open(moved['facade.py.j2'], 'a') as f:
        f.write('# edited by hand\n')
    os.remove(moved['trait.rs.j2'])

    assert run(monkeypatch, 'generate.py', '--check') == 1
    err = capsys.readouterr().err
    assert 'stale, re-run generator/generate.py' in err
    assert 'platform_api/facade.py' in err
    assert 'crates/platform-api/src/generated.rs' in err


def test_an_arity_problem_stops_the_generator_before_it_writes(tmp_path, monkeypatch, capsys):
    moved = outputs_under(monkeypatch, tmp_path)
    monkeypatch.setattr(generate, 'check_arity',
                        lambda model: ['Foo.heat needs a unit'])

    assert run(monkeypatch, 'generate.py') == 1
    assert 'arity: Foo.heat needs a unit' in capsys.readouterr().err
    assert not any(os.path.exists(p) for p in moved.values())


@pytest.mark.parametrize('signature, required', [
    ('(self)', []),
    ('()', []),
    ('(self, unit)', ['unit']),
    # A classmethod's receiver is bound by Python, whatever it is called.
    ('(cls)', []),
    ('(cls, index)', ['index']),
    ('(self, scale=...)', []),
    ('(self, unit, scale=...)', ['unit']),
    # Nothing after *args is positional.
    ('(self, index, *args, key)', ['index']),
    ('(self, **kwargs)', []),
    # A keyword-only argument without a default still has to be passed.
    ('(self, *, key)', ['key']),
])
def test_the_arguments_a_caller_must_pass_are_read_from_the_signature(signature, required):
    assert generate._required_args(signature) == required


def model_of(tmp_path):
    path = tmp_path / 'facade.pyi'
    path.write_text(HEADER + GOOD_ROW + GOOD_API)
    return parse_pyi.parse(str(path))


def inventory(tmp_path, classes):
    path = tmp_path / 'inventory.json'
    path.write_text(json.dumps({'classes': classes}))
    return str(path)


def test_a_zero_argument_read_of_a_getter_that_needs_one_is_refused(tmp_path):
    inv = inventory(tmp_path, {
        'ThermalBase': {'reached': {'get_temperature': {'signature': '(self, unit)'}},
                        'unreached': []},
    })
    problems = generate.check_arity(model_of(tmp_path), inventory_path=inv)
    assert problems == [
        'Foo.heat reads ThermalBase.get_temperature(self, unit) with no arguments;'
        ' it requires unit -- declare WithName() or pass them']


def test_a_getter_that_takes_nothing_passes_the_arity_check(tmp_path):
    inv = inventory(tmp_path, {
        'ThermalBase': {'reached': {}, 'unreached': {'get_temperature': {
            'signature': '(self)'}}},
        # A class the scan did not reach in the old list shape, and one whose
        # buckets are not a mapping at all: both are skipped, not trusted.
        'FanBase': {'reached': {}, 'unreached': ['get_speed']},
        'PsuBase': ['get_voltage'],
    })
    assert generate.check_arity(model_of(tmp_path), inventory_path=inv) == []


@pytest.mark.parametrize('content', [None, '{not json'])
def test_no_readable_inventory_means_nothing_to_check_against(tmp_path, content):
    path = tmp_path / 'inventory.json'
    if content is not None:
        path.write_text(content)
    assert generate.check_arity(model_of(tmp_path), inventory_path=str(path)) == []


# -- api_coverage.py ---------------------------------------------------------

def test_every_omission_still_names_something_a_consumer_reaches(monkeypatch, capsys):
    assert run(monkeypatch, 'api_coverage.py', '--check') == 0
    out = capsys.readouterr().out
    assert 'in-scope declarations' in out
    assert 'omissions that no consumer reaches any more' not in out


def test_an_omission_nothing_reaches_any_more_fails_the_check(tmp_path, monkeypatch, capsys):
    with open(api_coverage.INVENTORY) as f:
        inv = json.load(f)
    cls, meth = sorted(api_coverage.omitted())[0]
    del inv['classes'][cls]['reached'][meth]
    path = tmp_path / 'inventory.json'
    path.write_text(json.dumps(inv))
    monkeypatch.setattr(api_coverage, 'INVENTORY', str(path))

    # Reported either way; only --check turns it into a failure.
    assert run(monkeypatch, 'api_coverage.py') == 0
    assert run(monkeypatch, 'api_coverage.py', '--check') == 1
    captured = capsys.readouterr()
    assert 'omissions that no consumer reaches any more (1)' in captured.out
    assert '%s.%s' % (cls, meth) in captured.out
    assert 'remove them from OMITTED' in captured.err


def test_a_stub_that_omits_nothing_says_so(tmp_path):
    path = tmp_path / 'facade.pyi'
    path.write_text(HEADER + GOOD_ROW + GOOD_API)
    assert api_coverage.omitted(str(path)) == {}
