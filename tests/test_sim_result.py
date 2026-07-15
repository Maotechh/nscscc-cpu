from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools import sim_result


PASS_LOG = """
Using /tmp/tools/la32r-nemu-interpreter-so for difftest
The first instruction of core 0 has commited. Difftest enabled.
HIT GOOD TRAP
Reached test end PC.
total clock is 100
total instruction is 80
"""


class SimulationResultTests(unittest.TestCase):
    def summarize(self, text: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "simulation.log"
            path.write_text(text, encoding="utf-8")
            return sim_result.summarize(text, path)

    def test_complete_positive_markers_pass_without_warnings(self) -> None:
        result = self.summarize(PASS_LOG)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["warning_count"], 0)

    def test_func_lab19_requires_syscall_termination(self) -> None:
        missing = self.summarize(PASS_LOG)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "simulation.log"
            path.write_text(PASS_LOG, encoding="utf-8")
            locked_missing = sim_result.summarize(
                PASS_LOG, path, sim_result.refactor.LOCKED_SMOKE_CASE
            )
            locked_complete = sim_result.summarize(
                PASS_LOG + "END by Syscall\n",
                path,
                sim_result.refactor.LOCKED_SMOKE_CASE,
            )
        self.assertEqual("pass", missing["status"])
        self.assertEqual("fail", locked_missing["status"])
        self.assertEqual("pass", locked_complete["status"])
        self.assertEqual(
            "end_by_syscall",
            locked_complete["simulation"]["termination_expectation"],
        )

    def test_time_limit_is_failure_even_when_chiplab_returns_zero(self) -> None:
        result = self.summarize(PASS_LOG + "Time limit exceeded.\n")
        self.assertEqual(result["status"], "fail")
        self.assertIn("time_limit", result["simulation"]["failures"])

    def test_missing_trap_and_end_markers_is_failure(self) -> None:
        result = self.summarize("total clock is 10\ntotal instruction is 5\n")
        self.assertEqual(result["status"], "fail")

    def test_compiler_warning_is_recorded_and_fails(self) -> None:
        result = self.summarize(PASS_LOG + "model.cpp:1: warning: unsafe conversion\n")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["warning_count"], 1)


if __name__ == "__main__":
    unittest.main()
