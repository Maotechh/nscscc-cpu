package openla500.ooo

import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OooDataCacheHierarchyProbe(config: OooCoreConfig) extends Component {
  val io = new Bundle {
    val requestValid = in Bool ()
    val request = in(OooCacheRequest(config))
    val requestReady = out Bool ()
    val responseValid = out Bool ()
    val response = out(OooCacheResponse(config))
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

  val hierarchy = new OooDataCacheHierarchy(config)
  hierarchy.io.requestValid := io.requestValid
  hierarchy.io.request := io.request
  hierarchy.io.memoryReadReady := io.memoryReadReady
  hierarchy.io.memoryReadBeatValid := io.memoryReadBeatValid
  hierarchy.io.memoryReadBeat := io.memoryReadBeat
  hierarchy.io.memoryWriteReady := io.memoryWriteReady
  hierarchy.io.invalidate := io.invalidate

  io.requestReady := hierarchy.io.requestReady
  io.responseValid := hierarchy.io.responseValid
  io.response := hierarchy.io.response
  io.memoryReadValid := hierarchy.io.memoryReadValid
  io.memoryRead := hierarchy.io.memoryRead
  io.memoryReadBeatReady := hierarchy.io.memoryReadBeatReady
  io.memoryWriteValid := hierarchy.io.memoryWriteValid
  io.memoryWrite := hierarchy.io.memoryWrite
  io.invalidateBusy := hierarchy.io.invalidateBusy
}

class OooDataCacheHierarchySpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def sample(dut: OooDataCacheHierarchyProbe): Unit = {
    dut.clockDomain.waitSampling()
    sleep(1)
  }

  private def clearInputs(dut: OooDataCacheHierarchyProbe): Unit = {
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

  private def waitForInitialization(dut: OooDataCacheHierarchyProbe): Unit = {
    var cycles = 0
    while (dut.io.invalidateBusy.toBoolean && cycles < config.level2Cache.sets + 16) {
      sample(dut)
      cycles += 1
    }
    assert(!dut.io.invalidateBusy.toBoolean)
    assert(dut.io.requestReady.toBoolean)
  }

  private def acceptRequest(
      dut: OooDataCacheHierarchyProbe,
      address: BigInt,
      isWrite: Boolean,
      data: BigInt,
      mask: BigInt,
      robPointer: BigInt,
      pdst: BigInt
  ): Unit = {
    var cycles = 0
    while (!dut.io.requestReady.toBoolean && cycles < 40) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.requestReady.toBoolean)
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
    sleep(1)
    assert(dut.io.requestReady.toBoolean)
    sample(dut)
    dut.io.requestValid #= false
  }

  private def serviceMemoryRefill(
      dut: OooDataCacheHierarchyProbe,
      expectedAddress: BigInt,
      beatData: Int => BigInt
  ): Unit = {
    var cycles = 0
    while (!dut.io.memoryReadValid.toBoolean && cycles < 30) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.memoryReadValid.toBoolean)
    assert(dut.io.memoryRead.lineAddress.toBigInt == expectedAddress)
    assert(dut.io.memoryRead.mshrId.toBigInt == 0)

    for (_ <- 0 until 2) {
      sample(dut)
      assert(dut.io.memoryReadValid.toBoolean)
      assert(dut.io.memoryRead.lineAddress.toBigInt == expectedAddress)
    }

    dut.io.memoryReadReady #= true
    sample(dut)
    dut.io.memoryReadReady #= false

    for (beat <- 0 until OooCacheContract.BeatsPerLine) {
      dut.io.memoryReadBeatValid #= true
      dut.io.memoryReadBeat.mshrId #= 0
      dut.io.memoryReadBeat.beat #= beat
      dut.io.memoryReadBeat.data #= beatData(beat)
      dut.io.memoryReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
      dut.io.memoryReadBeat.error #= false
      sleep(1)
      assert(dut.io.memoryReadBeatReady.toBoolean)
      sample(dut)
    }
    dut.io.memoryReadBeatValid #= false
  }

  private def expectResponse(
      dut: OooDataCacheHierarchyProbe,
      data: BigInt,
      robPointer: BigInt,
      pdst: BigInt,
      forbidMemoryRead: Boolean = false
  ): Unit = {
    var cycles = 0
    while (!dut.io.responseValid.toBoolean && cycles < 40) {
      if (forbidMemoryRead) assert(!dut.io.memoryReadValid.toBoolean)
      sample(dut)
      cycles += 1
    }
    assert(dut.io.responseValid.toBoolean)
    assert(dut.io.response.data.toBigInt == data)
    assert(dut.io.response.robPointer.toBigInt == robPointer)
    assert(dut.io.response.pdst.toBigInt == pdst)
    assert(!dut.io.response.error.toBoolean)
    if (forbidMemoryRead) assert(!dut.io.memoryReadValid.toBoolean)
    sample(dut)
  }

  private def loadFromMemory(
      dut: OooDataCacheHierarchyProbe,
      address: BigInt,
      base: BigInt,
      robPointer: BigInt
  ): Unit = {
    acceptRequest(dut, address, isWrite = false, 0, 0xf, robPointer, pdst = 7)
    serviceMemoryRefill(
      dut,
      address & ~BigInt(OooCacheContract.LineBytes - 1),
      beat => base + beat
    )
    expectResponse(dut, base & BigInt("ffffffff", 16), robPointer, pdst = 7)
  }

  test("L1D and L2 form a coherent 64-byte writeback hierarchy") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-data-hierarchy")
      .compile(new OooDataCacheHierarchyProbe(config))
      .doSim("ooo-data-hierarchy-writeback", 0x4c34) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        assert(dut.io.invalidateBusy.toBoolean)
        waitForInitialization(dut)

        val lineA = BigInt("1111000000000000", 16)
        loadFromMemory(dut, 0x0100, lineA, robPointer = 1)

        acceptRequest(dut, 0x0100, isWrite = false, 0, 0xf, robPointer = 2, pdst = 8)
        expectResponse(dut, 0, robPointer = 2, pdst = 8, forbidMemoryRead = true)

        acceptRequest(
          dut,
          0x0100,
          isWrite = true,
          data = BigInt("deadbeef", 16),
          mask = 0xf,
          robPointer = 3,
          pdst = 0
        )
        sample(dut)

        acceptRequest(dut, 0x0100, isWrite = false, 0, 0xf, robPointer = 4, pdst = 9)
        expectResponse(
          dut,
          BigInt("deadbeef", 16),
          robPointer = 4,
          pdst = 9,
          forbidMemoryRead = true
        )

        loadFromMemory(dut, 0x1100, BigInt("2222000000000000", 16), robPointer = 5)
        loadFromMemory(dut, 0x2100, BigInt("3333000000000000", 16), robPointer = 6)
        loadFromMemory(dut, 0x3100, BigInt("4444000000000000", 16), robPointer = 7)

        acceptRequest(dut, 0x0100, isWrite = false, 0, 0xf, robPointer = 8, pdst = 10)
        expectResponse(
          dut,
          BigInt("deadbeef", 16),
          robPointer = 8,
          pdst = 10,
          forbidMemoryRead = true
        )
        assert(!dut.io.memoryWriteValid.toBoolean)
      }
  }
}
