package openla500.compat

import openla500.config.CoreConfig
import openla500.execute.{OpenLa500Div, OpenLa500LaccCore, OpenLa500Mul}
import openla500.memory.{OpenLa500DCache, OpenLa500ICache, OpenLa500TypedAxiBridge}
import openla500.observe.{ArchState, ChiplabDiffTestAdapter, CommitEvent, OpenLa500PerfCounter}
import openla500.pipeline._
import openla500.predict.OpenLa500Predictor
import openla500.privileged.{OpenLa500AddrTrans, OpenLa500Csr}
import spinal.core._
import spinal.lib._

/** Active SpinalHDL implementation behind the locked chiplab compatibility boundary.
  *
  * The component owns the complete pipeline and the active memory/privileged leaf components.
  * External protocol adaptation remains in [[CoreTopCompat]]. There is one architectural clock;
  * leaf components that retain legacy clock/reset ports receive that same clock and reset.
  */
private[compat] final class SpinalCoreBackend(
    config: CoreConfig = CoreConfig.Locked
) extends Component {
  val io = new Bundle {
    val aclk = in Bool ()
    val aresetn = in Bool ()
    val intrpt = in Bits (8 bits)

    /** Typed AXI3/WID contract; raw chiplab pin names belong only to CoreTopCompat. */
    val axi = master(Axi3Compat())

    val break_point = in Bool ()
    val infor_flag = in Bool ()
    val reg_num = in Bits (5 bits)
    val ws_valid = out Bool ()
    val rf_rdata = out Bits (32 bits)
    val debug0_wb_pc = out Bits (32 bits)
    val debug0_wb_rf_wen = out Bits (4 bits)
    val debug0_wb_rf_wnum = out Bits (5 bits)
    val debug0_wb_rf_wdata = out Bits (32 bits)
    val debug0_wb_inst = out Bits (32 bits)
  }
  noIoPrefix()

  val reset = !io.aresetn

  val fetch = new FetchStage(config)
  val decode = new DecodeStage(config)
  val execute = new ExecuteStage(config)
  val memory = new MemoryStage
  val writeback = new WritebackStage(emitCommit = true, exposeObservation = false)

  fetch.io.downstream >> decode.io.input
  decode.io.output >> execute.io.input
  execute.io.output >> memory.io.input
  memory.io.output >> writeback.io.input

  val csr = new OpenLa500Csr(diffTestEnabled = config.diffTestEnabled, tlbNum = config.tlbEntries)
  val addressTranslation = new OpenLa500AddrTrans
  val instructionCache = new OpenLa500ICache
  val dataCache = new OpenLa500DCache
  val axiBridge = new OpenLa500TypedAxiBridge
  val divider = new OpenLa500Div
  val multiplier = new OpenLa500Mul
  val performanceCounter = new OpenLa500PerfCounter

  for (
    clocked <- Seq(
      csr.io.clk,
      addressTranslation.io.clk,
      instructionCache.io.clk,
      dataCache.io.clk,
      axiBridge.io.clk,
      divider.io.div_clk,
      multiplier.io.mul_clk,
      performanceCounter.io.clk
    )
  ) {
    clocked := io.aclk
  }
  csr.io.reset := reset
  instructionCache.io.reset := reset
  dataCache.io.reset := reset
  axiBridge.io.reset := reset
  divider.io.reset := reset
  multiplier.io.reset := reset
  performanceCounter.io.reset := reset

  performanceCounter.io.events.dataCacheMiss := writeback.io.perf.dataCacheMiss
  performanceCounter.io.events.instructionCacheMiss := writeback.io.perf.instructionCacheMiss
  performanceCounter.io.events.retired := writeback.io.realValid
  performanceCounter.io.events.branch := writeback.io.perf.branch
  performanceCounter.io.events.memoryAccess := writeback.io.perf.memoryAccess
  performanceCounter.io.events.predictedBranch := writeback.io.perf.predictedBranch
  performanceCounter.io.events.predictionError := writeback.io.perf.predictionError

  // Writeback is the only producer of architectural state changes and global pipeline flushes.
  writeback.io.debugBreakPoint := io.break_point
  writeback.io.tlbFillIndex := csr.io.rand_index.asUInt
  decode.io.registerWrite.valid := writeback.io.registerWrite.valid
  decode.io.registerWrite.destination := writeback.io.registerWrite.index
  decode.io.registerWrite.data := writeback.io.registerWrite.data

  decode.io.flush.exception := writeback.io.flush.exception
  decode.io.flush.ertn := writeback.io.flush.ertn
  decode.io.flush.refetch := writeback.io.flush.refetch
  decode.io.flush.instructionCacheOperation := writeback.io.flush.instructionCacheOperation
  decode.io.flush.idle := writeback.io.flush.idle
  execute.io.flush.exception := writeback.io.flush.exception
  execute.io.flush.ertn := writeback.io.flush.ertn
  execute.io.flush.refetch := writeback.io.flush.refetch
  execute.io.flush.instructionCacheOperation := writeback.io.flush.instructionCacheOperation
  execute.io.flush.idle := writeback.io.flush.idle
  memory.io.flush.exception := writeback.io.flush.exception
  memory.io.flush.ertn := writeback.io.flush.ertn
  memory.io.flush.refetch := writeback.io.flush.refetch
  memory.io.flush.instructionCacheOperation := writeback.io.flush.instructionCacheOperation
  memory.io.flush.idle := writeback.io.flush.idle

  fetch.io.exceptionFlush := writeback.io.flush.exception
  fetch.io.ertnFlush := writeback.io.flush.ertn
  fetch.io.refetchFlush := writeback.io.flush.refetch
  fetch.io.instructionCacheFlush := writeback.io.flush.instructionCacheOperation
  fetch.io.idleFlush := writeback.io.flush.idle
  fetch.io.writebackPc := writeback.io.debug.pc

  decode.io.executeForward.writeEnabled := execute.io.forward.writeEnabled
  decode.io.executeForward.dependencyNeedsStall := execute.io.forward.dependencyNeedsStall
  decode.io.executeForward.destination := execute.io.forward.destination
  decode.io.executeForward.data := execute.io.forward.result
  decode.io.memoryForward.writeEnabled := memory.io.forward.writeEnabled
  decode.io.memoryForward.dependencyNeedsStall := memory.io.forward.dependencyNeedsStall
  decode.io.memoryForward.destination := memory.io.forward.destination
  decode.io.memoryForward.data := memory.io.forward.result
  decode.io.executeTlbStall := execute.io.tlbInstructionStall
  decode.io.memoryTlbStall := memory.io.tlbInstructionStall
  decode.io.writebackTlbStall := writeback.io.tlb.instructionStall
  decode.io.executeOccupied := execute.io.forward.valid
  decode.io.memoryOccupied := memory.io.forward.valid
  decode.io.writebackOccupied := writeback.io.stageValid

  fetch.io.branchRepair := decode.io.branchRepair.active
  fetch.io.branchTarget := decode.io.branchRepair.target

  val predictor = new OpenLa500Predictor(config)
  predictor.io.lookup.valid := fetch.io.fetchEnable
  predictor.io.lookup.payload.pc := fetch.io.fetchPc
  fetch.io.btbEnabled := predictor.io.prediction.valid
  fetch.io.btbTaken := predictor.io.prediction.payload.taken
  fetch.io.btbIndex := predictor.io.prediction.payload.legacyIndex
  fetch.io.btbTarget := predictor.io.prediction.payload.target

  predictor.io.update.valid := decode.io.btb.enable
  predictor.io.update.payload.popReturnStack := decode.io.btb.popReturnStack
  predictor.io.update.payload.pushReturnStack := decode.io.btb.pushReturnStack
  predictor.io.update.payload.addEntry := decode.io.btb.addEntry
  predictor.io.update.payload.predictionError := decode.io.btb.predictionError
  predictor.io.update.payload.predictionRight := decode.io.btb.predictionRight
  predictor.io.update.payload.targetError := decode.io.btb.targetError
  predictor.io.update.payload.actualTaken := decode.io.btb.actualTaken
  predictor.io.update.payload.actualTarget := decode.io.btb.actualTarget
  predictor.io.update.payload.pc := decode.io.btb.pc
  predictor.io.update.payload.legacyIndex := decode.io.btb.index

  // CSR and precise exception/state-update wiring.
  csr.io.rd_addr := decode.io.csrReadAddress.asBits
  decode.io.csrReadData := csr.io.rd_data
  decode.io.csrPrivilege := csr.io.plv_out
  decode.io.timer := csr.io.timer_64_out
  decode.io.timerId := csr.io.tid_out
  decode.io.reservationValid := csr.io.llbit_out
  decode.io.interruptPending := csr.io.has_int
  fetch.io.interrupt := csr.io.has_int
  csr.io.csr_wr_en := writeback.io.csrWrite.valid
  csr.io.wr_addr := writeback.io.csrWrite.address.asBits
  csr.io.wr_data := writeback.io.csrWrite.data
  csr.io.interrupt := io.intrpt
  csr.io.excp_flush := writeback.io.exception.valid
  csr.io.ertn_flush := writeback.io.flush.ertn
  csr.io.era_in := writeback.io.debug.pc.asBits
  csr.io.esubcode_in := writeback.io.exception.esubcode.asBits
  csr.io.ecode_in := writeback.io.exception.ecode.asBits
  csr.io.va_error_in := writeback.io.exception.badVAddrValid
  csr.io.bad_va_in := writeback.io.exception.badVAddr.asBits
  csr.io.tlbsrch_en := writeback.io.tlb.search
  csr.io.tlbsrch_found := writeback.io.tlb.searchFound
  csr.io.tlbsrch_index := writeback.io.tlb.searchIndex.asBits
  csr.io.excp_tlbrefill := writeback.io.exception.tlbRefill
  csr.io.excp_tlb := writeback.io.exception.tlbException
  csr.io.excp_tlb_vppn := writeback.io.exception.tlbVppn.asBits
  csr.io.llbit_in := writeback.io.reservation.bitValue
  csr.io.llbit_set_in := writeback.io.reservation.bitSet
  csr.io.lladdr_in := writeback.io.reservation.lineAddress.asBits
  csr.io.lladdr_set_in := writeback.io.reservation.addressSet
  fetch.io.exceptionEntry := csr.io.eentry_out.asUInt
  fetch.io.exceptionEra := csr.io.era_out.asUInt
  fetch.io.exceptionTlbRefill := writeback.io.exception.tlbRefill
  fetch.io.tlbRefillEntry := csr.io.tlbrentry_out.asUInt

  fetch.io.paging := csr.io.pg_out
  fetch.io.directAddress := csr.io.da_out
  fetch.io.dmw0 := csr.io.dmw0_out
  fetch.io.dmw1 := csr.io.dmw1_out
  fetch.io.currentPlv := csr.io.plv_out.asUInt
  fetch.io.directFetchMat := csr.io.datf_out
  fetch.io.disableCache := csr.io.disable_cache_out
  execute.io.csrVirtualPageNumber := csr.io.vppn_out.asUInt
  memory.io.csrPage := csr.io.pg_out
  memory.io.csrDirectAddress := csr.io.da_out
  memory.io.csrDmw0Plv0 := csr.io.dmw0_out(0)
  memory.io.csrDmw0Plv3 := csr.io.dmw0_out(3)
  memory.io.csrDmw0VirtualSegment := csr.io.dmw0_out(31 downto 29)
  memory.io.csrDmw0MemoryAttribute := csr.io.dmw0_out(5 downto 4)
  memory.io.csrDmw1Plv0 := csr.io.dmw1_out(0)
  memory.io.csrDmw1Plv3 := csr.io.dmw1_out(3)
  memory.io.csrDmw1VirtualSegment := csr.io.dmw1_out(31 downto 29)
  memory.io.csrDmw1MemoryAttribute := csr.io.dmw1_out(5 downto 4)
  memory.io.csrPlv := csr.io.plv_out
  memory.io.csrDatm := csr.io.datm_out
  memory.io.disableCache := csr.io.disable_cache_out
  memory.io.llAddress := csr.io.lladdr_out

  // TLB ownership and address translation.
  addressTranslation.io.asid := csr.io.asid_out
  addressTranslation.io.inst_addr_trans_en := fetch.io.addressTranslation
  addressTranslation.io.inst_fetch := fetch.io.fetchEnable
  addressTranslation.io.inst_vaddr := fetch.io.instructionAddress.asBits
  addressTranslation.io.inst_dmw0_en := fetch.io.dmw0Enabled
  addressTranslation.io.inst_dmw1_en := fetch.io.dmw1Enabled
  fetch.io.tlbFound := addressTranslation.io.inst_tlb_found
  fetch.io.tlbValid := addressTranslation.io.inst_tlb_v
  fetch.io.tlbMat := addressTranslation.io.inst_tlb_mat
  fetch.io.tlbPlv := addressTranslation.io.inst_tlb_plv.asUInt

  addressTranslation.io.data_addr_trans_en := memory.io.dataAddressTranslationEnable
  addressTranslation.io.data_fetch := execute.io.dataFetch
  addressTranslation.io.data_vaddr := execute.io.memory.virtualAddress.asBits
  addressTranslation.io.data_dmw0_en := memory.io.dmw0Enable
  addressTranslation.io.data_dmw1_en := memory.io.dmw1Enable
  addressTranslation.io.cacop_op_mode_di := memory.io.cacopModeDi
  memory.io.dataIndexDiff := addressTranslation.io.data_index
  memory.io.dataTagDiff := addressTranslation.io.data_tag
  memory.io.dataOffsetDiff := addressTranslation.io.data_offset
  memory.io.dataTlbFound := addressTranslation.io.data_tlb_found
  memory.io.dataTlbIndex := addressTranslation.io.data_tlb_index.asUInt
  memory.io.dataTlbValid := addressTranslation.io.data_tlb_v
  memory.io.dataTlbDirty := addressTranslation.io.data_tlb_d
  memory.io.dataTlbMat := addressTranslation.io.data_tlb_mat
  memory.io.dataTlbPlv := addressTranslation.io.data_tlb_plv
  memory.io.dataTlbPpn := addressTranslation.io.data_tag

  addressTranslation.io.tlbfill_en := writeback.io.tlb.fill
  addressTranslation.io.tlbwr_en := writeback.io.tlb.write
  addressTranslation.io.rand_index := csr.io.rand_index.asUInt
  addressTranslation.io.tlbehi_in := csr.io.tlbehi_out
  addressTranslation.io.tlbelo0_in := csr.io.tlbelo0_out
  addressTranslation.io.tlbelo1_in := csr.io.tlbelo1_out
  addressTranslation.io.tlbidx_in := csr.io.tlbidx_out
  addressTranslation.io.ecode_in := csr.io.ecode_out
  addressTranslation.io.invtlb_en := writeback.io.tlb.invalidate
  addressTranslation.io.invtlb_asid := writeback.io.tlb.invalidateAsid
  addressTranslation.io.invtlb_vpn := writeback.io.tlb.invalidateVpn
  addressTranslation.io.invtlb_op := writeback.io.tlb.invalidateOperation
  addressTranslation.io.csr_dmw0 := csr.io.dmw0_out
  addressTranslation.io.csr_dmw1 := csr.io.dmw1_out
  addressTranslation.io.csr_da := csr.io.da_out
  addressTranslation.io.csr_pg := csr.io.pg_out
  csr.io.tlbrd_en := writeback.io.tlb.read
  csr.io.tlbehi_in := addressTranslation.io.tlbehi_out
  csr.io.tlbelo0_in := addressTranslation.io.tlbelo0_out
  csr.io.tlbelo1_in := addressTranslation.io.tlbelo1_out
  csr.io.tlbidx_in := addressTranslation.io.tlbidx_out
  csr.io.asid_in := addressTranslation.io.asid_out

  if (config.diffTestEnabled) {
    val architecturalCommit = Flow(CommitEvent())
    architecturalCommit := writeback.io.commit

    val architecturalState = ArchState()
    for (index <- 0 until 32) {
      architecturalState.gpr(index) := (if (index == 0) B(0, 32 bits)
                                        else decode.io.registers(index))
    }
    architecturalState.crmd := csr.io.csr_crmd_diff
    architecturalState.prmd := csr.io.csr_prmd_diff
    architecturalState.euen := 0
    architecturalState.ecfg := csr.io.csr_ectl_diff
    architecturalState.estat := csr.io.csr_estat_diff
    architecturalState.era := csr.io.csr_era_diff
    architecturalState.badv := csr.io.csr_badv_diff
    architecturalState.eentry := csr.io.csr_eentry_diff
    architecturalState.tlbidx := csr.io.csr_tlbidx_diff
    architecturalState.tlbehi := csr.io.csr_tlbehi_diff
    architecturalState.tlbelo0 := csr.io.csr_tlbelo0_diff
    architecturalState.tlbelo1 := csr.io.csr_tlbelo1_diff
    architecturalState.asid := csr.io.csr_asid_diff
    architecturalState.pgdl := csr.io.csr_pgdl_diff
    architecturalState.pgdh := csr.io.csr_pgdh_diff
    architecturalState.save0 := csr.io.csr_save0_diff
    architecturalState.save1 := csr.io.csr_save1_diff
    architecturalState.save2 := csr.io.csr_save2_diff
    architecturalState.save3 := csr.io.csr_save3_diff
    architecturalState.tid := csr.io.csr_tid_diff
    architecturalState.tcfg := csr.io.csr_tcfg_diff
    architecturalState.tval := csr.io.csr_tval_diff
    architecturalState.ticlr := csr.io.csr_ticlr_diff
    architecturalState.llbctl := csr.io.csr_llbctl_diff
    architecturalState.tlbrentry := csr.io.csr_tlbrentry_diff
    architecturalState.dmw0 := csr.io.csr_dmw0_diff
    architecturalState.dmw1 := csr.io.csr_dmw1_diff

    val diffTest = new ChiplabDiffTestAdapter
    diffTest.io.clock := io.aclk
    diffTest.io.commit := architecturalCommit
    diffTest.io.archState := architecturalState
  }

  // Instruction cache request/response and its bridge-side refill channels.
  instructionCache.io.valid := fetch.io.instructionRequest
  instructionCache.io.op := False
  instructionCache.io.index := addressTranslation.io.inst_index
  instructionCache.io.tag := addressTranslation.io.inst_tag
  instructionCache.io.offset := addressTranslation.io.inst_offset
  instructionCache.io.wstrb := 0
  instructionCache.io.wdata := 0
  instructionCache.io.uncache_en := fetch.io.instructionUncached
  instructionCache.io.icacop_op_en := execute.io.cache.instructionOperationEnable
  instructionCache.io.cacop_op_mode := execute.io.cache.operationMode
  instructionCache.io.cacop_op_addr_index := addressTranslation.io.data_index
  instructionCache.io.cacop_op_addr_tag := addressTranslation.io.data_tag
  instructionCache.io.cacop_op_addr_offset := addressTranslation.io.data_offset
  instructionCache.io.tlb_excp_cancel_req := fetch.io.tlbCancel
  fetch.io.instructionAddressAccepted := instructionCache.io.addr_ok
  fetch.io.instructionDataValid := instructionCache.io.data_ok
  fetch.io.instructionData := instructionCache.io.rdata
  fetch.io.instructionMiss := instructionCache.io.cache_miss
  execute.io.instructionCacheUnbusy := instructionCache.io.icache_unbusy

  // Data cache request/response. EXE owns request creation; MEM owns translation/cancellation.
  dataCache.io.valid := execute.io.memory.valid
  dataCache.io.op := execute.io.memory.isWrite
  dataCache.io.size := execute.io.memory.size
  dataCache.io.index := addressTranslation.io.data_index
  dataCache.io.tag := addressTranslation.io.data_tag
  dataCache.io.offset := addressTranslation.io.data_offset
  dataCache.io.wstrb := execute.io.memory.byteMask
  dataCache.io.wdata := execute.io.memory.writeData
  dataCache.io.uncache_en := memory.io.dataUncached
  dataCache.io.dcacop_op_en := execute.io.cache.dataOperationEnable
  dataCache.io.cacop_op_mode := execute.io.cache.operationMode
  dataCache.io.preld_hint := execute.io.cache.preloadHint
  dataCache.io.preld_en := execute.io.cache.preloadEnable
  dataCache.io.tlb_excp_cancel_req := memory.io.tlbExceptionCancel
  dataCache.io.sc_cancel_req := memory.io.scCancel
  execute.io.memoryAddressAccepted := dataCache.io.addr_ok
  memory.io.dataDataOk := dataCache.io.data_ok
  memory.io.dcacheMiss := dataCache.io.cache_miss
  memory.io.dataReadData := dataCache.io.rdata
  decode.io.dataCacheEmpty := dataCache.io.dcache_empty
  execute.io.memoryWritesTlbEntryHigh := memory.io.writeTlbEntryHigh
  execute.io.memoryFlush := memory.io.stageFlush

  if (config.laccEnabled) {
    val accelerator = new OpenLa500LaccCore
    accelerator.io.clk := io.aclk
    accelerator.io.reset := reset
    accelerator.io.flush := execute.io.laccOutput.flush
    accelerator.io.request.valid := execute.io.laccOutput.request
    accelerator.io.request.payload.command := execute.io.laccOutput.command
    accelerator.io.request.payload.immediate := execute.io.laccOutput.immediate
    accelerator.io.request.payload.registerJ := execute.io.mulDiv.operandJ
    accelerator.io.request.payload.registerK := execute.io.mulDiv.operandKOrD

    execute.io.laccInput.requestReady := False
    execute.io.laccInput.responseValid := accelerator.io.response.valid
    execute.io.laccInput.responseData := accelerator.io.response.payload.data
    execute.io.laccInput.dataValid := accelerator.io.memoryRequest.valid
    execute.io.laccInput.dataRead := accelerator.io.memoryRequest.payload.read
    execute.io.laccInput.dataAddress := accelerator.io.memoryRequest.payload.address
    execute.io.laccInput.dataWriteData := accelerator.io.memoryRequest.payload.writeData
    execute.io.laccInput.dataSize := accelerator.io.memoryRequest.payload.size
    execute.io.laccInput.dataAccepted := dataCache.io.data_ok

    accelerator.io.memoryRequest.ready := dataCache.io.addr_ok
    accelerator.io.memoryResponse.valid := execute.io.laccOutput.dataResponseValid
    accelerator.io.memoryResponse.payload.data := dataCache.io.rdata
  }

  // Divider and multiplier retain their verified cycle-level leaf contracts.
  divider.io.div := execute.io.mulDiv.divideEnable
  divider.io.div_signed := execute.io.mulDiv.signed
  divider.io.x := execute.io.mulDiv.operandJ
  divider.io.y := execute.io.mulDiv.operandKOrD
  execute.io.divideComplete := divider.io.complete
  multiplier.io.mul_signed := execute.io.mulDiv.signed
  multiplier.io.x := execute.io.mulDiv.operandJ
  multiplier.io.y := execute.io.mulDiv.operandKOrD
  memory.io.divResult := divider.io.s
  memory.io.modResult := divider.io.r
  memory.io.mulResult := multiplier.io.result

  // Cache refill/writeback channels are arbitrated only by the verified AXI bridge.
  axiBridge.io.inst.read.valid := instructionCache.io.rd_req
  axiBridge.io.inst.read.payload.requestType := instructionCache.io.rd_type
  axiBridge.io.inst.read.payload.address := instructionCache.io.rd_addr.asUInt
  instructionCache.io.rd_rdy := axiBridge.io.inst.read.ready
  instructionCache.io.ret_valid := axiBridge.io.inst.readResponse.valid
  instructionCache.io.ret_last := axiBridge.io.inst.readResponse.payload.last
  instructionCache.io.ret_data := axiBridge.io.inst.readResponse.payload.data
  axiBridge.io.inst.write.valid := instructionCache.io.wr_req
  axiBridge.io.inst.write.payload.requestType := instructionCache.io.wr_type
  axiBridge.io.inst.write.payload.address := instructionCache.io.wr_addr.asUInt
  axiBridge.io.inst.write.payload.byteMask := instructionCache.io.wr_wstrb
  axiBridge.io.inst.write.payload.data := instructionCache.io.wr_data
  instructionCache.io.wr_rdy := axiBridge.io.inst.write.ready

  axiBridge.io.data.read.valid := dataCache.io.rd_req
  axiBridge.io.data.read.payload.requestType := dataCache.io.rd_type
  axiBridge.io.data.read.payload.address := dataCache.io.rd_addr.asUInt
  dataCache.io.rd_rdy := axiBridge.io.data.read.ready
  dataCache.io.ret_valid := axiBridge.io.data.readResponse.valid
  dataCache.io.ret_last := axiBridge.io.data.readResponse.payload.last
  dataCache.io.ret_data := axiBridge.io.data.readResponse.payload.data
  axiBridge.io.data.write.valid := dataCache.io.wr_req
  axiBridge.io.data.write.payload.requestType := dataCache.io.wr_type
  axiBridge.io.data.write.payload.address := dataCache.io.wr_addr.asUInt
  axiBridge.io.data.write.payload.byteMask := dataCache.io.wr_wstrb
  axiBridge.io.data.write.payload.data := dataCache.io.wr_data
  dataCache.io.wr_rdy := axiBridge.io.data.write.ready
  decode.io.writeBufferEmpty := axiBridge.io.writeBufferEmpty

  // Locked external AXI3/WID boundary.
  axiBridge.io.axi.ar.ready := io.axi.ar.ready
  axiBridge.io.axi.r.payload.id := io.axi.r.payload.id
  axiBridge.io.axi.r.payload.data := io.axi.r.payload.data
  axiBridge.io.axi.r.payload.response := io.axi.r.payload.response
  axiBridge.io.axi.r.payload.last := io.axi.r.payload.last
  axiBridge.io.axi.r.valid := io.axi.r.valid
  axiBridge.io.axi.aw.ready := io.axi.aw.ready
  axiBridge.io.axi.w.ready := io.axi.w.ready
  axiBridge.io.axi.b.payload.id := io.axi.b.payload.id
  axiBridge.io.axi.b.payload.response := io.axi.b.payload.response
  axiBridge.io.axi.b.valid := io.axi.b.valid

  io.axi.ar.payload.id := axiBridge.io.axi.ar.payload.id
  io.axi.ar.payload.address := axiBridge.io.axi.ar.payload.address
  io.axi.ar.payload.len := axiBridge.io.axi.ar.payload.len
  io.axi.ar.payload.size := axiBridge.io.axi.ar.payload.size
  io.axi.ar.payload.burst := axiBridge.io.axi.ar.payload.burst
  io.axi.ar.payload.lock := axiBridge.io.axi.ar.payload.lock
  io.axi.ar.payload.cache := axiBridge.io.axi.ar.payload.cache
  io.axi.ar.payload.prot := axiBridge.io.axi.ar.payload.prot
  io.axi.ar.valid := axiBridge.io.axi.ar.valid
  io.axi.r.ready := axiBridge.io.axi.r.ready
  io.axi.aw.payload.id := axiBridge.io.axi.aw.payload.id
  io.axi.aw.payload.address := axiBridge.io.axi.aw.payload.address
  io.axi.aw.payload.len := axiBridge.io.axi.aw.payload.len
  io.axi.aw.payload.size := axiBridge.io.axi.aw.payload.size
  io.axi.aw.payload.burst := axiBridge.io.axi.aw.payload.burst
  io.axi.aw.payload.lock := axiBridge.io.axi.aw.payload.lock
  io.axi.aw.payload.cache := axiBridge.io.axi.aw.payload.cache
  io.axi.aw.payload.prot := axiBridge.io.axi.aw.payload.prot
  io.axi.aw.valid := axiBridge.io.axi.aw.valid
  io.axi.w.payload.id := axiBridge.io.axi.w.payload.id
  io.axi.w.payload.data := axiBridge.io.axi.w.payload.data
  io.axi.w.payload.byteMask := axiBridge.io.axi.w.payload.byteMask
  io.axi.w.payload.last := axiBridge.io.axi.w.payload.last
  io.axi.w.valid := axiBridge.io.axi.w.valid
  io.axi.b.ready := axiBridge.io.axi.b.ready

  decode.io.debugReadSelect := io.infor_flag
  decode.io.debugReadAddress := io.reg_num.asUInt
  io.rf_rdata := decode.io.debugLegacyValue
  io.ws_valid := writeback.io.debug.stageValid
  io.debug0_wb_pc := writeback.io.debug.pc.asBits
  io.debug0_wb_rf_wen := writeback.io.debug.gprWriteMask
  io.debug0_wb_rf_wnum := writeback.io.debug.gprIndex.asBits
  io.debug0_wb_rf_wdata := writeback.io.debug.gprData
  io.debug0_wb_inst := writeback.io.debug.instruction
}
