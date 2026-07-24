package openla500.memory

import openla500.core._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core.sim._

import scala.collection.mutable.ArrayBuffer
import scala.language.reflectiveCalls

class OooAxiLineBridgeSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def sample(dut: OooAxiLineBridge): Unit = {
    dut.clockDomain.waitSampling()
    sleep(1)
  }

  private def clearInputs(dut: OooAxiLineBridge): Unit = {
    dut.io.memoryReadValid #= false
    dut.io.memoryRead.lineAddress #= 0
    dut.io.memoryRead.mshrId #= 0
    dut.io.memoryReadBeatReady #= true
    dut.io.memoryWriteValid #= false
    dut.io.memoryWrite.lineAddress #= 0
    dut.io.memoryWrite.data #= 0
    dut.io.memoryWrite.byteMask #= 0
    dut.io.memoryWrite.mshrId #= 0
    dut.io.uncachedInstructionRequestValid #= false
    dut.io.uncachedInstructionRequest.virtualAddress #= 0
    dut.io.uncachedInstructionRequest.physicalAddress #= 0
    dut.io.uncachedInstructionRequest.uncached #= true
    dut.io.uncachedDataRequestValid #= false
    dut.io.uncachedDataRequest.virtualAddress #= 0
    dut.io.uncachedDataRequest.physicalAddress #= 0
    dut.io.uncachedDataRequest.isWrite #= false
    dut.io.uncachedDataRequest.size #= 2
    dut.io.uncachedDataRequest.byteMask #= 0xf
    dut.io.uncachedDataRequest.writeData #= 0
    dut.io.uncachedDataRequest.uncached #= true
    dut.io.uncachedDataRequest.robPointer #= 0
    dut.io.uncachedDataRequest.pdst #= 0
    dut.io.axi.ar.ready #= false
    dut.io.axi.r.valid #= false
    dut.io.axi.r.payload.id #= 0
    dut.io.axi.r.payload.data #= 0
    dut.io.axi.r.payload.response #= 0
    dut.io.axi.r.payload.last #= false
    dut.io.axi.aw.ready #= false
    dut.io.axi.w.ready #= false
    dut.io.axi.b.valid #= false
    dut.io.axi.b.payload.id #= 1
    dut.io.axi.b.payload.response #= 0
  }

  test("64-byte line reads merge sixteen AXI words into eight internal beats") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-axi-line-read")
      .compile(new OooAxiLineBridge(config))
      .doSim("ooo-axi-line-read", 0x4c64) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.memoryReadValid #= true
        dut.io.memoryRead.lineAddress #= 0x4000
        dut.io.memoryRead.mshrId #= 3
        sleep(1)
        assert(dut.io.memoryReadReady.toBoolean)
        sample(dut)
        dut.io.memoryReadValid #= false

        assert(dut.io.axi.ar.valid.toBoolean)
        assert(dut.io.axi.ar.payload.address.toBigInt == 0x4000)
        assert(dut.io.axi.ar.payload.len.toBigInt == 15)
        assert(dut.io.axi.ar.payload.size.toBigInt == 2)
        dut.io.axi.ar.ready #= true
        sample(dut)
        dut.io.axi.ar.ready #= false

        val observed = ArrayBuffer.empty[BigInt]
        fork {
          while (observed.size < OooCacheContract.BeatsPerLine) {
            sample(dut)
            if (dut.io.memoryReadBeatValid.toBoolean) {
              val beat = observed.size
              assert(dut.io.memoryReadBeat.mshrId.toBigInt == 3)
              assert(dut.io.memoryReadBeat.beat.toBigInt == beat)
              assert(
                dut.io.memoryReadBeat.last.toBoolean ==
                  (beat == OooCacheContract.BeatsPerLine - 1)
              )
              assert(!dut.io.memoryReadBeat.error.toBoolean)
              observed += dut.io.memoryReadBeat.data.toBigInt
            }
          }
        }

        for (word <- 0 until 16) {
          dut.io.axi.r.valid #= true
          dut.io.axi.r.payload.id #= 0
          dut.io.axi.r.payload.data #= (0x100 + word)
          dut.io.axi.r.payload.response #= 0
          dut.io.axi.r.payload.last #= word == 15
          sleep(1)
          assert(dut.io.axi.r.ready.toBoolean)
          sample(dut)
        }
        dut.io.axi.r.valid #= false
        while (observed.size < OooCacheContract.BeatsPerLine) { sample(dut) }
        for (beat <- observed.indices) {
          assert(
            observed(beat) ==
              (BigInt(0x101 + beat * 2) << 32 | BigInt(0x100 + beat * 2))
          )
        }
      }
  }

  test("64-byte line writes split data and byte masks into sixteen AXI words") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-axi-line-write")
      .compile(new OooAxiLineBridge(config))
      .doSim("ooo-axi-line-write", 0x4c65) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        val words = (0 until 16).map(index => BigInt("a5000000", 16) | index)
        val line =
          words.zipWithIndex.map { case (word, index) => word << (index * 32) }.reduce(_ | _)
        val masks = (0 until 16).map(index => BigInt(index & 0xf) << (index * 4)).reduce(_ | _)
        dut.io.memoryWriteValid #= true
        dut.io.memoryWrite.lineAddress #= 0x8000
        dut.io.memoryWrite.data #= line
        dut.io.memoryWrite.byteMask #= masks
        dut.io.memoryWrite.mshrId #= 2
        sleep(1)
        assert(dut.io.memoryWriteReady.toBoolean)
        sample(dut)
        dut.io.memoryWriteValid #= false

        assert(dut.io.axi.aw.valid.toBoolean)
        assert(dut.io.axi.aw.payload.address.toBigInt == 0x8000)
        assert(dut.io.axi.aw.payload.len.toBigInt == 15)
        dut.io.axi.aw.ready #= true
        sample(dut)
        dut.io.axi.aw.ready #= false

        dut.io.axi.w.ready #= true
        for (word <- 0 until 16) {
          sleep(1)
          assert(dut.io.axi.w.valid.toBoolean)
          assert(dut.io.axi.w.payload.data.toBigInt == words(word))
          assert(dut.io.axi.w.payload.byteMask.toBigInt == (word & 0xf))
          assert(dut.io.axi.w.payload.last.toBoolean == (word == 15))
          sample(dut)
        }
        dut.io.axi.w.ready #= false
        assert(dut.io.axi.b.ready.toBoolean)
        dut.io.axi.b.valid #= true
        sample(dut)
        dut.io.axi.b.valid #= false
        assert(dut.io.memoryWriteReady.toBoolean)
      }
  }

  test("uncached instruction fetches use one aligned four-word AXI burst") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-axi-line-read")
      .compile(new OooAxiLineBridge(config))
      .doSim("ooo-axi-uncached-instruction-read", 0x4c67) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.uncachedInstructionRequestValid #= true
        dut.io.uncachedInstructionRequest.virtualAddress #= BigInt("1c00100c", 16)
        dut.io.uncachedInstructionRequest.physicalAddress #= 0x100c
        sleep(1)
        assert(dut.io.uncachedInstructionRequestReady.toBoolean)
        sample(dut)
        dut.io.uncachedInstructionRequestValid #= false

        assert(dut.io.axi.ar.valid.toBoolean)
        assert(dut.io.axi.ar.payload.id.toBigInt == 2)
        assert(dut.io.axi.ar.payload.address.toBigInt == 0x1000)
        assert(dut.io.axi.ar.payload.len.toBigInt == 3)
        assert(dut.io.axi.ar.payload.size.toBigInt == 2)
        dut.io.axi.ar.ready #= true
        sample(dut)
        dut.io.axi.ar.ready #= false

        for (word <- 0 until config.fetchWidth) {
          dut.io.axi.r.valid #= true
          dut.io.axi.r.payload.id #= 2
          dut.io.axi.r.payload.data #= 0x600 + word
          dut.io.axi.r.payload.response #= 0
          dut.io.axi.r.payload.last #= word == config.fetchWidth - 1
          sleep(1)
          assert(dut.io.axi.r.ready.toBoolean)
          sample(dut)
        }
        dut.io.axi.r.valid #= false
        assert(dut.io.uncachedInstructionResponseValid.toBoolean)
        assert(
          dut.io.uncachedInstructionResponse.virtualAddress.toBigInt ==
            BigInt("1c00100c", 16)
        )
        assert(dut.io.uncachedInstructionResponse.physicalAddress.toBigInt == 0x100c)
        assert(!dut.io.uncachedInstructionResponse.error.toBoolean)
        for (word <- 0 until config.fetchWidth) {
          assert(dut.io.uncachedInstructionResponse.instructions(word).toBigInt == 0x600 + word)
        }
      }
  }

  test("uncached data accesses preserve size and wait for the write response") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-axi-line-write")
      .compile(new OooAxiLineBridge(config))
      .doSim("ooo-axi-uncached-data", 0x4c68) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.uncachedDataRequestValid #= true
        dut.io.uncachedDataRequest.physicalAddress #= BigInt("1fe00101", 16)
        dut.io.uncachedDataRequest.size #= 0
        dut.io.uncachedDataRequest.robPointer #= 17
        dut.io.uncachedDataRequest.pdst #= 23
        sleep(1)
        assert(dut.io.uncachedDataRequestReady.toBoolean)
        sample(dut)
        dut.io.uncachedDataRequestValid #= false

        assert(dut.io.axi.ar.valid.toBoolean)
        assert(dut.io.axi.ar.payload.id.toBigInt == 3)
        assert(dut.io.axi.ar.payload.address.toBigInt == BigInt("1fe00101", 16))
        assert(dut.io.axi.ar.payload.len.toBigInt == 0)
        assert(dut.io.axi.ar.payload.size.toBigInt == 0)
        dut.io.axi.ar.ready #= true
        sample(dut)
        dut.io.axi.ar.ready #= false
        dut.io.axi.r.valid #= true
        dut.io.axi.r.payload.id #= 3
        dut.io.axi.r.payload.data #= BigInt("00005a00", 16)
        dut.io.axi.r.payload.response #= 0
        dut.io.axi.r.payload.last #= true
        sample(dut)
        dut.io.axi.r.valid #= false
        assert(dut.io.uncachedDataResponseValid.toBoolean)
        assert(dut.io.uncachedDataResponse.robPointer.toBigInt == 17)
        assert(dut.io.uncachedDataResponse.pdst.toBigInt == 23)
        assert(dut.io.uncachedDataResponse.data.toBigInt == BigInt("00005a00", 16))

        sample(dut)
        dut.io.uncachedDataRequestValid #= true
        dut.io.uncachedDataRequest.isWrite #= true
        dut.io.uncachedDataRequest.physicalAddress #= BigInt("1fe00102", 16)
        dut.io.uncachedDataRequest.size #= 1
        dut.io.uncachedDataRequest.byteMask #= 0xc
        dut.io.uncachedDataRequest.writeData #= BigInt("abcd0000", 16)
        sleep(1)
        assert(!dut.io.uncachedDataRequestReady.toBoolean)
        sample(dut)

        assert(dut.io.axi.aw.valid.toBoolean)
        assert(dut.io.axi.aw.payload.id.toBigInt == 3)
        assert(dut.io.axi.aw.payload.address.toBigInt == BigInt("1fe00102", 16))
        assert(dut.io.axi.aw.payload.len.toBigInt == 0)
        assert(dut.io.axi.aw.payload.size.toBigInt == 1)
        dut.io.axi.aw.ready #= true
        sample(dut)
        dut.io.axi.aw.ready #= false
        dut.io.axi.w.ready #= true
        sleep(1)
        assert(dut.io.axi.w.valid.toBoolean)
        assert(dut.io.axi.w.payload.id.toBigInt == 3)
        assert(dut.io.axi.w.payload.data.toBigInt == BigInt("abcd0000", 16))
        assert(dut.io.axi.w.payload.byteMask.toBigInt == 0xc)
        assert(dut.io.axi.w.payload.last.toBoolean)
        sample(dut)
        dut.io.axi.w.ready #= false
        assert(dut.io.axi.b.ready.toBoolean)
        assert(!dut.io.uncachedDataRequestReady.toBoolean)
        dut.io.axi.b.valid #= true
        dut.io.axi.b.payload.id #= 3
        dut.io.axi.b.payload.response #= 0
        sleep(1)
        assert(dut.io.uncachedDataRequestReady.toBoolean)
        sample(dut)
        dut.io.uncachedDataRequestValid #= false
        dut.io.axi.b.valid #= false
      }
  }
}
