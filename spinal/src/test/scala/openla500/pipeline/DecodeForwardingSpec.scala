package openla500.pipeline

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class DecodeForwardingSimTop extends Component {
  val io = new Bundle {
    val fetchValid = in Bool ()
    val fetchBits = in Bits (FetchPayload.LegacyWidth bits)
    val fetchReady = out Bool ()
    val decodeReady = in Bool ()
    val executeWriteEnabled = in Bool ()
    val executeNeedsStall = in Bool ()
    val executeDestination = in UInt (5 bits)
    val executeData = in Bits (32 bits)
    val memoryWriteEnabled = in Bool ()
    val memoryNeedsStall = in Bool ()
    val memoryDestination = in UInt (5 bits)
    val memoryData = in Bits (32 bits)
    val registerWriteValid = in Bool ()
    val registerWriteDestination = in UInt (5 bits)
    val registerWriteData = in Bits (32 bits)
    val decodeValid = out Bool ()
    val registerDataJ = out Bits (32 bits)
    val decodeGprWrite = out Bool ()
    val decodeDestination = out UInt (5 bits)
    val branchRepairActive = out Bool ()
    val branchRepairTarget = out UInt (32 bits)
    val keepAlive = out Bits (2048 bits)
  }

  val decode = new DecodeStage(
    lateResultForwardingEnabled = true,
    memoryBranchForwardingEnabled = true
  )
  decode.io.input.valid := io.fetchValid
  decode.io.input.payload := FetchPayload.unpackLegacy(io.fetchBits)
  decode.io.directionPrediction.phtIndex := 0
  decode.io.directionPrediction.baseTaken := False
  decode.io.directionPrediction.localTaken := False
  io.fetchReady := decode.io.input.ready
  decode.io.output.ready := io.decodeReady

  decode.io.executeForward.dependencyNeedsStall := io.executeNeedsStall
  decode.io.executeForward.writeEnabled := io.executeWriteEnabled
  decode.io.executeForward.destination := io.executeDestination
  decode.io.executeForward.data := io.executeData
  decode.io.executeLateResultAllowed := False
  decode.io.memoryForward.dependencyNeedsStall := io.memoryNeedsStall
  decode.io.memoryForward.writeEnabled := io.memoryWriteEnabled
  decode.io.memoryForward.destination := io.memoryDestination
  decode.io.memoryForward.data := io.memoryData
  decode.io.flush.assignDontCare()
  decode.io.flush.exception := False
  decode.io.flush.ertn := False
  decode.io.flush.refetch := False
  decode.io.flush.instructionCacheOperation := False
  decode.io.flush.idle := False
  decode.io.executeTlbStall := False
  decode.io.memoryTlbStall := False
  decode.io.writebackTlbStall := False
  decode.io.interruptPending := False
  decode.io.csrReadData := 0
  decode.io.csrPrivilege := 0
  decode.io.timer := 0
  decode.io.timerId := 0
  decode.io.reservationValid := False
  decode.io.executeOccupied := True
  decode.io.memoryOccupied := False
  decode.io.writebackOccupied := False
  decode.io.writeBufferEmpty := True
  decode.io.dataCacheEmpty := True
  decode.io.registerWrite.valid := io.registerWriteValid
  decode.io.registerWrite.destination := io.registerWriteDestination
  decode.io.registerWrite.data := io.registerWriteData
  decode.io.debugReadSelect := False
  decode.io.debugReadAddress := 0

  io.decodeValid := decode.io.output.valid
  io.registerDataJ := decode.io.output.payload.registerDataJ
  io.decodeGprWrite := decode.io.output.payload.gprWrite
  io.decodeDestination := decode.io.output.payload.destination
  io.branchRepairActive := decode.io.branchRepair.active
  io.branchRepairTarget := decode.io.branchRepair.target
  io.keepAlive := (
    decode.io.input.ready.asBits ##
      decode.io.output.valid.asBits ##
      decode.io.output.payload.asBits ##
      decode.io.csrReadAddress.asBits ##
      decode.io.debugLegacyValue ##
      decode.io.branchRepair.asBits ##
      decode.io.btb.asBits ##
      decode.io.lateForwardJ.asBits ##
      decode.io.lateForwardKOrD.asBits ##
      decode.io.lateForwardDestination.asBits
  ).resize(2048)
}

class DecodeForwardingSpec extends AnyFunSuite {
  test("occupied store does not forward its effective address as a GPR write") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-decode")
    val workspace = Paths.get(workspaceRoot, "decode-store-forwarding").toString

    SimConfig
      .withConfig(SpinalConfig(oneFilePerComponent = true, removePruned = false))
      .withVerilator
      .addSimulatorFlag("-Wall")
      .addSimulatorFlag("-Wwarn-WIDTH")
      .addSimulatorFlag("-Wwarn-UNOPTFLAT")
      .addSimulatorFlag("-Wwarn-CMPCONST")
      .addSimulatorFlag("-Wwarn-UNSIGNED")
      .addSimulatorFlag("-Wno-UNUSEDSIGNAL")
      .disableCache
      .workspacePath(workspace)
      .compile(new DecodeForwardingSimTop)
      .doSim("decode-store-forwarding", 0x158aa8) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.fetchValid #= false
        dut.io.fetchBits #= 0
        dut.io.decodeReady #= true
        dut.io.executeWriteEnabled #= false
        dut.io.executeNeedsStall #= false
        dut.io.executeDestination #= 19
        dut.io.executeData #= 0x001d0004
        dut.io.memoryWriteEnabled #= false
        dut.io.memoryNeedsStall #= false
        dut.io.memoryDestination #= 19
        dut.io.memoryData #= 0x001d0008
        dut.io.registerWriteValid #= false
        dut.io.registerWriteDestination #= 0
        dut.io.registerWriteData #= 0

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        dut.io.registerWriteValid #= true
        dut.io.registerWriteDestination #= 19
        dut.io.registerWriteData #= 0x001d0000
        dut.clockDomain.waitSampling()
        dut.io.registerWriteValid #= false

        val firstStore = BigInt("29801273", 16) // st.w r19, r19, 4
        val secondStore = BigInt("2980127b", 16) // st.w r27, r19, 4
        dut.io.fetchBits #= BigInt("1c0752b4", 16) | (firstStore << 32)
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)

        assert(dut.io.decodeValid.toBoolean)
        assert(dut.io.registerDataJ.toBigInt == BigInt("001d0000", 16))
        assert(!dut.io.decodeGprWrite.toBoolean)
        assert(dut.io.decodeDestination.toBigInt == 19)

        dut.clockDomain.waitSampling()
        dut.io.fetchBits #= BigInt("1c0752b8", 16) | (secondStore << 32)
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)

        assert(dut.io.decodeValid.toBoolean)
        assert(dut.io.registerDataJ.toBigInt == BigInt("001d0000", 16))

        dut.clockDomain.waitSampling()
        dut.io.executeWriteEnabled #= true
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)

        assert(dut.io.decodeValid.toBoolean)
        assert(dut.io.registerDataJ.toBigInt == BigInt("001d0004", 16))

        dut.clockDomain.waitSampling()
        dut.io.executeWriteEnabled #= false
        dut.io.executeNeedsStall #= false
        dut.io.memoryWriteEnabled #= false
        dut.io.memoryNeedsStall #= false
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)

        assert(dut.io.decodeValid.toBoolean)
        assert(dut.io.registerDataJ.toBigInt == BigInt("001d0000", 16))

        dut.clockDomain.waitSampling()
        dut.io.memoryWriteEnabled #= true
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)

        assert(dut.io.decodeValid.toBoolean)
        assert(dut.io.registerDataJ.toBigInt == BigInt("001d0008", 16))
      }
  }

  test("indirect branch repair waits for decode handshake under backpressure") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-decode")
    val workspace = Paths.get(workspaceRoot, "decode-branch-repair-backpressure").toString

    SimConfig
      .withConfig(SpinalConfig(oneFilePerComponent = true, removePruned = false))
      .withVerilator
      .addSimulatorFlag("-Wall")
      .addSimulatorFlag("-Wwarn-WIDTH")
      .addSimulatorFlag("-Wwarn-UNOPTFLAT")
      .addSimulatorFlag("-Wwarn-CMPCONST")
      .addSimulatorFlag("-Wwarn-UNSIGNED")
      .addSimulatorFlag("-Wno-UNUSEDSIGNAL")
      .disableCache
      .workspacePath(workspace)
      .compile(new DecodeForwardingSimTop)
      .doSim("decode-branch-repair-backpressure", 0x1c00a520) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.fetchValid #= false
        dut.io.fetchBits #= 0
        dut.io.decodeReady #= false
        dut.io.executeWriteEnabled #= false
        dut.io.executeNeedsStall #= false
        dut.io.executeDestination #= 0
        dut.io.executeData #= 0
        dut.io.memoryWriteEnabled #= false
        dut.io.memoryNeedsStall #= false
        dut.io.memoryDestination #= 0
        dut.io.memoryData #= 0
        dut.io.registerWriteValid #= false
        dut.io.registerWriteDestination #= 0
        dut.io.registerWriteData #= 0

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        val sourceRegister = 15
        val staleTarget = BigInt("1c009f08", 16)
        val resolvedTarget = BigInt("1c00a798", 16)
        dut.io.registerWriteValid #= true
        dut.io.registerWriteDestination #= sourceRegister
        dut.io.registerWriteData #= staleTarget
        dut.clockDomain.waitSampling()
        dut.io.registerWriteValid #= false

        val jirlR0R15 = BigInt("4c0001e0", 16)
        dut.io.fetchBits #= BigInt("1c00a520", 16) | (jirlR0R15 << 32)
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)

        assert(dut.io.decodeValid.toBoolean)
        assert(!dut.io.branchRepairActive.toBoolean)

        dut.io.registerWriteValid #= true
        dut.io.registerWriteDestination #= sourceRegister
        dut.io.registerWriteData #= resolvedTarget
        dut.clockDomain.waitSampling()
        dut.io.registerWriteValid #= false
        sleep(1)

        assert(dut.io.decodeValid.toBoolean)
        assert(!dut.io.branchRepairActive.toBoolean)
        assert(dut.io.branchRepairTarget.toBigInt == resolvedTarget)

        dut.io.decodeReady #= true
        sleep(1)
        assert(dut.io.branchRepairActive.toBoolean)
        assert(dut.io.branchRepairTarget.toBigInt == resolvedTarget)
        dut.clockDomain.waitSampling()
      }
  }

  test("branch consumes a completed memory-stage result without waiting for writeback") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-decode")
    val workspace = Paths.get(workspaceRoot, "decode-memory-branch-forwarding").toString

    SimConfig
      .withConfig(SpinalConfig(oneFilePerComponent = true, removePruned = false))
      .withVerilator
      .addSimulatorFlag("-Wall")
      .addSimulatorFlag("-Wwarn-WIDTH")
      .addSimulatorFlag("-Wwarn-UNOPTFLAT")
      .addSimulatorFlag("-Wwarn-CMPCONST")
      .addSimulatorFlag("-Wwarn-UNSIGNED")
      .addSimulatorFlag("-Wno-UNUSEDSIGNAL")
      .disableCache
      .workspacePath(workspace)
      .compile(new DecodeForwardingSimTop)
      .doSim("decode-memory-branch-forwarding", 0x1c00a520) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.fetchValid #= false
        dut.io.fetchBits #= 0
        dut.io.decodeReady #= true
        dut.io.executeWriteEnabled #= false
        dut.io.executeNeedsStall #= false
        dut.io.executeDestination #= 0
        dut.io.executeData #= 0
        dut.io.memoryWriteEnabled #= true
        dut.io.memoryNeedsStall #= true
        dut.io.memoryDestination #= 15
        dut.io.memoryData #= BigInt("1c00a798", 16)
        dut.io.registerWriteValid #= false
        dut.io.registerWriteDestination #= 0
        dut.io.registerWriteData #= 0

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        val jirlR0R15 = BigInt("4c0001e0", 16)
        dut.io.fetchBits #= BigInt("1c00a520", 16) | (jirlR0R15 << 32)
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)

        assert(!dut.io.decodeValid.toBoolean)
        assert(!dut.io.branchRepairActive.toBoolean)

        dut.io.memoryNeedsStall #= false
        sleep(1)
        assert(dut.io.decodeValid.toBoolean)
        assert(dut.io.branchRepairActive.toBoolean)
        assert(dut.io.branchRepairTarget.toBigInt == BigInt("1c00a798", 16))
        dut.clockDomain.waitSampling()
      }
  }
}
