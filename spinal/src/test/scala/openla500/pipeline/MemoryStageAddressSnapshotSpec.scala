package openla500.pipeline

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class MemoryStageAddressSnapshotSimTop extends Component {
  val io = new Bundle {
    val inputValid = in Bool ()
    val inputBits = in Bits (ExecutePayload.LegacyWidth bits)
    val inputReady = out Bool ()
    val outputReady = in Bool ()
    val dataDataOk = in Bool ()
    val dataTag = in Bits (20 bits)
    val dataIndex = in Bits (8 bits)
    val dataOffset = in Bits (4 bits)
    val outputValid = out Bool ()
    val outputPhysicalAddress = out UInt (32 bits)
    val outputMemoryPhysicalAddress = out UInt (32 bits)
    val keepAlive = out Bits (1024 bits)
  }

  val stage = new MemoryStage
  stage.io.input.valid := io.inputValid
  stage.io.input.payload := ExecutePayload.unpackLegacy(io.inputBits)
  stage.io.input.payload.preload.allowPruning()
  stage.payload.preload.allowPruning()
  stage.io.output.ready := io.outputReady
  stage.io.divResult := 0
  stage.io.modResult := 0
  stage.io.mulResult := 0
  stage.io.flush.assignDontCare()
  stage.io.flush.exception := False
  stage.io.flush.ertn := False
  stage.io.flush.refetch := False
  stage.io.flush.instructionCacheOperation := False
  stage.io.flush.idle := False
  stage.io.dataDataOk := io.dataDataOk
  stage.io.dcacheMiss := False
  stage.io.dataReadData := 0
  stage.io.csrPage := False
  stage.io.csrDirectAddress := True
  stage.io.csrDmw0Plv0 := False
  stage.io.csrDmw0Plv3 := False
  stage.io.csrDmw0VirtualSegment := 0
  stage.io.csrDmw0MemoryAttribute := 1
  stage.io.csrDmw1Plv0 := False
  stage.io.csrDmw1Plv3 := False
  stage.io.csrDmw1VirtualSegment := 0
  stage.io.csrDmw1MemoryAttribute := 1
  stage.io.csrPlv := 0
  stage.io.csrDatm := 1
  stage.io.disableCache := False
  stage.io.llAddress := 0
  stage.io.dataIndexDiff := io.dataIndex
  stage.io.dataTagDiff := io.dataTag
  stage.io.dataOffsetDiff := io.dataOffset
  stage.io.dataTlbFound := True
  stage.io.dataTlbIndex := 0
  stage.io.dataTlbValid := True
  stage.io.dataTlbDirty := True
  stage.io.dataTlbMat := 1
  stage.io.dataTlbPlv := 0
  stage.io.dataTlbPpn := io.dataTag

  io.inputReady := stage.io.input.ready
  io.outputValid := stage.io.output.valid
  io.outputPhysicalAddress := stage.io.output.payload.physicalAddress
  io.outputMemoryPhysicalAddress := stage.io.output.payload.memoryPhysicalAddress
  io.keepAlive := (
    stage.io.input.ready.asBits ##
      stage.io.output.valid.asBits ##
      stage.io.output.payload.asBits ##
      stage.io.dataUncached.asBits ##
      stage.io.tlbExceptionCancel.asBits ##
      stage.io.scCancel.asBits ##
      stage.io.dataAddressTranslationEnable.asBits ##
      stage.io.dmw0Enable.asBits ##
      stage.io.dmw1Enable.asBits ##
      stage.io.cacopModeDi.asBits ##
      stage.io.tlbInstructionStall.asBits ##
      stage.io.writeTlbEntryHigh.asBits ##
      stage.io.stageFlush.asBits ##
      stage.io.forward.asBits
  ).resize(1024)
}

class MemoryStageAddressSnapshotSpec extends AnyFunSuite {
  private def field(value: BigInt, low: Int): BigInt = value << low

  test("a replayed memory request retains its accepted physical address") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-memory-address")
    val workspace = Paths.get(workspaceRoot, "memory-address-snapshot").toString

    SimConfig
      .withConfig(SpinalConfig(oneFilePerComponent = true))
      .withVerilator
      .addSimulatorFlag("-Wall")
      .addSimulatorFlag("-Wwarn-WIDTH")
      .addSimulatorFlag("-Wwarn-UNOPTFLAT")
      .addSimulatorFlag("-Wwarn-CMPCONST")
      .addSimulatorFlag("-Wwarn-UNSIGNED")
      .addSimulatorFlag("-Wno-UNUSEDSIGNAL")
      .disableCache
      .workspacePath(workspace)
      .compile(new MemoryStageAddressSnapshotSimTop)
      .doSim("memory-address-snapshot", 0x158aa8) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.inputValid #= false
        dut.io.inputBits #= 0
        dut.io.outputReady #= true
        dut.io.dataDataOk #= false
        dut.io.dataTag #= BigInt("1c0ff", 16)
        dut.io.dataIndex #= 0xff
        dut.io.dataOffset #= 0xc

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        val address = BigInt("1c0ffffc", 16)
        val payload =
          field(BigInt("1c000554", 16), 0) |
            field(1, 138) |
            field(address, 183) |
            field(address, 320) |
            field(4, 352) |
            field(BigInt("1c0003e0", 16), 360)

        dut.io.inputBits #= payload
        dut.io.inputValid #= true
        sleep(1)
        assert(dut.io.inputReady.toBoolean, "memory request was not accepted")
        dut.clockDomain.waitSampling()

        // The next EX instruction owns the combinational virtual index while the accepted
        // request remains in MEM for the extra physical-color replay cycle.
        dut.io.inputValid #= false
        dut.io.dataIndex #= 0
        dut.io.dataOffset #= 0
        dut.clockDomain.waitSampling()

        dut.io.dataDataOk #= true
        sleep(1)
        assert(dut.io.outputValid.toBoolean, "replayed store did not complete")
        assert(dut.io.outputPhysicalAddress.toBigInt == address)
        assert(
          dut.io.outputMemoryPhysicalAddress.toBigInt == address,
          f"store observation used overwritten EX address 0x${dut.io.outputMemoryPhysicalAddress.toBigInt}%08x"
        )
      }
  }
}
