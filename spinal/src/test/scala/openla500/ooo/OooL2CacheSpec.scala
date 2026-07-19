package openla500.ooo

import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OooL2CacheProbe(config: OooCoreConfig) extends Component {
  val io = new Bundle {
    val readValid = in Bool ()
    val read = in(OooLineReadRequest(config))
    val readReady = out Bool ()
    val readBeatValid = out Bool ()
    val readBeat = out(OooLineReadBeat(config))
    val readBeatReady = in Bool ()
    val writeValid = in Bool ()
    val write = in(OooLineWriteRequest(config))
    val writeReady = out Bool ()
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

  val l2 = new OooL2Cache(config)
  l2.io.readValid := io.readValid
  l2.io.read := io.read
  l2.io.readBeatReady := io.readBeatReady
  l2.io.writeValid := io.writeValid
  l2.io.write := io.write
  l2.io.memoryReadReady := io.memoryReadReady
  l2.io.memoryReadBeatValid := io.memoryReadBeatValid
  l2.io.memoryReadBeat := io.memoryReadBeat
  l2.io.memoryWriteReady := io.memoryWriteReady
  l2.io.invalidate := io.invalidate

  io.readReady := l2.io.readReady
  io.readBeatValid := l2.io.readBeatValid
  io.readBeat := l2.io.readBeat
  io.writeReady := l2.io.writeReady
  io.memoryReadValid := l2.io.memoryReadValid
  io.memoryRead := l2.io.memoryRead
  io.memoryReadBeatReady := l2.io.memoryReadBeatReady
  io.memoryWriteValid := l2.io.memoryWriteValid
  io.memoryWrite := l2.io.memoryWrite
  io.invalidateBusy := l2.io.invalidateBusy
}

class OooL2CacheSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit
  private val fullLineMask = (BigInt(1) << OooCacheContract.LineBytes) - 1

  private def clearInputs(dut: OooL2CacheProbe): Unit = {
    dut.io.readValid #= false
    dut.io.read.lineAddress #= 0
    dut.io.read.mshrId #= 0
    dut.io.readBeatReady #= false
    dut.io.writeValid #= false
    dut.io.write.lineAddress #= 0
    dut.io.write.data #= 0
    dut.io.write.byteMask #= fullLineMask
    dut.io.write.mshrId #= 0
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

  private def sample(dut: OooL2CacheProbe): Unit = {
    dut.clockDomain.waitSampling()
    sleep(1)
  }

  private def waitUntilReady(dut: OooL2CacheProbe): Unit = {
    var cycles = 0
    while (!dut.io.readReady.toBoolean && cycles < config.level2Cache.sets + 12) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.readReady.toBoolean)
  }

  private def acceptRead(dut: OooL2CacheProbe, address: BigInt, mshrId: BigInt): Unit = {
    dut.io.readValid #= true
    dut.io.read.lineAddress #= address
    dut.io.read.mshrId #= mshrId
    sleep(1)
    assert(dut.io.readReady.toBoolean)
    sample(dut)
    dut.io.readValid #= false
  }

  private def sendMemoryRefill(dut: OooL2CacheProbe, expectedAddress: BigInt): Unit = {
    var cycles = 0
    while (!dut.io.memoryReadValid.toBoolean && cycles < 8) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.memoryReadValid.toBoolean)
    assert(dut.io.memoryRead.lineAddress.toBigInt == expectedAddress)
    assert(dut.io.memoryRead.mshrId.toBigInt == 0)
    dut.io.memoryReadReady #= true
    sample(dut)
    dut.io.memoryReadReady #= false

    for (beat <- 0 until OooCacheContract.BeatsPerLine) {
      dut.io.memoryReadBeatValid #= true
      dut.io.memoryReadBeat.mshrId #= 0
      dut.io.memoryReadBeat.beat #= beat
      dut.io.memoryReadBeat.data #= BigInt("1000000000000000", 16) + beat
      dut.io.memoryReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
      sleep(1)
      assert(dut.io.memoryReadBeatReady.toBoolean)
      sample(dut)
    }
    dut.io.memoryReadBeatValid #= false
  }

  private def consumeReadLine(dut: OooL2CacheProbe, expectedMshrId: BigInt): Unit = {
    var waitCycles = 0
    while (!dut.io.readBeatValid.toBoolean && waitCycles < 6) {
      sample(dut)
      waitCycles += 1
    }
    assert(dut.io.readBeatValid.toBoolean)
    dut.io.readBeatReady #= true
    for (beat <- 0 until OooCacheContract.BeatsPerLine) {
      sleep(1)
      assert(dut.io.readBeatValid.toBoolean)
      assert(dut.io.readBeat.mshrId.toBigInt == expectedMshrId)
      assert(dut.io.readBeat.beat.toBigInt == beat)
      assert(dut.io.readBeat.data.toBigInt == BigInt("1000000000000000", 16) + beat)
      assert(dut.io.readBeat.last.toBoolean == (beat == OooCacheContract.BeatsPerLine - 1))
      sample(dut)
    }
    dut.io.readBeatReady #= false
  }

  test("L2 refills a 64-byte miss and returns hits with the original MSHR id") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l2")
      .compile(new OooL2CacheProbe(config))
      .doSim("ooo-l2-refill-hit", 0x4c32) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        assert(dut.io.invalidateBusy.toBoolean)
        waitUntilReady(dut)
        assert(!dut.io.invalidateBusy.toBoolean)

        acceptRead(dut, 0x4000, 2)
        sendMemoryRefill(dut, 0x4000)
        consumeReadLine(dut, 2)

        acceptRead(dut, 0x4000, 3)
        sample(dut)
        assert(!dut.io.memoryReadValid.toBoolean)
        consumeReadLine(dut, 3)
      }
  }

  test("L2 writes a dirty victim to memory before installing another L1 writeback") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l2")
      .compile(new OooL2CacheProbe(config))
      .doSim("ooo-l2-dirty-writeback", 0x4c33) { dut =>
        def acceptWrite(address: BigInt, data: BigInt, mshrId: BigInt): Unit = {
          var cycles = 0
          while (!dut.io.writeReady.toBoolean && cycles < 8) {
            sample(dut)
            cycles += 1
          }
          assert(dut.io.writeReady.toBoolean)
          dut.io.writeValid #= true
          dut.io.write.lineAddress #= address
          dut.io.write.data #= data
          dut.io.write.byteMask #= fullLineMask
          dut.io.write.mshrId #= mshrId
          sleep(1)
          assert(dut.io.writeReady.toBoolean)
          sample(dut)
          dut.io.writeValid #= false
        }

        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        waitUntilReady(dut)

        val lineA = BigInt("11", 16) * ((BigInt(1) << OooCacheContract.LineBits) - 1) / 0xff
        val lineB = BigInt("22", 16) * ((BigInt(1) << OooCacheContract.LineBits) - 1) / 0xff
        val lineC = BigInt("33", 16) * ((BigInt(1) << OooCacheContract.LineBits) - 1) / 0xff
        acceptWrite(0x0000, lineA, 0)
        acceptWrite(0x8000, lineB, 1)
        acceptWrite(0x10000, lineC, 2)

        var waitCycles = 0
        while (!dut.io.memoryWriteValid.toBoolean && waitCycles < 8) {
          sample(dut)
          waitCycles += 1
        }
        assert(dut.io.memoryWriteValid.toBoolean)
        assert(dut.io.memoryWrite.lineAddress.toBigInt == 0x0000)
        assert(dut.io.memoryWrite.data.toBigInt == lineA)

        val heldData = dut.io.memoryWrite.data.toBigInt
        for (_ <- 0 until 3) {
          sample(dut)
          assert(dut.io.memoryWriteValid.toBoolean)
          assert(dut.io.memoryWrite.data.toBigInt == heldData)
        }
        dut.io.memoryWriteReady #= true
        sample(dut)
        dut.io.memoryWriteReady #= false
      }
  }
}
