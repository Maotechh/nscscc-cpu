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

  private def tlbLow(
      ppn: BigInt,
      global: Boolean = false,
      memoryAttribute: Int = 1,
      privilege: Int = 0,
      dirty: Boolean = true,
      valid: Boolean = true
  ): BigInt =
    (ppn << 8) |
      (if (global) BigInt(1) << 6 else BigInt(0)) |
      (BigInt(memoryAttribute) << 4) |
      (BigInt(privilege) << 2) |
      (if (dirty) BigInt(1) << 1 else BigInt(0)) |
      (if (valid) BigInt(1) else BigInt(0))

  private def writeTlb(
      dut: OooAddressTranslationUnit,
      index: Int,
      virtualAddress: BigInt,
      ppn0: BigInt,
      ppn1: BigInt,
      asid: Int,
      low0Flags: BigInt = 0x13,
      low1Flags: BigInt = 0x13,
      pageSize: Int = 12
  ): Unit = {
    dut.io.csrAsid #= asid
    dut.io.csrTlbIndex #= ((BigInt(pageSize) << 24) | index)
    dut.io.csrTlbEntryHigh #= ((virtualAddress >> 13) << 13)
    dut.io.csrTlbEntryLow0 #= ((ppn0 << 8) | low0Flags)
    dut.io.csrTlbEntryLow1 #= ((ppn1 << 8) | low1Flags)
    dut.io.tlbWriteValid #= true
    sample(dut)
    dut.io.tlbWriteValid #= false
  }

  private def translateInstruction(
      dut: OooAddressTranslationUnit,
      virtualAddress: BigInt
  ): Int = {
    dut.io.instructionRequest.valid #= true
    dut.io.instructionRequest.virtualAddress #= virtualAddress
    dut.io.instructionRequest.isWrite #= false
    sleep(1)
    assert(dut.io.instructionRequest.ready.toBoolean)
    sample(dut)
    dut.io.instructionRequest.valid #= false
    var cycles = 0
    while (!dut.io.instructionResponse.valid.toBoolean && cycles < 24) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.instructionResponse.valid.toBoolean)
    cycles
  }

  private def translateData(
      dut: OooAddressTranslationUnit,
      virtualAddress: BigInt,
      isWrite: Boolean
  ): Int = {
    dut.io.dataRequest.valid #= true
    dut.io.dataRequest.virtualAddress #= virtualAddress
    dut.io.dataRequest.isWrite #= isWrite
    sleep(1)
    assert(dut.io.dataRequest.ready.toBoolean)
    sample(dut)
    dut.io.dataRequest.valid #= false
    var cycles = 0
    while (!dut.io.dataResponse.valid.toBoolean && cycles < 24) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.dataResponse.valid.toBoolean)
    cycles
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

        assert(translateInstruction(dut, 0x1c001234) == 0)
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
        assert(translateInstruction(dut, 0x80001234L) == 0)
        assert(dut.io.instructionResponse.physicalAddress.toBigInt == 0x20001234)
        assert(!dut.io.instructionResponse.exception.valid.toBoolean)
        sample(dut)

        assert(translateData(dut, 0x80001238L, isWrite = true) == 0)
        assert(dut.io.dataResponse.physicalAddress.toBigInt == 0x20001238)
        assert(!dut.io.dataResponse.uncached.toBoolean)
        assert(!dut.io.dataResponse.exception.valid.toBoolean)
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
        assert(translateInstruction(dut, 0x00004000) > 0)
        assert(dut.io.instructionResponse.exception.valid.toBoolean)
        assert(dut.io.instructionResponse.exception.ecode.toBigInt == 0x3f)
        assert(dut.io.instructionResponse.exception.badVAddrValid.toBoolean)
        assert(dut.io.instructionResponse.exception.badVAddr.toBigInt == 0x00004000)
        assert(dut.io.instructionResponse.exception.tlbRefill.toBoolean)
      }
  }

  test(
    "micro TLBs cache main-walk results and mutations discard stale positive and negative state"
  ) {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-hierarchical-tlb")
      .compile(new OooAddressTranslationUnit(config))
      .doSim("ooo-hierarchical-tlb", 0x7b31) { dut =>
        dut.domain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.domain.assertReset()
        dut.domain.waitSampling(2)
        dut.domain.deassertReset()
        sample(dut)

        dut.io.csrDa #= false
        dut.io.csrPg #= true
        val asid = 0x12
        val instructionAddress = BigInt("00456044", 16)
        val dataAddress = BigInt("0089a088", 16)
        val instructionPpn = BigInt("12345", 16)
        val dataPpn = BigInt("23456", 16)
        writeTlb(
          dut,
          index = 29,
          virtualAddress = instructionAddress,
          ppn0 = instructionPpn,
          ppn1 = instructionPpn + 1,
          asid = asid,
          low0Flags = tlbLow(0) & 0xff,
          low1Flags = tlbLow(0) & 0xff
        )
        writeTlb(
          dut,
          index = 30,
          virtualAddress = dataAddress,
          ppn0 = dataPpn,
          ppn1 = dataPpn + 1,
          asid = asid,
          low0Flags = tlbLow(0) & 0xff,
          low1Flags = tlbLow(0) & 0xff
        )

        dut.io.instructionRequest.valid #= true
        dut.io.instructionRequest.virtualAddress #= instructionAddress
        dut.io.dataRequest.valid #= true
        dut.io.dataRequest.virtualAddress #= dataAddress
        dut.io.dataRequest.isWrite #= false
        sleep(1)
        assert(dut.io.instructionRequest.ready.toBoolean)
        assert(dut.io.dataRequest.ready.toBoolean)
        sample(dut)
        dut.io.instructionRequest.valid #= false
        dut.io.dataRequest.valid #= false

        var instructionSeen = false
        var dataSeen = false
        var arbitrationCycles = 0
        while (!(instructionSeen && dataSeen) && arbitrationCycles < 28) {
          sample(dut)
          arbitrationCycles += 1
          if (dut.io.instructionResponse.valid.toBoolean) {
            instructionSeen = true
            assert(!dut.io.instructionResponse.exception.valid.toBoolean)
            assert(
              dut.io.instructionResponse.physicalAddress.toBigInt ==
                ((instructionPpn << 12) | (instructionAddress & 0xfff))
            )
          }
          if (dut.io.dataResponse.valid.toBoolean) {
            dataSeen = true
            assert(!dut.io.dataResponse.exception.valid.toBoolean)
            assert(
              dut.io.dataResponse.physicalAddress.toBigInt ==
                ((dataPpn << 12) | (dataAddress & 0xfff))
            )
          }
        }
        assert(instructionSeen && dataSeen)
        assert(arbitrationCycles >= 10)
        sample(dut)

        assert(translateInstruction(dut, instructionAddress) == 1)
        assert(!dut.io.instructionResponse.exception.valid.toBoolean)
        sample(dut)
        assert(translateData(dut, dataAddress, isWrite = false) == 1)
        assert(!dut.io.dataResponse.exception.valid.toBoolean)
        sample(dut)

        dut.io.tlbInvalidateValid #= true
        dut.io.tlbInvalidateOperation #= 0
        sample(dut)
        dut.io.tlbInvalidateValid #= false
        assert(translateInstruction(dut, instructionAddress) >= 10)
        assert(dut.io.instructionResponse.exception.valid.toBoolean)
        assert(dut.io.instructionResponse.exception.ecode.toBigInt == 0x3f)
        sample(dut)
        assert(translateInstruction(dut, instructionAddress) == 1)
        assert(dut.io.instructionResponse.exception.tlbRefill.toBoolean)
        sample(dut)

        val replacementPpn = BigInt("34567", 16)
        writeTlb(
          dut,
          index = 29,
          virtualAddress = instructionAddress,
          ppn0 = replacementPpn,
          ppn1 = replacementPpn + 1,
          asid = asid,
          low0Flags = tlbLow(0) & 0xff,
          low1Flags = tlbLow(0) & 0xff
        )
        assert(translateInstruction(dut, instructionAddress) >= 10)
        assert(!dut.io.instructionResponse.exception.valid.toBoolean)
        assert(
          dut.io.instructionResponse.physicalAddress.toBigInt ==
            ((replacementPpn << 12) | (instructionAddress & 0xfff))
        )
      }
  }

  test("TLB validity, modify, and privilege faults report precise architectural metadata") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-address-translation-faults")
      .compile(new OooAddressTranslationUnit(config))
      .doSim("ooo-address-translation-faults", 0x4c68) { dut =>
        dut.domain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.domain.assertReset()
        dut.domain.waitSampling(2)
        dut.domain.deassertReset()
        sample(dut)

        dut.io.csrDa #= false
        dut.io.csrPg #= true
        val asid = 0x21
        val invalidFlags = tlbLow(0, valid = false) & 0xff
        val readOnlyFlags = tlbLow(0, dirty = false) & 0xff
        val kernelFlags = tlbLow(0, privilege = 0) & 0xff
        val pifAddress = BigInt("00400000", 16)
        val pilAddress = BigInt("00800000", 16)
        val pisAddress = BigInt("00c00000", 16)
        val pmeAddress = BigInt("01000000", 16)
        val instructionPpiAddress = BigInt("01400000", 16)
        val dataPpiAddress = BigInt("01800000", 16)

        writeTlb(dut, 0, pifAddress, 0x10000, 0x10001, asid, invalidFlags, invalidFlags)
        writeTlb(dut, 1, pilAddress, 0x11000, 0x11001, asid, invalidFlags, invalidFlags)
        writeTlb(dut, 2, pisAddress, 0x12000, 0x12001, asid, invalidFlags, invalidFlags)
        writeTlb(dut, 3, pmeAddress, 0x13000, 0x13001, asid, readOnlyFlags, readOnlyFlags)
        writeTlb(
          dut,
          4,
          instructionPpiAddress,
          0x14000,
          0x14001,
          asid,
          kernelFlags,
          kernelFlags
        )
        writeTlb(dut, 5, dataPpiAddress, 0x15000, 0x15001, asid, kernelFlags, kernelFlags)

        def assertInstructionFault(address: BigInt, ecode: Int): Unit = {
          translateInstruction(dut, address)
          assert(dut.io.instructionResponse.exception.valid.toBoolean)
          assert(dut.io.instructionResponse.exception.ecode.toBigInt == ecode)
          assert(dut.io.instructionResponse.exception.esubcode.toBigInt == 0)
          assert(dut.io.instructionResponse.exception.badVAddrValid.toBoolean)
          assert(dut.io.instructionResponse.exception.badVAddr.toBigInt == address)
          assert(!dut.io.instructionResponse.exception.tlbRefill.toBoolean)
          sample(dut)
        }

        def assertDataFault(address: BigInt, isWrite: Boolean, ecode: Int): Unit = {
          translateData(dut, address, isWrite)
          assert(dut.io.dataResponse.exception.valid.toBoolean)
          assert(dut.io.dataResponse.exception.ecode.toBigInt == ecode)
          assert(dut.io.dataResponse.exception.esubcode.toBigInt == 0)
          assert(dut.io.dataResponse.exception.badVAddrValid.toBoolean)
          assert(dut.io.dataResponse.exception.badVAddr.toBigInt == address)
          assert(!dut.io.dataResponse.exception.tlbRefill.toBoolean)
          sample(dut)
        }

        assertInstructionFault(pifAddress, ecode = 3)
        assertDataFault(pilAddress, isWrite = false, ecode = 1)
        assertDataFault(pisAddress, isWrite = true, ecode = 2)
        assertDataFault(pmeAddress, isWrite = true, ecode = 4)

        dut.io.csrPrivilege #= 3
        assertInstructionFault(instructionPpiAddress, ecode = 7)
        assertDataFault(dataPpiAddress, isWrite = false, ecode = 7)
      }
  }

  test("PS=21 translation selects each half and concatenates PPN[19:9] with VA[20:0]") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-address-translation")
      .compile(new OooAddressTranslationUnit(config))
      .doSim("ooo-address-translation-ps21", 0x4c78) { dut =>
        dut.domain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.domain.assertReset()
        dut.domain.waitSampling(2)
        dut.domain.deassertReset()
        sample(dut)

        dut.io.csrDa #= false
        dut.io.csrPg #= true
        val asid = 0x2a
        val evenAddress = BigInt("00401234", 16)
        val oddAddress = evenAddress + (BigInt(1) << 21)
        val ppn0 = BigInt("52345", 16) // PPN[9] = 1
        val ppn1 = BigInt("1a812", 16) // PPN[9] = 0; reverse and non-contiguous
        val evenFlags = tlbLow(0, memoryAttribute = 2, privilege = 0, dirty = true) & 0xff
        val oddFlags = tlbLow(0, memoryAttribute = 0, privilege = 0, dirty = false) & 0xff

        writeTlb(
          dut,
          index = 7,
          virtualAddress = evenAddress,
          ppn0 = ppn0,
          ppn1 = ppn1,
          asid = asid,
          pageSize = 21,
          low0Flags = evenFlags,
          low1Flags = oddFlags
        )

        dut.io.csrTlbIndex #= 7
        sleep(1)
        assert(dut.io.tlbReadEntryHigh.toBigInt == ((evenAddress >> 13) << 13))
        assert(((dut.io.tlbReadEntryLow0.toBigInt >> 8) & 0xfffff) == ppn0)
        assert(((dut.io.tlbReadEntryLow1.toBigInt >> 8) & 0xfffff) == ppn1)
        assert(((dut.io.tlbReadIndex.toBigInt >> 24) & 0x3f) == 21)
        assert(dut.io.tlbReadAsid.toBigInt == asid)

        def expectedPhysical(ppn: BigInt, address: BigInt): BigInt =
          ((ppn >> 9) << 21) | (address & ((BigInt(1) << 21) - 1))

        dut.io.csrPrivilege #= 0
        translateInstruction(dut, evenAddress)
        assert(!dut.io.instructionResponse.exception.valid.toBoolean)
        assert(
          dut.io.instructionResponse.physicalAddress.toBigInt ==
            expectedPhysical(ppn0, evenAddress)
        )
        assert(!dut.io.instructionResponse.uncached.toBoolean)
        sample(dut)

        translateInstruction(dut, oddAddress)
        assert(!dut.io.instructionResponse.exception.valid.toBoolean)
        assert(
          dut.io.instructionResponse.physicalAddress.toBigInt ==
            expectedPhysical(ppn1, oddAddress)
        )
        assert(dut.io.instructionResponse.uncached.toBoolean)
        sample(dut)

        translateData(dut, evenAddress, isWrite = false)
        assert(!dut.io.dataResponse.exception.valid.toBoolean)
        assert(
          dut.io.dataResponse.physicalAddress.toBigInt == expectedPhysical(ppn0, evenAddress)
        )
        assert(!dut.io.dataResponse.uncached.toBoolean)
        sample(dut)

        translateData(dut, oddAddress, isWrite = false)
        assert(!dut.io.dataResponse.exception.valid.toBoolean)
        assert(
          dut.io.dataResponse.physicalAddress.toBigInt == expectedPhysical(ppn1, oddAddress)
        )
        assert(dut.io.dataResponse.uncached.toBoolean)
        sample(dut)

        translateData(dut, oddAddress, isWrite = true)
        assert(dut.io.dataResponse.exception.valid.toBoolean)
        assert(dut.io.dataResponse.exception.ecode.toBigInt == 4)
        assert(dut.io.dataResponse.exception.badVAddr.toBigInt == oddAddress)
        sample(dut)

        dut.io.csrPrivilege #= 3
        translateInstruction(dut, evenAddress)
        assert(dut.io.instructionResponse.exception.valid.toBoolean)
        assert(dut.io.instructionResponse.exception.ecode.toBigInt == 7)
        assert(dut.io.instructionResponse.exception.badVAddr.toBigInt == evenAddress)
        sample(dut)

        dut.io.csrPrivilege #= 0
        dut.io.tlbInvalidateAsid #= asid
        dut.io.tlbInvalidateVpn #= (oddAddress >> 13)
        dut.io.tlbInvalidateOperation #= 6
        dut.io.tlbInvalidateValid #= true
        sample(dut)
        dut.io.tlbInvalidateValid #= false
        translateData(dut, evenAddress, isWrite = false)
        assert(dut.io.dataResponse.exception.valid.toBoolean)
        assert(dut.io.dataResponse.exception.ecode.toBigInt == 0x3f)
        assert(dut.io.dataResponse.exception.tlbRefill.toBoolean)
        sample(dut)

        dut.io.csrTlbIndex #= (BigInt(21) << 24)
        dut.io.csrTlbEntryHigh #= ((evenAddress >> 13) << 13)
        dut.io.csrTlbEntryLow0 #= ((ppn0 << 8) | evenFlags)
        dut.io.csrTlbEntryLow1 #= ((ppn1 << 8) | oddFlags)
        dut.io.tlbRandomIndex #= 11
        dut.io.tlbFillValid #= true
        sample(dut)
        dut.io.tlbFillValid #= false
        translateInstruction(dut, oddAddress)
        assert(!dut.io.instructionResponse.exception.valid.toBoolean)
        assert(
          dut.io.instructionResponse.physicalAddress.toBigInt ==
            expectedPhysical(ppn1, oddAddress)
        )
        assert(dut.io.instructionResponse.uncached.toBoolean)
      }
  }
}
