package openla500.observe

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OrderedCommitGroupProbe extends Component {
  val io = new Bundle {
    val groupValid = in Bool ()
    val laneValid = in Bits (CommitGroup.Width bits)
    val exceptionValid = in Bits (CommitGroup.Width bits)
    val ertn = in Bits (CommitGroup.Width bits)
    val outputValid = out Bool ()
    val outputLaneValid = out Bits (CommitGroup.Width bits)
    val contractViolation = out Bool ()
  }
  noIoPrefix()

  private def clearEvent(event: CommitEvent, lane: Int): Unit = {
    event.pc := 0
    event.instruction := 0
    event.retired := True
    event.ertn := io.ertn(lane)
    event.isCounterInstruction := False
    event.csrRstat := False
    event.csrReadData := 0
    event.gprWrite.valid := False
    event.gprWrite.index := 0
    event.gprWrite.data := 0
    event.csrWrite.valid := False
    event.csrWrite.address := 0
    event.csrWrite.data := 0
    event.exception.valid := io.exceptionValid(lane)
    event.exception.ecode := 0
    event.exception.esubcode := 0
    event.exception.badVAddrValid := False
    event.exception.badVAddr := 0
    event.exception.tlbRefill := False
    event.exception.tlbException := False
    event.exception.tlbVppn := 0
    event.timer := 0
    event.load.instructionMask := 0
    event.load.pAddr := 0
    event.load.vAddr := 0
    event.store.instructionMask := 0
    event.store.pAddr := 0
    event.store.vAddr := 0
    event.store.data := 0
    event.store.byteMask := 0
    event.tlbFill.valid := False
    event.tlbFill.index := 0
  }

  val ordered = new OrderedCommitGroup
  ordered.io.input.valid := io.groupValid
  ordered.io.input.payload.valid := io.laneValid
  for (lane <- 0 until CommitGroup.Width) {
    clearEvent(ordered.io.input.payload.events(lane), lane)
  }

  io.outputValid := ordered.io.output.valid
  io.outputLaneValid := ordered.io.output.payload.valid
  io.contractViolation := ordered.io.contractViolation
}

class OrderedCommitGroupSpec extends AnyFunSuite {
  test("commit lanes stay prefix ordered and stop after precise control events") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-ordered-commit")
    val workspace = Paths.get(workspaceRoot, "ordered-commit-group").toString

    SimConfig.withVerilator.disableCache
      .workspacePath(workspace)
      .compile(new OrderedCommitGroupProbe)
      .doSim("ordered-commit-directed", 0x158aa8) { dut =>
        def check(
            lanes: Int,
            exceptions: Int,
            ertn: Int,
            expected: Int,
            violation: Boolean
        ): Unit = {
          dut.io.groupValid #= true
          dut.io.laneValid #= lanes
          dut.io.exceptionValid #= exceptions
          dut.io.ertn #= ertn
          sleep(1)
          assert(dut.io.outputValid.toBoolean)
          assert(dut.io.outputLaneValid.toInt == expected)
          assert(dut.io.contractViolation.toBoolean == violation)
        }

        check(lanes = 0x7, exceptions = 0, ertn = 0, expected = 0x7, violation = false)
        check(lanes = 0x5, exceptions = 0, ertn = 0, expected = 0x1, violation = true)
        check(lanes = 0x7, exceptions = 0x2, ertn = 0, expected = 0x3, violation = true)
        check(lanes = 0x7, exceptions = 0, ertn = 0x1, expected = 0x1, violation = true)
        check(lanes = 0x7, exceptions = 0x4, ertn = 0, expected = 0x7, violation = false)

        dut.io.groupValid #= false
        dut.io.laneValid #= 0x5
        dut.io.exceptionValid #= 0
        dut.io.ertn #= 0
        sleep(1)
        assert(!dut.io.outputValid.toBoolean)
        assert(!dut.io.contractViolation.toBoolean)
      }
  }
}
