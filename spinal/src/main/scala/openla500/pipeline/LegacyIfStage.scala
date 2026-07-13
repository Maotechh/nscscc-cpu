package openla500.pipeline

import openla500.config.CoreConfig
import spinal.core._

/** Exact legacy `if_stage` port shell around the typed fetch contract. */
final class LegacyIfStage(config: CoreConfig = CoreConfig.Locked) extends Component {
  setDefinitionName("if_stage")
  val io = new Bundle {
    val clk = in Bool (); val reset = in Bool (); val ds_allowin = in Bool ();
    val br_bus = in Bits (33 bits)
    val fs_to_ds_valid = out Bool (); val fs_to_ds_bus = out Bits (109 bits)
    val excp_flush = in Bool (); val ertn_flush = in Bool (); val refetch_flush = in Bool ();
    val icacop_flush = in Bool ()
    val ws_pc = in Bits (32 bits); val csr_eentry = in Bits (32 bits);
    val csr_era = in Bits (32 bits)
    val excp_tlbrefill = in Bool (); val csr_tlbrentry = in Bits (32 bits);
    val has_int = in Bool (); val idle_flush = in Bool ()
    val inst_valid = out Bool (); val inst_op = out Bool (); val inst_wstrb = out Bits (4 bits);
    val inst_wdata = out Bits (32 bits)
    val inst_addr_ok = in Bool (); val inst_data_ok = in Bool (); val icache_miss = in Bool ();
    val inst_rdata = in Bits (32 bits)
    val inst_uncache_en = out Bool (); val tlb_excp_cancel_req = out Bool ()
    val csr_pg = in Bool (); val csr_da = in Bool (); val csr_dmw0 = in Bits (32 bits);
    val csr_dmw1 = in Bits (32 bits)
    val csr_plv = in Bits (2 bits); val csr_datf = in Bits (2 bits); val disable_cache = in Bool ()
    val fetch_pc = out Bits (32 bits); val fetch_en = out Bool ();
    val btb_ret_pc = in Bits (32 bits); val btb_taken = in Bool (); val btb_en = in Bool ();
    val btb_index = in Bits (5 bits)
    val inst_addr = out Bits (32 bits); val inst_addr_trans_en = out Bool ();
    val dmw0_en = out Bool (); val dmw1_en = out Bool ()
    val inst_tlb_found = in Bool (); val inst_tlb_v = in Bool (); val inst_tlb_d = in Bool ();
    val inst_tlb_mat = in Bits (2 bits); val inst_tlb_plv = in Bits (2 bits)
  }
  noIoPrefix()

  val domain = ClockDomain(
    io.clk,
    io.reset,
    config = ClockDomainConfig(resetKind = SYNC, resetActiveLevel = HIGH)
  )
  val area = new ClockingArea(domain) { val stage = new FetchStage(config) }
  val stage = area.stage
  stage.io.downstream.ready := io.ds_allowin
  stage.io.branchRepair := io.br_bus(32)
  stage.io.branchTarget := io.br_bus(31 downto 0).asUInt
  stage.io.exceptionFlush := io.excp_flush
  stage.io.ertnFlush := io.ertn_flush
  stage.io.refetchFlush := io.refetch_flush
  stage.io.instructionCacheFlush := io.icacop_flush
  stage.io.idleFlush := io.idle_flush
  stage.io.writebackPc := io.ws_pc.asUInt
  stage.io.exceptionEntry := io.csr_eentry.asUInt
  stage.io.exceptionEra := io.csr_era.asUInt
  stage.io.exceptionTlbRefill := io.excp_tlbrefill
  stage.io.tlbRefillEntry := io.csr_tlbrentry.asUInt
  stage.io.interrupt := io.has_int
  stage.io.instructionAddressAccepted := io.inst_addr_ok
  stage.io.instructionDataValid := io.inst_data_ok
  stage.io.instructionData := io.inst_rdata
  stage.io.instructionMiss := io.icache_miss
  stage.io.paging := io.csr_pg
  stage.io.directAddress := io.csr_da
  stage.io.dmw0 := io.csr_dmw0
  stage.io.dmw1 := io.csr_dmw1
  stage.io.currentPlv := io.csr_plv.asUInt
  stage.io.directFetchMat := io.csr_datf
  stage.io.disableCache := io.disable_cache
  stage.io.btbTarget := io.btb_ret_pc.asUInt
  stage.io.btbTaken := io.btb_taken
  stage.io.btbEnabled := io.btb_en
  stage.io.btbIndex := io.btb_index.asUInt
  stage.io.tlbFound := io.inst_tlb_found
  stage.io.tlbValid := io.inst_tlb_v
  stage.io.tlbMat := io.inst_tlb_mat
  stage.io.tlbPlv := io.inst_tlb_plv.asUInt

  io.fs_to_ds_valid := stage.io.downstream.valid
  io.fs_to_ds_bus := stage.io.downstream.payload.toLegacyBits
  io.inst_valid := stage.io.instructionRequest
  io.inst_op := False
  io.inst_wstrb := 0
  io.inst_wdata := 0
  io.inst_uncache_en := stage.io.instructionUncached
  io.tlb_excp_cancel_req := stage.io.tlbCancel
  io.fetch_pc := stage.io.fetchPc.asBits
  io.fetch_en := stage.io.fetchEnable
  io.inst_addr := stage.io.instructionAddress.asBits
  io.inst_addr_trans_en := stage.io.addressTranslation
  io.dmw0_en := stage.io.dmw0Enabled
  io.dmw1_en := stage.io.dmw1Enabled
}

object GenerateOpenLa500LegacyIfStage {
  def main(args: Array[String]): Unit = {
    val out = args match {
      case Array(path)              => path
      case Array("--out-dir", path) => path
      case _ => sys.env.getOrElse("OUT_DIR", throw new IllegalArgumentException("OUT_DIR required"))
    }
    SpinalConfig(targetDirectory = out, oneFilePerComponent = false).generateVerilog(
      new LegacyIfStage()
    )
  }
}
