package openla500.memory

import openla500.core._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OooL1DataCacheProbe(config: OooCoreConfig) extends Component {
  val io = new Bundle {
    val requestValid = in Bool ()
    val request = in(OooCacheRequest(config))
    val requestReady = out Bool ()
    val responseValid = out Bool ()
    val response = out(OooCacheResponse(config))
    val lineReadValid = out Bool ()
    val lineRead = out(OooLineReadRequest(config))
    val lineReadReady = in Bool ()
    val lineReadBeatValid = in Bool ()
    val lineReadBeat = in(OooLineReadBeat(config))
    val lineReadBeatReady = out Bool ()
    val lineWriteValid = out Bool ()
    val lineWrite = out(OooLineWriteRequest(config))
    val lineWriteReady = in Bool ()
    val invalidate = in Bool ()
    val invalidateBusy = out Bool ()
  }
  noIoPrefix()

  val cache = new OooL1DataCache(config)
  cache.io.requestValid := io.requestValid
  cache.io.request := io.request
  cache.io.lineReadReady := io.lineReadReady
  cache.io.lineReadBeatValid := io.lineReadBeatValid
  cache.io.lineReadBeat := io.lineReadBeat
  cache.io.lineWriteReady := io.lineWriteReady
  cache.io.invalidate := io.invalidate
  cache.io.writebackInvalidate := False

  io.requestReady := cache.io.requestReady
  io.responseValid := cache.io.responseValid
  io.response := cache.io.response
  io.lineReadValid := cache.io.lineReadValid
  io.lineRead := cache.io.lineRead
  io.lineReadBeatReady := cache.io.lineReadBeatReady
  io.lineWriteValid := cache.io.lineWriteValid
  io.lineWrite := cache.io.lineWrite
  io.invalidateBusy := cache.io.invalidateBusy
}

class OooL1DataCacheSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def clearInputs(dut: OooL1DataCacheProbe): Unit = {
    dut.io.requestValid #= false
    dut.io.request.virtualAddress #= 0
    dut.io.request.physicalAddress #= 0
    dut.io.request.isWrite #= false
    dut.io.request.size #= 2
    dut.io.request.byteMask #= 0xf
    dut.io.request.writeData #= 0
    dut.io.request.uncached #= false
    dut.io.request.robPointer #= 0
    dut.io.request.pdst #= 0
    dut.io.lineReadReady #= false
    dut.io.lineReadBeatValid #= false
    dut.io.lineReadBeat.mshrId #= 0
    dut.io.lineReadBeat.beat #= 0
    dut.io.lineReadBeat.data #= 0
    dut.io.lineReadBeat.last #= false
    dut.io.lineReadBeat.error #= false
    dut.io.lineWriteReady #= false
    dut.io.invalidate #= false
  }

  private def sample(dut: OooL1DataCacheProbe): Unit = {
    dut.clockDomain.waitSampling()
    sleep(1)
  }

  private def setRequest(
      dut: OooL1DataCacheProbe,
      address: BigInt,
      isWrite: Boolean,
      data: BigInt,
      mask: BigInt,
      robPointer: BigInt,
      pdst: BigInt
  ): Unit = {
    dut.io.requestValid #= true
    dut.io.request.virtualAddress #= address
    dut.io.request.physicalAddress #= address
    dut.io.request.isWrite #= isWrite
    dut.io.request.size #= 2
    dut.io.request.byteMask #= mask
    dut.io.request.writeData #= data
    dut.io.request.uncached #= false
    dut.io.request.robPointer #= robPointer
    dut.io.request.pdst #= pdst
  }

  private def refillLine(
      dut: OooL1DataCacheProbe,
      expectedAddress: BigInt,
      beatData: Int => BigInt
  ): Unit = {
    dut.io.lineReadReady #= false
    var waitCycles = 0
    while (!dut.io.lineReadValid.toBoolean && waitCycles < 6) {
      sample(dut)
      waitCycles += 1
    }
    assert(dut.io.lineReadValid.toBoolean)
    val address = dut.io.lineRead.lineAddress.toBigInt
    assert(address == expectedAddress)
    dut.io.lineReadReady #= true
    sleep(1)
    assert(dut.io.lineReadValid.toBoolean)
    sample(dut)
    dut.io.lineReadReady #= false

    for (beat <- 0 until OooCacheContract.BeatsPerLine) {
      dut.io.lineReadBeatValid #= true
      dut.io.lineReadBeat.mshrId #= 0
      dut.io.lineReadBeat.beat #= beat
      dut.io.lineReadBeat.data #= beatData(beat)
      dut.io.lineReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
      dut.io.lineReadBeat.error #= false
      sleep(1)
      assert(dut.io.lineReadBeatReady.toBoolean)
      sample(dut)
    }
    dut.io.lineReadBeatValid #= false
    sample(dut)
  }

  test("L1D invalidates, refills eight beats, hits, and merges byte stores") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l1d")
      .compile(new OooL1DataCacheProbe(config))
      .doSim("ooo-l1d-refill-hit-merge", 0x4c31) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        assert(dut.io.invalidateBusy.toBoolean)
        dut.clockDomain.waitSampling(70)
        sleep(1)
        assert(!dut.io.invalidateBusy.toBoolean)
        assert(dut.io.requestReady.toBoolean)

        setRequest(dut, 0x10c, isWrite = false, data = 0, mask = 0xf, robPointer = 3, pdst = 9)
        sleep(1)
        assert(dut.io.requestReady.toBoolean)
        sample(dut)
        dut.io.requestValid #= false
        assert(!dut.io.lineReadValid.toBoolean)

        refillLine(
          dut,
          expectedAddress = 0x100,
          beat => if (beat == 1) BigInt("1122334455667788", 16) else BigInt(beat + 1)
        )
        assert(dut.io.responseValid.toBoolean)
        assert(dut.io.response.robPointer.toBigInt == 3)
        assert(dut.io.response.pdst.toBigInt == 9)
        assert(dut.io.response.data.toBigInt == BigInt("11223344", 16))
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)

        setRequest(dut, 0x10c, isWrite = false, data = 0, mask = 0xf, robPointer = 4, pdst = 10)
        sample(dut)
        dut.io.requestValid #= false
        sample(dut)
        assert(!dut.io.lineReadValid.toBoolean)
        assert(dut.io.responseValid.toBoolean)
        assert(dut.io.response.data.toBigInt == BigInt("11223344", 16))
        sample(dut)

        setRequest(
          dut,
          0x10c,
          isWrite = true,
          data = BigInt("aabbccdd", 16),
          mask = 0x5,
          robPointer = 5,
          pdst = 0
        )
        sample(dut)
        dut.io.requestValid #= false
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)

        setRequest(dut, 0x10c, isWrite = false, data = 0, mask = 0xf, robPointer = 6, pdst = 11)
        sample(dut)
        dut.io.requestValid #= false
        sample(dut)
        assert(dut.io.responseValid.toBoolean)
        assert(dut.io.response.data.toBigInt == BigInt("11bb33dd", 16))
      }
  }

  test("L1D line read request remains stable until lower-level acceptance") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l1d")
      .compile(new OooL1DataCacheProbe(config))
      .doSim("ooo-l1d-read-backpressure", 0x4c32) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(70)

        setRequest(dut, 0x240, isWrite = false, data = 0, mask = 0xf, robPointer = 1, pdst = 2)
        sample(dut)
        dut.io.requestValid #= false
        dut.clockDomain.waitSampling(2)
        sleep(1)
        assert(dut.io.lineReadValid.toBoolean)
        val heldAddress = dut.io.lineRead.lineAddress.toBigInt
        for (_ <- 0 until 3) {
          sample(dut)
          assert(dut.io.lineReadValid.toBoolean)
          assert(dut.io.lineRead.lineAddress.toBigInt == heldAddress)
          assert(!dut.io.lineWriteValid.toBoolean)
        }
      }
  }

  test("L1D writes a dirty 64-byte victim before refilling its replacement") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l1d")
      .compile(new OooL1DataCacheProbe(config))
      .doSim("ooo-l1d-dirty-writeback", 0x4c33) { dut =>
        def loadMiss(address: BigInt, fill: BigInt, pointer: BigInt): Unit = {
          setRequest(
            dut,
            address,
            isWrite = false,
            data = 0,
            mask = 0xf,
            robPointer = pointer,
            pdst = 3
          )
          sleep(1)
          assert(dut.io.requestReady.toBoolean)
          sample(dut)
          dut.io.requestValid #= false
          refillLine(dut, address & ~BigInt(0x3f), beat => fill + beat)
          assert(dut.io.responseValid.toBoolean)
          sample(dut)
        }

        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(70)
        sleep(1)

        loadMiss(0x100, BigInt("1000000000000000", 16), 1)
        loadMiss(0x1100, BigInt("2000000000000000", 16), 2)

        setRequest(
          dut,
          0x100,
          isWrite = true,
          data = BigInt("deadbeef", 16),
          mask = 0xf,
          robPointer = 3,
          pdst = 0
        )
        sample(dut)
        dut.io.requestValid #= false
        sample(dut)
        assert(!dut.io.lineWriteValid.toBoolean)

        loadMiss(0x2100, BigInt("3000000000000000", 16), 4)

        setRequest(dut, 0x3100, isWrite = false, data = 0, mask = 0xf, robPointer = 5, pdst = 4)
        sample(dut)
        dut.io.requestValid #= false
        var waitCycles = 0
        while (!dut.io.lineWriteValid.toBoolean && waitCycles < 6) {
          sample(dut)
          waitCycles += 1
        }
        assert(dut.io.lineWriteValid.toBoolean)
        assert(dut.io.lineWrite.lineAddress.toBigInt == 0x100)
        assert((dut.io.lineWrite.data.toBigInt & BigInt("ffffffff", 16)) == BigInt("deadbeef", 16))

        val heldData = dut.io.lineWrite.data.toBigInt
        for (_ <- 0 until 3) {
          sample(dut)
          assert(dut.io.lineWriteValid.toBoolean)
          assert(dut.io.lineWrite.lineAddress.toBigInt == 0x100)
          assert(dut.io.lineWrite.data.toBigInt == heldData)
        }

        dut.io.lineWriteReady #= true
        sample(dut)
        dut.io.lineWriteReady #= false
        assert(dut.io.lineReadValid.toBoolean)
        assert(dut.io.lineRead.lineAddress.toBigInt == 0x3100)
      }
  }
}
