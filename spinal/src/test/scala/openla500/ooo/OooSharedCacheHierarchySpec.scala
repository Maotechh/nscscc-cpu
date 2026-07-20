package openla500.ooo

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
    val invalidateBusy = out Bool ()
  }
  noIoPrefix()

  val hierarchy = new OooSharedCacheHierarchy(config)
  hierarchy.io.instructionRequestValid := io.instructionRequestValid
  hierarchy.io.instructionRequest := io.instructionRequest
  hierarchy.io.instructionKill := io.instructionKill
  hierarchy.io.dataRequestValid := io.dataRequestValid
  hierarchy.io.dataRequest := io.dataRequest
  hierarchy.io.memoryReadReady := io.memoryReadReady
  hierarchy.io.memoryReadBeatValid := io.memoryReadBeatValid
  hierarchy.io.memoryReadBeat := io.memoryReadBeat
  hierarchy.io.memoryWriteReady := io.memoryWriteReady
  hierarchy.io.invalidate := io.invalidate

  io.instructionRequestReady := hierarchy.io.instructionRequestReady
  io.instructionResponseValid := hierarchy.io.instructionResponseValid
  io.instructionResponse := hierarchy.io.instructionResponse
  io.dataRequestReady := hierarchy.io.dataRequestReady
  io.dataResponseValid := hierarchy.io.dataResponseValid
  io.dataResponse := hierarchy.io.dataResponse
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
    dut.io.memoryReadReady #= false
    dut.io.memoryReadBeatValid #= false
    dut.io.memoryReadBeat.mshrId #= 0
    dut.io.memoryReadBeat.beat #= 0
    dut.io.memoryReadBeat.data #= 0
    dut.io.memoryReadBeat.last #= false
    dut.io.memoryReadBeat.error #= false
    dut.io.memoryWriteReady #= false
    dut.io.invalidate #= false
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

        for (beat <- 0 until OooCacheContract.BeatsPerLine) {
          dut.io.memoryReadBeatValid #= true
          dut.io.memoryReadBeat.mshrId #= 0
          dut.io.memoryReadBeat.beat #= beat
          dut.io.memoryReadBeat.data #= instructionBeat(300, beat)
          dut.io.memoryReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
          sleep(1)
          assert(dut.io.memoryReadBeatReady.toBoolean)
          sample(dut)
        }
        dut.io.memoryReadBeatValid #= false

        var sawInstruction = false
        var sawData = false
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
      }
  }
}
