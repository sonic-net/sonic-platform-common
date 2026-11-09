"""Reject misleading wheel inventories in incremental build evidence."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

from wheel_incremental import (ORIGINAL, SOURCE, WHEEL, action_metrics, build, check,
                               payload, payload_delta, require_noop)


class ActionAccountingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Unmodified ActionSummary messages from the actual four-phase hosted run.
        path = Path(__file__).parent / "fixtures/wheel_action_summaries.json"
        cls.phases = json.loads(path.read_text())["phases"]

    def read_metrics(self, summary):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            path.write_text(json.dumps({"buildMetrics": {"actionSummary": summary}}) + "\n")
            return action_metrics(path)

    def test_actual_noop_counts_workspace_action_without_a_spawn(self):
        metrics = self.read_metrics(self.phases["no-op"])
        self.assertEqual(metrics["total"], 1)
        self.assertEqual({name: count for name, count in metrics["by_mnemonic"].items() if count},
                         {"BazelWorkspaceStatusAction": 1})
        require_noop({"uncached_spawns": 0, "actions": metrics})

    def test_internal_file_write_cannot_hide_behind_zero_spawns(self):
        summary = copy.deepcopy(self.phases["no-op"])
        summary["actionsExecuted"] = "2"
        for action in summary["actionData"]:
            if action["mnemonic"] == "FileWrite":
                action["actionsExecuted"] = "1"
        summary["runnerCount"] = [{"name": "total", "count": 2}, {"name": "internal", "count": 2}]
        metrics = self.read_metrics(summary)
        # The old uncached-spawn assertion accepted this internal rebuild.
        with self.assertRaisesRegex(AssertionError, "FileWrite"):
            require_noop({"uncached_spawns": 0, "actions": metrics})

    def test_cache_served_wheel_is_an_action_but_not_an_uncached_process(self):
        metrics = self.read_metrics(self.phases["restored"])
        self.assertEqual(metrics["total"], 2)
        self.assertEqual(metrics["by_mnemonic"]["PyWheel"], 1)
        self.assertIn({"name": "disk cache hit", "count": 1, "execKind": "Remote"}, metrics["runners"])
        with self.assertRaisesRegex(AssertionError, "PyWheel"):
            require_noop({"uncached_spawns": 0, "actions": metrics})

    def test_incomplete_or_malformed_counts_fail(self):
        for mutation in ("missing mnemonic", "duplicate mnemonic", "negative", "boolean"):
            with self.subTest(mutation=mutation):
                summary = copy.deepcopy(self.phases["no-op"])
                if mutation == "missing mnemonic":
                    summary["actionData"] = []
                elif mutation == "duplicate mnemonic":
                    summary["actionData"].append(summary["actionData"][0])
                elif mutation == "negative":
                    summary["actionsExecuted"] = "-1"
                else:
                    summary["actionsExecuted"] = True
                with self.assertRaises(AssertionError):
                    self.read_metrics(summary)

    def test_missing_or_duplicate_summary_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            for events in ([], [{"buildMetrics": {}}],
                           [{"buildMetrics": {"actionSummary": self.phases["no-op"]}}] * 2):
                with self.subTest(events=len(events)):
                    path.write_text("\n".join(json.dumps(event) for event in events))
                    with self.assertRaisesRegex(AssertionError, "one complete"):
                        action_metrics(path)

    def test_build_requests_all_mnemonics_and_retains_separate_cache_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "bazel-bin").mkdir()
            (root / "bazel-bin" / WHEEL).write_bytes(b"retained wheel fixture")

            def record_command(command, **kwargs):
                self.assertIn("--experimental_record_metrics_for_all_mnemonics", command)
                event_path = next(arg.split("=", 1)[1] for arg in command if arg.startswith("--build_event_json_file="))
                execution_path = next(arg.split("=", 1)[1] for arg in command if arg.startswith("--execution_log_json_file="))
                Path(event_path).write_text(json.dumps({"buildMetrics": {"actionSummary": self.phases["restored"]}}))
                Path(execution_path).write_text(json.dumps({"cacheHit": True}))

            with mock.patch("wheel_incremental.subprocess.run", side_effect=record_command), mock.patch(
                    "wheel_incremental.installed_probe", return_value={"switch_count_manual": "manual"}):
                result = build(root, root / "evidence", "unused", "restored", "manual")
            self.assertEqual(result["logged_spawns"], 1)
            self.assertEqual(result["uncached_spawns"], 0)
            self.assertEqual(result["actions"]["total"], 2)


class PayloadEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.before = {name: {"sha256": "before", "mode": 0o100644 << 16} for name in
                       (SOURCE, "sonic_platform_common-1.0.dist-info/RECORD", "sonic_platform_base/device_base.py")}
        self.after = copy.deepcopy(self.before)
        for name in (SOURCE, "sonic_platform_common-1.0.dist-info/RECORD"):
            self.after[name]["sha256"] = "after"

    def test_expected_edit_preserves_other_payloads(self):
        self.assertEqual(len(payload_delta(self.before, self.after)), 2)

    def test_edited_file_cannot_change_mode(self):
        self.after[SOURCE]["mode"] = 0o100755 << 16
        with self.assertRaisesRegex(AssertionError, "modes"):
            payload_delta(self.before, self.after)

    def test_unrelated_file_cannot_change(self):
        self.after["sonic_platform_base/device_base.py"]["sha256"] = "after"
        with self.assertRaisesRegex(AssertionError, "unrelated"):
            payload_delta(self.before, self.after)

    def test_duplicate_zip_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.whl"
            with zipfile.ZipFile(path, "w") as archive, warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(SOURCE, "first")
                archive.writestr(SOURCE, "second")
            with self.assertRaisesRegex(AssertionError, "Duplicate"):
                payload(path)


class CheckoutTrustTest(unittest.TestCase):
    def test_different_owner_checkout_preserves_source_guard_and_restoration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "checkout"
            root.mkdir()
            source = root / SOURCE
            source.parent.mkdir()
            source.write_bytes(ORIGINAL + b"\n")
            for command in (["init", "-q"], ["add", SOURCE],
                            ["-c", "user.name=Wheel test", "-c", "user.email=test@example.invalid",
                             "commit", "-qm", "Fixture"]):
                subprocess.run(["git", *command], cwd=root, check=True)

            def wheel_phase(repository, output, bazel, phase, expected):
                directory = output / phase
                directory.mkdir(parents=True)
                wheel = directory / WHEEL
                with zipfile.ZipFile(wheel, "w") as archive:
                    for name, value in ((SOURCE, source.read_bytes()),
                                        ("sonic_platform_common-1.0.dist-info/RECORD", source.read_bytes()),
                                        ("sonic_platform_base/device_base.py", b"unchanged")):
                        archive.writestr(zipfile.ZipInfo(name, date_time=(2023, 1, 1, 0, 0, 0)), value)
                return {"sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "uncached_spawns": 0,
                        "actions": {"total": 1, "by_mnemonic": {"BazelWorkspaceStatusAction": 1}}}

            environment = {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1",
                           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
            with mock.patch.dict(os.environ, environment), mock.patch(
                    "wheel_incremental.build", side_effect=wheel_phase) as build:
                rejected = subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", SOURCE],
                                          cwd=root, capture_output=True, text=True)
                self.assertNotEqual(rejected.returncode, 0, "negative control must reject untrusted checkout")
                self.assertIn("Could not access", rejected.stderr)
                output = Path(temporary) / "evidence"
                check(root, output, "unused")
                self.assertEqual(build.call_count, 4)
                self.assertEqual(source.read_bytes(), ORIGINAL + b"\n")
                receipt = json.loads((output / "receipt.json").read_text())
                self.assertEqual(receipt["status"], "passed")
                self.assertTrue(receipt["source_restored"])
                # Trusting this exact checkout must not bypass the clean-source fence.
                source.write_bytes(ORIGINAL + b"\n# unexpected change\n")
                build.reset_mock()
                with self.assertRaises(subprocess.CalledProcessError):
                    check(root, Path(temporary) / "dirty-evidence", "unused")
                build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
