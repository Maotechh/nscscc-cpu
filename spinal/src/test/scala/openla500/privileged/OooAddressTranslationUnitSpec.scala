package openla500.privileged

import openla500.core._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core.sim._

import scala.language.reflectiveCalls

class OooAddressTranslationUnitSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def sample(dut: OooAddressTranslationUnit): Unit = {
    dut.domain.waitSampling()
    sleep(1)
  }

  private def clearInputs(dut: OooAddressTranslationUnit): Unit = {
    dut.io.instructionRequest.valid #= false
    dut.io.instructionRequest.virtualAddress #= 0
    dut.io.instructionRequest.isWrite #= false
    dut.io.instructionResponse.ready #= true
    dut.io.dataRequest.valid #= false
    dut.io.dataRequest.virtualAddress #= 0
    dut.io.dataRequest.isWrite #= false
    dut.io.dataResponse.ready #= true
    dut.io.csrAsid #= 0
    dut.io.csrDa #= true
    dut.io.csrPg #= false
    dut.io.csrDmw0 #= 0
    dut.io.csrDmw1 #= 0
    dut.io.csrPrivilege #= 0
    dut.io.instructionMat #= 1
    dut.io.dataMat #= 1
    dut.io.disableCache #= false
    dut.io.tlbFillValid #= false
    dut.io.tlbWriteValid #= false
    dut.io.tlbRandomIndex #= 0
    dut.io.csrTlbEntryHigh #= 0
    dut.io.csrTlbEntryLow0 #= 0
    dut.io.csrTlbEntryLow1 #= 0
    dut.io.csrTlbIndex #= 0
    dut.io.csrExceptionCode #= 0
    dut.io.tlbInvalidateValid #= false
    dut.io.tlbInvalidateAsid #= 0
    dut.io.tlbInvalidateVpn #= 0
    dut.io.tlbInvalidateOperation #= 0
    dut.io.tlbSearchValid #= false
    dut.io.tlbSearchVppn #= 0
  }

  private def translateInstruction(
      dut: OooAddressTranslationUnit,
      virtualAddress: BigInt
  ): Unit = {
    dut.io.instructionRequest.valid #= true
    dut.io.instructionRequest.virtualAddress #= virtualAddress
    dut.io.instructionRequest.isWrite #= false
    sleep(1)
    assert(dut.io.instructionRequest.ready.toBoolean)
    sample(dut)
    dut.io.instructionRequest.valid #= false
    var cycles = 0
    while (!dut.io.instructionResponse.valid.toBoolean && cycles < 8) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.instructionResponse.valid.toBoolean)
  }

  test("direct, DMW, and TLB-refill instruction translations are precise") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-address-translation")
      .compile(new OooAddressTranslationUnit(config))
      .doSim("ooo-address-translation-modes", 0x4c67) { dut =>
        dut.domain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.domain.assertReset()
        dut.domain.waitSampling(2)
        dut.domain.deassertReset()
        sample(dut)

        translateInstruction(dut, 0x1c001234)
        assert(dut.io.instructionResponse.physicalAddress.toBigInt == 0x1c001234)
        assert(!dut.io.instructionResponse.uncached.toBoolean)
        assert(!dut.io.instructionResponse.exception.valid.toBoolean)
        sample(dut)

        translateInstruction(dut, 0x1c001235)
        assert(dut.io.instructionResponse.exception.valid.toBoolean)
        assert(dut.io.instructionResponse.exception.ecode.toBigInt == 8)
        assert(dut.io.instructionResponse.exception.badVAddrValid.toBoolean)
        assert(dut.io.instructionResponse.exception.badVAddr.toBigInt == 0x1c001235)
        assert(!dut.io.instructionResponse.exception.tlbRefill.toBoolean)
        sample(dut)

        val dmw0 = (BigInt(4) << 29) | (BigInt(1) << 25) | (BigInt(1) << 4) | 1
        dut.io.csrDa #= false
        dut.io.csrPg #= true
        dut.io.csrDmw0 #= dmw0
        translateInstruction(dut, 0x80001234L)
        assert(dut.io.instructionResponse.physicalAddress.toBigInt == 0x20001234)
        assert(!dut.io.instructionResponse.exception.valid.toBoolean)
        sample(dut)

        dut.io.csrAsid #= 0xaa
        dut.io.csrTlbIndex #= ((BigInt(12) << 24) | 1)
        dut.io.csrTlbEntryHigh #= 0x00014000
        dut.io.tlbWriteValid #= true
        sample(dut)
        dut.io.tlbWriteValid #= false
        dut.io.tlbSearchVppn #= (0x00014000 >> 13)
        dut.io.tlbSearchValid #= true
        sleep(1)
        assert(dut.io.tlbSearchReady.toBoolean)
        assert(dut.io.tlbSearchResponseValid.toBoolean)
        assert(dut.io.tlbSearchFound.toBoolean)
        assert(dut.io.tlbSearchIndex.toBigInt == 1)
        sample(dut)
        dut.io.tlbSearchValid #= false

        dut.io.csrDmw0 #= 0
        dut.io.tlbInvalidateValid #= true
        dut.io.tlbInvalidateOperation #= 0
        sample(dut)
        dut.io.tlbInvalidateValid #= false
        translateInstruction(dut, 0x00004000)
        assert(dut.io.instructionResponse.exception.valid.toBoolean)
        assert(dut.io.instructionResponse.exception.ecode.toBigInt == 0x3f)
        assert(dut.io.instructionResponse.exception.badVAddrValid.toBoolean)
        assert(dut.io.instructionResponse.exception.badVAddr.toBigInt == 0x00004000)
        assert(dut.io.instructionResponse.exception.tlbRefill.toBoolean)
      }
  }
}
