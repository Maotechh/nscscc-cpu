package openla500.memory

import openla500.core._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OooSharedCacheHierarchyProbe(config: OooCoreConfig) extends Component {
  val io = new Bundle {
    val instructionRequestValid = in Bool ()
    val instructionRequest = in(OooInstructionCacheRequest(config))
    val instructionRequestReady = out Bool ()
    val instructionResponseValid = out Bool ()
    val instructionResponse = out(OooInstructionCacheResponse(config))
    val instructionKill = in Bool ()
    val dataRequestValid = in Bool ()
    val dataRequest = in(OooCacheRequest(config))
    val dataRequestReady = out Bool ()
    val dataResponseValid = out Bool ()
    val dataResponse = out(OooCacheResponse(config))
    val uncachedInstructionRequestValid = out Bool ()
    val uncachedInstructionRequest = out(OooInstructionCacheRequest(config))
    val uncachedInstructionRequestReady = in Bool ()
    val uncachedInstructionResponseValid = in Bool ()
    val uncachedInstructionResponse = in(OooInstructionCacheResponse(config))
    val uncachedDataRequestValid = out Bool ()
    val uncachedDataRequest = out(OooCacheRequest(config))
    val uncachedDataRequestReady = in Bool ()
    val uncachedDataResponseValid = in Bool ()
    val uncachedDataResponse = in(OooCacheResponse(config))
    val memoryReadValid = out Bool ()
    val memoryRead = out(OooLineReadRequest(config))
    val memoryReadReady = in Bool ()
    val memoryReadBeatValid = in Bool ()
    val memoryReadBeat = in(OooLineReadBeat(config))
    val memoryReadBeatReady = out Bool ()
    val memoryWriteValid = out Bool ()
    val memoryWrite = out(OooLineWriteRequest(config))
    val memoryWriteReady = in Bool ()
    val invalidate = in Bool ()
    val dataInvalidate = in Bool ()
    val dataWritebackInvalidate = in Bool ()
    val level2Invalidate = in Bool ()
    val invalidateBusy = out Bool ()
  }
  noIoPrefix()

  val hierarchy = new OooSharedCacheHierarchy(config)
  hierarchy.io.instructionRequestValid := io.instructionRequestValid
  hierarchy.io.instructionRequest := io.instructionRequest
  hierarchy.io.instructionKill := io.instructionKill
  hierarchy.io.dataRequestValid := io.dataRequestValid
  hierarchy.io.dataRequest := io.dataRequest
  hierarchy.io.uncachedInstructionRequestReady := io.uncachedInstructionRequestReady
  hierarchy.io.uncachedInstructionResponseValid := io.uncachedInstructionResponseValid
  hierarchy.io.uncachedInstructionResponse := io.uncachedInstructionResponse
  hierarchy.io.uncachedDataRequestReady := io.uncachedDataRequestReady
  hierarchy.io.uncachedDataResponseValid := io.uncachedDataResponseValid
  hierarchy.io.uncachedDataResponse := io.uncachedDataResponse
  hierarchy.io.memoryReadReady := io.memoryReadReady
  hierarchy.io.memoryReadBeatValid := io.memoryReadBeatValid
  hierarchy.io.memoryReadBeat := io.memoryReadBeat
  hierarchy.io.memoryWriteReady := io.memoryWriteReady
  hierarchy.io.invalidate := io.invalidate
  hierarchy.io.dataInvalidate := io.dataInvalidate
  hierarchy.io.dataWritebackInvalidate := io.dataWritebackInvalidate
  hierarchy.io.level2Invalidate := io.level2Invalidate

  io.instructionRequestReady := hierarchy.io.instructionRequestReady
  io.instructionResponseValid := hierarchy.io.instructionResponseValid
  io.instructionResponse := hierarchy.io.instructionResponse
  io.dataRequestReady := hierarchy.io.dataRequestReady
  io.dataResponseValid := hierarchy.io.dataResponseValid
  io.dataResponse := hierarchy.io.dataResponse
  io.uncachedInstructionRequestValid := hierarchy.io.uncachedInstructionRequestValid
  io.uncachedInstructionRequest := hierarchy.io.uncachedInstructionRequest
  io.uncachedDataRequestValid := hierarchy.io.uncachedDataRequestValid
  io.uncachedDataRequest := hierarchy.io.uncachedDataRequest
  io.memoryReadValid := hierarchy.io.memoryReadValid
  io.memoryRead := hierarchy.io.memoryRead
  io.memoryReadBeatReady := hierarchy.io.memoryReadBeatReady
  io.memoryWriteValid := hierarchy.io.memoryWriteValid
  io.memoryWrite := hierarchy.io.memoryWrite
  io.invalidateBusy := hierarchy.io.invalidateBusy
}

class OooSharedCacheHierarchySpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def sample(dut: OooSharedCacheHierarchyProbe): Unit = {
    dut.clockDomain.waitSampling()
    sleep(1)
  }

  private def clearInputs(dut: OooSharedCacheHierarchyProbe): Unit = {
    dut.io.instructionRequestValid #= false
    dut.io.instructionRequest.virtualAddress #= 0
    dut.io.instructionRequest.physicalAddress #= 0
    dut.io.instructionRequest.uncached #= false
    dut.io.instructionKill #= false
    dut.io.dataRequestValid #= false
    dut.io.dataRequest.virtualAddress #= 0
    dut.io.dataRequest.physicalAddress #= 0
    dut.io.dataRequest.isWrite #= false
    dut.io.dataRequest.size #= 2
    dut.io.dataRequest.byteMask #= 0xf
    dut.io.dataRequest.writeData #= 0
    dut.io.dataRequest.uncached #= false
    dut.io.dataRequest.robPointer #= 0
    dut.io.dataRequest.pdst #= 0
    dut.io.uncachedInstructionRequestReady #= false
    dut.io.uncachedInstructionResponseValid #= false
    dut.io.uncachedInstructionResponse.virtualAddress #= 0
    dut.io.uncachedInstructionResponse.physicalAddress #= 0
    dut.io.uncachedInstructionResponse.error #= false
    for (lane <- 0 until config.fetchWidth) {
      dut.io.uncachedInstructionResponse.instructions(lane) #= 0
    }
    dut.io.uncachedDataRequestReady #= false
    dut.io.uncachedDataResponseValid #= false
    dut.io.uncachedDataResponse.robPointer #= 0
    dut.io.uncachedDataResponse.pdst #= 0
    dut.io.uncachedDataResponse.data #= 0
    dut.io.uncachedDataResponse.error #= false
    dut.io.memoryReadReady #= false
    dut.io.memoryReadBeatValid #= false
    dut.io.memoryReadBeat.mshrId #= 0
    dut.io.memoryReadBeat.beat #= 0
    dut.io.memoryReadBeat.data #= 0
    dut.io.memoryReadBeat.last #= false
    dut.io.memoryReadBeat.error #= false
    dut.io.memoryWriteReady #= false
    dut.io.invalidate #= false
    dut.io.dataInvalidate #= false
    dut.io.dataWritebackInvalidate #= false
    dut.io.level2Invalidate #= false
  }

  private def instructionBeat(firstInstruction: Int, beat: Int): BigInt = {
    val low = BigInt(firstInstruction + beat * 2) & BigInt("ffffffff", 16)
    val high = BigInt(firstInstruction + beat * 2 + 1) & BigInt("ffffffff", 16)
    (high << 32) | low
  }

  test("simultaneous L1I and L1D misses share one L2 refill without cross-routing") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-shared-cache")
      .compile(new OooSharedCacheHierarchyProbe(config))
      .doSim("ooo-shared-cache-same-line", 0x4c52) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()

        var initCycles = 0
        while (dut.io.invalidateBusy.toBoolean && initCycles < config.level2Cache.sets + 16) {
          sample(dut)
          initCycles += 1
        }
        assert(!dut.io.invalidateBusy.toBoolean)
        assert(dut.io.instructionRequestReady.toBoolean)
        assert(dut.io.dataRequestReady.toBoolean)

        dut.io.instructionRequestValid #= true
        dut.io.instructionRequest.virtualAddress #= BigInt("1c000410", 16)
        dut.io.instructionRequest.physicalAddress #= 0x410
        dut.io.dataRequestValid #= true
        dut.io.dataRequest.virtualAddress #= 0x408
        dut.io.dataRequest.physicalAddress #= 0x408
        dut.io.dataRequest.isWrite #= false
        dut.io.dataRequest.robPointer #= 5
        dut.io.dataRequest.pdst #= 9
        sample(dut)
        dut.io.instructionRequestValid #= false
        dut.io.dataRequestValid #= false

        var waitCycles = 0
        while (!dut.io.memoryReadValid.toBoolean && waitCycles < 32) {
          sample(dut)
          waitCycles += 1
        }
        assert(dut.io.memoryReadValid.toBoolean)
        assert(dut.io.memoryRead.lineAddress.toBigInt == 0x400)
        dut.io.memoryReadReady #= true
        sample(dut)
        dut.io.memoryReadReady #= false

        var sawInstruction = false
        var sawData = false
        for (beat <- 0 until OooCacheContract.BeatsPerLine) {
          dut.io.memoryReadBeatValid #= true
          dut.io.memoryReadBeat.mshrId #= 0
          dut.io.memoryReadBeat.beat #= beat
          dut.io.memoryReadBeat.data #= instructionBeat(300, beat)
          dut.io.memoryReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
          sleep(1)
          assert(dut.io.memoryReadBeatReady.toBoolean)
          sample(dut)
          if (dut.io.instructionResponseValid.toBoolean) {
            assert(!sawInstruction)
            assert(dut.io.instructionResponse.virtualAddress.toBigInt == BigInt("1c000410", 16))
            for (lane <- 0 until config.fetchWidth) {
              assert(dut.io.instructionResponse.instructions(lane).toBigInt == 304 + lane)
            }
            sawInstruction = true
          }
          if (dut.io.dataResponseValid.toBoolean) {
            assert(!sawData)
            assert(dut.io.dataResponse.robPointer.toBigInt == 5)
            assert(dut.io.dataResponse.pdst.toBigInt == 9)
            assert(dut.io.dataResponse.data.toBigInt == 302)
            sawData = true
          }
        }
        dut.io.memoryReadBeatValid #= false

        var drainCycles = 0
        while (!(sawInstruction && sawData) && drainCycles < 64) {
          assert(!dut.io.memoryReadValid.toBoolean)
          assert(!dut.io.memoryWriteValid.toBoolean)
          if (dut.io.instructionResponseValid.toBoolean) {
            assert(!sawInstruction)
            assert(dut.io.instructionResponse.virtualAddress.toBigInt == BigInt("1c000410", 16))
            for (lane <- 0 until config.fetchWidth) {
              assert(dut.io.instructionResponse.instructions(lane).toBigInt == 304 + lane)
            }
            sawInstruction = true
          }
          if (dut.io.dataResponseValid.toBoolean) {
            assert(!sawData)
            assert(dut.io.dataResponse.robPointer.toBigInt == 5)
            assert(dut.io.dataResponse.pdst.toBigInt == 9)
            assert(dut.io.dataResponse.data.toBigInt == 302)
            sawData = true
          }
          sample(dut)
          drainCycles += 1
        }
        assert(sawInstruction)
        assert(sawData)

        dut.io.invalidate #= true
        sample(dut)
        dut.io.invalidate #= false
        var invalidateCycles = 0
        while (dut.io.invalidateBusy.toBoolean && invalidateCycles < config.level2Cache.sets + 16) {
          sample(dut)
          invalidateCycles += 1
        }
        assert(!dut.io.invalidateBusy.toBoolean)

        // I-cache maintenance keeps the private data copy but removes the shared instruction copy.
        dut.io.dataRequestValid #= true
        dut.io.dataRequest.virtualAddress #= 0x408
        dut.io.dataRequest.physicalAddress #= 0x408
        while (!dut.io.dataRequestReady.toBoolean) { sample(dut) }
        sample(dut)
        dut.io.dataRequestValid #= false
        var dataHit = false
        var dataHitCycles = 0
        while (!dataHit && dataHitCycles < 16) {
          assert(!dut.io.memoryReadValid.toBoolean)
          dataHit = dut.io.dataResponseValid.toBoolean
          if (!dataHit) sample(dut)
          dataHitCycles += 1
        }
        assert(dataHit)
        assert(dut.io.dataResponse.data.toBigInt == 302)

        dut.io.instructionRequestValid #= true
        dut.io.instructionRequest.virtualAddress #= BigInt("1c000410", 16)
        dut.io.instructionRequest.physicalAddress #= 0x410
        while (!dut.io.instructionRequestReady.toBoolean) { sample(dut) }
        sample(dut)
        dut.io.instructionRequestValid #= false
        var refillWait = 0
        while (!dut.io.memoryReadValid.toBoolean && refillWait < 32) {
          sample(dut)
          refillWait += 1
        }
        assert(dut.io.memoryReadValid.toBoolean)
        assert(dut.io.memoryRead.lineAddress.toBigInt == 0x400)
        dut.io.memoryReadReady #= true
        sample(dut)
        dut.io.memoryReadReady #= false
        var instructionRefill = false
        for (beat <- 0 until OooCacheContract.BeatsPerLine) {
          dut.io.memoryReadBeatValid #= true
          dut.io.memoryReadBeat.mshrId #= 0
          dut.io.memoryReadBeat.beat #= beat
          dut.io.memoryReadBeat.data #= instructionBeat(400, beat)
          dut.io.memoryReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
          sleep(1)
          assert(dut.io.memoryReadBeatReady.toBoolean)
          sample(dut)
          if (dut.io.instructionResponseValid.toBoolean) {
            assert(!instructionRefill)
            for (lane <- 0 until config.fetchWidth) {
              assert(dut.io.instructionResponse.instructions(lane).toBigInt == 404 + lane)
            }
            instructionRefill = true
          }
        }
        dut.io.memoryReadBeatValid #= false

        var instructionRefillCycles = 0
        while (!instructionRefill && instructionRefillCycles < 64) {
          instructionRefill = dut.io.instructionResponseValid.toBoolean
          if (instructionRefill) {
            for (lane <- 0 until config.fetchWidth) {
              assert(dut.io.instructionResponse.instructions(lane).toBigInt == 404 + lane)
            }
          }
          if (!instructionRefill) sample(dut)
          instructionRefillCycles += 1
        }
        assert(instructionRefill)
      }
  }

  test("uncached instruction and data requests bypass L1 and L2") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-shared-cache")
      .compile(new OooSharedCacheHierarchyProbe(config))
      .doSim("ooo-shared-cache-uncached-bypass", 0x4c53) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(config.level2Cache.sets + 8)
        sleep(1)

        dut.io.instructionRequestValid #= true
        dut.io.instructionRequest.virtualAddress #= BigInt("1c00100c", 16)
        dut.io.instructionRequest.physicalAddress #= 0x100c
        dut.io.instructionRequest.uncached #= true
        dut.io.uncachedInstructionRequestReady #= true
        sleep(1)
        assert(dut.io.instructionRequestReady.toBoolean)
        assert(dut.io.uncachedInstructionRequestValid.toBoolean)
        assert(dut.io.uncachedInstructionRequest.physicalAddress.toBigInt == 0x100c)
        assert(!dut.io.memoryReadValid.toBoolean)
        sample(dut)
        dut.io.instructionRequestValid #= false
        dut.io.uncachedInstructionRequestReady #= false

        dut.io.uncachedInstructionResponseValid #= true
        dut.io.uncachedInstructionResponse.virtualAddress #= BigInt("1c00100c", 16)
        dut.io.uncachedInstructionResponse.physicalAddress #= 0x100c
        for (lane <- 0 until config.fetchWidth) {
          dut.io.uncachedInstructionResponse.instructions(lane) #= 0x700 + lane
        }
        sleep(1)
        assert(dut.io.instructionResponseValid.toBoolean)
        assert(dut.io.instructionResponse.instructions(3).toBigInt == 0x703)
        sample(dut)
        dut.io.uncachedInstructionResponseValid #= false

        dut.io.dataRequestValid #= true
        dut.io.dataRequest.virtualAddress #= BigInt("bfe00104", 16)
        dut.io.dataRequest.physicalAddress #= BigInt("1fe00104", 16)
        dut.io.dataRequest.uncached #= true
        dut.io.dataRequest.robPointer #= 9
        dut.io.dataRequest.pdst #= 13
        dut.io.uncachedDataRequestReady #= true
        sleep(1)
        assert(dut.io.dataRequestReady.toBoolean)
        assert(dut.io.uncachedDataRequestValid.toBoolean)
        assert(dut.io.uncachedDataRequest.physicalAddress.toBigInt == BigInt("1fe00104", 16))
        assert(!dut.io.memoryReadValid.toBoolean)
        sample(dut)
        dut.io.dataRequestValid #= false
        dut.io.uncachedDataRequestReady #= false

        dut.io.uncachedDataResponseValid #= true
        dut.io.uncachedDataResponse.robPointer #= 9
        dut.io.uncachedDataResponse.pdst #= 13
        dut.io.uncachedDataResponse.data #= BigInt("89abcdef", 16)
        sleep(1)
        assert(dut.io.dataResponseValid.toBoolean)
        assert(dut.io.dataResponse.data.toBigInt == BigInt("89abcdef", 16))
      }
  }
}
