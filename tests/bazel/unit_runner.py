"""Run the complete owner suite with its original mocks and declared inputs."""

import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

import pytest


def main():
    source = Path(sys.argv[1]).absolute().parent
    output = Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    # The original tests create files next to fixtures. Copy only declared owner
    # inputs so neither a writable checkout nor generated host files are needed.
    with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as temporary:
        work = Path(temporary)
        for child in source.iterdir():
            if child.name.startswith("sonic_") or child.name == "tests":
                shutil.copytree(child, work / child.name)
        for name in ("pytest.ini", "setup.cfg", "test_credo_aec_800g.py"):
            shutil.copyfile(source / name, work / name)
        os.chdir(work)
        sys.path.insert(0, str(work))
        # Port-mapping tests exercise config-engine's file fallback. Give its
        # real Common connector a private, deliberately unavailable socket so
        # it cannot use an agent's /var/run/redis configuration or live data.
        from swsscommon import swsscommon
        database_config = work / "database_config.json"
        database_config.write_text(json.dumps({
            "INSTANCES": {"redis": {"hostname": "127.0.0.1", "port": 0,
                                    "unix_socket_path": str(work / "absent-redis.sock")}},
            "DATABASES": {"CONFIG_DB": {"id": 4, "separator": "|", "instance": "redis"}},
            "VERSION": "1.0",
        }))
        swsscommon.SonicDBConfig.load_sonic_db_config(str(database_config))
        report = output / "pytest.xml"
        status = pytest.main([
            "-o", "addopts=", "-v", "--cov=sonic_platform_base",
            "--cov-report=xml:" + str(output / "coverage.xml"),
            "--cov-report=term", "--junitxml=" + str(report),
            "tests", "test_credo_aec_800g.py",
        ])
        summary = {}
        if report.exists():
            root = ET.parse(report).getroot()
            cases = root.findall(".//testcase")
            summary = {
                "tests": len(cases),
                "failures": len(root.findall(".//failure")),
                "errors": len(root.findall(".//error")),
                "skipped": len(root.findall(".//skipped")),
                "inventory": [case.attrib for case in cases],
            }
        (output / "source-tests.json").write_text(json.dumps({
            "status": "passed" if status == 0 else "failed",
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "source": str(source),
            "selection": ["tests", "test_credo_aec_800g.py"],
            **summary,
        }, indent=2) + "\n")
        if not summary.get("tests"):
            raise RuntimeError("The original suite produced no test inventory")
        return int(status)


if __name__ == "__main__":
    raise SystemExit(main())
