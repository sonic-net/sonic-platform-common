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
"""The scan that decides which platform API methods are in scope.

It reads trees from other repositories -- the base classes, the daemons,
healthd, the CLI and the conformance suite -- so it cannot run against the
real ones here.  Each test builds the smallest tree that shows one behaviour
and points the scan at it.

`scope_scan` is imported as a module and never `from`-imported: it has a
function called `test_methods`, and a bare name like that in this file would
be collected as a test.
"""

import ast
import os
import sys
import textwrap

import pytest

GENERATOR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'generator')
sys.path.insert(0, GENERATOR)

import scope_scan  # noqa: E402


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


BASES = '''
    class DeviceBase:
        def get_name(self):
            """Retrieves the name of the device

            Returns:
                string: The name of the device
            """
            raise NotImplementedError

        def get_presence(self):
            return False

        def _private(self):
            pass


    class FanBase(DeviceBase):
        def get_speed(self, unit, scale=1):
            pass

        def get_drawer(self):
            """
            Returns:
                A FanBase object
            """
            return None

        @classmethod
        def create(cls, *args, **kwargs):
            x = 1
            return x

        def get_unused(self):
            return 0
'''

SHIM_FAN = '''
    def get_speed(conn, index):
        return fan_api(conn, index, 'get_speed')


    def get_fan_name(conn, index):
        return fan_api(conn, index, 'get_name')
'''

SHIM_PSU = '''
    def get_psu_presence(conn, index):
        return psu_api(conn, index, 'get_presence')
'''


@pytest.fixture
def trees(tmp_path, monkeypatch):
    """A buildimage and a sonic-mgmt with one consumer of each kind."""
    build = tmp_path / 'build'
    mgmt = tmp_path / 'mgmt'
    abc = build / 'src/sonic-platform-common/sonic_platform_base'
    write(abc / 'device_base.py', BASES)
    write(abc / 'broken.py', 'def (:\n')
    write(abc / 'sonic_pcie/pcie_common.py', '''
        class PcieUtil:
            def get_pcie_check(self):
                return []
    ''')

    daemons = build / 'src/sonic-platform-daemons'
    write(daemons / 'sonic-psud/scripts/psud', '''\
        #!/usr/bin/env python3
        chassis.get_name()
        fan.get_speed(1)
        self.get_presence()
    ''')
    write(daemons / 'sonic-psud/scripts/README', 'fan.get_drawer()\n')
    write(daemons / 'sonic-psud/scripts/bad.py', 'def (:\n')
    write(daemons / 'sonic-psud/tests/test_psud.py', 'fan.get_unused()\n')

    write(build / 'src/system-health/health_checker.py', 'chassis.get_presence()\n')
    write(build / 'src/sonic-utilities/show/platform.py', 'fan.get_drawer()\n')
    (build / 'src/sonic-host-services').mkdir(parents=True)

    api = mgmt / 'tests/platform_tests/api'
    write(api / 'test_fan.py', 'fan.get_speed(conn, 0)\nfan.get_fan_name(conn, 0)\n')
    write(api / 'power_api_test_base.py', 'power_unit_api.get_psu_presence(conn, 0)\n')
    shims = mgmt / 'tests/common/helpers/platform_api'
    write(shims / '__init__.py', '')
    write(shims / 'fan.py', SHIM_FAN)
    write(shims / 'psu.py', SHIM_PSU)

    for name, value in {
        'BUILD': str(build),
        'MGMT': str(mgmt),
        'ABC_DIR': str(abc),
        'DAEMON_ROOT': str(daemons),
        'HEALTHD_ROOTS': [str(build / 'src/system-health')],
        'CLI_ROOTS': [str(build / 'src/sonic-utilities'),
                      str(build / 'src/sonic-host-services')],
        'API_TESTS': str(api),
        'SHIMS': str(shims),
        'INVENTORY': str(tmp_path / 'inventory.json'),
    }.items():
        monkeypatch.setattr(scope_scan, name, value)
    monkeypatch.setattr(scope_scan, '_sha', lambda path: 'abc1234')
    return tmp_path


def function(source):
    return ast.parse(textwrap.dedent(source)).body[0]


# -- the declaring side --------------------------------------------------------

@pytest.mark.parametrize('body, kind', [
    ('"""Only a docstring."""', 'literal'),
    ('pass', 'literal'),
    ('return', 'literal'),
    ('return 3', 'literal'),
    ('raise NotImplementedError', 'raise'),
    # Returned, not raised: a truthy class object, and not a usable literal.
    ('return NotImplementedError', 'returns-notimplementederror'),
    ('return self.speed', 'body'),
    ('self.x = 1', 'body'),
    ('x = 1\nreturn x', 'body'),
])
def test_a_default_body_is_classified_by_what_it_does(body, kind):
    source = 'def f(self):\n' + textwrap.indent(body, '    ') + '\n'
    assert scope_scan._default_kind(function(source)) == kind


@pytest.mark.parametrize('params, signature', [
    ('self', '(self)'),
    ('self, unit, scale=1', '(self, unit, scale=...)'),
    ('self, /, index', '(self, index)'),
    ('cls, *args, **kwargs', '(cls, *args, **kwargs)'),
    ('self, *, key, opt=None', '(self, *, key, opt=...)'),
    ('self, *names, key', '(self, *names, key)'),
])
def test_a_signature_marks_a_default_without_spelling_it(params, signature):
    assert scope_scan._signature(function('def f(%s): pass' % params)) == signature


def test_a_decorator_is_named_whatever_its_form():
    fn = function('''
        @plain
        @module.attribute
        @factory(1)
        @module.factory(2)
        @table[0]
        def f(self): pass
    ''')
    assert scope_scan._decorators(fn) == ['plain', 'attribute', 'factory', 'factory']


def test_the_base_classes_declare_what_the_facade_can_offer(trees):
    decls = scope_scan.abc_declarations()
    assert sorted(decls) == [
        ('DeviceBase', 'get_name'), ('DeviceBase', 'get_presence'),
        ('FanBase', 'create'), ('FanBase', 'get_drawer'), ('FanBase', 'get_speed'),
        ('FanBase', 'get_unused'), ('PcieUtil', 'get_pcie_check'),
    ]
    assert decls[('DeviceBase', 'get_name')]['default'] == 'raise'
    assert decls[('DeviceBase', 'get_name')]['returns_doc'] == 'string: The name of the device'
    assert decls[('FanBase', 'get_speed')]['signature'] == '(self, unit, scale=...)'
    assert decls[('FanBase', 'get_drawer')]['returns_object']
    assert decls[('FanBase', 'create')]['varargs']
    assert decls[('FanBase', 'create')]['classmethod']


# -- the consuming side ----------------------------------------------------------

def test_a_consumer_is_a_python_file_or_a_script(trees):
    scripts = trees / 'build/src/sonic-platform-daemons/sonic-psud/scripts'
    os.symlink(str(trees / 'nowhere'), str(scripts / 'dangling'))
    found = sorted(os.path.basename(p) for p in scope_scan.py_files([str(scripts.parent)]))
    # README has no #!, the dangling link cannot be read, and tests/ is not a
    # consumer.
    assert found == ['bad.py', 'psud']


def test_a_consumer_reaching_through_itself_is_not_a_platform_call(trees):
    names = {'get_name', 'get_speed', 'get_presence', 'get_drawer', 'get_unused'}
    used = scope_scan.attrs_used(
        [os.path.join(scope_scan.DAEMON_ROOT, 'sonic-psud/scripts')], names)
    assert dict(used) == {
        'get_name': {'src/sonic-platform-daemons/sonic-psud/scripts/psud'},
        'get_speed': {'src/sonic-platform-daemons/sonic-psud/scripts/psud'},
    }


def test_the_conformance_suite_is_read_through_its_shims(trees):
    names = {'get_name', 'get_speed', 'get_presence'}
    found = scope_scan.test_methods(names)
    assert dict(found) == {
        'get_speed': {'test_fan.py'},
        'get_name': {'test_fan.py'},
        'get_presence': {'power_api_test_base.py'},
    }


def test_a_suite_without_the_power_base_is_scanned_all_the_same(trees):
    os.remove(os.path.join(scope_scan.API_TESTS, 'power_api_test_base.py'))
    assert sorted(scope_scan.test_methods({'get_speed', 'get_presence'})) == ['get_speed']


def test_a_missing_tree_is_refused_by_name(trees, monkeypatch):
    gone = str(trees / 'no-such-mgmt/tests/platform_tests/api')
    monkeypatch.setattr(scope_scan, 'API_TESTS', gone)
    with pytest.raises(SystemExit) as caught:
        scope_scan.build_inventory()
    assert gone in str(caught.value)
    assert 'SONIC_MGMT' in str(caught.value)


def test_the_inventory_attributes_each_method_to_the_consumers_that_reach_it(trees):
    inv = scope_scan.build_inventory()
    assert inv['by_consumer'] == {
        'daemon': ['get_name', 'get_speed'],
        'healthd': ['get_presence'],
        'cli': ['get_drawer'],
        'test': ['get_name', 'get_presence', 'get_speed'],
    }
    assert inv['counts']['union'] == 4
    assert inv['counts']['unreached'] == 3
    assert inv['classes']['DeviceBase']['reached']['get_presence']['consumers'] == \
        ['healthd', 'test']
    assert sorted(inv['classes']['FanBase']['unreached']) == ['create', 'get_unused']
    assert list(inv['blocked']) == ['FanBase.get_drawer']
    assert set(inv['source'].values()) == {'abc1234'}


def test_the_sha_of_a_tree_that_is_not_a_repository_is_unknown(tmp_path):
    assert scope_scan._sha(str(tmp_path)) == 'unknown'


# -- main --------------------------------------------------------------------------

def run(monkeypatch, *args):
    monkeypatch.setattr(sys, 'argv', ['scope_scan.py'] + list(args))
    return scope_scan.main()


def test_an_inventory_is_written_and_then_checks_clean(trees, monkeypatch, capsys):
    assert run(monkeypatch) == 0
    out = capsys.readouterr().out
    assert 'union             4   <- the facade covers this' in out
    assert 'wrote %s' % scope_scan.INVENTORY in out

    assert run(monkeypatch, '--check') == 0
    assert 'inventory up to date' in capsys.readouterr().out


def test_a_new_commit_alone_does_not_make_the_inventory_stale(trees, monkeypatch, capsys):
    assert run(monkeypatch) == 0
    monkeypatch.setattr(scope_scan, '_sha', lambda path: 'fedcba9')
    assert run(monkeypatch, '--check') == 0


def test_a_consumer_that_starts_reaching_a_method_makes_it_stale(trees, monkeypatch, capsys):
    assert run(monkeypatch) == 0
    write(trees / 'build/src/sonic-utilities/show/fan.py', 'fan.get_unused()\n')
    assert run(monkeypatch, '--check') == 1
    assert 'is stale' in capsys.readouterr().err


@pytest.mark.parametrize('content', ['{not json', '[]'])
def test_an_unreadable_inventory_is_stale(trees, monkeypatch, capsys, content):
    with open(scope_scan.INVENTORY, 'w') as f:
        f.write(content)
    assert run(monkeypatch, '--check') == 1
    assert 'is stale' in capsys.readouterr().err


def test_a_missing_inventory_is_reported_as_missing(trees, monkeypatch, capsys):
    out = str(trees / 'elsewhere.json')
    assert run(monkeypatch, '--check', '-o', out) == 1
    assert 'missing %s' % out in capsys.readouterr().err


def test_the_default_trees_are_where_a_buildimage_checkout_keeps_them():
    root = os.path.dirname(GENERATOR)
    if 'SONIC_BUILDIMAGE' not in os.environ:
        assert scope_scan.BUILD == os.path.dirname(os.path.dirname(root))
    if 'SONIC_MGMT' not in os.environ:
        assert scope_scan.MGMT == os.path.join(os.path.dirname(scope_scan.BUILD), 'sonic-mgmt')
