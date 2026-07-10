from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import refactor


class IterationValidationTests(unittest.TestCase):
    HEAD_SHA = "a" * 40
    BASE_SHA = "b" * 40
    ITERATION_ID = "20260710-2200-validator-test"

    def _write_iteration(self, root: Path, *, status: str = "blocked") -> Path:
        iteration_dir = root / self.ITERATION_ID
        reviews_dir = iteration_dir / "reviews"
        evidence_dir = iteration_dir / "evidence"
        reviews_dir.mkdir(parents=True)
        evidence_dir.mkdir()

        artifact = evidence_dir / "result.txt"
        artifact.write_text("verified evidence\n", encoding="utf-8")
        gate_passed = status in {"ready", "complete"}
        gate = {
            "status": "pass" if gate_passed else "fail",
            "planned": 1,
            "executed": 1,
            "passed": 1 if gate_passed else 0,
            "failed": 0 if gate_passed else 1,
            "skipped": 0,
        }
        summary = {
            "schema_version": 1,
            "iteration_id": self.ITERATION_ID,
            "status": status,
            "base_sha": self.BASE_SHA,
            "head_sha": self.HEAD_SHA,
            "gates": {"claim_review": gate},
        }
        if gate_passed:
            summary["required_gates"] = ["claim_review"]
            summary["review_target_sha"] = self.HEAD_SHA
        refactor.write_json(iteration_dir / "summary.json", summary)
        refactor.write_json(
            iteration_dir / "artifacts.json",
            {
                "schema_version": 1,
                "iteration_id": self.ITERATION_ID,
                "artifacts": [
                    {
                        "id": "result",
                        "path": "evidence/result.txt",
                        "sha256": refactor.sha256_file(artifact),
                        "size": artifact.stat().st_size,
                    }
                ],
            },
        )
        command = {
            "argv": ["validator-test"],
            "cwd": str(iteration_dir),
            "exit_code": 0 if gate_passed else 1,
            "elapsed_seconds": 0.1,
            "evidence": ["evidence/result.txt"],
        }
        (iteration_dir / "commands.jsonl").write_text(
            json.dumps(command, sort_keys=True) + "\n", encoding="utf-8"
        )
        (iteration_dir / "iteration.md").write_text(
            "# Validator test\n\n\u8fed\u4ee3\u8bb0\u5f55\u5305\u542b\u4e2d\u6587\u8bc1\u636e\u3002\n",
            encoding="utf-8",
        )
        (iteration_dir / "pr.md").write_text("# PR\n\nValidation evidence.\n", encoding="utf-8")

        job_id = "job-validator-1234"
        if gate_passed:
            provider = "anthropic"
            model = "claude-sonnet-validation"
            reviewed_head_sha: str | None = self.HEAD_SHA
            review_status = "pass"
            raw_event = {
                "jobId": job_id,
                "status": "completed",
                "done": True,
                "provider": provider,
                "model": model,
                "response": "Independent review completed with no blocking findings.",
                "error": None,
            }
            error = None
            open_blocking_count = 0
            fresh = True
            allow_ready = True
            allow_promotion = True
        else:
            provider = None
            model = None
            reviewed_head_sha = None
            review_status = "unavailable"
            error = "Claude provider credential is unavailable"
            raw_event = {
                "jobId": job_id,
                "status": "failed",
                "done": True,
                "provider": provider,
                "model": model,
                "response": None,
                "error": error,
            }
            open_blocking_count = 1
            fresh = False
            allow_ready = False
            allow_promotion = False
        raw_path = reviews_dir / "claude-raw.md"
        raw_path.write_text(json.dumps(raw_event, sort_keys=True) + "\n", encoding="utf-8")
        raw_sha = refactor.sha256_file(raw_path)
        review_summary = {
            "schema_version": 1,
            "iteration_id": self.ITERATION_ID,
            "status": review_status,
            "job_id": job_id,
            "provider": provider,
            "model": model,
            "reviewed_head_sha": reviewed_head_sha,
            "raw_sha256": raw_sha,
            "provenance": {
                "source": "claude-review-mcp",
                "raw_path": "reviews/claude-raw.md",
                "raw_sha256": raw_sha,
                "job_id": job_id,
                "provider": provider,
                "model": model,
                "reviewed_head_sha": reviewed_head_sha,
            },
            "error": error,
            "open_blocking_count": open_blocking_count,
            "fresh_against_head": fresh,
            "allow_ready": allow_ready,
            "allow_status_promotion": allow_promotion,
        }
        refactor.write_json(reviews_dir / "claude-summary.json", review_summary)
        return iteration_dir

    def _validate(self, iteration_dir: Path) -> int:
        with mock.patch.object(refactor, "git_text", return_value=self.HEAD_SHA):
            with contextlib.redirect_stdout(io.StringIO()):
                return refactor.command_validate_iteration(
                    SimpleNamespace(iteration_dir=str(iteration_dir))
                )

    def test_accepts_minimal_truthful_blocked_iteration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            iteration_dir = self._write_iteration(Path(temporary))
            self.assertEqual(0, self._validate(iteration_dir))

    def test_local_files_cannot_authorize_ready_even_with_structurally_valid_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            iteration_dir = self._write_iteration(Path(temporary), status="ready")
            with self.assertRaisesRegex(
                refactor.RefactorError, "cannot authorize status=ready"
            ):
                self._validate(iteration_dir)

    def test_local_files_cannot_authorize_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            iteration_dir = self._write_iteration(Path(temporary), status="complete")
            with self.assertRaisesRegex(
                refactor.RefactorError, "cannot authorize status=complete"
            ):
                self._validate(iteration_dir)

    def test_rejects_empty_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            iteration_dir = self._write_iteration(Path(temporary))
            summary_path = iteration_dir / "summary.json"
            summary = refactor.validate_json_file(summary_path)
            summary["gates"] = {}
            refactor.write_json(summary_path, summary)
            with self.assertRaisesRegex(refactor.RefactorError, "non-empty"):
                self._validate(iteration_dir)

    def test_rejects_gate_count_conservation_errors(self) -> None:
        mutations = [
            {"planned": 1, "executed": 1, "passed": 0, "failed": 0, "skipped": 0},
            {"planned": 2, "executed": 1, "passed": 0, "failed": 1, "skipped": 0},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                iteration_dir = self._write_iteration(Path(temporary))
                summary_path = iteration_dir / "summary.json"
                summary = refactor.validate_json_file(summary_path)
                summary["gates"]["claim_review"].update(mutation)
                refactor.write_json(summary_path, summary)
                with self.assertRaises(refactor.RefactorError):
                    self._validate(iteration_dir)

    def test_rejects_unknown_gate_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            iteration_dir = self._write_iteration(Path(temporary))
            summary_path = iteration_dir / "summary.json"
            summary = refactor.validate_json_file(summary_path)
            summary["gates"]["claim_review"]["status"] = "trust_me"
            refactor.write_json(summary_path, summary)
            with self.assertRaisesRegex(refactor.RefactorError, "status must be one of"):
                self._validate(iteration_dir)

    def test_ready_rejects_empty_required_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            iteration_dir = self._write_iteration(Path(temporary), status="ready")
            summary_path = iteration_dir / "summary.json"
            summary = refactor.validate_json_file(summary_path)
            summary["required_gates"] = []
            refactor.write_json(summary_path, summary)
            with self.assertRaisesRegex(refactor.RefactorError, "at least one required gate"):
                self._validate(iteration_dir)

    def test_rejects_minimal_handwritten_review_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            iteration_dir = self._write_iteration(Path(temporary), status="ready")
            refactor.write_json(
                iteration_dir / "reviews" / "claude-summary.json",
                {"open_blocking_count": 0, "fresh_against_head": True},
            )
            with self.assertRaises(refactor.RefactorError):
                self._validate(iteration_dir)

    def test_rejects_tampered_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            iteration_dir = self._write_iteration(Path(temporary))
            (iteration_dir / "evidence" / "result.txt").write_text(
                "tampered evidence\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(refactor.RefactorError, "mismatch"):
                self._validate(iteration_dir)

    def test_rejects_artifact_outside_workspace_and_iteration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            iteration_dir = self._write_iteration(root)
            outside = root / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            artifacts_path = iteration_dir / "artifacts.json"
            artifacts = refactor.validate_json_file(artifacts_path)
            artifacts["artifacts"][0].update(
                {
                    "path": str(outside),
                    "sha256": refactor.sha256_file(outside),
                    "size": outside.stat().st_size,
                }
            )
            refactor.write_json(artifacts_path, artifacts)
            with self.assertRaisesRegex(refactor.RefactorError, "inside the workspace or iteration"):
                self._validate(iteration_dir)

    def test_rejects_command_without_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            iteration_dir = self._write_iteration(Path(temporary))
            command_path = iteration_dir / "commands.jsonl"
            command = json.loads(command_path.read_text(encoding="utf-8"))
            command.pop("evidence")
            command_path.write_text(json.dumps(command) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(refactor.RefactorError, "evidence"):
                self._validate(iteration_dir)

    def test_review_ancestor_allows_only_evidence_only_followup_commits(self) -> None:
        # A review target may trail HEAD only when every later path is review/status/PR evidence.
        with mock.patch.object(
            refactor,
            "git_text",
            side_effect=[
                f"{self.HEAD_SHA} {self.BASE_SHA}",
                "logs/refactor/example/reviews/claude-summary.json\ndocs/refactor/status.yml",
            ],
        ):
            refactor._review_target_is_acceptable(self.BASE_SHA, self.HEAD_SHA)
        with mock.patch.object(
            refactor,
            "git_text",
            side_effect=[f"{self.HEAD_SHA} {self.BASE_SHA}", "tools/refactor.py"],
        ):
            with self.assertRaisesRegex(refactor.RefactorError, "non-evidence"):
                refactor._review_target_is_acceptable(self.BASE_SHA, self.HEAD_SHA)


if __name__ == "__main__":
    unittest.main()
