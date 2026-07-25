package openla500.memory

import openla500.core._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core.sim._

import scala.language.reflectiveCalls

class OooL2CacheSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def clearInputs(dut: OooL2Cache): Unit = {
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
  }

  test("an L1D writeback is written through and retained as a clean L2 hit") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l2-cache")
      .compile(new OooL2Cache(config))
      .doSim("ooo-l2-write-through", 0x4c61) { dut =>
        dut.clockDomain.forkStimulus(period = 10)

        clearInputs(dut)

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
        assert(
          dut.io.memoryWrite.byteMask.toBigInt ==
            (BigInt(1) << OooCacheContract.LineBytes) - 1
        )

        dut.io.memoryWriteReady #= true
        dut.clockDomain.waitSampling()
        dut.io.memoryWriteReady #= false

        dut.io.readBeatReady #= false
        dut.io.readValid #= true
        dut.io.read.lineAddress #= address
        dut.io.read.mshrId #= 3
        while (!dut.io.readReady.toBoolean) { dut.clockDomain.waitSampling() }
        dut.clockDomain.waitSampling()
        dut.io.readValid #= false

        var firstBeatWait = 0
        while (!dut.io.readBeatValid.toBoolean && firstBeatWait < 8) {
          dut.clockDomain.waitSampling()
          firstBeatWait += 1
        }
        for (_ <- 0 until 2) {
          sleep(1)
          assert(dut.io.readBeatValid.toBoolean)
          assert(dut.io.readBeat.beat.toBigInt == 0)
          assert(dut.io.readBeat.data.toBigInt == beats.head)
          dut.clockDomain.waitSampling()
        }
        dut.io.readBeatReady #= true

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
          assert(
            dut.io.readBeat.last.toBoolean ==
              (expectedBeat == OooCacheContract.BeatsPerLine - 1)
          )
          dut.clockDomain.waitSampling()
          sleep(1)
        }
      }
  }

  test("an L2 hit returns while an unrelated memory miss is outstanding") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l2-cache")
      .compile(new OooL2Cache(config))
      .doSim("ooo-l2-hit-under-miss", 0x4c64) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(config.level2Cache.sets + 4)

        val hitAddress = BigInt("d0100000", 16)
        val missAddress = BigInt("00002000", 16)
        val beats = (0 until OooCacheContract.BeatsPerLine).map { beat =>
          BigInt("5a5a000000000000", 16) + beat
        }
        val line = beats.zipWithIndex.foldLeft(BigInt(0)) { case (value, (beat, index)) =>
          value | (beat << (index * OooCacheContract.BeatBits))
        }

        dut.io.writeValid #= true
        dut.io.write.lineAddress #= hitAddress
        dut.io.write.data #= line
        dut.io.write.byteMask #= (BigInt(1) << OooCacheContract.LineBytes) - 1
        dut.io.write.mshrId #= 3
        while (!dut.io.writeReady.toBoolean) { dut.clockDomain.waitSampling() }
        dut.clockDomain.waitSampling()
        dut.io.writeValid #= false
        while (!dut.io.memoryWriteValid.toBoolean) { dut.clockDomain.waitSampling() }
        dut.io.memoryWriteReady #= true
        dut.clockDomain.waitSampling()
        dut.io.memoryWriteReady #= false
        dut.clockDomain.waitSampling(2)

        dut.io.readValid #= true
        dut.io.read.lineAddress #= missAddress
        dut.io.read.mshrId #= 0
        while (!dut.io.readReady.toBoolean) { dut.clockDomain.waitSampling() }
        dut.clockDomain.waitSampling()
        dut.io.readValid #= false
        while (!dut.io.memoryReadValid.toBoolean) { dut.clockDomain.waitSampling() }
        assert(dut.io.memoryRead.lineAddress.toBigInt == missAddress)
        assert(dut.io.memoryRead.mshrId.toBigInt == 0)

        dut.io.readValid #= true
        dut.io.read.lineAddress #= hitAddress
        dut.io.read.mshrId #= 1
        while (!dut.io.readReady.toBoolean) { dut.clockDomain.waitSampling() }
        dut.clockDomain.waitSampling()
        dut.io.readValid #= false

        for (beat <- beats.indices) {
          while (!dut.io.readBeatValid.toBoolean) { dut.clockDomain.waitSampling() }
          assert(dut.io.readBeat.mshrId.toBigInt == 1)
          assert(dut.io.readBeat.beat.toBigInt == beat)
          assert(dut.io.readBeat.data.toBigInt == beats(beat))
          assert(dut.io.memoryReadValid.toBoolean)
          assert(dut.io.memoryRead.mshrId.toBigInt == 0)
          dut.clockDomain.waitSampling()
        }
      }
  }

  test("a memory refill streams beats to the requesting L1 before the L2 install") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l2-streaming-refill")
      .compile(new OooL2Cache(config))
      .doSim("ooo-l2-streaming-refill", 0x4c62) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(config.level2Cache.sets + 4)

        val address = BigInt("1c123400", 16)
        dut.io.readValid #= true
        dut.io.read.lineAddress #= address
        dut.io.read.mshrId #= 2
        while (!dut.io.readReady.toBoolean) { dut.clockDomain.waitSampling() }
        dut.clockDomain.waitSampling()
        dut.io.readValid #= false

        while (!dut.io.memoryReadValid.toBoolean) { dut.clockDomain.waitSampling() }
        assert(dut.io.memoryRead.lineAddress.toBigInt == address)
        assert(dut.io.memoryRead.mshrId.toBigInt == 2)
        dut.io.memoryReadReady #= true
        dut.clockDomain.waitSampling()
        dut.io.memoryReadReady #= false

        val beats = (0 until OooCacheContract.BeatsPerLine).map { beat =>
          BigInt("abcd000000000000", 16) + beat
        }
        for (beat <- beats.indices) {
          dut.io.memoryReadBeatValid #= true
          dut.io.memoryReadBeat.mshrId #= 2
          dut.io.memoryReadBeat.beat #= beat
          dut.io.memoryReadBeat.data #= beats(beat)
          dut.io.memoryReadBeat.last #= beat == beats.size - 1
          if (beat == 3) {
            dut.io.readBeatReady #= false
            sleep(1)
            assert(!dut.io.memoryReadBeatReady.toBoolean)
            assert(dut.io.readBeatValid.toBoolean)
            assert(dut.io.readBeat.beat.toBigInt == beat)
            for (_ <- 0 until 2) {
              dut.clockDomain.waitSampling()
              sleep(1)
              assert(!dut.io.memoryReadBeatReady.toBoolean)
              assert(dut.io.readBeatValid.toBoolean)
              assert(dut.io.readBeat.beat.toBigInt == beat)
              assert(dut.io.readBeat.data.toBigInt == beats(beat))
            }
            dut.io.readBeatReady #= true
          }
          sleep(1)
          assert(dut.io.memoryReadBeatReady.toBoolean)
          dut.clockDomain.waitSampling()
          sleep(1)
          assert(dut.io.readBeatValid.toBoolean)
          assert(dut.io.readBeat.mshrId.toBigInt == 2)
          assert(dut.io.readBeat.beat.toBigInt == beat)
          assert(dut.io.readBeat.data.toBigInt == beats(beat))
          assert(dut.io.readBeat.last.toBoolean == (beat == beats.size - 1))
        }
        dut.io.memoryReadBeatValid #= false

        dut.clockDomain.waitSampling(2)
        assert(dut.io.readReady.toBoolean)

        dut.io.readValid #= true
        dut.io.read.lineAddress #= address
        dut.io.read.mshrId #= 3
        dut.clockDomain.waitSampling()
        dut.io.readValid #= false
        for (beat <- beats.indices) {
          var waitCycles = 0
          while (!dut.io.readBeatValid.toBoolean && waitCycles < 8) {
            assert(!dut.io.memoryReadValid.toBoolean)
            dut.clockDomain.waitSampling()
            waitCycles += 1
          }
          assert(dut.io.readBeatValid.toBoolean)
          assert(dut.io.readBeat.mshrId.toBigInt == 3)
          assert(dut.io.readBeat.beat.toBigInt == beat)
          assert(dut.io.readBeat.data.toBigInt == beats(beat))
          dut.clockDomain.waitSampling()
        }
      }
  }

  test("four L2 miss slots route interleaved memory returns by global identity") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-l2-four-mshr")
      .compile(new OooL2Cache(config))
      .doSim("ooo-l2-four-mshr-interleaved", 0x4c63) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling(config.level2Cache.sets + 4)

        val addresses = (0 until config.mshrEntries).map(index => BigInt(0x400 + index * 0x40))
        for ((address, id) <- addresses.zipWithIndex) {
          dut.io.readValid #= true
          dut.io.read.lineAddress #= address
          dut.io.read.mshrId #= id
          var wait = 0
          while (!dut.io.readReady.toBoolean && wait < 8) {
            dut.clockDomain.waitSampling()
            wait += 1
          }
          assert(dut.io.readReady.toBoolean)
          dut.clockDomain.waitSampling()
          dut.io.readValid #= false
          dut.clockDomain.waitSampling()
        }

        dut.io.readValid #= true
        dut.io.read.lineAddress #= 0x800
        dut.io.read.mshrId #= 0
        for (_ <- 0 until 3) dut.clockDomain.waitSampling()
        assert(!dut.io.readReady.toBoolean)
        dut.io.readValid #= false

        dut.io.memoryReadReady #= true
        for ((address, id) <- addresses.zipWithIndex) {
          var wait = 0
          while (!dut.io.memoryReadValid.toBoolean && wait < 8) {
            dut.clockDomain.waitSampling()
            wait += 1
          }
          assert(dut.io.memoryReadValid.toBoolean)
          assert(dut.io.memoryRead.lineAddress.toBigInt == address)
          assert(dut.io.memoryRead.mshrId.toBigInt == id)
          dut.clockDomain.waitSampling()
          sleep(1)
        }
        dut.io.memoryReadReady #= false

        for (beat <- 0 until OooCacheContract.BeatsPerLine) {
          for (id <- (0 until config.mshrEntries).reverse) {
            val data = BigInt(id * 0x100 + beat)
            dut.io.memoryReadBeatValid #= true
            dut.io.memoryReadBeat.mshrId #= id
            dut.io.memoryReadBeat.beat #= beat
            dut.io.memoryReadBeat.data #= data
            dut.io.memoryReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
            sleep(1)
            assert(dut.io.memoryReadBeatReady.toBoolean)
            dut.clockDomain.waitSampling()
            sleep(1)
            assert(dut.io.readBeatValid.toBoolean)
            assert(dut.io.readBeat.mshrId.toBigInt == id)
            assert(dut.io.readBeat.beat.toBigInt == beat)
            assert(dut.io.readBeat.data.toBigInt == data)
            assert(dut.io.readBeat.last.toBoolean == (beat == OooCacheContract.BeatsPerLine - 1))
          }
        }
        dut.io.memoryReadBeatValid #= false
      }
  }
}
