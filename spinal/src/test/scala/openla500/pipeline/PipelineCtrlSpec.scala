package openla500.pipeline

import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class PipelineCtrlProbe extends Component {
  val io = new Bundle {
    val control = in(PipelineCtrl())
    val globalFlush = out(Bool())
    val globalTarget = out(UInt(32 bits))
    val olderStages = in(OlderStageOccupancy())
    val anyOlderStage = out(Bool())
    val executeBranchRepair = in(RedirectRequest())
    val branchRepairActive = out(Bool())
    val branchRepairTarget = out(UInt(32 bits))
    val debugBreakPoint = out(Bool())
    val heartbeat = out(Bool())
  }
  noIoPrefix()

  io.globalFlush := io.control.globalFlush
  io.globalTarget := io.control.globalTarget
  io.anyOlderStage := io.olderStages.any
  val selectedBranchRepair = PipelineCtrlPriority.selectBranchRepair(
    io.control.globalFlush,
    io.executeBranchRepair,
    io.control.branchRepair
  )
  io.branchRepairActive := selectedBranchRepair.active
  io.branchRepairTarget := selectedBranchRepair.target
  io.debugBreakPoint := io.control.debugBreakPoint
  val heartbeat = Reg(Bool()) init (False)
  heartbeat := !heartbeat
  io.heartbeat := heartbeat
}

class PipelineCtrlSpec extends AnyFunSuite {
  import GlobalRedirectCause._

  test("global redirect priority is explicit and stable") {
    assert(
      PipelineCtrlPriority.HighestFirst == Vector(
        Exception,
        Ertn,
        Refetch,
        InstructionCacheOp,
        Idle
      )
    )
    assert(PipelineCtrlPriority.selectGlobal(false, false, false, false, false).isEmpty)
    assert(PipelineCtrlPriority.selectGlobal(false, false, false, false, true).contains(Idle))
    assert(
      PipelineCtrlPriority
        .selectGlobal(false, false, false, true, true)
        .contains(InstructionCacheOp)
    )
    assert(PipelineCtrlPriority.selectGlobal(false, false, true, true, true).contains(Refetch))
    assert(PipelineCtrlPriority.selectGlobal(false, true, true, true, true).contains(Ertn))
    assert(PipelineCtrlPriority.selectGlobal(true, true, true, true, true).contains(Exception))
  }

  test("branch repair and debug breakpoint are not global redirect causes") {
    assert(!PipelineCtrlPriority.HighestFirst.exists(_.toString.contains("Branch")))
    assert(!PipelineCtrlPriority.HighestFirst.exists(_.toString.contains("Debug")))
  }

  test("hardware redirect mux applies the same priority to active targets") {
    val workspace =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-contracts") +
        "/pipeline-ctrl"
    SimConfig.withVerilator
      .addSimulatorFlag("-Wall")
      .addSimulatorFlag("-Wwarn-WIDTH")
      .addSimulatorFlag("-Wwarn-UNOPTFLAT")
      .addSimulatorFlag("-Wwarn-CMPCONST")
      .addSimulatorFlag("-Wwarn-UNSIGNED")
      .disableCache
      .workspacePath(workspace)
      .compile(new PipelineCtrlProbe)
      .doSim { dut =>
        val requests = Seq(
          dut.io.control.exception,
          dut.io.control.ertn,
          dut.io.control.refetch,
          dut.io.control.instructionCacheOp,
          dut.io.control.idle,
          dut.io.control.branchRepair
        )
        requests.zipWithIndex.foreach { case (request, index) =>
          request.active #= false
          request.target #= 0x1000 + index * 4
        }
        dut.io.control.debugBreakPoint #= false
        dut.io.executeBranchRepair.active #= false
        dut.io.executeBranchRepair.target #= 0x2000
        dut.io.olderStages.execute #= false
        dut.io.olderStages.memory #= true
        dut.io.olderStages.writeback #= false
        sleep(1)
        assert(!dut.io.globalFlush.toBoolean)
        assert(dut.io.anyOlderStage.toBoolean)

        dut.io.control.idle.active #= true
        dut.io.control.instructionCacheOp.active #= true
        dut.io.control.refetch.active #= true
        dut.io.control.ertn.active #= true
        dut.io.control.exception.active #= true
        sleep(1)
        assert(dut.io.globalFlush.toBoolean)
        assert(dut.io.globalTarget.toBigInt == 0x1000)

        dut.io.control.exception.active #= false
        sleep(1)
        assert(dut.io.globalTarget.toBigInt == 0x1004)

        // A global writeback redirect is older than both repair sources.
        dut.io.control.branchRepair.active #= true
        dut.io.control.branchRepair.target #= 0x3000
        dut.io.executeBranchRepair.active #= true
        sleep(1)
        assert(!dut.io.branchRepairActive.toBoolean)

        // Once the global redirect drains, EX wins over Decode; Decode wins when EX is absent.
        dut.io.control.ertn.active #= false
        dut.io.control.refetch.active #= false
        dut.io.control.instructionCacheOp.active #= false
        dut.io.control.idle.active #= false
        sleep(1)
        assert(dut.io.branchRepairActive.toBoolean)
        assert(dut.io.branchRepairTarget.toBigInt == 0x2000)

        dut.io.executeBranchRepair.active #= false
        sleep(1)
        assert(dut.io.branchRepairActive.toBoolean)
        assert(dut.io.branchRepairTarget.toBigInt == 0x3000)
      }
  }
}
