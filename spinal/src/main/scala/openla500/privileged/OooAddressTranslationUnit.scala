package openla500.privileged

import openla500.backend.OooExceptionMeta
import openla500.core._
import spinal.core._
import spinal.lib._

final case class OooTranslationRequest(config: OooCoreConfig) extends Bundle {
  val virtualAddress = UInt(config.xlen bits)
  val isWrite = Bool()
}

final case class OooTranslationResponse(config: OooCoreConfig) extends Bundle {
  val virtualAddress = UInt(config.xlen bits)
  val physicalAddress = UInt(config.xlen bits)
  val uncached = Bool()
  val exception = OooExceptionMeta()
}

final case class OooTranslationContext(config: OooCoreConfig) extends Bundle {
  val virtualAddress = UInt(config.xlen bits)
  val isWrite = Bool()
  val translationEnabled = Bool()
  val dmw0Enabled = Bool()
  val dmw1Enabled = Bool()
  val memoryAttribute = Bits(2 bits)
  val privilege = Bits(2 bits)
  val disableCache = Bool()
}

/** Shared two-port LA32R translator around the verified 32-entry TLB storage. */
final class OooAddressTranslationUnit(
    config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit
) extends Component {
  val io = new Bundle {
    val clk = in Bool ()
    val reset = in Bool ()
    val instructionRequest = slave(Stream(OooTranslationRequest(config)))
    val instructionResponse = master(Stream(OooTranslationResponse(config)))
    val dataRequest = slave(Stream(OooTranslationRequest(config)))
    val dataResponse = master(Stream(OooTranslationResponse(config)))

    val csrAsid = in Bits (10 bits)
    val csrDa = in Bool ()
    val csrPg = in Bool ()
    val csrDmw0 = in Bits (32 bits)
    val csrDmw1 = in Bits (32 bits)
    val csrPrivilege = in Bits (2 bits)
    val instructionMat = in Bits (2 bits)
    val dataMat = in Bits (2 bits)
    val disableCache = in Bool ()

    val tlbFillValid = in Bool ()
    val tlbWriteValid = in Bool ()
    val tlbRandomIndex = in UInt (5 bits)
    val csrTlbEntryHigh = in Bits (32 bits)
    val csrTlbEntryLow0 = in Bits (32 bits)
    val csrTlbEntryLow1 = in Bits (32 bits)
    val csrTlbIndex = in Bits (32 bits)
    val csrExceptionCode = in Bits (6 bits)
    val tlbReadEntryHigh = out Bits (32 bits)
    val tlbReadEntryLow0 = out Bits (32 bits)
    val tlbReadEntryLow1 = out Bits (32 bits)
    val tlbReadIndex = out Bits (32 bits)
    val tlbReadAsid = out Bits (10 bits)

    val tlbInvalidateValid = in Bool ()
    val tlbInvalidateAsid = in Bits (10 bits)
    val tlbInvalidateVpn = in Bits (19 bits)
    val tlbInvalidateOperation = in Bits (5 bits)

    val tlbSearchValid = in Bool ()
    val tlbSearchVppn = in Bits (19 bits)
    val tlbSearchReady = out Bool ()
    val tlbSearchResponseValid = out Bool ()
    val tlbSearchFound = out Bool ()
    val tlbSearchIndex = out Bits (5 bits)
  }
  noIoPrefix()

  val domain = ClockDomain(
    clock = io.clk,
    reset = io.reset,
    config = ClockDomainConfig(clockEdge = RISING, resetKind = SYNC, resetActiveLevel = HIGH)
  )

  val area = new ClockingArea(domain) {
    val translator = new OpenLa500AddrTrans(managementSearchEnabled = true)
    translator.io.clk := io.clk
    translator.io.asid := io.csrAsid
    translator.io.tlbfill_en := io.tlbFillValid
    translator.io.tlbwr_en := io.tlbWriteValid
    translator.io.rand_index := io.tlbRandomIndex
    translator.io.tlbehi_in := io.csrTlbEntryHigh
    translator.io.tlbelo0_in := io.csrTlbEntryLow0
    translator.io.tlbelo1_in := io.csrTlbEntryLow1
    translator.io.tlbidx_in := io.csrTlbIndex
    translator.io.ecode_in := io.csrExceptionCode
    translator.io.invtlb_en := io.tlbInvalidateValid
    translator.io.invtlb_asid := io.tlbInvalidateAsid
    translator.io.invtlb_vpn := io.tlbInvalidateVpn
    translator.io.invtlb_op := io.tlbInvalidateOperation
    translator.io.csr_dmw0 := io.csrDmw0
    translator.io.csr_dmw1 := io.csrDmw1
    translator.io.csr_da := io.csrDa
    translator.io.csr_pg := io.csrPg
    translator.io.management_search_vppn := io.tlbSearchVppn

    io.tlbReadEntryHigh := translator.io.tlbehi_out
    io.tlbReadEntryLow0 := translator.io.tlbelo0_out
    io.tlbReadEntryLow1 := translator.io.tlbelo1_out
    io.tlbReadIndex := translator.io.tlbidx_out
    io.tlbReadAsid := translator.io.asid_out

    val pagingMode = !io.csrDa && io.csrPg
    def dmwEnabled(address: UInt, dmw: Bits): Bool =
      pagingMode && address(31 downto 29) === dmw(31 downto 29).asUInt &&
        ((io.csrPrivilege === 0 && dmw(0)) || (io.csrPrivilege === 3 && dmw(3)))

    def bypassPhysicalAddress(address: UInt, dmw0Enabled: Bool, dmw1Enabled: Bool): UInt = {
      val physicalAddress = UInt(config.xlen bits)
      physicalAddress := address
      when(dmw0Enabled) {
        physicalAddress := (io.csrDmw0(27 downto 25) ## address(28 downto 0)).asUInt
      }.elsewhen(dmw1Enabled) {
        physicalAddress := (io.csrDmw1(27 downto 25) ## address(28 downto 0)).asUInt
      }
      physicalAddress
    }

    val instructionContext = Reg(OooTranslationContext(config))
    val instructionSearchPending = RegInit(False)
    val instructionResponseValid = RegInit(False)
    val instructionResponse = Reg(OooTranslationResponse(config))
    val instructionDmw0 = dmwEnabled(io.instructionRequest.virtualAddress, io.csrDmw0)
    val instructionDmw1 = dmwEnabled(io.instructionRequest.virtualAddress, io.csrDmw1)
    val instructionTranslate = pagingMode && !instructionDmw0 && !instructionDmw1
    val instructionRequestReady = !instructionSearchPending && !instructionResponseValid
    io.instructionRequest.ready := instructionRequestReady
    val instructionRequestFire = io.instructionRequest.valid && io.instructionRequest.ready
    when(instructionRequestFire) {
      instructionContext.virtualAddress := io.instructionRequest.virtualAddress
      instructionContext.isWrite := False
      instructionContext.translationEnabled := instructionTranslate
      instructionContext.dmw0Enabled := instructionDmw0
      instructionContext.dmw1Enabled := instructionDmw1
      instructionContext.memoryAttribute := Mux(
        instructionDmw0,
        io.csrDmw0(5 downto 4),
        Mux(instructionDmw1, io.csrDmw1(5 downto 4), io.instructionMat)
      )
      instructionContext.privilege := io.csrPrivilege
      instructionContext.disableCache := io.disableCache
      instructionSearchPending := instructionTranslate
      when(!instructionTranslate) {
        val misaligned = io.instructionRequest.virtualAddress(1 downto 0) =/= 0
        val memoryAttribute = Mux(
          instructionDmw0,
          io.csrDmw0(5 downto 4),
          Mux(instructionDmw1, io.csrDmw1(5 downto 4), io.instructionMat)
        )
        instructionResponseValid := True
        instructionResponse.virtualAddress := io.instructionRequest.virtualAddress
        instructionResponse.physicalAddress := bypassPhysicalAddress(
          io.instructionRequest.virtualAddress,
          instructionDmw0,
          instructionDmw1
        )
        instructionResponse.uncached := io.disableCache || memoryAttribute === 0
        instructionResponse.exception.valid := misaligned
        instructionResponse.exception.ecode := Mux(misaligned, U(8, 6 bits), U(0, 6 bits))
        instructionResponse.exception.esubcode := 0
        instructionResponse.exception.badVAddrValid := misaligned
        instructionResponse.exception.badVAddr := io.instructionRequest.virtualAddress
        instructionResponse.exception.tlbRefill := False
      }
    }
    when(io.instructionResponse.valid && io.instructionResponse.ready) {
      instructionResponseValid := False
    }

    val instructionDriveAddress = Mux(
      instructionRequestFire,
      io.instructionRequest.virtualAddress,
      instructionContext.virtualAddress
    )
    translator.io.inst_fetch := instructionRequestFire && instructionTranslate
    translator.io.inst_vaddr := instructionDriveAddress.asBits
    translator.io.inst_addr_trans_en := Mux(
      instructionRequestFire,
      instructionTranslate,
      instructionContext.translationEnabled
    )
    translator.io.inst_dmw0_en := Mux(
      instructionRequestFire,
      instructionDmw0,
      instructionContext.dmw0Enabled
    )
    translator.io.inst_dmw1_en := Mux(
      instructionRequestFire,
      instructionDmw1,
      instructionContext.dmw1Enabled
    )

    when(instructionSearchPending) {
      val misaligned = instructionContext.virtualAddress(1 downto 0) =/= 0
      val refill = instructionContext.translationEnabled && !translator.io.inst_tlb_found
      val invalid = instructionContext.translationEnabled && translator.io.inst_tlb_found &&
        !translator.io.inst_tlb_v
      val privilege = instructionContext.translationEnabled && translator.io.inst_tlb_found &&
        translator.io.inst_tlb_v &&
        instructionContext.privilege.asUInt > translator.io.inst_tlb_plv.asUInt
      instructionSearchPending := False
      instructionResponseValid := True
      instructionResponse.virtualAddress := instructionContext.virtualAddress
      instructionResponse.physicalAddress :=
        (translator.io.inst_tag ## instructionContext.virtualAddress(11 downto 0)).asUInt
      instructionResponse.uncached := instructionContext.disableCache ||
        Mux(
          instructionContext.translationEnabled,
          translator.io.inst_tlb_mat,
          instructionContext.memoryAttribute
        ) === 0
      instructionResponse.exception.valid := misaligned || refill || invalid || privilege
      instructionResponse.exception.ecode := Mux(
        misaligned,
        U(8, 6 bits),
        Mux(
          refill,
          U(0x3f, 6 bits),
          Mux(invalid, U(3, 6 bits), Mux(privilege, U(7, 6 bits), U(0, 6 bits)))
        )
      )
      instructionResponse.exception.esubcode := 0
      instructionResponse.exception.badVAddrValid := misaligned || refill || invalid || privilege
      instructionResponse.exception.badVAddr := instructionContext.virtualAddress
      instructionResponse.exception.tlbRefill := !misaligned && refill
    }
    io.instructionResponse.valid := instructionResponseValid
    io.instructionResponse.payload := instructionResponse

    val dataContext = Reg(OooTranslationContext(config))
    val dataSearchPending = RegInit(False)
    val dataResponseValid = RegInit(False)
    val dataResponse = Reg(OooTranslationResponse(config))
    val dataDmw0 = dmwEnabled(io.dataRequest.virtualAddress, io.csrDmw0)
    val dataDmw1 = dmwEnabled(io.dataRequest.virtualAddress, io.csrDmw1)
    val dataTranslate = pagingMode && !dataDmw0 && !dataDmw1
    val dataRequestReady = !dataSearchPending && !dataResponseValid
    io.dataRequest.ready := dataRequestReady
    val dataRequestFire = io.dataRequest.valid && io.dataRequest.ready
    io.tlbSearchReady := True
    when(dataRequestFire) {
      dataContext.virtualAddress := io.dataRequest.virtualAddress
      dataContext.isWrite := io.dataRequest.isWrite
      dataContext.translationEnabled := dataTranslate
      dataContext.dmw0Enabled := dataDmw0
      dataContext.dmw1Enabled := dataDmw1
      dataContext.memoryAttribute := Mux(
        dataDmw0,
        io.csrDmw0(5 downto 4),
        Mux(dataDmw1, io.csrDmw1(5 downto 4), io.dataMat)
      )
      dataContext.privilege := io.csrPrivilege
      dataContext.disableCache := io.disableCache
      dataSearchPending := dataTranslate
      when(!dataTranslate) {
        val memoryAttribute = Mux(
          dataDmw0,
          io.csrDmw0(5 downto 4),
          Mux(dataDmw1, io.csrDmw1(5 downto 4), io.dataMat)
        )
        dataResponseValid := True
        dataResponse.virtualAddress := io.dataRequest.virtualAddress
        dataResponse.physicalAddress := bypassPhysicalAddress(
          io.dataRequest.virtualAddress,
          dataDmw0,
          dataDmw1
        )
        dataResponse.uncached := io.disableCache || memoryAttribute === 0
        dataResponse.exception.valid := False
        dataResponse.exception.ecode := 0
        dataResponse.exception.esubcode := 0
        dataResponse.exception.badVAddrValid := False
        dataResponse.exception.badVAddr := io.dataRequest.virtualAddress
        dataResponse.exception.tlbRefill := False
      }
    }
    when(io.dataResponse.valid && io.dataResponse.ready) { dataResponseValid := False }

    val dataDriveAddress = UInt(config.xlen bits)
    dataDriveAddress := dataContext.virtualAddress
    when(dataRequestFire) { dataDriveAddress := io.dataRequest.virtualAddress }
    translator.io.data_fetch := dataRequestFire
    translator.io.data_vaddr := dataDriveAddress.asBits
    translator.io.data_addr_trans_en := Mux(
      dataRequestFire,
      dataTranslate,
      dataContext.translationEnabled
    )
    translator.io.data_dmw0_en := Mux(dataRequestFire, dataDmw0, dataContext.dmw0Enabled)
    translator.io.data_dmw1_en := Mux(dataRequestFire, dataDmw1, dataContext.dmw1Enabled)
    translator.io.cacop_op_mode_di := False

    when(dataSearchPending) {
      val refill = dataContext.translationEnabled && !translator.io.data_tlb_found
      val invalid = dataContext.translationEnabled && translator.io.data_tlb_found &&
        !translator.io.data_tlb_v
      val privilege = dataContext.translationEnabled && translator.io.data_tlb_found &&
        translator.io.data_tlb_v &&
        dataContext.privilege.asUInt > translator.io.data_tlb_plv.asUInt
      val modify = dataContext.translationEnabled && dataContext.isWrite &&
        translator.io.data_tlb_found && translator.io.data_tlb_v && !privilege &&
        !translator.io.data_tlb_d
      dataSearchPending := False
      dataResponseValid := True
      dataResponse.virtualAddress := dataContext.virtualAddress
      dataResponse.physicalAddress :=
        (translator.io.data_tag ## dataContext.virtualAddress(11 downto 0)).asUInt
      dataResponse.uncached := dataContext.disableCache ||
        Mux(
          dataContext.translationEnabled,
          translator.io.data_tlb_mat,
          dataContext.memoryAttribute
        ) === 0
      dataResponse.exception.valid := refill || invalid || privilege || modify
      dataResponse.exception.ecode := Mux(
        refill,
        U(0x3f, 6 bits),
        Mux(
          invalid,
          Mux(dataContext.isWrite, U(2, 6 bits), U(1, 6 bits)),
          Mux(privilege, U(7, 6 bits), Mux(modify, U(4, 6 bits), U(0, 6 bits)))
        )
      )
      dataResponse.exception.esubcode := 0
      dataResponse.exception.badVAddrValid := refill || invalid || privilege || modify
      dataResponse.exception.badVAddr := dataContext.virtualAddress
      dataResponse.exception.tlbRefill := refill
    }
    io.dataResponse.valid := dataResponseValid
    io.dataResponse.payload := dataResponse
    // Management search is combinational, matching the architectural TLBSRCH
    // boundary: TLBIDX is updated on the same edge that retires the instruction.
    io.tlbSearchResponseValid := io.tlbSearchValid
    io.tlbSearchFound := translator.io.management_search_found
    io.tlbSearchIndex := translator.io.management_search_index
  }
}
