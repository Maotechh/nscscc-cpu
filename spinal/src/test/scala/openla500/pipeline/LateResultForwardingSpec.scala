package openla500.pipeline

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class LateResultForwardingSimTop extends Component {
  val io = new Bundle {
    val fetchValid = in Bool ()
    val fetchBits = in Bits (FetchPayload.LegacyWidth bits)
    val registerWrite = in(DecodeRegisterWrite())
    val producerValid = in Bool ()
    val producerDestination = in UInt (5 bits)
    val producerLateResultAllowed = in Bool ()
    val memoryResultValid = in Bool ()
    val memoryResultStalled = in Bool ()
    val memoryResult = in Bits (32 bits)
    val executeReady = in Bool ()
    val decodeFlush = in Bool ()
    val redirectTargetAccepted = in Bool ()
    val decodeInputReady = out Bool ()
    val decodeValid = out Bool ()
    val decodeBranchRepair = out Bool ()
    val decodeBranchTarget = out UInt (32 bits)
    val decodeLateJ = out Bool ()
    val executeValid = out Bool ()
    val executeResult = out Bits (32 bits)
    val executePredictionError = out Bool ()
    val executeBranchRepair = out Bool ()
    val executeBranchTarget = out UInt (32 bits)
    val executeBtbEnable = out Bool ()
    val executeBtbAddEntry = out Bool ()
    val executeBtbActualTaken = out Bool ()
    val executeBtbPhtIndex = out UInt (8 bits)
    val executeBtbBaseTaken = out Bool ()
    val executeBtbLocalTaken = out Bool ()
    val keepAlive = out Bits (4096 bits)
  }

  val decode = new DecodeStage(
    lateResultForwardingEnabled = true,
    delayedBranchResolutionEnabled = true
  )
  val execute = new ExecuteStage(delayedBranchResolutionEnabled = true)

  decode.io.input.valid := io.fetchValid
  decode.io.input.payload := FetchPayload.unpackLegacy(io.fetchBits)
  decode.io.directionPrediction.phtIndex := 0xa5
  decode.io.directionPrediction.baseTaken := False
  decode.io.directionPrediction.localTaken := True
  decode.io.output >> execute.io.input

  decode.io.executeForward.dependencyNeedsStall := io.producerValid
  decode.io.executeForward.writeEnabled := io.producerValid
  decode.io.executeForward.destination := io.producerDestination
  decode.io.executeForward.data := 0
  decode.io.executeLateResultAllowed := io.producerLateResultAllowed
  decode.io.memoryForward.dependencyNeedsStall := False
  decode.io.memoryForward.writeEnabled := False
  decode.io.memoryForward.destination := 0
  decode.io.memoryForward.data := 0
  decode.io.flush.assignDontCare()
  decode.io.flush.exception := False
  decode.io.flush.ertn := False
  decode.io.flush.refetch := io.decodeFlush
  decode.io.flush.instructionCacheOperation := False
  decode.io.flush.idle := False
  decode.io.delayedBranchSlotCancel := io.decodeFlush
  decode.io.redirectTargetAccepted := io.redirectTargetAccepted
  decode.io.executeTlbStall := False
  decode.io.memoryTlbStall := False
  decode.io.writebackTlbStall := False
  decode.io.interruptPending := False
  decode.io.csrReadData := 0
  decode.io.csrPrivilege := 0
  decode.io.timer := 0
  decode.io.timerId := 0
  decode.io.reservationValid := False
  decode.io.executeOccupied := io.producerValid
  decode.io.memoryOccupied := io.memoryResultValid
  decode.io.writebackOccupied := False
  decode.io.writeBufferEmpty := True
  decode.io.dataCacheEmpty := True
  decode.io.registerWrite := io.registerWrite
  decode.io.debugReadSelect := False
  decode.io.debugReadAddress := 0

  execute.io.output.ready := io.executeReady
  execute.io.lateForwardJ := decode.io.lateForwardJ
  execute.io.lateForwardKOrD := decode.io.lateForwardKOrD
  execute.io.lateForwardDestination := decode.io.lateForwardDestination
  execute.io.delayedBranch := decode.io.delayedBranch
  execute.io.memoryForward.valid := io.memoryResultValid
  execute.io.memoryForward.dependencyNeedsStall := io.memoryResultStalled
  execute.io.memoryForward.writeEnabled := io.memoryResultValid
  execute.io.memoryForward.destination := io.producerDestination
  execute.io.memoryForward.result := io.memoryResult
  execute.io.divideComplete := False
  execute.io.flush.assignDontCare()
  execute.io.flush.exception := False
  execute.io.flush.ertn := False
  execute.io.flush.refetch := False
  execute.io.flush.instructionCacheOperation := False
  execute.io.flush.idle := False
  execute.io.memoryFlush := False
  execute.io.memoryWritesTlbEntryHigh := False
  execute.io.instructionCacheUnbusy := True
  execute.io.memoryAddressAccepted := False
  execute.io.csrVirtualPageNumber := 0

  io.decodeInputReady := decode.io.input.ready
  io.decodeValid := decode.io.output.valid
  io.decodeBranchRepair := decode.io.branchRepair.active
  io.decodeBranchTarget := decode.io.branchRepair.target
  io.decodeLateJ := decode.io.lateForwardJ
  io.executeValid := execute.io.output.valid
  io.executeResult := execute.io.output.payload.executeResult
  io.executePredictionError := execute.io.output.payload.predictionError
  io.executeBranchRepair := execute.io.branchRepair.active
  io.executeBranchTarget := execute.io.branchRepair.target
  io.executeBtbEnable := execute.io.btb.enable
  io.executeBtbAddEntry := execute.io.btb.addEntry
  io.executeBtbActualTaken := execute.io.btb.actualTaken
  io.executeBtbPhtIndex := execute.io.btb.direction.phtIndex
  io.executeBtbBaseTaken := execute.io.btb.direction.baseTaken
  io.executeBtbLocalTaken := execute.io.btb.direction.localTaken
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
      decode.io.lateForwardDestination.asBits ##
      execute.io.output.ready.asBits ##
      execute.io.output.valid.asBits ##
      execute.io.output.payload.asBits ##
      execute.io.forward.asBits ##
      execute.io.mulDiv.asBits ##
      execute.io.memory.asBits ##
      execute.io.cache.asBits ##
      execute.io.tlbInstructionStall.asBits ##
      execute.io.dataFetch.asBits ##
      execute.io.branchRepair.asBits ##
      execute.io.btb.asBits
  ).resize(4096)
}

class LateResultForwardingSpec extends AnyFunSuite {
  test("non-branch EX dependency advances and waits in EX only until the MEM result is valid") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-late-forward")
    val workspace = Paths.get(workspaceRoot, "late-result-forwarding").toString

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
      .compile(new LateResultForwardingSimTop)
      .doSim("late-result-forwarding", 0x158aa8) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.fetchValid #= false
        dut.io.fetchBits #= 0
        dut.io.registerWrite.valid #= false
        dut.io.registerWrite.destination #= 0
        dut.io.registerWrite.data #= 0
        dut.io.producerValid #= false
        dut.io.producerDestination #= 1
        dut.io.producerLateResultAllowed #= false
        dut.io.memoryResultValid #= false
        dut.io.memoryResultStalled #= true
        dut.io.memoryResult #= 0
        dut.io.executeReady #= false
        dut.io.decodeFlush #= false
        dut.io.redirectTargetAccepted #= false

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        dut.io.registerWrite.valid #= true
        dut.io.registerWrite.destination #= 1
        dut.io.registerWrite.data #= 1
        dut.clockDomain.waitSampling()
        dut.io.registerWrite.destination #= 2
        dut.io.registerWrite.data #= 7
        dut.clockDomain.waitSampling()
        dut.io.registerWrite.valid #= false

        // mul.w r3, r1, r2 keeps the legacy bubble because the shared multiplier samples raw
        // operands. This avoids feeding MEM results combinationally back through the shared unit.
        val multiply = BigInt("001c0823", 16)
        dut.io.fetchBits #= BigInt("1c000ffc", 16) | (multiply << 32)
        dut.io.fetchValid #= true
        dut.io.producerValid #= true
        dut.io.producerLateResultAllowed #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)
        assert(!dut.io.decodeValid.toBoolean)
        assert(!dut.io.decodeLateJ.toBoolean)
        dut.io.producerValid #= false
        dut.io.executeReady #= true
        dut.clockDomain.waitSampling(2)
        dut.io.executeReady #= false

        // add.w r3, r1, r2. r1 is produced by the instruction currently leaving EX.
        val add = BigInt("00100823", 16)
        dut.io.fetchBits #= BigInt("1c001000", 16) | (add << 32)
        dut.io.fetchValid #= true
        dut.io.producerValid #= true
        dut.io.producerLateResultAllowed #= false
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)

        // A producer that will take an exception must retain the legacy decode stall so no younger
        // side effect can escape before the exception flush arrives.
        assert(!dut.io.decodeValid.toBoolean)
        assert(!dut.io.decodeLateJ.toBoolean)
        dut.io.producerLateResultAllowed #= true
        sleep(1)

        assert(dut.io.decodeValid.toBoolean)
        assert(dut.io.decodeLateJ.toBoolean)

        // The dependent add enters EX without a decode bubble, then waits safely while a load miss
        // (or any other delayed producer) has no valid MEM result.
        dut.clockDomain.waitSampling()
        dut.io.producerValid #= false
        sleep(1)
        assert(!dut.io.executeValid.toBoolean)

        // MEM supplies r1=11 for one cycle while the downstream stage is backpressured.
        dut.io.memoryResultValid #= true
        dut.io.memoryResultStalled #= false
        dut.io.memoryResult #= 11
        sleep(1)
        assert(dut.io.executeValid.toBoolean)
        assert(dut.io.executeResult.toBigInt == 18)

        // The result is retained in EX: after the MEM pulse disappears, the add still completes.
        dut.clockDomain.waitSampling()
        dut.io.memoryResultValid #= false
        dut.io.memoryResultStalled #= true
        dut.io.memoryResult #= 0
        dut.io.executeReady #= true
        sleep(1)
        assert(dut.io.executeValid.toBoolean)
        assert(dut.io.executeResult.toBigInt == 18)
      }
  }

  test("EX-dependent branch advances immediately and repairs only when its MEM operand commits") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-late-forward")
    val workspace = Paths.get(workspaceRoot, "delayed-branch-resolution").toString

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
      .compile(new LateResultForwardingSimTop)
      .doSim("delayed-branch-resolution", 0x158aa8) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.fetchValid #= false
        dut.io.fetchBits #= 0
        dut.io.registerWrite.valid #= false
        dut.io.registerWrite.destination #= 0
        dut.io.registerWrite.data #= 0
        dut.io.producerValid #= false
        dut.io.producerDestination #= 1
        dut.io.producerLateResultAllowed #= true
        dut.io.memoryResultValid #= false
        dut.io.memoryResultStalled #= true
        dut.io.memoryResult #= 0
        dut.io.executeReady #= false
        dut.io.decodeFlush #= false
        dut.io.redirectTargetAccepted #= false

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        dut.io.registerWrite.valid #= true
        dut.io.registerWrite.destination #= 2
        dut.io.registerWrite.data #= 7
        dut.clockDomain.waitSampling()
        dut.io.registerWrite.valid #= false

        // beq r1, r2, +8. r1 belongs to the load/mul/div producer currently leaving EX.
        val pc = BigInt("1c001000", 16)
        val instruction =
          (BigInt(0x16) << 26) | (BigInt(2) << 10) | (BigInt(1) << 5) | BigInt(2)
        dut.io.fetchBits #= pc | (instruction << 32)
        dut.io.fetchValid #= true
        dut.io.producerValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)

        // Decode no longer inserts the fixed EX-dependency bubble; the branch carries a late-J
        // marker into Execute instead.
        assert(dut.io.decodeValid.toBoolean)
        assert(dut.io.decodeLateJ.toBoolean)
        dut.clockDomain.waitSampling()
        dut.io.producerValid #= false
        sleep(1)
        assert(!dut.io.executeValid.toBoolean)
        assert(!dut.io.executeBranchRepair.toBoolean)

        // The final producer result makes the branch taken. Backpressure must hold both redirect
        // and predictor update until the branch itself can leave Execute.
        dut.io.memoryResultValid #= true
        dut.io.memoryResultStalled #= false
        dut.io.memoryResult #= 7
        sleep(1)
        assert(dut.io.executeValid.toBoolean)
        assert(!dut.io.executeBranchRepair.toBoolean)
        assert(!dut.io.executeBtbEnable.toBoolean)

        dut.io.executeReady #= true
        sleep(1)
        assert(dut.io.executeBranchRepair.toBoolean)
        assert(dut.io.executeBranchTarget.toBigInt == pc + 8)
        assert(dut.io.executeBtbEnable.toBoolean)
        assert(dut.io.executeBtbAddEntry.toBoolean)
        assert(dut.io.executeBtbActualTaken.toBoolean)
        assert(dut.io.executeBtbPhtIndex.toInt == 0xa5)
        assert(!dut.io.executeBtbBaseTaken.toBoolean)
        assert(dut.io.executeBtbLocalTaken.toBoolean)
        assert(dut.io.executePredictionError.toBoolean)
        dut.clockDomain.waitSampling()
      }
  }

  test("late branch flush consumes the stale Fetch slot even while Decode is backpressured") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-late-forward")
    val workspace = Paths.get(workspaceRoot, "late-branch-flush").toString

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
      .compile(new LateResultForwardingSimTop)
      .doSim("late-branch-flush", 0x158aa8) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.fetchValid #= false
        dut.io.fetchBits #= 0
        dut.io.registerWrite.valid #= false
        dut.io.registerWrite.destination #= 0
        dut.io.registerWrite.data #= 0
        dut.io.producerValid #= false
        dut.io.producerDestination #= 1
        dut.io.producerLateResultAllowed #= true
        dut.io.memoryResultValid #= false
        dut.io.memoryResultStalled #= false
        dut.io.memoryResult #= 0
        dut.io.executeReady #= false
        dut.io.decodeFlush #= false
        dut.io.redirectTargetAccepted #= false

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        // Hold one instruction in Decode and a younger wrong-path slot at its Fetch input.
        val add = BigInt("00100823", 16)
        dut.io.fetchBits #= BigInt("1c001000", 16) | (add << 32)
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchBits #= BigInt("1c001004", 16) | (add << 32)
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)
        assert(dut.io.decodeValid.toBoolean)
        assert(!dut.io.decodeInputReady.toBoolean)

        // The stale Fetch response is not ready in the repair cycle, so Decode must remember that
        // the next arriving slot is still on the discarded path.
        dut.io.decodeFlush #= true
        sleep(1)
        assert(dut.io.decodeInputReady.toBoolean)
        dut.clockDomain.waitSampling()
        dut.io.decodeFlush #= false

        dut.io.fetchBits #= BigInt("1c001008", 16) | (add << 32)
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)
        assert(!dut.io.decodeValid.toBoolean)
      }
  }

  test("accepted late-branch target is not discarded as a stale Fetch slot") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-late-forward")
    val workspace = Paths.get(workspaceRoot, "accepted-late-branch-target").toString

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
      .compile(new LateResultForwardingSimTop)
      .doSim("accepted-late-branch-target", 0x158aa8) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.fetchValid #= false
        dut.io.fetchBits #= 0
        dut.io.registerWrite.valid #= false
        dut.io.registerWrite.destination #= 0
        dut.io.registerWrite.data #= 0
        dut.io.producerValid #= false
        dut.io.producerDestination #= 1
        dut.io.producerLateResultAllowed #= true
        dut.io.memoryResultValid #= false
        dut.io.memoryResultStalled #= false
        dut.io.memoryResult #= 0
        dut.io.executeReady #= false
        dut.io.decodeFlush #= false
        dut.io.redirectTargetAccepted #= false

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        val add = BigInt("00100823", 16)
        dut.io.fetchBits #= BigInt("1c001000", 16) | (add << 32)
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)
        assert(dut.io.decodeValid.toBoolean)

        // The redirect target request was accepted in the repair cycle. No old-path response can
        // remain ahead of it, so the next slot is the target and must survive Decode cancellation.
        dut.io.decodeFlush #= true
        dut.io.redirectTargetAccepted #= true
        dut.clockDomain.waitSampling()
        dut.io.decodeFlush #= false
        dut.io.redirectTargetAccepted #= false

        dut.io.fetchBits #= BigInt("1c002000", 16) | (add << 32)
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)
        assert(dut.io.decodeValid.toBoolean)
      }
  }

  test("accepted Decode BL repair target is not discarded") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-late-forward")
    val workspace = Paths.get(workspaceRoot, "accepted-decode-repair-target").toString

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
      .compile(new LateResultForwardingSimTop)
      .doSim("accepted-decode-repair-target", 0x158aa8) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.fetchValid #= false
        dut.io.fetchBits #= 0
        dut.io.registerWrite.valid #= false
        dut.io.registerWrite.destination #= 0
        dut.io.registerWrite.data #= 0
        dut.io.producerValid #= false
        dut.io.producerDestination #= 1
        dut.io.producerLateResultAllowed #= true
        dut.io.memoryResultValid #= false
        dut.io.memoryResultStalled #= false
        dut.io.memoryResult #= 0
        dut.io.executeReady #= false
        dut.io.decodeFlush #= false
        dut.io.redirectTargetAccepted #= false

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        val pc = BigInt("1c001000", 16)
        val bl = (BigInt(0x15) << 26) | (BigInt(2) << 10)
        dut.io.fetchBits #= pc | (bl << 32)
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        dut.io.redirectTargetAccepted #= true
        sleep(1)
        assert(dut.io.decodeBranchRepair.toBoolean)
        assert(dut.io.decodeBranchTarget.toBigInt == pc + 8)
        dut.clockDomain.waitSampling()
        dut.io.redirectTargetAccepted #= false

        val add = BigInt("00100823", 16)
        dut.io.fetchBits #= (pc + 8) | (add << 32)
        dut.io.fetchValid #= true
        dut.clockDomain.waitSampling()
        dut.io.fetchValid #= false
        sleep(1)
        assert(dut.io.decodeValid.toBoolean)
      }
  }
}
