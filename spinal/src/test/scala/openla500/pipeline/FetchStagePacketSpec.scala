package openla500.pipeline

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

class FetchStagePacketSpec extends AnyFunSuite {
  private val ResetVector = BigInt("1c000000", 16)
  private val NonControlWords = Vector(
    BigInt("02800421", 16),
    BigInt("02800842", 16),
    BigInt("02800c63", 16),
    BigInt("02801084", 16)
  )

  private def packedLine(words: Seq[BigInt]): BigInt =
    words.zipWithIndex.foldLeft(BigInt(0)) { case (line, (word, index)) =>
      line | ((word & BigInt("ffffffff", 16)) << (index * 32))
    }

  private def simulationConfig(workspace: String) =
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

  private def initialize(dut: FetchStage): Unit = {
    dut.io.downstreamPacket.ready #= true
    dut.io.branchRepair #= false
    dut.io.branchTarget #= 0
    dut.io.exceptionFlush #= false
    dut.io.ertnFlush #= false
    dut.io.refetchFlush #= false
    dut.io.instructionCacheFlush #= false
    dut.io.idleFlush #= false
    dut.io.writebackPc #= 0
    dut.io.exceptionEntry #= 0
    dut.io.exceptionEra #= 0
    dut.io.exceptionTlbRefill #= false
    dut.io.tlbRefillEntry #= 0
    dut.io.interrupt #= false
    dut.io.instructionAddressAccepted #= false
    dut.io.instructionDataValid #= false
    dut.io.instructionData #= 0
    dut.io.instructionLineValid #= false
    dut.io.instructionLineData #= 0
    dut.io.instructionMiss #= false
    dut.io.paging #= false
    dut.io.directAddress #= true
    dut.io.dmw0 #= 0
    dut.io.dmw1 #= 0
    dut.io.currentPlv #= 0
    dut.io.directFetchMat #= 1
    dut.io.disableCache #= false
    dut.io.btbTarget #= 0
    dut.io.btbTaken #= false
    dut.io.btbEnabled #= false
    dut.io.btbIndex #= 0
    dut.io.btbDirection.phtIndex #= 0
    dut.io.btbDirection.baseTaken #= false
    dut.io.btbDirection.localTaken #= false
    dut.io.tlbFound #= true
    dut.io.tlbValid #= true
    dut.io.tlbMat #= 1
    dut.io.tlbPlv #= 0
  }

  private def reset(dut: FetchStage): Unit = {
    initialize(dut)
    dut.clockDomain.assertReset()
    dut.clockDomain.waitSampling(2)
    dut.clockDomain.deassertReset()
    dut.clockDomain.waitSampling()
  }

  private def acceptInitialRequest(dut: FetchStage): Unit = {
    sleep(1)
    assert(dut.io.instructionRequest.toBoolean)
    assert(dut.io.instructionAddress.toBigInt == ResetVector)
    dut.io.instructionAddressAccepted #= true
    dut.clockDomain.waitSampling()
    dut.io.instructionAddressAccepted #= false
  }

  /** Replace the initial outstanding request with an accepted redirect target.
    *
    * The scalar response makes the old Fetch slot ready in the redirect cycle, which is the same
    * timing used by the active frontend when a stale response and its redirect request coincide.
    */
  private def moveToPc(dut: FetchStage, target: BigInt): Unit = {
    acceptInitialRequest(dut)
    if (target != ResetVector) {
      dut.io.instructionData #= BigInt("00150000", 16)
      dut.io.instructionDataValid #= true
      dut.io.branchRepair #= true
      dut.io.branchTarget #= target
      dut.io.instructionAddressAccepted #= true
      sleep(1)
      assert(dut.io.instructionRequest.toBoolean)
      assert(dut.io.instructionAddress.toBigInt == target)
      dut.clockDomain.waitSampling()
      dut.io.instructionDataValid #= false
      dut.io.branchRepair #= false
      dut.io.instructionAddressAccepted #= false
    }
  }

  private def expectPacket(
      dut: FetchStage,
      pc: BigInt,
      words: Seq[BigInt],
      validMask: Int
  ): Unit = {
    assert(dut.io.downstreamPacket.valid.toBoolean)
    assert(dut.io.downstreamPacket.payload.slotValid.toInt == validMask)
    val startWord = ((pc >> 2) & 3).toInt
    for (lane <- 0 until FetchPacket.Width if (validMask & (1 << lane)) != 0) {
      assert(dut.io.downstreamPacket.payload.slots(lane).fetch.pc.toBigInt == pc + lane * 4)
      assert(
        dut.io.downstreamPacket.payload.slots(lane).fetch.instruction.toBigInt ==
          words(startWord + lane)
      )
    }
  }

  test("fetch4 extracts every line offset and truncates later control-flow instructions") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-fetch-stage-packet")
    val workspace = Paths.get(workspaceRoot, "offset-control").toString
    val compiled = simulationConfig(workspace).compile(new FetchStage(fetchPacketEnabled = true))

    for (startWord <- 0 until FetchPacket.Width) {
      compiled.doSim(s"line-offset-$startWord", 0x158aa8 + startWord) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        reset(dut)
        val pc = ResetVector + startWord * 4
        moveToPc(dut, pc)

        dut.io.instructionLineData #= packedLine(NonControlWords)
        dut.io.instructionLineValid #= true
        sleep(1)
        expectPacket(dut, pc, NonControlWords, (1 << (4 - startWord)) - 1)
        assert(dut.io.instructionAddress.toBigInt == ResetVector + 16)
      }
    }

    for (controlLane <- 0 until FetchPacket.Width) {
      compiled.doSim(s"control-lane-$controlLane", 0x158ab0 + controlLane) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        reset(dut)
        moveToPc(dut, ResetVector)
        val words = NonControlWords.updated(controlLane, BigInt("50000000", 16))

        dut.io.instructionLineData #= packedLine(words)
        dut.io.instructionLineValid #= true
        sleep(1)
        val validMask = if (controlLane == 0) 1 else (1 << controlLane) - 1
        val nextPc = ResetVector + (if (controlLane == 0) 4 else controlLane * 4)
        expectPacket(dut, ResetVector, words, validMask)
        assert(dut.io.instructionAddress.toBigInt == nextPc)
      }
    }
  }

  test("a consumed line advances across cache backpressure and accepted replacement binding") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-fetch-stage-packet")
    val workspace = Paths.get(workspaceRoot, "line-response-age").toString
    val compiled = simulationConfig(workspace).compile(new FetchStage(fetchPacketEnabled = true))

    compiled.doSim("line-next-request-backpressured", 0x158ab8) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      reset(dut)
      moveToPc(dut, ResetVector)

      dut.io.instructionLineData #= packedLine(NonControlWords)
      dut.io.instructionLineValid #= true
      sleep(1)
      expectPacket(dut, ResetVector, NonControlWords, 0xf)
      assert(dut.io.instructionAddress.toBigInt == ResetVector + 16)
      dut.clockDomain.waitSampling()

      dut.io.instructionLineValid #= false
      sleep(1)
      assert(dut.io.instructionRequest.toBoolean)
      assert(dut.io.instructionAddress.toBigInt == ResetVector + 16)

      dut.io.instructionAddressAccepted #= true
      dut.clockDomain.waitSampling()
      dut.io.instructionAddressAccepted #= false
      dut.io.instructionLineData #= packedLine(NonControlWords)
      dut.io.instructionLineValid #= true
      sleep(1)
      expectPacket(dut, ResetVector + 16, NonControlWords, 0xf)
    }

    compiled.doSim("line-next-request-accepted", 0x158ab9) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      reset(dut)
      moveToPc(dut, ResetVector)

      dut.io.instructionLineData #= packedLine(NonControlWords)
      dut.io.instructionLineValid #= true
      dut.io.instructionAddressAccepted #= true
      sleep(1)
      expectPacket(dut, ResetVector, NonControlWords, 0xf)
      assert(dut.io.instructionAddress.toBigInt == ResetVector + 16)
      dut.clockDomain.waitSampling()

      dut.io.instructionLineValid #= false
      dut.io.instructionAddressAccepted #= false
      sleep(1)
      assert(!dut.io.downstreamPacket.valid.toBoolean)

      dut.io.instructionLineData #= packedLine(NonControlWords)
      dut.io.instructionLineValid #= true
      sleep(1)
      expectPacket(dut, ResetVector + 16, NonControlWords, 0xf)
    }
  }

  test("taken prediction emits only lane zero and preserves the packet under backpressure") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-fetch-stage-packet")
    val workspace = Paths.get(workspaceRoot, "prediction-backpressure").toString
    val compiled = simulationConfig(workspace).compile(new FetchStage(fetchPacketEnabled = true))

    compiled.doSim("predicted-taken", 0x158ac0) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      reset(dut)
      moveToPc(dut, ResetVector)
      val target = BigInt("1c004000", 16)
      dut.io.btbEnabled #= true
      dut.io.btbTaken #= true
      dut.io.btbTarget #= target
      dut.io.btbIndex #= 7
      dut.io.instructionLineData #= packedLine(NonControlWords)
      dut.io.instructionLineValid #= true
      sleep(1)

      expectPacket(dut, ResetVector, NonControlWords, 1)
      assert(dut.io.instructionAddress.toBigInt == target)
      assert(dut.io.downstreamPacket.payload.slots(0).fetch.btbTaken.toBoolean)
      assert(dut.io.downstreamPacket.payload.slots(0).fetch.btbTarget.toBigInt == target)
    }

    compiled.doSim("line-backpressure", 0x158ac1) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      reset(dut)
      moveToPc(dut, ResetVector)
      dut.io.downstreamPacket.ready #= false
      dut.io.instructionLineData #= packedLine(NonControlWords)
      dut.io.instructionLineValid #= true
      sleep(1)
      expectPacket(dut, ResetVector, NonControlWords, 0xf)
      dut.clockDomain.waitSampling()

      dut.io.instructionLineValid #= false
      dut.io.instructionLineData #= 0
      sleep(1)
      expectPacket(dut, ResetVector, NonControlWords, 0xf)
      dut.clockDomain.waitSampling(2)
      sleep(1)
      expectPacket(dut, ResetVector, NonControlWords, 0xf)

      dut.io.downstreamPacket.ready #= true
      dut.clockDomain.waitSampling()
      sleep(1)
      assert(!dut.io.downstreamPacket.valid.toBoolean)
    }
  }

  test("flush removes a buffered line and uncached or exceptional fetches remain scalar") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-fetch-stage-packet")
    val workspace = Paths.get(workspaceRoot, "flush-scalar").toString
    val compiled = simulationConfig(workspace).compile(new FetchStage(fetchPacketEnabled = true))

    compiled.doSim("flush-buffered-line", 0x158ad0) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      reset(dut)
      moveToPc(dut, ResetVector)
      dut.io.downstreamPacket.ready #= false
      dut.io.instructionLineData #= packedLine(NonControlWords)
      dut.io.instructionLineValid #= true
      dut.clockDomain.waitSampling()
      dut.io.instructionLineValid #= false
      sleep(1)
      expectPacket(dut, ResetVector, NonControlWords, 0xf)

      dut.io.refetchFlush #= true
      dut.io.writebackPc #= ResetVector + 0x100
      dut.clockDomain.waitSampling()
      dut.io.refetchFlush #= false
      sleep(1)
      assert(!dut.io.downstreamPacket.valid.toBoolean)
    }

    compiled.doSim("uncached-scalar", 0x158ad1) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      reset(dut)
      moveToPc(dut, ResetVector)
      val instruction = BigInt("028014a5", 16)
      dut.io.directFetchMat #= 0
      dut.io.instructionData #= instruction
      dut.io.instructionDataValid #= true
      sleep(1)
      expectPacket(dut, ResetVector, Seq(instruction), 1)
      assert(dut.io.instructionUncached.toBoolean)
    }

    compiled.doSim("translation-exception-scalar", 0x158ad2) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      reset(dut)
      moveToPc(dut, ResetVector)
      dut.io.directAddress #= false
      dut.io.paging #= true
      dut.io.tlbFound #= false
      dut.io.tlbValid #= false
      sleep(1)
      assert(dut.io.downstreamPacket.valid.toBoolean)
      assert(dut.io.downstreamPacket.payload.slotValid.toInt == 1)
      assert(dut.io.downstreamPacket.payload.slots(0).fetch.hasException.toBoolean)
      // FetchPayload encodes [privilege, invalid, refill, alignment]; the golden IF
      // path intentionally exposes both refill and invalid when the TLB lookup misses.
      assert(dut.io.downstreamPacket.payload.slots(0).fetch.exceptionCode.toInt == 6)
    }

    compiled.doSim("translation-invalid-scalar", 0x158ad3) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      reset(dut)
      moveToPc(dut, ResetVector)
      dut.io.directAddress #= false
      dut.io.paging #= true
      dut.io.tlbFound #= true
      dut.io.tlbValid #= false
      sleep(1)
      assert(dut.io.downstreamPacket.valid.toBoolean)
      assert(dut.io.downstreamPacket.payload.slotValid.toInt == 1)
      assert(dut.io.downstreamPacket.payload.slots(0).fetch.exceptionCode.toInt == 4)
    }

    compiled.doSim("translation-privilege-scalar", 0x158ad4) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      reset(dut)
      moveToPc(dut, ResetVector)
      dut.io.directAddress #= false
      dut.io.paging #= true
      dut.io.tlbFound #= true
      dut.io.tlbValid #= true
      dut.io.currentPlv #= 3
      dut.io.tlbPlv #= 0
      sleep(1)
      assert(dut.io.downstreamPacket.valid.toBoolean)
      assert(dut.io.downstreamPacket.payload.slotValid.toInt == 1)
      assert(dut.io.downstreamPacket.payload.slots(0).fetch.exceptionCode.toInt == 8)
    }
  }

  test("scalar response buffer remains stable across consecutive downstream stalls") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-fetch-stage-packet")
    val workspace = Paths.get(workspaceRoot, "scalar-response-backpressure").toString
    val compiled = simulationConfig(workspace).compile(new FetchStage(fetchPacketEnabled = false))

    compiled.doSim("scalar-response-backpressure", 0x158ad5) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      dut.io.downstream.ready #= false
      dut.io.branchRepair #= false
      dut.io.branchTarget #= 0
      dut.io.exceptionFlush #= false
      dut.io.ertnFlush #= false
      dut.io.refetchFlush #= false
      dut.io.instructionCacheFlush #= false
      dut.io.idleFlush #= false
      dut.io.writebackPc #= 0
      dut.io.exceptionEntry #= 0
      dut.io.exceptionEra #= 0
      dut.io.exceptionTlbRefill #= false
      dut.io.tlbRefillEntry #= 0
      dut.io.interrupt #= false
      dut.io.instructionAddressAccepted #= false
      dut.io.instructionDataValid #= false
      dut.io.instructionData #= 0
      dut.io.instructionMiss #= false
      dut.io.paging #= false
      dut.io.directAddress #= true
      dut.io.dmw0 #= 0
      dut.io.dmw1 #= 0
      dut.io.currentPlv #= 0
      dut.io.directFetchMat #= 1
      dut.io.disableCache #= false
      dut.io.btbTarget #= 0
      dut.io.btbTaken #= false
      dut.io.btbEnabled #= false
      dut.io.btbIndex #= 0
      dut.io.btbDirection.phtIndex #= 0
      dut.io.btbDirection.baseTaken #= false
      dut.io.btbDirection.localTaken #= false
      dut.io.tlbFound #= true
      dut.io.tlbValid #= true
      dut.io.tlbMat #= 1
      dut.io.tlbPlv #= 0

      dut.clockDomain.assertReset()
      dut.clockDomain.waitSampling(2)
      dut.clockDomain.deassertReset()
      dut.clockDomain.waitSampling()

      dut.io.instructionAddressAccepted #= true
      dut.clockDomain.waitSampling()
      dut.io.instructionAddressAccepted #= false

      val bufferedInstruction = BigInt("290011ae", 16)
      dut.io.instructionData #= bufferedInstruction
      dut.io.instructionDataValid #= true
      dut.clockDomain.waitSampling()
      dut.io.instructionDataValid #= false
      dut.io.instructionData #= BigInt("ffffffff", 16)

      for (_ <- 0 until 3) {
        sleep(1)
        assert(dut.io.downstream.valid.toBoolean)
        assert(dut.io.downstream.payload.instruction.toBigInt == bufferedInstruction)
        dut.clockDomain.waitSampling()
      }

      dut.io.downstream.ready #= true
      sleep(1)
      assert(dut.io.downstream.valid.toBoolean)
      assert(dut.io.downstream.payload.instruction.toBigInt == bufferedInstruction)
    }
  }
}
