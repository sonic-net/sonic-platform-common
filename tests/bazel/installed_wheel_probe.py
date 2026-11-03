"""Check the exact owner wheel against setup.py and a source-free installation."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from tools.bazel.tests.integration.installed_wheel_fixture import installed_wheels, write_wheel_receipt
from tools.bazel.tests.integration.wheel_contract import assert_wheel_contract, setup_contract

parser = argparse.ArgumentParser()
for name in ("wheel", "setup", "common-wheel", "config-wheel", "yang-wheel"):
    parser.add_argument("--" + name, type=Path, required=True)
INPUTS, REST = parser.parse_known_args()
DETAILS = {}


class InstalledWheelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wheels = [getattr(INPUTS, name).absolute() for name in
                      ("yang_wheel", "common_wheel", "config_wheel", "wheel")]
        cls.setup = INPUTS.setup.absolute()
        import sonic_py_common
        import portconfig
        import sonic_yang
        # Exclude each installed owner's source, including the buildimage root.
        roots = [cls.setup.parent,
                 Path(sonic_py_common.__file__).absolute().parent.parent,
                 Path(portconfig.__file__).absolute().parent,
                 Path(sonic_yang.__file__).absolute().parent]
        cls.installed = cls.enterClassContext(installed_wheels(cls.wheels, exclude_source_roots=roots))
        # setup.py checks the SONiC dependency distributions before declaring
        # metadata. Supply the actual installed owner-wheel metadata for capture.
        sys.path.insert(0, str(cls.installed.site))
        try:
            cls.contract = setup_contract(cls.setup)
        finally:
            sys.path.pop(0)

    def test_complete_owner_payload_and_metadata(self):
        assert_wheel_contract(INPUTS.wheel.absolute(), self.setup, self.contract, self.installed)
        DETAILS["declared_packages"] = len(set(self.contract["packages"]))
        DETAILS["dependency_boundary"] = "SONiC Python owner wheels installed; declared external/native test dependencies borrowed from runfiles"

    def test_installed_interfaces_without_owner_source(self):
        probe = r'''import importlib,importlib.metadata,json,pathlib,sys
site=pathlib.Path(sys.argv[1]).resolve()
for distribution in ('sonic-platform-common','sonic-py-common','sonic-config-engine','sonic-yang-mgmt'):
    metadata=importlib.metadata.distribution(distribution)
    assert metadata.version=='1.0', (distribution,metadata.version)
    assert pathlib.Path(metadata.locate_file('')).resolve()==site, distribution
modules=[
    'sonic_platform_base.chassis_base','sonic_platform_base.fan_base',
    'sonic_platform_base.psu_base','sonic_platform_base.module_base',
    'sonic_platform_base.sonic_eeprom.eeprom_tlvinfo',
    'sonic_platform_base.sonic_sfp.sfputilhelper',
    'sonic_platform_base.sonic_xcvr.api.public.cmis',
    'sonic_platform_base.sonic_xcvr.cdb.cdb',
    'sonic_platform_base.sonic_thermal_control.thermal_manager_base',
    'sonic_y_cable.y_cable_base','sonic_sfp.sfputilbase',
]
for name in modules:
    module=importlib.import_module(name)
    assert pathlib.Path(module.__file__).resolve().is_relative_to(site), (name,module.__file__)
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
assert CmisCodes is not None
from sonic_platform_base.sonic_sfp.sfputilhelper import SfpUtilHelper
assert isinstance(SfpUtilHelper().logical, list)
print(json.dumps({'installed_modules':modules}))
'''
        result = subprocess.run([str(self.installed.python), "-I", "-c", probe, str(self.installed.site)],
                                cwd=self.installed.root, env=self.installed.env,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        DETAILS.update(json.loads(result.stdout))


if __name__ == "__main__":
    result = unittest.main(argv=[__file__, *REST], exit=False).result
    write_wheel_receipt(getattr(InstalledWheelTest, "wheels", None), required=True,
                        status="passed" if result.wasSuccessful() else "failed",
                        details=dict(DETAILS, tests_run=result.testsRun))
    raise SystemExit(not result.wasSuccessful())
