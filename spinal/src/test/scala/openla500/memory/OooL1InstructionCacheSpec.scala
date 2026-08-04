package openla500.memory

import openla500.core._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OooL1InstructionCacheProbe(config: OooCoreConfig) extends Component {
  val io = new Bundle {
    val requestValid = in Bool ()
    val request = in(OooInstructionCacheRequest(config))
    val requestReady = out Bool ()
    val responseValid = out Bool ()
    val response = out(OooInstructionCacheResponse(config))
    val kill = in Bool ()
    val lineReadValid = out Bool ()
    val lineRead = out(OooLineReadRequest(config))
    val lineReadReady = in Bool ()
    val lineReadBeatValid = in Bool ()
    val lineReadBeat = in(OooLineReadBeat(config))
    val lineReadBeatReady = out Bool ()
    val invalidate = in Bool ()
    val maintenanceValid = in Bool ()
    val maintenanceRequest = in(OooCacheMaintenanceRequest(config))
    val maintenanceReady = out Bool ()
    val maintenanceDone = out Bool ()
    val invalidateBusy = out Bool ()
  }
  noIoPrefix()

  val cache = new OooL1InstructionCache(config)
  cache.io.requestValid := io.requestValid
  cache.io.request := io.request
  cache.io.kill := io.kill
  cache.io.lineReadReady := io.lineReadReady
  cache.io.lineReadBeatValid := io.lineReadBeatValid
  cache.io.lineReadBeat := io.lineReadBeat
  cache.io.invalidate := io.invalidate
  cache.io.maintenanceRequest.valid := io.maintenanceValid
  cache.io.maintenanceRequest.payload := io.maintenanceRequest

  io.requestReady := cache.io.requestReady
  io.responseValid := cache.io.responseValid
  io.response := cache.io.response
  io.lineReadValid := cache.io.lineReadValid
  io.lineRead := cache.io.lineRead
  io.lineReadBeatReady := cache.io.lineReadBeatReady
  io.invalidateBusy := cache.io.invalidateBusy
  io.maintenanceReady := cache.io.maintenanceRequest.ready
  io.maintenanceDone := cache.io.maintenanceDone
}

class OooL1InstructionCacheSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def sample(dut: OooL1InstructionCacheProbe): Unit = {
    dut.clockDomain.waitSampling()
    sleep(1)
  }

  private def clearInputs(dut: OooL1InstructionCacheProbe): Unit = {
    dut.io.requestValid #= false
    dut.io.request.virtualAddress #= 0
    dut.io.request.physicalAddress #= 0
    dut.io.request.uncached #= false
    dut.io.kill #= false
    dut.io.lineReadReady #= false
    dut.io.lineReadBeatValid #= false
    dut.io.lineReadBeat.mshrId #= 0
    dut.io.lineReadBeat.beat #= 0
    dut.io.lineReadBeat.data #= 0
    dut.io.lineReadBeat.last #= false
    dut.io.lineReadBeat.error #= false
    dut.io.invalidate #= false
    dut.io.maintenanceValid #= false
    dut.io.maintenanceRequest.code #= 0
    dut.io.maintenanceRequest.virtualAddress #= 0
    dut.io.maintenanceRequest.physicalAddress #= 0
    dut.io.maintenanceRequest.robPointer #= 0
    dut.io.maintenanceRequest.recoveryEpoch #= 0
  }

  private def maintain(
      dut: OooL1InstructionCacheProbe,
      code: Int,
      virtualAddress: BigInt,
      physicalAddress: BigInt
  ): Unit = {
    var cycles = 0
    while (!dut.io.maintenanceReady.toBoolean && cycles < 80) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.maintenanceReady.toBoolean)
    dut.io.maintenanceValid #= true
    dut.io.maintenanceRequest.code #= code
    dut.io.maintenanceRequest.virtualAddress #= virtualAddress
    dut.io.maintenanceRequest.physicalAddress #= physicalAddress
    sample(dut)
    dut.io.maintenanceValid #= false
    cycles = 0
    while (!dut.io.maintenanceDone.toBoolean && cycles < 16) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.maintenanceDone.toBoolean)
    sample(dut)
  }

  private def acceptRequest(
      dut: OooL1InstructionCacheProbe,
      virtualAddress: BigInt,
      physicalAddress: BigInt
  ): Unit = {
    var cycles = 0
    while (!dut.io.requestReady.toBoolean && cycles < 80) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.requestReady.toBoolean)
    dut.io.requestValid #= true
    dut.io.request.virtualAddress #= virtualAddress
    dut.io.request.physicalAddress #= physicalAddress
    sample(dut)
    dut.io.requestValid #= false
  }

  private def instructionBeat(firstInstruction: Int, beat: Int): BigInt = {
    val low = BigInt(firstInstruction + beat * 2) & BigInt("ffffffff", 16)
    val high = BigInt(firstInstruction + beat * 2 + 1) & BigInt("ffffffff", 16)
    (high << 32) | low
  }

  private def refill(
      dut: OooL1InstructionCacheProbe,
      expectedLineAddress: BigInt,
      firstInstruction: Int,
      expectedResponseFirstInstruction: Option[Int] = None
  ): Unit = {
    var cycles = 0
    while (!dut.io.lineReadValid.toBoolean && cycles < 16) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.lineReadValid.toBoolean)
    assert(dut.io.lineRead.lineAddress.toBigInt == expectedLineAddress)
    dut.io.lineReadReady #= true
    sample(dut)
    dut.io.lineReadReady #= false

    var responseCount = 0
    for (beat <- 0 until OooCacheContract.BeatsPerLine) {
      dut.io.lineReadBeatValid #= true
      dut.io.lineReadBeat.mshrId #= 0
      dut.io.lineReadBeat.beat #= beat
      dut.io.lineReadBeat.data #= instructionBeat(firstInstruction, beat)
      dut.io.lineReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
      sleep(1)
      assert(dut.io.lineReadBeatReady.toBoolean)
      sample(dut)
      if (dut.io.responseValid.toBoolean) {
        responseCount += 1
        assert(expectedResponseFirstInstruction.nonEmpty)
        for (lane <- 0 until config.fetchWidth) {
          assert(
            dut.io.response.instructions(lane).toBigInt ==
              expectedResponseFirstInstruction.get + lane
          )
        }
      }
    }
    dut.io.lineReadBeatValid #= false
    sample(dut)
    assert(responseCount == expectedResponseFirstInstruction.size)
  }

  private def expectGroup(
      dut: OooL1InstructionCacheProbe,
      virtualAddress: BigInt,
      firstInstruction: Int,
      forbidLineRead: Boolean = false,
      expectedDirectBranchTarget: Option[BigInt] = None
  ): Unit = {
    var cycles = 0
    while (!dut.io.responseValid.toBoolean && cycles < 24) {
      if (forbidLineRead) assert(!dut.io.lineReadValid.toBoolean)
      sample(dut)
      cycles += 1
    }
    assert(dut.io.responseValid.toBoolean)
    assert(dut.io.response.virtualAddress.toBigInt == virtualAddress)
    assert(!dut.io.response.error.toBoolean)
    for (lane <- 0 until config.fetchWidth) {
      assert(dut.io.response.instructions(lane).toBigInt == firstInstruction + lane)
    }
    expectedDirectBranchTarget.foreach { target =>
      assert(dut.io.response.predecode(0).valid.toBoolean)
      assert(dut.io.response.predecode(0).branchType.toBigInt == 1)
      assert(dut.io.response.predecode(0).target.toBigInt == target)
      assert(dut.io.response.predecode(0).staticTaken.toBoolean)
      assert(!dut.io.response.predecode(0).indirect.toBoolean)
    }
    sample(dut)
  }

  test("L1I refills 64-byte lines, selects fetch groups, and suppresses killed responses") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l1i")
      .compile(new OooL1InstructionCacheProbe(config))
      .doSim("ooo-l1i-refill-hit-kill", 0x4c51) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(config.instructionCache.sets + 8)
        sleep(1)
        assert(dut.io.requestReady.toBoolean)

        // A prediction correction may arrive with an already translated next-group request.
        // Accept it to keep kill out of the lookup enable, then abort before allocating a miss.
        dut.io.requestValid #= true
        dut.io.request.virtualAddress #= 0x1c000040
        dut.io.request.physicalAddress #= 0x40
        dut.io.request.uncached #= false
        dut.io.kill #= true
        sleep(1)
        assert(dut.io.requestReady.toBoolean)
        sample(dut)
        dut.io.requestValid #= false
        dut.io.kill #= false
        for (_ <- 0 until 3) {
          sample(dut)
          assert(!dut.io.responseValid.toBoolean)
          assert(!dut.io.lineReadValid.toBoolean)
        }
        assert(dut.io.requestReady.toBoolean)

        acceptRequest(dut, virtualAddress = 0x1c000130, physicalAddress = 0x130)
        refill(
          dut,
          expectedLineAddress = 0x100,
          firstInstruction = 100,
          expectedResponseFirstInstruction = Some(112)
        )

        acceptRequest(dut, virtualAddress = 0x1c000110, physicalAddress = 0x110)
        expectGroup(
          dut,
          virtualAddress = 0x1c000110,
          firstInstruction = 104,
          forbidLineRead = true
        )

        // Populate the other way of the same set with a direct branch.  A subsequent hit must
        // select the matching way's instruction and its independently predecoded branch facts.
        acceptRequest(dut, virtualAddress = 0x1c001100, physicalAddress = 0x1100)
        refill(
          dut,
          expectedLineAddress = 0x1100,
          firstInstruction = 0x50000000,
          expectedResponseFirstInstruction = Some(0x50000000)
        )
        acceptRequest(dut, virtualAddress = 0x1c001100, physicalAddress = 0x1100)
        expectGroup(
          dut,
          virtualAddress = 0x1c001100,
          firstInstruction = 0x50000000,
          forbidLineRead = true,
          expectedDirectBranchTarget = Some(0x1c001100)
        )

        acceptRequest(dut, virtualAddress = 0x1c000240, physicalAddress = 0x240)
        var cycles = 0
        while (!dut.io.lineReadValid.toBoolean && cycles < 16) {
          sample(dut)
          cycles += 1
        }
        assert(dut.io.lineReadValid.toBoolean)
        dut.io.kill #= true
        sample(dut)
        dut.io.kill #= false
        refill(dut, expectedLineAddress = 0x240, firstInstruction = 200)
        assert(!dut.io.responseValid.toBoolean)
        for (_ <- 0 until 3) {
          sample(dut)
          assert(!dut.io.responseValid.toBoolean)
        }

        acceptRequest(dut, virtualAddress = 0x1c000240, physicalAddress = 0x240)
        expectGroup(
          dut,
          virtualAddress = 0x1c000240,
          firstInstruction = 200,
          forbidLineRead = true
        )

        acceptRequest(dut, virtualAddress = 0x1c000340, physicalAddress = 0x340)
        cycles = 0
        while (!dut.io.lineReadValid.toBoolean && cycles < 16) {
          sample(dut)
          cycles += 1
        }
        assert(dut.io.lineReadValid.toBoolean)
        dut.io.invalidate #= true
        sample(dut)
        dut.io.invalidate #= false
        refill(dut, expectedLineAddress = 0x340, firstInstruction = 400)
        assert(!dut.io.responseValid.toBoolean)
        cycles = 0
        while (dut.io.invalidateBusy.toBoolean && cycles < config.instructionCache.sets + 16) {
          sample(dut)
          cycles += 1
        }
        assert(!dut.io.invalidateBusy.toBoolean)

        acceptRequest(dut, virtualAddress = 0x1c000340, physicalAddress = 0x340)
        cycles = 0
        while (!dut.io.lineReadValid.toBoolean && cycles < 16) {
          sample(dut)
          cycles += 1
        }
        assert(dut.io.lineReadValid.toBoolean)
      }
  }

  test("L1I returns the requested 16-byte group before the complete line is installed") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l1i-critical-group")
      .compile(new OooL1InstructionCacheProbe(config))
      .doSim("ooo-l1i-critical-group-first", 0x4c52) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(config.instructionCache.sets + 8)

        acceptRequest(dut, virtualAddress = 0x1c000110, physicalAddress = 0x110)
        while (!dut.io.lineReadValid.toBoolean) { sample(dut) }
        dut.io.lineReadReady #= true
        sample(dut)
        dut.io.lineReadReady #= false

        for (beat <- 0 until 4) {
          dut.io.lineReadBeatValid #= true
          dut.io.lineReadBeat.mshrId #= 0
          dut.io.lineReadBeat.beat #= beat
          dut.io.lineReadBeat.data #= instructionBeat(500, beat)
          dut.io.lineReadBeat.last #= false
          sleep(1)
          assert(dut.io.lineReadBeatReady.toBoolean)
          if (beat < 3) assert(!dut.io.responseValid.toBoolean)
          sample(dut)
        }
        dut.io.lineReadBeatValid #= false
        sleep(1)
        assert(dut.io.responseValid.toBoolean)
        assert(dut.io.response.virtualAddress.toBigInt == 0x1c000110L)
        for (lane <- 0 until config.fetchWidth) {
          assert(dut.io.response.instructions(lane).toBigInt == 504 + lane)
        }
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)
        assert(dut.io.requestReady.toBoolean)

        for (beat <- 4 until OooCacheContract.BeatsPerLine) {
          dut.io.lineReadBeatValid #= true
          dut.io.lineReadBeat.beat #= beat
          dut.io.lineReadBeat.data #= instructionBeat(500, beat)
          dut.io.lineReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
          sleep(1)
          assert(dut.io.lineReadBeatReady.toBoolean)
          assert(!dut.io.responseValid.toBoolean)
          sample(dut)
        }
        dut.io.lineReadBeatValid #= false
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)

        acceptRequest(dut, virtualAddress = 0x1c000130, physicalAddress = 0x130)
        expectGroup(
          dut,
          virtualAddress = 0x1c000130,
          firstInstruction = 512,
          forbidLineRead = true
        )
      }
  }

  test("L1I streams later fetch groups from the line being refilled") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l1i-streaming-groups")
      .compile(new OooL1InstructionCacheProbe(config))
      .doSim("ooo-l1i-streaming-groups", 0x4c53) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(config.instructionCache.sets + 8)

        val virtualBase = BigInt("1c000100", 16)
        val physicalBase = BigInt("100", 16)
        acceptRequest(dut, virtualBase, physicalBase)
        while (!dut.io.lineReadValid.toBoolean) { sample(dut) }
        dut.io.lineReadReady #= true
        sample(dut)
        dut.io.lineReadReady #= false

        for (beat <- 0 until 2) {
          dut.io.lineReadBeatValid #= true
          dut.io.lineReadBeat.beat #= beat
          dut.io.lineReadBeat.data #= instructionBeat(700, beat)
          sample(dut)
        }
        assert(dut.io.responseValid.toBoolean)
        assert(dut.io.response.virtualAddress.toBigInt == virtualBase)

        dut.io.requestValid #= true
        dut.io.request.virtualAddress #= virtualBase + 16
        dut.io.request.physicalAddress #= physicalBase + 16
        dut.io.lineReadBeat.beat #= 2
        dut.io.lineReadBeat.data #= instructionBeat(700, 2)
        sleep(1)
        assert(dut.io.requestReady.toBoolean)
        sample(dut)
        dut.io.requestValid #= false
        assert(!dut.io.responseValid.toBoolean)

        dut.io.lineReadBeat.beat #= 3
        dut.io.lineReadBeat.data #= instructionBeat(700, 3)
        sample(dut)
        assert(dut.io.responseValid.toBoolean)
        assert(dut.io.response.virtualAddress.toBigInt == virtualBase + 16)
        for (lane <- 0 until config.fetchWidth) {
          assert(dut.io.response.instructions(lane).toBigInt == 704 + lane)
        }

        dut.io.requestValid #= true
        dut.io.request.virtualAddress #= virtualBase + 64
        dut.io.request.physicalAddress #= physicalBase + 64
        sleep(1)
        assert(!dut.io.requestReady.toBoolean)
        dut.io.requestValid #= false

        for (beat <- 4 until OooCacheContract.BeatsPerLine) {
          dut.io.lineReadBeat.beat #= beat
          dut.io.lineReadBeat.data #= instructionBeat(700, beat)
          dut.io.lineReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
          sample(dut)
        }
        dut.io.lineReadBeatValid #= false
        sample(dut)
        assert(dut.io.requestReady.toBoolean)
      }
  }

  test("L1I does not install a line when any refill beat reports an error") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l1i-refill-error")
      .compile(new OooL1InstructionCacheProbe(config))
      .doSim("ooo-l1i-refill-error", 0x4c55) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(config.instructionCache.sets + 8)

        val virtualAddress = BigInt("1c000500", 16)
        val physicalAddress = BigInt(0x500)
        acceptRequest(dut, virtualAddress, physicalAddress)
        while (!dut.io.lineReadValid.toBoolean) sample(dut)
        val mshrId = dut.io.lineRead.mshrId.toBigInt
        dut.io.lineReadReady #= true
        sample(dut)
        dut.io.lineReadReady #= false

        for (beat <- 0 until OooCacheContract.BeatsPerLine) {
          dut.io.lineReadBeatValid #= true
          dut.io.lineReadBeat.mshrId #= mshrId
          dut.io.lineReadBeat.beat #= beat
          dut.io.lineReadBeat.data #= instructionBeat(900, beat)
          dut.io.lineReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
          dut.io.lineReadBeat.error #= beat == 3
          assert(dut.io.lineReadBeatReady.toBoolean)
          sample(dut)
        }
        dut.io.lineReadBeatValid #= false
        dut.io.lineReadBeat.error #= false
        sample(dut)

        acceptRequest(dut, virtualAddress, physicalAddress)
        var waitCycles = 0
        while (!dut.io.lineReadValid.toBoolean && waitCycles < 8) {
          assert(!dut.io.responseValid.toBoolean)
          sample(dut)
          waitCycles += 1
        }
        assert(dut.io.lineReadValid.toBoolean)
        assert(dut.io.lineRead.lineAddress.toBigInt == physicalAddress)
      }
  }

  test("L1I CACOP modes invalidate only the selected line") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l1i-maintenance")
      .compile(new OooL1InstructionCacheProbe(config))
      .doSim("ooo-l1i-exact-maintenance", 0x4c54) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(config.instructionCache.sets + 8)

        def install(address: BigInt, firstInstruction: Int): Unit = {
          acceptRequest(dut, address, address)
          refill(dut, address & ~BigInt(0x3f), firstInstruction, Some(firstInstruction))
        }
        def expectMissAndRefill(address: BigInt, firstInstruction: Int): Unit = {
          acceptRequest(dut, address, address)
          var cycles = 0
          while (!dut.io.lineReadValid.toBoolean && cycles < 16) {
            sample(dut)
            cycles += 1
          }
          assert(dut.io.lineReadValid.toBoolean)
          refill(dut, address & ~BigInt(0x3f), firstInstruction, Some(firstInstruction))
        }

        val setSpan = BigInt(config.instructionCache.sets * config.instructionCache.lineBytes)
        val line0 = BigInt(0x100)
        val line1 = line0 + setSpan
        val absentLine = line0 + setSpan * 2
        install(line0, 0x1000)
        install(line1, 0x2000)

        // A hit operation that misses is a side-effect-free completion.
        maintain(dut, code = 0x10, virtualAddress = absentLine, physicalAddress = absentLine)
        acceptRequest(dut, line1, line1)
        expectGroup(dut, line1, 0x2000, forbidLineRead = true)

        // Store Tag and Index select the way from VA bit zero and the set from VA index bits.
        maintain(dut, code = 0x00, virtualAddress = line0, physicalAddress = 0)
        acceptRequest(dut, line1, line1)
        expectGroup(dut, line1, 0x2000, forbidLineRead = true)
        expectMissAndRefill(line0, 0x3000)

        maintain(dut, code = 0x08, virtualAddress = line0 + 1, physicalAddress = 0)
        acceptRequest(dut, line0, line0)
        expectGroup(dut, line0, 0x3000, forbidLineRead = true)
        expectMissAndRefill(line1, 0x4000)

        maintain(dut, code = 0x10, virtualAddress = line0, physicalAddress = line0)
        acceptRequest(dut, line1, line1)
        expectGroup(dut, line1, 0x4000, forbidLineRead = true)
        expectMissAndRefill(line0, 0x5000)
      }
  }
}
