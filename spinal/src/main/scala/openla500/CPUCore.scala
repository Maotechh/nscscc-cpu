package openla500
import spinal.core._

class CPUCore extends Component {
  val io = new Bundle {
    val aclk = in Bool(); val aresetn = in Bool(); val intrpt = in UInt(8 bits)
    val arid = out UInt(4 bits); val araddr = out UInt(32 bits); val arlen = out UInt(8 bits)
    val arsize = out UInt(3 bits); val arburst = out UInt(2 bits); val arlock = out UInt(2 bits)
    val arcache = out UInt(4 bits); val arprot = out UInt(3 bits); val arvalid = out Bool(); val arready = in Bool()
    val rid = in UInt(4 bits); val rdata = in UInt(32 bits); val rresp = in UInt(2 bits)
    val rlast = in Bool(); val rvalid = in Bool(); val rready = out Bool()
    val awid = out UInt(4 bits); val awaddr = out UInt(32 bits); val awlen = out UInt(8 bits)
    val awsize = out UInt(3 bits); val awburst = out UInt(2 bits); val awlock = out UInt(2 bits)
    val awcache = out UInt(4 bits); val awprot = out UInt(3 bits); val awvalid = out Bool(); val awready = in Bool()
    val wid = out UInt(4 bits); val wdata = out UInt(32 bits); val wstrb = out UInt(4 bits)
    val wlast = out Bool(); val wvalid = out Bool(); val wready = in Bool()
    val bid = in UInt(4 bits); val bresp = in UInt(2 bits); val bvalid = in Bool(); val bready = out Bool()
    val dbg_pc = out UInt(32 bits); val dbg_wen = out Bool(); val dbg_wnum = out UInt(5 bits); val dbg_wdata = out UInt(32 bits)
  }

  // === Submodules ===
  val if_stage   = new IFStage();   val id_stage   = new IDStage()
  val exe_stage  = new EXEStage();  val mem_stage  = new MEMStage()
  val wb_stage   = new WBStage();   val regfile    = new RegFile()
  val alu = new ALU(); val mul = new Multiplier(); val div = new Divider()
  val icache = new ICache(); val dcache = new DCache()
  val csr = new CSRFile(); val btb = new BTB(); val tlb = new TLBEntry()
  val addr_trans = new AddrTrans(); val perf_ctr = new PerfCounter()
  val axi = new AxiBridge()

  // Pipeline regs
  val if2id_r  = Reg(IF2ID());   val id2exe_r = Reg(ID2EXE())
  val exe2mem_r = Reg(EXE2MEM()); val mem2wb_r = Reg(MEM2WB())
  val stall_if = Reg(Bool()) init(False); val stall_id = Reg(Bool()) init(False)

  // == IF ==
  if_stage.io.imem_rdata := icache.io.rsp_data; if_stage.io.imem_valid := icache.io.rsp_valid
  if_stage.io.br_taken := exe_stage.io.br_taken; if_stage.io.br_target := exe_stage.io.br_target
  if_stage.io.ertn_req := False; if_stage.io.ertn_addr := U(0, 32 bits); if_stage.io.stall_req := stall_if
  icache.io.req_valid := !stall_if; icache.io.req_addr := if_stage.io.imem_addr; icache.io.req_op := False
  icache.io.req_wdata := U(0); icache.io.req_wstrb := U(0, 4 bits)
  icache.io.cacop_en := False; icache.io.cacop_mode := U(0, 2 bits); icache.io.cacop_vaddr := U(0)
  icache.io.refill_valid := False; icache.io.refill_data := U(0); icache.io.refill_last := False
  if2id_r := if_stage.io.if2id

  // == ID ==
  id_stage.io.if2id := if2id_r; id_stage.io.rf_rdata1 := regfile.io.rdata1
  id_stage.io.rf_rdata2 := regfile.io.rdata2; id_stage.io.stall_exe := stall_id
  regfile.io.rnum1 := id_stage.io.rf_rnum1; regfile.io.rnum2 := id_stage.io.rf_rnum2
  id2exe_r := id_stage.io.id2exe

  // == EXE ==
  exe_stage.io.id2exe := id2exe_r; exe_stage.io.alu_result := alu.io.result
  exe_stage.io.mul_result := mul.io.result; exe_stage.io.div_result := div.io.result
  exe_stage.io.stall_mem := mem_stage.io.stall
  alu.io.alu_op := exe_stage.io.alu_op; alu.io.src1 := exe_stage.io.alu_src1; alu.io.src2 := exe_stage.io.alu_src2
  mul.io.valid := exe_stage.io.mul_valid; mul.io.mul_op := exe_stage.io.mul_op
  mul.io.mul_signed := True; mul.io.src1 := exe_stage.io.mul_src1; mul.io.src2 := exe_stage.io.mul_src2
  div.io.valid := exe_stage.io.div_valid; div.io.div_op := exe_stage.io.div_op
  div.io.div_signed := True; div.io.src1 := exe_stage.io.div_src1; div.io.src2 := exe_stage.io.div_src2
  exe2mem_r := exe_stage.io.exe2mem

  // == MEM ==
  mem_stage.io.exe2mem := exe2mem_r; mem_stage.io.dmem_rdata := dcache.io.rsp_data
  mem_stage.io.dmem_valid := dcache.io.rsp_valid
  dcache.io.req_valid := mem_stage.io.dmem_read || mem_stage.io.dmem_write
  dcache.io.req_op := mem_stage.io.dmem_write; dcache.io.req_addr := mem_stage.io.dmem_addr
  dcache.io.req_wdata := mem_stage.io.dmem_wdata; dcache.io.req_wstrb := mem_stage.io.dmem_wstrb
  dcache.io.req_uncached := False; dcache.io.cacop_en := False; dcache.io.cacop_mode := U(0, 2 bits)
  dcache.io.cacop_vaddr := U(0); dcache.io.refill_valid := False; dcache.io.refill_data := U(0)
  dcache.io.refill_last := False; dcache.io.wb_valid := False
  val dm_stall = mem_stage.io.dmem_read && !dcache.io.rsp_valid
  stall_if := dm_stall; stall_id := dm_stall
  mem2wb_r := mem_stage.io.mem2wb

  // == WB ==
  wb_stage.io.mem2wb := mem2wb_r
  regfile.io.wen := wb_stage.io.rf_wen; regfile.io.wnum := wb_stage.io.rf_wnum
  regfile.io.wdata := wb_stage.io.rf_wdata

  // == AXI ==
  val d_active = dcache.io.refill_req || dcache.io.wb_req
  icache.io.refill_valid := !d_active && icache.io.refill_req; icache.io.refill_data := axi.io.cpu_rdata
  dcache.io.refill_valid := d_active && dcache.io.refill_req; dcache.io.refill_data := axi.io.cpu_rdata
  axi.io.cpu_req := d_active || icache.io.refill_req; axi.io.cpu_wr := dcache.io.wb_req
  axi.io.cpu_addr := d_active ? dcache.io.refill_addr | icache.io.refill_addr
  axi.io.cpu_wdata := dcache.io.wb_data; axi.io.cpu_wstrb := U"4'hF"; axi.io.cpu_size := U(2, 2 bits)
  axi.io.awready := io.awready; axi.io.wready := io.wready; axi.io.arready := io.arready
  axi.io.rvalid := io.rvalid; axi.io.rlast := io.rlast; axi.io.bvalid := io.bvalid
  axi.io.rdata := io.rdata; axi.io.bid := io.bid; axi.io.rid := io.rid
  axi.io.bresp := io.bresp; axi.io.rresp := io.rresp

  io.arid := axi.io.arid; io.araddr := axi.io.araddr; io.arlen := axi.io.arlen
  io.arsize := axi.io.arsize; io.arburst := axi.io.arburst; io.arvalid := axi.io.arvalid
  io.rready := axi.io.rready
  io.awid := axi.io.awid; io.awaddr := axi.io.awaddr; io.awlen := axi.io.awlen
  io.awsize := axi.io.awsize; io.awburst := axi.io.awburst; io.awvalid := axi.io.awvalid
  io.wdata := axi.io.wdata; io.wstrb := axi.io.wstrb; io.wlast := axi.io.wlast; io.wvalid := axi.io.wvalid
  io.bready := axi.io.bready
  io.arlock := U"2'h0"; io.arcache := U"4'h0"; io.arprot := U"3'h0"
  io.awlock := U"2'h0"; io.awcache := U"4'h0"; io.awprot := U"3'h0"; io.wid := U"4'h0"

  // == Debug ==
  io.dbg_pc := mem2wb_r.pc; io.dbg_wen := wb_stage.io.rf_wen
  io.dbg_wnum := wb_stage.io.rf_wnum; io.dbg_wdata := wb_stage.io.rf_wdata

  // == Unused submodule defaults ==
  btb.io.lookup_pc := if_stage.io.if2id.pc; btb.io.update_pc := U(0); btb.io.update_target := U(0)
  btb.io.call_pc := U(0); btb.io.update_valid := False; btb.io.update_taken := False
  btb.io.update_is_br := False; btb.io.is_call := False; btb.io.is_ret := False
  csr.io.clk := io.aclk; csr.io.reset := !io.aresetn; csr.io.csr_num := U(0); csr.io.csr_wdata := U(0)
  csr.io.csr_rd := False; csr.io.csr_wr := False; csr.io.csr_xchg := False
  csr.io.excp_valid := False; csr.io.excp_era := U(0); csr.io.excp_code := U(0, 6 bits)
  csr.io.excp_subcode := U(0, 9 bits); csr.io.excp_badv := U(0)
  csr.io.ertn_valid := False; csr.io.ext_int := False
  tlb.io.search_vpn := U(0); tlb.io.search_asid := U(0); tlb.io.search_valid := False
  tlb.io.write_valid := False; tlb.io.write_index := U(0); tlb.io.write_vpn := U(0)
  tlb.io.write_ppn0 := U(0); tlb.io.write_ppn1 := U(0); tlb.io.write_ps := U(0); tlb.io.write_asid := U(0)
  tlb.io.write_g := False; tlb.io.write_v := False; tlb.io.write_d0 := False; tlb.io.write_d1 := False
  tlb.io.inv_req := False; tlb.io.inv_vpn := U(0); tlb.io.inv_asid := U(0); tlb.io.probe_index := U(0)
  addr_trans.io.va := U(0); addr_trans.io.is_load := False
  perf_ctr.io.commit_inst := wb_stage.io.rf_wen; perf_ctr.io.dcache_miss := dcache.io.cache_miss
  perf_ctr.io.icache_miss := icache.io.cache_miss; perf_ctr.io.br_inst := id_stage.io.br_inst
  perf_ctr.io.mem_inst := mem_stage.io.dmem_read || mem_stage.io.dmem_write
  perf_ctr.io.br_pre := False; perf_ctr.io.br_pre_error := False
}

object GenCPUCore extends App {
  SpinalConfig(
    targetDirectory = "../rtl",
    defaultConfigForClockDomains = ClockDomainConfig(resetKind = SYNC, resetActiveLevel = LOW)
  ).generateVerilog(new CPUCore)
}
