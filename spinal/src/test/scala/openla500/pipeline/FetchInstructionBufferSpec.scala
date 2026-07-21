package openla500.pipeline

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class FetchBufferRedirectSimTop extends Component {
  val io = new Bundle {
    val addressAccepted = in Bool ()
    val dataValid = in Bool ()
    val data = in Bits (32 bits)
    val redirect = in Bool ()
    val redirectTarget = in UInt (32 bits)
    val popReady = in Bool ()
    val request = out Bool ()
    val requestAddress = out UInt (32 bits)
    val fetchOutputValid = out Bool ()
    val bufferPushReady = out Bool ()
    val popValid = out Bool ()
    val popPc = out UInt (32 bits)
    val popInstruction = out Bits (32 bits)
    val occupancy = out UInt (4 bits)
  }

  val fetch = new FetchStage()
  val buffer = new FetchInstructionBuffer(depth = 8)

  buffer.io.flush := io.redirect
  buffer.io.redirect := io.redirect
  buffer.io.redirectTargetAccepted :=
    io.redirect && fetch.io.fetchEnable && fetch.io.fetchPc === io.redirectTarget
  buffer.io.push.valid := fetch.io.downstream.valid
  fetch.io.downstream.ready := buffer.io.push.ready
  buffer.io.push.payload.slotValid := B"4'b0001"
  for (lane <- 0 until FetchPacket.Width) {
    buffer.io.push.payload.slots(lane).fetch := fetch.io.downstream.payload
    buffer.io.push.payload.slots(lane).direction := fetch.io.directionPrediction
  }
  buffer.io.pop.ready := io.popReady

  fetch.io.branchRepair := io.redirect
  fetch.io.branchTarget := io.redirectTarget
  fetch.io.exceptionFlush := False
  fetch.io.ertnFlush := False
  fetch.io.refetchFlush := False
  fetch.io.instructionCacheFlush := False
  fetch.io.idleFlush := False
  fetch.io.writebackPc := 0
  fetch.io.exceptionEntry := 0
  fetch.io.exceptionEra := 0
  fetch.io.exceptionTlbRefill := False
  fetch.io.tlbRefillEntry := 0
  fetch.io.interrupt := False
  fetch.io.instructionAddressAccepted := io.addressAccepted
  fetch.io.instructionDataValid := io.dataValid
  fetch.io.instructionData := io.data
  fetch.io.instructionMiss := False
  fetch.io.paging := False
  fetch.io.directAddress := True
  fetch.io.dmw0 := 0
  fetch.io.dmw1 := 0
  fetch.io.currentPlv := 0
  fetch.io.directFetchMat := B"01"
  fetch.io.disableCache := False
  fetch.io.btbTarget := 0
  fetch.io.btbTaken := False
  fetch.io.btbEnabled := False
  fetch.io.btbIndex := 0
  fetch.io.btbDirection.phtIndex := 0
  fetch.io.btbDirection.baseTaken := False
  fetch.io.btbDirection.localTaken := False
  fetch.io.tlbFound := True
  fetch.io.tlbValid := True
  fetch.io.tlbMat := B"01"
  fetch.io.tlbPlv := 0

  io.request := fetch.io.instructionRequest
  io.requestAddress := fetch.io.instructionAddress
  io.fetchOutputValid := fetch.io.downstream.valid
  io.bufferPushReady := buffer.io.push.ready
  io.popValid := buffer.io.pop.valid
  io.popPc := buffer.io.pop.payload.fetch.pc
  io.popInstruction := buffer.io.pop.payload.fetch.instruction
  io.occupancy := buffer.io.occupancy
}

class FetchInstructionBufferSpec extends AnyFunSuite {
  private def driveSlot(
      dut: FetchInstructionBuffer,
      lane: Int,
      pc: BigInt,
      instruction: BigInt
  ): Unit = {
    val slot = dut.io.push.payload.slots(lane)
    slot.fetch.pc #= pc
    slot.fetch.instruction #= instruction
    slot.fetch.exceptionCode #= 0
    slot.fetch.hasException #= false
    slot.fetch.instructionCacheMiss #= false
    slot.fetch.btbEnabled #= false
    slot.fetch.btbTaken #= false
    slot.fetch.btbIndex #= 0
    slot.fetch.btbTarget #= 0
    slot.direction.phtIndex #= lane
    slot.direction.baseTaken #= false
    slot.direction.localTaken #= lane % 2 == 1
  }

  test("fetch4 packets remain ordered and redirects atomically discard younger instructions") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-fetch-buffer")
    val workspace = Paths.get(workspaceRoot, "fetch4-window").toString

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
      .compile(new FetchInstructionBuffer(depth = 8))
      .doSim("fetch-buffer-directed", 0x158aa8) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.flush #= false
        dut.io.redirect #= false
        dut.io.redirectTargetAccepted #= false
        dut.io.push.valid #= false
        dut.io.push.payload.slotValid #= 0
        dut.io.pop.ready #= false
        for (lane <- 0 until FetchPacket.Width) driveSlot(dut, lane, 0, 0)

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()
        sleep(1)
        assert(!dut.io.pop.valid.toBoolean)
        assert(dut.io.occupancy.toInt == 0)

        for (lane <- 0 until FetchPacket.Width) {
          driveSlot(dut, lane, 0x1c000000L + lane * 4, 0x1000 + lane)
        }
        dut.io.push.payload.slotValid #= 0xf
        dut.io.push.valid #= true
        sleep(1)
        assert(dut.io.push.ready.toBoolean)
        dut.clockDomain.waitSampling()
        dut.io.push.valid #= false
        dut.io.push.payload.slotValid #= 0
        sleep(1)

        assert(dut.io.occupancy.toInt == 4)
        assert(dut.io.windowValid.toInt == 0xf)
        for (lane <- 0 until FetchPacket.Width) {
          assert(dut.io.window(lane).fetch.pc.toBigInt == 0x1c000000L + lane * 4)
          assert(dut.io.window(lane).fetch.instruction.toBigInt == 0x1000 + lane)
          assert(dut.io.window(lane).direction.phtIndex.toInt == lane)
          assert(dut.io.window(lane).direction.localTaken.toBoolean == (lane % 2 == 1))
        }

        dut.io.pop.ready #= true
        for (lane <- 0 until FetchPacket.Width) {
          sleep(1)
          assert(dut.io.pop.valid.toBoolean)
          assert(dut.io.pop.payload.fetch.pc.toBigInt == 0x1c000000L + lane * 4)
          dut.clockDomain.waitSampling()
        }
        dut.io.pop.ready #= false
        sleep(1)
        assert(!dut.io.pop.valid.toBoolean)
        assert(dut.io.occupancy.toInt == 0)

        // Fill six entries, then prove a simultaneous dequeue admits a three-slot packet at depth 8.
        for (packet <- 0 until 2) {
          for (lane <- 0 until 3) {
            driveSlot(dut, lane, 0x1c001000L + (packet * 3 + lane) * 4, 0x2000 + packet * 3 + lane)
          }
          dut.io.push.payload.slotValid #= 0x7
          dut.io.push.valid #= true
          dut.clockDomain.waitSampling()
          dut.io.push.valid #= false
          dut.io.push.payload.slotValid #= 0
        }
        sleep(1)
        assert(dut.io.occupancy.toInt == 6)

        for (lane <- 0 until 3) {
          driveSlot(dut, lane, 0x1c002000L + lane * 4, 0x3000 + lane)
        }
        dut.io.push.payload.slotValid #= 0x7
        dut.io.push.valid #= true
        dut.io.pop.ready #= true
        sleep(1)
        assert(dut.io.push.ready.toBoolean)
        dut.clockDomain.waitSampling()
        dut.io.push.valid #= false
        dut.io.push.payload.slotValid #= 0
        dut.io.pop.ready #= false
        sleep(1)
        assert(dut.io.occupancy.toInt == 8)

        dut.io.flush #= true
        sleep(1)
        assert(!dut.io.pop.valid.toBoolean)
        assert(dut.io.push.ready.toBoolean)
        dut.clockDomain.waitSampling()
        dut.io.flush #= false
        sleep(1)
        assert(dut.io.occupancy.toInt == 0)
        assert(dut.io.windowValid.toInt == 0)

        // A non-branch global flush must not arm delayed branch-response cancellation. Its first
        // authoritative refetch packet is accepted normally.
        driveSlot(dut, 0, 0x1c003000L, 0x4000)
        dut.io.push.payload.slotValid #= 0x1
        dut.io.push.valid #= true
        sleep(1)
        assert(dut.io.push.ready.toBoolean)
        dut.clockDomain.waitSampling()
        dut.io.push.valid #= false
        dut.io.push.payload.slotValid #= 0
        sleep(1)
        assert(dut.io.occupancy.toInt == 1)
        assert(dut.io.pop.valid.toBoolean)
        assert(dut.io.pop.payload.fetch.pc.toBigInt == 0x1c003000L)
      }
  }

  test("redirect drains the stale Fetch response and binds returned data to the target PC") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-fetch-buffer")
    val workspace = Paths.get(workspaceRoot, "fetch-buffer-redirect").toString

    val compiled = SimConfig
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
      .compile(new FetchBufferRedirectSimTop)

    compiled.doSim("fetch-buffer-redirect-immediate", 0x1c010054) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      dut.io.addressAccepted #= false
      dut.io.dataValid #= false
      dut.io.data #= 0
      dut.io.redirect #= false
      dut.io.redirectTarget #= 0
      dut.io.popReady #= false
      dut.clockDomain.assertReset()
      dut.clockDomain.waitSampling(2)
      dut.clockDomain.deassertReset()
      dut.clockDomain.waitSampling()

      sleep(1)
      assert(dut.io.request.toBoolean)
      assert(dut.io.requestAddress.toBigInt == BigInt("1c000000", 16))
      dut.io.addressAccepted #= true
      dut.clockDomain.waitSampling()
      dut.io.addressAccepted #= false

      // A stale sequential response and an immediately accepted redirect target coincide.
      val immediateTarget = BigInt("1c010380", 16)
      val staleInstruction = BigInt("55152801", 16)
      val targetInstruction = BigInt("4c000020", 16)
      dut.io.data #= staleInstruction
      dut.io.dataValid #= true
      dut.io.redirect #= true
      dut.io.redirectTarget #= immediateTarget
      dut.io.addressAccepted #= true
      sleep(1)
      assert(dut.io.fetchOutputValid.toBoolean)
      assert(dut.io.bufferPushReady.toBoolean)
      assert(dut.io.request.toBoolean)
      assert(dut.io.requestAddress.toBigInt == immediateTarget)
      dut.clockDomain.waitSampling()
      dut.io.dataValid #= false
      dut.io.redirect #= false
      dut.io.addressAccepted #= false
      sleep(1)
      assert(dut.io.occupancy.toInt == 0)

      dut.io.data #= targetInstruction
      dut.io.dataValid #= true
      dut.clockDomain.waitSampling()
      dut.io.dataValid #= false
      sleep(1)
      assert(dut.io.occupancy.toInt == 1)
      assert(dut.io.popValid.toBoolean)
      assert(dut.io.popPc.toBigInt == immediateTarget)
      assert(dut.io.popInstruction.toBigInt == targetInstruction)
    }

    compiled.doSim("fetch-buffer-redirect-target-already-current", 0x1c010058) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      dut.io.addressAccepted #= false
      dut.io.dataValid #= false
      dut.io.data #= 0
      dut.io.redirect #= false
      dut.io.redirectTarget #= 0
      dut.io.popReady #= false
      dut.clockDomain.assertReset()
      dut.clockDomain.waitSampling(2)
      dut.clockDomain.deassertReset()
      dut.clockDomain.waitSampling()

      val initialPc = BigInt("1c000000", 16)
      val target = initialPc + 4
      val initialInstruction = BigInt("00150000", 16)
      val targetInstruction = BigInt("0280058c", 16)
      val sequentialInstruction = BigInt("02800421", 16)

      dut.io.addressAccepted #= true
      dut.clockDomain.waitSampling()
      dut.io.addressAccepted #= false

      // Drain Fetch while retaining the returned instruction in the queue. The natural next PC is
      // now exactly the redirect target, reproducing the empty-Fetch corner seen in bitcount.
      dut.io.data #= initialInstruction
      dut.io.dataValid #= true
      dut.clockDomain.waitSampling()
      dut.io.dataValid #= false
      sleep(1)
      assert(dut.io.occupancy.toInt == 1)

      dut.io.redirect #= true
      dut.io.redirectTarget #= target
      dut.io.addressAccepted #= true
      sleep(1)
      assert(dut.io.request.toBoolean)
      assert(dut.io.requestAddress.toBigInt == target)
      dut.clockDomain.waitSampling()

      // The target response makes Fetch ready to issue again. It must request target + 4 rather
      // than replaying the target that was accepted in the redirect cycle.
      dut.io.redirect #= false
      dut.io.data #= targetInstruction
      dut.io.dataValid #= true
      sleep(1)
      assert(dut.io.request.toBoolean)
      assert(dut.io.requestAddress.toBigInt == target + 4)
      dut.clockDomain.waitSampling()
      dut.io.addressAccepted #= false

      dut.io.data #= sequentialInstruction
      dut.clockDomain.waitSampling()
      dut.io.dataValid #= false
      sleep(1)
      assert(dut.io.occupancy.toInt == 2)

      dut.io.popReady #= true
      sleep(1)
      assert(dut.io.popValid.toBoolean)
      assert(dut.io.popPc.toBigInt == target)
      assert(dut.io.popInstruction.toBigInt == targetInstruction)
      dut.clockDomain.waitSampling()
      sleep(1)
      assert(dut.io.popValid.toBoolean)
      assert(dut.io.popPc.toBigInt == target + 4)
      assert(dut.io.popInstruction.toBigInt == sequentialInstruction)
    }

    compiled.doSim("fetch-buffer-redirect-delayed", 0x1c020240) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      dut.io.addressAccepted #= false
      dut.io.dataValid #= false
      dut.io.data #= 0
      dut.io.redirect #= false
      dut.io.redirectTarget #= 0
      dut.io.popReady #= false
      dut.clockDomain.assertReset()
      dut.clockDomain.waitSampling(2)
      dut.clockDomain.deassertReset()
      dut.clockDomain.waitSampling()

      sleep(1)
      assert(dut.io.request.toBoolean)
      assert(dut.io.requestAddress.toBigInt == BigInt("1c000000", 16))
      dut.io.addressAccepted #= true
      dut.clockDomain.waitSampling()
      dut.io.addressAccepted #= false

      // Target-address backpressure must retry the target, never the stale PC.
      val delayedTarget = BigInt("1c020240", 16)
      val staleInstruction = BigInt("55152801", 16)
      val targetInstruction = BigInt("4c000020", 16)
      dut.io.data #= staleInstruction
      dut.io.dataValid #= true
      dut.io.redirect #= true
      dut.io.redirectTarget #= delayedTarget
      sleep(1)
      assert(dut.io.bufferPushReady.toBoolean)
      assert(dut.io.request.toBoolean)
      assert(dut.io.requestAddress.toBigInt == delayedTarget)
      dut.clockDomain.waitSampling()
      dut.io.dataValid #= false
      dut.io.redirect #= false
      sleep(1)
      assert(dut.io.request.toBoolean)
      assert(dut.io.requestAddress.toBigInt == delayedTarget)
      assert(dut.io.occupancy.toInt == 0)

      dut.io.addressAccepted #= true
      dut.clockDomain.waitSampling()
      dut.io.addressAccepted #= false
      dut.io.data #= targetInstruction
      dut.io.dataValid #= true
      dut.clockDomain.waitSampling()
      dut.io.dataValid #= false
      sleep(1)
      assert(dut.io.popValid.toBoolean)
      assert(dut.io.popPc.toBigInt == delayedTarget)
      assert(dut.io.popInstruction.toBigInt == targetInstruction)
    }

    compiled.doSim("fetch-buffer-redirect-inflight-response", 0x1c030240) { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      dut.io.addressAccepted #= false
      dut.io.dataValid #= false
      dut.io.data #= 0
      dut.io.redirect #= false
      dut.io.redirectTarget #= 0
      dut.io.popReady #= false
      dut.clockDomain.assertReset()
      dut.clockDomain.waitSampling(2)
      dut.clockDomain.deassertReset()
      dut.clockDomain.waitSampling()

      // Accept one sequential request, then redirect while its response is still outstanding.
      dut.io.addressAccepted #= true
      dut.clockDomain.waitSampling()
      dut.io.addressAccepted #= false

      val target = BigInt("1c030240", 16)
      val staleInstruction = BigInt("55152801", 16)
      val targetInstruction = BigInt("4c000020", 16)
      dut.io.redirect #= true
      dut.io.redirectTarget #= target
      sleep(1)
      assert(dut.io.request.toBoolean)
      assert(dut.io.requestAddress.toBigInt == target)
      dut.clockDomain.waitSampling()
      dut.io.redirect #= false

      // The old response and target address handshake may coincide. The buffer must consume only
      // that old response, leaving the subsequently returned target instruction intact.
      dut.io.data #= staleInstruction
      dut.io.dataValid #= true
      dut.io.addressAccepted #= true
      dut.clockDomain.waitSampling()
      dut.io.dataValid #= false
      dut.io.addressAccepted #= false
      sleep(1)
      assert(dut.io.occupancy.toInt == 0)
      assert(!dut.io.popValid.toBoolean)

      dut.io.data #= targetInstruction
      dut.io.dataValid #= true
      dut.clockDomain.waitSampling()
      dut.io.dataValid #= false
      sleep(1)
      assert(dut.io.occupancy.toInt == 1)
      assert(dut.io.popValid.toBoolean)
      assert(dut.io.popPc.toBigInt == target)
      assert(dut.io.popInstruction.toBigInt == targetInstruction)
    }
  }
}
