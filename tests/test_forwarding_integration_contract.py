from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]


class ForwardingIntegrationContractTest(unittest.TestCase):
    def test_generated_backend_separates_stage_occupancy_from_forwarding_enable(self) -> None:
        rtl = (
            REPO / "rtl" / "mycpu_top.v"
        ).read_text(encoding="utf-8")

        self.assertIn(
            ".io_executeForward_writeEnabled         (execute_io_forward_writeEnabled",
            rtl,
        )
        self.assertIn(
            ".io_memoryForward_writeEnabled          (memory_io_forward_writeEnabled",
            rtl,
        )
        self.assertIn(
            ".io_executeOccupied                     (execute_io_forward_valid",
            rtl,
        )
        self.assertIn(
            ".io_memoryOccupied                      (memory_io_forward_valid",
            rtl,
        )
        self.assertNotIn(
            ".io_executeForward_writeEnabled         (execute_io_forward_valid",
            rtl,
        )
        self.assertNotIn(
            ".io_memoryForward_writeEnabled          (memory_io_forward_valid",
            rtl,
        )


if __name__ == "__main__":
    unittest.main()
