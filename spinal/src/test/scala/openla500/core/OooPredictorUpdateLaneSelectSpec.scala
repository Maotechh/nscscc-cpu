package openla500.core

import openla500.backend.OooRecoveryCause
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

class OooPredictorUpdateLaneSelectSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private final class SelectorHarness extends Component {
    val io = new Bundle {
      val committedBranch = in Bits (config.commitWidth bits)
      val commitRobPointer = in Vec (UInt(config.robPointerWidth bits), config.commitWidth)
      val recoveryValid = in Bool ()
      val recoveryCause = in UInt (OooRecoveryCause.Width bits)
      val recoveryRobPointer = in UInt (config.robPointerWidth bits)
      val selectedLane = out UInt (log2Up(config.commitWidth) bits)
    }

    io.selectedLane := OooPredictorUpdateLaneSelect(
      config,
      io.committedBranch,
      io.commitRobPointer,
      io.recoveryValid,
      io.recoveryCause,
      io.recoveryRobPointer
    )
  }

  test("a retiring recovery branch overrides the normal oldest-branch training priority") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-predictor-update-select")
      .compile(new SelectorHarness)
      .doSim("ooo-predictor-update-select", 0xb03) { dut =>
        def drive(
            branches: Int,
            pointers: Seq[Int],
            recoveryValid: Boolean,
            recoveryCause: Int,
            recoveryPointer: Int,
            expectedLane: Int
        ): Unit = {
          dut.io.committedBranch #= branches
          for (lane <- 0 until config.commitWidth) {
            dut.io.commitRobPointer(lane) #= pointers(lane)
          }
          dut.io.recoveryValid #= recoveryValid
          dut.io.recoveryCause #= recoveryCause
          dut.io.recoveryRobPointer #= recoveryPointer
          sleep(1)
          assert(dut.io.selectedLane.toInt == expectedLane)
        }

        val pointers = Seq(9, 10, 11)
        drive(
          0x3,
          pointers,
          recoveryValid = false,
          recoveryCause = 0,
          recoveryPointer = 0,
          expectedLane = 0
        )
        drive(
          0x6,
          pointers,
          recoveryValid = false,
          recoveryCause = 0,
          recoveryPointer = 0,
          expectedLane = 1
        )

        drive(
          0x3,
          pointers,
          recoveryValid = true,
          recoveryCause = 1,
          recoveryPointer = 10,
          expectedLane = 1
        )
        drive(
          0x5,
          pointers,
          recoveryValid = true,
          recoveryCause = 1,
          recoveryPointer = 11,
          expectedLane = 2
        )

        drive(
          0x3,
          pointers,
          recoveryValid = true,
          recoveryCause = 2,
          recoveryPointer = 10,
          expectedLane = 0
        )
        drive(
          0x3,
          pointers,
          recoveryValid = true,
          recoveryCause = 1,
          recoveryPointer = 11,
          expectedLane = 0
        )
        drive(
          0x3,
          pointers,
          recoveryValid = true,
          recoveryCause = 1,
          recoveryPointer = 12,
          expectedLane = 0
        )
      }
  }
}
