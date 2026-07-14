package openla500.pipeline

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class WritebackStageSimTop extends Component {
  val io = new Bundle {
    val inputValid = in Bool ()
    val inputBits = in Bits (MemoryPayload.LegacyWidth bits)
    val inputReady = out Bool ()
    val breakPoint = in Bool ()
    val stageValid = out Bool ()
    val commitValid = out Bool ()
    val commitPc = out UInt (32 bits)
    val commitGprValid = out Bool ()
    val commitGprIndex = out UInt (5 bits)
    val commitGprData = out Bits (32 bits)
    val commitStoreMask = out Bits (4 bits)
    val keepAlive = out Bits (1024 bits)
  }

  val stage = new WritebackStage()
  stage.io.input.valid := io.inputValid
  stage.io.input.payload := MemoryPayload.unpackLegacy(io.inputBits)
  stage.io.debugBreakPoint := io.breakPoint
  stage.io.tlbFillIndex := 0

  io.inputReady := stage.io.input.ready
  io.stageValid := stage.io.stageValid
  io.commitValid := stage.io.commit.valid
  io.commitPc := stage.io.commit.payload.pc
  io.commitGprValid := stage.io.commit.payload.gprWrite.valid
  io.commitGprIndex := stage.io.commit.payload.gprWrite.index
  io.commitGprData := stage.io.commit.payload.gprWrite.data
  io.commitStoreMask := stage.io.commit.payload.store.byteMask
  io.keepAlive := (
    stage.io.stageValid.asBits ##
      stage.io.realValid.asBits ##
      stage.io.registerWrite.asBits ##
      stage.io.csrWrite.asBits ##
      stage.io.flush.asBits ##
      stage.io.exception.asBits ##
      stage.io.tlb.asBits ##
      stage.io.reservation.asBits ##
      stage.io.perf.asBits ##
      stage.io.debug.asBits ##
      stage.io.commit.valid.asBits ##
      stage.io.commit.payload.asBits
  ).resize(1024)
}

class WritebackStageSpec extends AnyFunSuite {
  private def field(value: BigInt, low: Int): BigInt = value << low

  test("breakpoint holds legacy valid but releases exactly one commit event") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-writeback")
    val workspace = Paths.get(workspaceRoot, "writeback-commit-contract").toString

    SimConfig
      .withConfig(SpinalConfig(oneFilePerComponent = true))
      .withVerilator
      .addSimulatorFlag("-Wall")
      .addSimulatorFlag("-Wwarn-WIDTH")
      .addSimulatorFlag("-Wwarn-UNOPTFLAT")
      .addSimulatorFlag("-Wwarn-CMPCONST")
      .addSimulatorFlag("-Wwarn-UNSIGNED")
      // The production WB lint gate separately permits exactly two locked legacy payload bits.
      .addSimulatorFlag("-Wno-UNUSEDSIGNAL")
      .disableCache
      .workspacePath(workspace)
      .compile(new WritebackStageSimTop)
      .doSim("writeback-commit-contract", 0x158aa8) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.inputValid #= false
        dut.io.inputBits #= 0
        dut.io.breakPoint #= false

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        val pc = BigInt("1c001234", 16)
        val result = BigInt("89abcdef", 16)
        val destination = 7
        val payload =
          field(pc, 0) |
            field(result, 32) |
            field(destination, 64) |
            field(1, 69)

        dut.io.inputBits #= payload
        dut.io.inputValid #= true
        dut.clockDomain.waitSampling()
        dut.io.inputValid #= false
        dut.io.breakPoint #= true
        sleep(1)

        assert(dut.io.stageValid.toBoolean)
        assert(!dut.io.inputReady.toBoolean)
        assert(!dut.io.commitValid.toBoolean)
        dut.clockDomain.waitSampling(3)
        assert(dut.io.stageValid.toBoolean)
        assert(!dut.io.commitValid.toBoolean)

        dut.io.breakPoint #= false
        sleep(1)
        assert(dut.io.commitValid.toBoolean)
        assert(dut.io.commitPc.toBigInt == pc)
        assert(dut.io.commitGprValid.toBoolean)
        assert(dut.io.commitGprIndex.toBigInt == destination)
        assert(dut.io.commitGprData.toBigInt == result)

        dut.clockDomain.waitSampling()
        sleep(1)
        assert(!dut.io.commitValid.toBoolean)
        assert(!dut.io.stageValid.toBoolean)

        val byteStorePayload = field(2, 388) | field(1, 420)
        dut.io.inputBits #= byteStorePayload
        dut.io.inputValid #= true
        dut.clockDomain.waitSampling()
        dut.io.inputValid #= false
        sleep(1)
        assert(dut.io.commitValid.toBoolean)
        assert(dut.io.commitStoreMask.toBigInt == 4)
      }
  }
}
