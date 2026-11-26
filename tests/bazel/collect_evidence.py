"""Retain successful source and installation evidence bound to the exact wheel."""

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import zipfile

def main():
    root = Path(__file__).resolve().parents[2]
    out = root / "bazel-evidence"
    out.mkdir(exist_ok=True)
    wheel = root / "bazel-bin/sonic_platform_common-1.0-py3-none-any.whl"
    assert wheel.is_file(), wheel
    sha = hashlib.sha256(wheel.read_bytes()).hexdigest()
    shutil.copy2(wheel, out / wheel.name)
    for name, expected in (("unit_tests", "source-tests.json"), ("installed_wheel_test", "wheels.json")):
        logs = root / "tests/bazel/bazel-testlogs" / name
        assert (logs / "test.xml").is_file(), logs
        shutil.copytree(logs, out / name, dirs_exist_ok=True)
        outputs = logs / "test.outputs"
        if (outputs / expected).is_file():
            receipt = json.loads((outputs / expected).read_text())
        else:
            with zipfile.ZipFile(outputs / "outputs.zip") as archive:
                receipt = json.loads(archive.read(expected))
        assert receipt["status"] == "passed", (name, receipt)
        assert receipt["architecture"] == "x86_64", receipt
        assert receipt["python"].startswith("3.13."), receipt
        if name == "unit_tests":
            assert receipt["tests"] > receipt["skipped"] and receipt["failures"] == receipt["errors"] == 0, receipt
        else:
            tested = next(w for w in receipt["wheels"] if w["filename"] == wheel.name)
            assert tested["sha256"] == sha, (tested, sha)
        (out / expected).write_text(json.dumps(receipt, indent=2) + "\n")
    for relative, destination in (("MODULE.bazel.lock", "wheel-MODULE.bazel.lock"),
                                  ("tests/bazel/MODULE.bazel.lock", "tests-MODULE.bazel.lock")):
        source = root / relative
        assert source.is_file(), source
        shutil.copy2(source, out / destination)
    for directory, name in ((root, "wheel-module-graph.txt"), (root / "tests/bazel", "tests-module-graph.txt")):
        command = ["bazel"]
        if directory != root and os.environ.get("BAZEL_TEST_OUTPUT_BASE"):
            command.append("--output_base=" + os.environ["BAZEL_TEST_OUTPUT_BASE"])
        graph = subprocess.check_output(command + ["mod", "graph"], cwd=directory, text=True)
        (out / name).write_text(graph)
    revision = subprocess.check_output(["git", "-c", "safe.directory=" + str(root), "rev-parse", "HEAD"], cwd=root, text=True).strip()
    # Read raw headers: `git show %P` hides parents in a shallow CI checkout.
    commit = subprocess.check_output(["git", "-c", "safe.directory=" + str(root), "cat-file", "-p", "HEAD"], cwd=root, text=True)
    parents = [line.removeprefix("parent ") for line in commit.split("\n\n", 1)[0].splitlines()
               if line.startswith("parent ")]
    (out / "provenance.json").write_text(json.dumps({
        "tested_revision": revision,
        "tested_revision_parents": parents,
        "pull_request_head": os.environ.get("CI_HEAD_SHA", ""),
        "architecture": platform.machine(),
        "os_release": Path("/etc/os-release").read_text(),
        "wheel": wheel.name,
        "sha256": sha,
        "buildimage_test_dependency": "c743d7521e80fc1733e5cc0ffc24889b08f78444",
        "outputs": "Python wheel only; no Debian package generation",
        "scope": "Native AMD64/Trixie with Python 3.13; existing owner mocks retained",
    }, indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        output = Path(__file__).resolve().parents[2] / "bazel-evidence"
        output.mkdir(exist_ok=True)
        (output / "collection-failure.json").write_text(json.dumps({
            "status": "failed", "error": str(error),
        }, indent=2) + "\n")
        raise
