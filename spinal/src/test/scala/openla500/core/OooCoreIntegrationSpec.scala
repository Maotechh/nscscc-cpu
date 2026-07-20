package openla500.core

import openla500.memory._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core.sim._

import scala.collection.mutable
import scala.language.reflectiveCalls

class OooCoreIntegrationSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def sample(dut: OooCore): Unit = {
    dut.clockDomain.waitSampling()
    sleep(1)
  }

  private def addiW(rd: Int, immediate: Int): BigInt =
    BigInt("02800000", 16) | (BigInt(immediate & 0xfff) << 10) | rd

  private def branchToSelf: BigInt = BigInt("50000000", 16)

  private def clearInputs(dut: OooCore): Unit = {
    dut.io.instructionTranslationRequest.ready #= false
    dut.io.instructionTranslationResponse.valid #= false
    dut.io.instructionTranslationResponse.virtualAddress #= 0
    dut.io.instructionTranslationResponse.physicalAddress #= 0
    dut.io.instructionTranslationResponse.uncached #= false
    dut.io.instructionTranslationResponse.exception.valid #= false
    dut.io.instructionTranslationResponse.exception.ecode #= 0
    dut.io.instructionTranslationResponse.exception.esubcode #= 0
    dut.io.instructionTranslationResponse.exception.badVAddrValid #= false
    dut.io.instructionTranslationResponse.exception.badVAddr #= 0
    dut.io.instructionTranslationResponse.exception.tlbRefill #= false
    dut.io.dataTranslationRequest.ready #= true
    dut.io.dataTranslationResponse.valid #= false
    dut.io.dataTranslationResponse.virtualAddress #= 0
    dut.io.dataTranslationResponse.physicalAddress #= 0
    dut.io.dataTranslationResponse.uncached #= false
    dut.io.dataTranslationResponse.exception.valid #= false
    dut.io.dataTranslationResponse.exception.ecode #= 0
    dut.io.dataTranslationResponse.exception.esubcode #= 0
    dut.io.dataTranslationResponse.exception.badVAddrValid #= false
    dut.io.dataTranslationResponse.exception.badVAddr #= 0
    dut.io.dataTranslationResponse.exception.tlbRefill #= false
    dut.io.reservationValid #= false
    dut.io.reservationLineAddress #= 0
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
    dut.io.memoryWriteReady #= true
    dut.io.systemReadData #= 0
    dut.io.timer #= 0
    dut.io.timerId #= 0
    dut.io.debugReadAddress #= 0
    dut.io.privilege #= 0
    dut.io.interruptPending #= false
    dut.io.exceptionEntryTarget #= BigInt("1c001000", 16)
    dut.io.tlbRefillTarget #= BigInt("1c002000", 16)
    dut.io.externalRedirectValid #= false
    dut.io.externalRedirectTarget #= 0
    dut.io.cacheInvalidate #= false
    dut.io.dataCacheInvalidate #= false
    dut.io.dataCacheWritebackInvalidate #= false
    dut.io.level2CacheInvalidate #= false
  }

  private def refillInstructionLine(
      dut: OooCore,
      expectedAddress: BigInt,
      instructions: IndexedSeq[BigInt],
      waitForInitialization: Boolean
  ): Unit = {
    if (waitForInitialization) {
      var initializationCycles = 0
      while (dut.io.cacheInvalidateBusy.toBoolean && initializationCycles <
        config.level2Cache.sets + 32) {
        sample(dut)
        initializationCycles += 1
      }
      assert(!dut.io.cacheInvalidateBusy.toBoolean)
    }

    var waitCycles = 0
    while (!dut.io.memoryReadValid.toBoolean && waitCycles < 80) {
      sample(dut)
      waitCycles += 1
    }
    assert(dut.io.memoryReadValid.toBoolean)
    assert(dut.io.memoryRead.lineAddress.toBigInt == expectedAddress)
    assert(dut.io.memoryRead.mshrId.toBigInt == 0)

    dut.io.memoryReadReady #= true
    sample(dut)
    dut.io.memoryReadReady #= false

    for (beat <- 0 until OooCacheContract.BeatsPerLine) {
      val data = instructions(beat * 2) | (instructions(beat * 2 + 1) << 32)
      dut.io.memoryReadBeatValid #= true
      dut.io.memoryReadBeat.mshrId #= 0
      dut.io.memoryReadBeat.beat #= beat
      dut.io.memoryReadBeat.data #= data
      dut.io.memoryReadBeat.last #= beat == OooCacheContract.BeatsPerLine - 1
      dut.io.memoryReadBeat.error #= false
      sleep(1)
      assert(dut.io.memoryReadBeatReady.toBoolean)
      sample(dut)
    }
    dut.io.memoryReadBeatValid #= false
  }

  test("self-fetching core executes a 64-byte instruction line and retires three-wide") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-core-integration")
      .compile(new OooCore(config))
      .doSim("ooo-core-fetch-execute-commit", 0x4c63) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        fork {
          while (true) {
            while (!dut.io.instructionTranslationRequest.valid.toBoolean) {
              sample(dut)
            }
            val address = dut.io.instructionTranslationRequest.virtualAddress.toBigInt
            dut.io.instructionTranslationRequest.ready #= true
            sample(dut)
            dut.io.instructionTranslationRequest.ready #= false
            dut.io.instructionTranslationResponse.virtualAddress #= address
            dut.io.instructionTranslationResponse.physicalAddress #= address
            dut.io.instructionTranslationResponse.valid #= true
            while (!dut.io.instructionTranslationResponse.ready.toBoolean) {
              sample(dut)
            }
            sample(dut)
            dut.io.instructionTranslationResponse.valid #= false
          }
        }

        val instructions = IndexedSeq.tabulate(16) { index =>
          if (index < 12) addiW(index + 1, index + 1) else branchToSelf
        }
        refillInstructionLine(
          dut,
          config.resetVector,
          instructions,
          waitForInitialization = true
        )

        val committed = mutable.LinkedHashMap.empty[BigInt, BigInt]
        var maximumCommitWidth = 0
        var branchRecoverySeen = false
        var cycles = 0
        while (committed.size < 12 && cycles < 160) {
          sample(dut)
          val mask = dut.io.commitValid.toBigInt
          maximumCommitWidth = maximumCommitWidth.max(mask.bitCount)
          for (lane <- 0 until config.commitWidth if (mask & (BigInt(1) << lane)) != 0) {
            val pc = dut.io.commit(lane).pc.toBigInt
            val index = ((pc - config.resetVector) / 4).toInt
            if (index >= 0 && index < 12) {
              assert(dut.io.commit(lane).instruction.toBigInt == instructions(index))
              assert(dut.io.commit(lane).result.toBigInt == index + 1)
              committed(pc) = dut.io.commit(lane).result.toBigInt
            }
          }
          if (dut.io.recoveryValid.toBoolean) {
            assert(dut.io.recovery.cause.toBigInt == 1)
            assert(dut.io.recovery.target.toBigInt == config.resetVector + 12 * 4)
            branchRecoverySeen = true
          }
          cycles += 1
        }

        assert(committed.keys.toSeq == (0 until 12).map(config.resetVector + _ * 4))
        assert(committed.values.toSeq == (1 to 12).map(BigInt(_)))
        assert(maximumCommitWidth == config.commitWidth)

        var recoveryWait = 0
        while (!branchRecoverySeen && recoveryWait < 40) {
          sample(dut)
          if (dut.io.recoveryValid.toBoolean) {
            assert(dut.io.recovery.cause.toBigInt == 1)
            assert(dut.io.recovery.target.toBigInt == config.resetVector + 12 * 4)
            branchRecoverySeen = true
          }
          recoveryWait += 1
        }
        assert(branchRecoverySeen)

        // The registered recovery pulse redirects one cycle later. Seeing the same self-branch
        // recover again proves that the frontend consumed that redirect instead of falling through.
        sample(dut)
        refillInstructionLine(
          dut,
          config.resetVector + OooCacheContract.LineBytes,
          IndexedSeq.fill(16)(branchToSelf),
          waitForInitialization = false
        )
        var repeatedRecoverySeen = false
        var repeatedRecoveryWait = 0
        while (!repeatedRecoverySeen && repeatedRecoveryWait < 60) {
          sample(dut)
          if (dut.io.recoveryValid.toBoolean) {
            assert(dut.io.recovery.cause.toBigInt == 1)
            assert(dut.io.recovery.target.toBigInt == config.resetVector + 12 * 4)
            repeatedRecoverySeen = true
          }
          repeatedRecoveryWait += 1
        }
        assert(repeatedRecoverySeen)
      }
  }

  test("registered TLB refill recovery redirects to the refill entry") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-core-tlb-refill")
      .compile(new OooCore(config))
      .doSim("ooo-core-tlb-refill-target", 0x4c64) { dut =>
        val exceptionEntry = BigInt("1c008000", 16)
        val tlbRefillEntry = BigInt("1c00f000", 16)

        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.io.exceptionEntryTarget #= exceptionEntry
        dut.io.tlbRefillTarget #= tlbRefillEntry
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        var requestWait = 0
        while (!dut.io.instructionTranslationRequest.valid.toBoolean && requestWait < 40) {
          sample(dut)
          requestWait += 1
        }
        assert(dut.io.instructionTranslationRequest.valid.toBoolean)
        val faultPc = dut.io.instructionTranslationRequest.virtualAddress.toBigInt
        assert(faultPc == config.resetVector)

        dut.io.instructionTranslationRequest.ready #= true
        sample(dut)
        dut.io.instructionTranslationRequest.ready #= false

        dut.io.instructionTranslationResponse.virtualAddress #= faultPc
        dut.io.instructionTranslationResponse.physicalAddress #= 0
        dut.io.instructionTranslationResponse.exception.valid #= true
        dut.io.instructionTranslationResponse.exception.ecode #= 0x3f
        dut.io.instructionTranslationResponse.exception.esubcode #= 0
        dut.io.instructionTranslationResponse.exception.badVAddrValid #= true
        dut.io.instructionTranslationResponse.exception.badVAddr #= faultPc
        dut.io.instructionTranslationResponse.exception.tlbRefill #= true
        dut.io.instructionTranslationResponse.valid #= true
        var responseWait = 0
        while (!dut.io.instructionTranslationResponse.ready.toBoolean && responseWait < 20) {
          sample(dut)
          responseWait += 1
        }
        assert(dut.io.instructionTranslationResponse.ready.toBoolean)
        sample(dut)
        dut.io.instructionTranslationResponse.valid #= false
        dut.io.instructionTranslationResponse.exception.valid #= false

        var recoveryWait = 0
        while (!dut.io.recoveryValid.toBoolean && recoveryWait < 80) {
          sample(dut)
          recoveryWait += 1
        }
        assert(dut.io.recoveryValid.toBoolean)
        assert(dut.io.recovery.cause.toBigInt == 2)
        assert(dut.io.recovery.exception.tlbRefill.toBoolean)

        // Recovery is captured on the retirement pulse and applied one cycle later.
        sample(dut)
        var redirectRequestWait = 0
        while (!dut.io.instructionTranslationRequest.valid.toBoolean &&
          redirectRequestWait < 40) {
          sample(dut)
          redirectRequestWait += 1
        }
        assert(dut.io.instructionTranslationRequest.valid.toBoolean)
        assert(dut.io.instructionTranslationRequest.virtualAddress.toBigInt == tlbRefillEntry)
        assert(dut.io.instructionTranslationRequest.virtualAddress.toBigInt != exceptionEntry)
      }
  }
}
