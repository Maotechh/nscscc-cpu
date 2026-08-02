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

private final case class EarlyResponse(
    valid: Boolean,
    robPointer: BigInt,
    pdst: BigInt,
    data: BigInt,
    error: Boolean
)

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

  private def startRefill(dut: OooL1DataCacheProbe, expectedAddress: BigInt): Unit = {
    dut.io.lineReadReady #= false
    var waitCycles = 0
    while (!dut.io.lineReadValid.toBoolean && waitCycles < 6) {
      sample(dut)
      waitCycles += 1
    }
    assert(dut.io.lineReadValid.toBoolean)
    assert(dut.io.lineRead.lineAddress.toBigInt == expectedAddress)
    dut.io.lineReadReady #= true
    sleep(1)
    assert(dut.io.lineReadValid.toBoolean)
    sample(dut)
    dut.io.lineReadReady #= false
  }

  private def driveBeat(
      dut: OooL1DataCacheProbe,
      beat: Int,
      data: BigInt,
      last: Boolean
  ): Unit = {
    dut.io.lineReadBeatValid #= true
    dut.io.lineReadBeat.mshrId #= 0
    dut.io.lineReadBeat.beat #= beat
    dut.io.lineReadBeat.data #= data
    dut.io.lineReadBeat.last #= last
    dut.io.lineReadBeat.error #= false
    sleep(1)
    assert(dut.io.lineReadBeatReady.toBoolean)
    sample(dut)
    dut.io.lineReadBeatValid #= false
  }

  private def captureResponse(dut: OooL1DataCacheProbe): EarlyResponse =
    EarlyResponse(
      valid = true,
      robPointer = dut.io.response.robPointer.toBigInt,
      pdst = dut.io.response.pdst.toBigInt,
      data = dut.io.response.data.toBigInt,
      error = dut.io.response.error.toBoolean
    )

  private def refillLine(
      dut: OooL1DataCacheProbe,
      expectedAddress: BigInt,
      beatData: Int => BigInt
  ): EarlyResponse = {
    startRefill(dut, expectedAddress)
    var seen = false
    var response = EarlyResponse(false, 0, 0, 0, false)
    for (beat <- 0 until OooCacheContract.BeatsPerLine) {
      driveBeat(dut, beat, beatData(beat), beat == OooCacheContract.BeatsPerLine - 1)
      if (dut.io.responseValid.toBoolean && !seen) {
        seen = true
        response = captureResponse(dut)
      }
    }
    sample(dut)
    response
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

        val early = refillLine(
          dut,
          expectedAddress = 0x100,
          beat => if (beat == 1) BigInt("1122334455667788", 16) else BigInt(beat + 1)
        )
        assert(early.valid)
        assert(early.robPointer == 3)
        assert(early.pdst == 9)
        assert(early.data == BigInt("11223344", 16))
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
          val early = refillLine(dut, address & ~BigInt(0x3f), beat => fill + beat)
          assert(early.valid)
          assert(early.robPointer == pointer)
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

  test("L1D replays a same-line load accepted during refill after its beat arrived") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l1d")
      .compile(new OooL1DataCacheProbe(config))
      .doSim("ooo-l1d-early-restart-replay", 0x4c34) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(70)
        sleep(1)

        setRequest(dut, 0x10c, isWrite = false, data = 0, mask = 0xf, robPointer = 3, pdst = 9)
        sleep(1)
        assert(dut.io.requestReady.toBoolean)
        sample(dut)
        dut.io.requestValid #= false

        startRefill(dut, 0x100)
        driveBeat(dut, 0, 1, last = false)
        driveBeat(dut, 1, BigInt("1122334455667788", 16), last = false)
        assert(dut.io.responseValid.toBoolean)
        assert(dut.io.response.robPointer.toBigInt == 3)
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)

        setRequest(dut, 0x108, isWrite = false, data = 0, mask = 0xf, robPointer = 4, pdst = 10)
        sleep(1)
        assert(dut.io.requestReady.toBoolean)
        sample(dut)
        dut.io.requestValid #= false
        sample(dut)
        assert(dut.io.responseValid.toBoolean)
        assert(dut.io.response.robPointer.toBigInt == 4)
        assert(dut.io.response.data.toBigInt == BigInt("55667788", 16))
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)

        for (beat <- 2 until OooCacheContract.BeatsPerLine) {
          driveBeat(dut, beat, beat + 0x100, last = beat == OooCacheContract.BeatsPerLine - 1)
        }
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)
      }
  }

  test("L1D early-responds a same-line load accepted mid-refill while its beat is in flight") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l1d")
      .compile(new OooL1DataCacheProbe(config))
      .doSim("ooo-l1d-early-restart-inflight", 0x4c35) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(70)
        sleep(1)

        setRequest(dut, 0x10c, isWrite = false, data = 0, mask = 0xf, robPointer = 3, pdst = 9)
        sleep(1)
        assert(dut.io.requestReady.toBoolean)
        sample(dut)
        dut.io.requestValid #= false

        startRefill(dut, 0x100)
        driveBeat(dut, 0, 1, last = false)
        driveBeat(dut, 1, BigInt("1122334455667788", 16), last = false)
        assert(dut.io.responseValid.toBoolean)
        assert(dut.io.response.robPointer.toBigInt == 3)
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)

        setRequest(dut, 0x114, isWrite = false, data = 0, mask = 0xf, robPointer = 4, pdst = 10)
        sleep(1)
        assert(dut.io.requestReady.toBoolean)
        sample(dut)
        dut.io.requestValid #= false
        assert(!dut.io.responseValid.toBoolean)

        driveBeat(dut, 2, BigInt("99aabbccddeeff00", 16), last = false)
        assert(dut.io.responseValid.toBoolean)
        assert(dut.io.response.robPointer.toBigInt == 4)
        assert(dut.io.response.data.toBigInt == BigInt("99aabbcc", 16))
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)

        for (beat <- 3 until OooCacheContract.BeatsPerLine) {
          driveBeat(dut, beat, beat + 0x200, last = beat == OooCacheContract.BeatsPerLine - 1)
        }
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)
      }
  }

  test("L1D blocks stores and different-line loads while refilling") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l1d")
      .compile(new OooL1DataCacheProbe(config))
      .doSim("ooo-l1d-early-restart-blocked", 0x4c36) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(70)
        sleep(1)

        setRequest(dut, 0x10c, isWrite = false, data = 0, mask = 0xf, robPointer = 3, pdst = 9)
        sleep(1)
        assert(dut.io.requestReady.toBoolean)
        sample(dut)
        dut.io.requestValid #= false

        startRefill(dut, 0x100)
        driveBeat(dut, 0, 1, last = false)
        driveBeat(dut, 1, BigInt("1122334455667788", 16), last = false)
        assert(dut.io.responseValid.toBoolean)
        assert(dut.io.response.robPointer.toBigInt == 3)
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)

        setRequest(dut, 0x100, isWrite = true, data = 0x1234, mask = 0xf, robPointer = 5, pdst = 0)
        sleep(1)
        assert(!dut.io.requestReady.toBoolean)
        sample(dut)
        dut.io.requestValid #= false

        setRequest(dut, 0x5000, isWrite = false, data = 0, mask = 0xf, robPointer = 6, pdst = 11)
        sleep(1)
        assert(!dut.io.requestReady.toBoolean)
        sample(dut)
        dut.io.requestValid #= false

        for (beat <- 2 until OooCacheContract.BeatsPerLine) {
          driveBeat(dut, beat, beat + 0x300, last = beat == OooCacheContract.BeatsPerLine - 1)
        }
        sample(dut)
        assert(!dut.io.responseValid.toBoolean)
      }
  }
}
