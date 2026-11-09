"""Verify a real source edit reaches the wheel, then restore its exact bytes."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile


SOURCE = "sonic_y_cable/y_cable_base.py"
TARGET = "//:sonic_platform_common_wheel"
WHEEL = "sonic_platform_common-1.0-py3-none-any.whl"
ORIGINAL = b'    SWITCH_COUNT_MANUAL = "manual"'
EDITED = b'    SWITCH_COUNT_MANUAL = "manual-bazel-incremental"'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def payload(wheel):
    with zipfile.ZipFile(wheel) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), "Duplicate wheel member names")
        return {item.filename: {"sha256": digest(archive.read(item)), "mode": item.external_attr}
                for item in archive.infolist()}


def payload_delta(before, after):
    require(before.keys() == after.keys(), "Source edit changed the installed file list")
    require(all(before[name]["mode"] == after[name]["mode"] for name in before),
            "Source edit changed installed file modes")
    differences = sorted(name for name in before if before[name] != after[name])
    require(differences == sorted([SOURCE, "sonic_platform_common-1.0.dist-info/RECORD"]),
            "Source edit changed unrelated wheel payloads: " + repr(differences))
    return differences


def installed_probe(wheel, expected):
    # Only the extracted wheel supplies the owner package. -I/-S exclude the
    # checkout, user environment and site packages from the import path.
    with tempfile.TemporaryDirectory(prefix="platform-wheel-") as temporary:
        site = Path(temporary) / "site"
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(site)
        probe = """import json,pathlib,sys
site=pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0,str(site))
from sonic_y_cable import y_cable_base
assert pathlib.Path(y_cable_base.__file__).resolve().is_relative_to(site)
assert y_cable_base.YCableBase.SWITCH_COUNT_MANUAL==sys.argv[2], y_cable_base.YCableBase.SWITCH_COUNT_MANUAL
print(json.dumps({'module':'sonic_y_cable.y_cable_base','switch_count_manual':y_cable_base.YCableBase.SWITCH_COUNT_MANUAL}))
"""
        result = subprocess.run([sys.executable, "-I", "-S", "-c", probe, str(site), expected],
                                cwd=temporary, capture_output=True, text=True, timeout=30)
        require(result.returncode == 0, "Installed wheel probe failed:\n" + result.stdout + result.stderr)
        return json.loads(result.stdout)


def execution_records(path):
    decoder = json.JSONDecoder()
    data = path.read_text()
    records = []
    while data.strip():
        record, end = decoder.raw_decode(data.lstrip())
        records.append(record)
        data = data.lstrip()[end:]
    return records


def action_metrics(path):
    """Account for internal actions as well as spawned or cache-served work."""
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    summaries = [event["buildMetrics"]["actionSummary"] for event in events
                 if "actionSummary" in event.get("buildMetrics", {})]
    require(len(summaries) == 1, "Expected one complete BEP action summary")
    summary = summaries[0]

    def count(value):
        # Protobuf JSON writes int64 as strings and omits zero-valued fields.
        require(type(value) in (str, int) and str(value).isascii() and str(value).isdigit(),
                "Invalid BEP action count: " + repr(value))
        return int(value)

    by_mnemonic = {}
    for item in summary.get("actionData", []):
        name = item["mnemonic"]
        require(isinstance(name, str) and name and name not in by_mnemonic,
                "Missing or duplicate BEP action mnemonic")
        by_mnemonic[name] = count(item.get("actionsExecuted", 0))
    total = count(summary.get("actionsExecuted", 0))
    require(sum(by_mnemonic.values()) == total, "Incomplete BEP action mnemonic accounting")
    runners = summary["runnerCount"]
    require(isinstance(runners, list) and runners, "Missing BEP runner counts")
    for runner in runners:
        require(isinstance(runner.get("name"), str) and runner["name"], "Missing BEP runner name")
        count(runner.get("count", 0))
    # These are Bazel's metrics, not a count of uncached processes. In particular,
    # a disk-cache-served PyWheel appears here but does not execute a wheel process.
    return {"total": total, "by_mnemonic": by_mnemonic, "runners": runners,
            "action_cache": summary.get("actionCacheStatistics", {})}


def require_noop(result):
    require(result["uncached_spawns"] == 0, "No-op executed uncached processes")
    actions = result["actions"]
    unexpected = {name: count for name, count in actions["by_mnemonic"].items()
                  if count and name != "BazelWorkspaceStatusAction"}
    require(not unexpected and actions["total"] <= 1,
            "No-op ran actions beyond workspace-status bookkeeping: " + repr(unexpected))


def build(root, output, bazel, phase, expected):
    directory = output / phase
    directory.mkdir(parents=True, exist_ok=True)
    command = [bazel, "build", TARGET,
               "--experimental_record_metrics_for_all_mnemonics",
               "--build_event_json_file=" + str(directory / "build-events.jsonl"),
               "--execution_log_json_file=" + str(directory / "execution.json")]
    started = time.monotonic()
    with (directory / "build.log").open("w") as log:
        subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
    elapsed = time.monotonic() - started
    wheel = directory / WHEEL
    shutil.copy2(root / "bazel-bin" / WHEEL, wheel)
    records = execution_records(directory / "execution.json")
    return {"sha256": digest(wheel.read_bytes()), "elapsed_seconds": round(elapsed, 3),
            "logged_spawns": len(records),
            "uncached_spawns": sum(not record.get("cacheHit", False) for record in records),
            "actions": action_metrics(directory / "build-events.jsonl"),
            "installed": installed_probe(wheel, expected)}


def check(root, output, bazel):
    root = root.resolve()
    # Actions checkout trust is temporary; trust only this inspected checkout.
    git = ["git", "-c", "safe.directory=" + str(root)]
    output.mkdir(parents=True, exist_ok=True)
    source = root / SOURCE
    original = source.read_bytes()
    require(original.count(ORIGINAL) == 1, "Expected exactly one original Y-cable switch counter type")
    subprocess.run(git + ["diff", "--exit-code", "HEAD", "--", SOURCE], cwd=root, check=True)
    before = subprocess.check_output(git + ["status", "--porcelain", "--untracked-files=no"], cwd=root)
    receipt = {"status": "running", "source": SOURCE, "source_sha256": digest(original),
               "target": TARGET, "phases": {},
               "scope": "Owner wheel and isolated installed Y-cable API; no Docker or hardware claim"}
    changed = False
    try:
        for phase in ("baseline", "no-op"):
            receipt["phases"][phase] = build(root, output, bazel, phase, "manual")
        baseline = receipt["phases"]["baseline"]["sha256"]
        require(receipt["phases"]["no-op"]["sha256"] == baseline, "No-op changed the wheel")
        require_noop(receipt["phases"]["no-op"])
        changed = True
        source.write_bytes(original.replace(ORIGINAL, EDITED))
        receipt["phases"]["edited"] = build(root, output, bazel, "edited", "manual-bazel-incremental")
        require(receipt["phases"]["edited"]["sha256"] != baseline, "Source edit did not change wheel bytes")
        old = payload(output / "baseline" / WHEEL)
        new = payload(output / "edited" / WHEEL)
        receipt["changed_members"] = payload_delta(old, new)
        receipt["status"] = "passed"
    except Exception as error:
        receipt.update(status="failed", error=str(error))
        raise
    finally:
        # Restore the exact original source even when the edited build or
        # isolated consumer fails, then rebuild the normal artifact for CI.
        if changed:
            source.write_bytes(original)
        try:
            if changed:
                receipt["phases"]["restored"] = build(root, output, bazel, "restored", "manual")
                require(receipt["phases"]["restored"]["sha256"] == receipt["phases"]["baseline"]["sha256"],
                        "Restored source did not recover the exact original wheel")
            require(source.read_bytes() == original, "Source restoration failed")
            require(subprocess.check_output(git + ["status", "--porcelain", "--untracked-files=no"], cwd=root) == before,
                    "Tracked files changed during the incremental check")
            receipt["source_restored"] = True
        except Exception as error:
            receipt.update(status="failed", restoration_error=str(error))
            raise
        finally:
            (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bazel", default="bazel")
    parser.add_argument("--output", type=Path, default=Path("bazel-evidence/incremental"))
    args = parser.parse_args()
    check(Path(__file__).resolve().parents[2], args.output.resolve(), args.bazel)
