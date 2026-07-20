package openla500.ooo

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

  io.requestReady := cache.io.requestReady
  io.responseValid := cache.io.responseValid
  io.response := cache.io.response
  io.lineReadValid := cache.io.lineReadValid
  io.lineRead := cache.io.lineRead
  io.lineReadBeatReady := cache.io.lineReadBeatReady
  io.invalidateBusy := cache.io.invalidateBusy
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
    dut.io.kill #= false
    dut.io.lineReadReady #= false
    dut.io.lineReadBeatValid #= false
    dut.io.lineReadBeat.mshrId #= 0
    dut.io.lineReadBeat.beat #= 0
    dut.io.lineReadBeat.data #= 0
    dut.io.lineReadBeat.last #= false
    dut.io.lineReadBeat.error #= false
    dut.io.invalidate #= false
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
      firstInstruction: Int
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

    for (beat <- 0 until OooCacheContract.BeatsPerLine) {
      dut.io.lineReadBeatValid #= true
      dut.io.lineReadBeat.mshrId #= 0
      dut.io.lineReadBeat.beat #= beat
      dut.io.lineReadBeat.data #= instructionBeat(firstInstruction, beat)
      dut.io.lineReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
      sleep(1)
      assert(dut.io.lineReadBeatReady.toBoolean)
      sample(dut)
    }
    dut.io.lineReadBeatValid #= false
    sample(dut)
  }

  private def expectGroup(
      dut: OooL1InstructionCacheProbe,
      virtualAddress: BigInt,
      firstInstruction: Int,
      forbidLineRead: Boolean = false
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

        acceptRequest(dut, virtualAddress = 0x1c000130, physicalAddress = 0x130)
        refill(dut, expectedLineAddress = 0x100, firstInstruction = 100)
        expectGroup(dut, virtualAddress = 0x1c000130, firstInstruction = 112)

        acceptRequest(dut, virtualAddress = 0x1c000110, physicalAddress = 0x110)
        expectGroup(
          dut,
          virtualAddress = 0x1c000110,
          firstInstruction = 104,
          forbidLineRead = true
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
}
