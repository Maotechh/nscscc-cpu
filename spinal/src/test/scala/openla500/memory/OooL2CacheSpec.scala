package openla500.memory

import openla500.core._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core.sim._

import scala.language.reflectiveCalls

class OooL2CacheSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  test("an L1D writeback is written through and retained as a clean L2 hit") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l2-cache")
      .compile(new OooL2Cache(config))
      .doSim("ooo-l2-write-through", 0x4c61) { dut =>
        dut.clockDomain.forkStimulus(period = 10)

        dut.io.readValid #= false
        dut.io.read.lineAddress #= 0
        dut.io.read.mshrId #= 0
        dut.io.readBeatReady #= true
        dut.io.writeValid #= false
        dut.io.write.lineAddress #= 0
        dut.io.write.data #= 0
        dut.io.write.byteMask #= 0
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
        dut.io.writebackInvalidate #= false

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(config.level2Cache.sets + 4)
        assert(!dut.io.invalidateBusy.toBoolean)

        val address = BigInt("d0100000", 16)
        val beats = (0 until OooCacheContract.BeatsPerLine).map { beat =>
          BigInt("1111000000000000", 16) + beat
        }
        val line = beats.zipWithIndex.foldLeft(BigInt(0)) { case (value, (beat, index)) =>
          value | (beat << (index * OooCacheContract.BeatBits))
        }

        dut.io.writeValid #= true
        dut.io.write.lineAddress #= address
        dut.io.write.data #= line
        dut.io.write.byteMask #= (BigInt(1) << OooCacheContract.LineBytes) - 1
        dut.io.write.mshrId #= 2
        while (!dut.io.writeReady.toBoolean) { dut.clockDomain.waitSampling() }
        dut.clockDomain.waitSampling()
        dut.io.writeValid #= false

        var writeWait = 0
        while (!dut.io.memoryWriteValid.toBoolean && writeWait < 8) {
          dut.clockDomain.waitSampling()
          writeWait += 1
        }
        assert(dut.io.memoryWriteValid.toBoolean)
        assert(dut.io.memoryWrite.lineAddress.toBigInt == address)
        assert(dut.io.memoryWrite.data.toBigInt == line)
        assert(dut.io.memoryWrite.byteMask.toBigInt ==
          (BigInt(1) << OooCacheContract.LineBytes) - 1)

        dut.io.memoryWriteReady #= true
        dut.clockDomain.waitSampling()
        dut.io.memoryWriteReady #= false

        dut.io.readValid #= true
        dut.io.read.lineAddress #= address
        dut.io.read.mshrId #= 3
        while (!dut.io.readReady.toBoolean) { dut.clockDomain.waitSampling() }
        dut.clockDomain.waitSampling()
        dut.io.readValid #= false

        for (expectedBeat <- beats.indices) {
          var responseWait = 0
          while (!dut.io.readBeatValid.toBoolean && responseWait < 8) {
            assert(!dut.io.memoryReadValid.toBoolean)
            dut.clockDomain.waitSampling()
            responseWait += 1
          }
          assert(dut.io.readBeatValid.toBoolean)
          assert(dut.io.readBeat.mshrId.toBigInt == 3)
          assert(dut.io.readBeat.beat.toBigInt == expectedBeat)
          assert(dut.io.readBeat.data.toBigInt == beats(expectedBeat))
          assert(dut.io.readBeat.last.toBoolean ==
            (expectedBeat == OooCacheContract.BeatsPerLine - 1))
          dut.clockDomain.waitSampling()
        }
      }
  }
}
