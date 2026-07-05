package openla500
import spinal.core._

case class MyCPUTop() extends Component {
  val io = new Bundle {
    val aclk = in Bool(); val resetn = in Bool()
    val axi_araddr = out UInt(32 bits); val axi_arvalid = out Bool(); val axi_arready = in Bool()
    val axi_rdata = in UInt(32 bits); val axi_rvalid = in Bool(); val axi_rready = out Bool()
    val axi_awaddr = out UInt(32 bits); val axi_awvalid = out Bool(); val axi_awready = in Bool()
    val axi_wdata = out UInt(32 bits); val axi_wstrb = out UInt(4 bits); val axi_wvalid = out Bool()
    val axi_wready = in Bool(); val axi_bvalid = in Bool(); val axi_bready = out Bool()
    val debug_wb_pc = out UInt(32 bits); val debug_wb_rf_wen = out Bool()
    val debug_wb_rf_wnum = out UInt(5 bits); val debug_wb_rf_wdata = out UInt(32 bits)
  }
  // Instantiate sub-modules
  val if_stage  = new IFStage
  val id_stage  = new IDStage
  val exe_stage = new EXEStage
  val mem_stage = new MEMStage
  val wb_stage  = new WBStage
  val regfile   = new RegFile
  val alu       = new ALU
  val mul       = new Multiplier
  val div       = new Divider
  val icache    = new ICache
  val dcache    = new DCache

  // Pipeline regs
  val if2id_r  = Reg(IF2ID()); val id2exe_r = Reg(ID2EXE())
  val exe2mem_r = Reg(EXE2MEM()); val mem2wb_r  = Reg(MEM2WB())
  val stall_if = Reg(Bool()) init(False); val stall_id = Reg(Bool()) init(False)

  // Drive defaults for cache
  icache.io.cacop_en    := False; icache.io.cacop_mode := U(0, 2 bits)
  icache.io.cacop_vaddr := U(0); icache.io.req_op := False
  icache.io.req_wdata   := U(0); icache.io.req_wstrb := U(0)
  dcache.io.cacop_en    := False; dcache.io.cacop_mode := U(0, 2 bits)
  dcache.io.cacop_vaddr := U(0); dcache.io.req_uncached := False
  icache.io.refill_last := False; dcache.io.refill_last := False

  // == IF connections ==
  if_stage.io.imem_rdata := icache.io.rsp_data
  if_stage.io.imem_valid := icache.io.rsp_valid
  if_stage.io.br_taken   := exe_stage.io.br_taken
  if_stage.io.br_target  := exe_stage.io.br_target
  if_stage.io.ertn_req   := False; if_stage.io.ertn_addr := U(0, 32 bits)
  if_stage.io.stall_req  := stall_if
  icache.io.req_valid := !stall_if; icache.io.req_addr := if_stage.io.imem_addr
  if2id_r := if_stage.io.if2id

  // == ID ==
  id_stage.io.if2id := if2id_r
  id_stage.io.rf_rdata1 := regfile.io.rdata1
  id_stage.io.rf_rdata2 := regfile.io.rdata2
  id_stage.io.stall_exe := stall_id
  regfile.io.rnum1 := id_stage.io.rf_rnum1
  regfile.io.rnum2 := id_stage.io.rf_rnum2
  id2exe_r := id_stage.io.id2exe

  // == EXE ==
  exe_stage.io.id2exe := id2exe_r
  exe_stage.io.alu_result := alu.io.result
  exe_stage.io.mul_result := mul.io.result
  exe_stage.io.div_result := div.io.result
  exe_stage.io.stall_mem := mem_stage.io.stall
  alu.io.alu_op := exe_stage.io.alu_op
  alu.io.src1 := exe_stage.io.alu_src1; alu.io.src2 := exe_stage.io.alu_src2
  mul.io.valid := exe_stage.io.mul_valid; mul.io.mul_op := exe_stage.io.mul_op
  mul.io.src1 := exe_stage.io.mul_src1; mul.io.src2 := exe_stage.io.mul_src2
  div.io.valid := exe_stage.io.div_valid; div.io.div_op := exe_stage.io.div_op
  div.io.src1 := exe_stage.io.div_src1; div.io.src2 := exe_stage.io.div_src2
  exe2mem_r := exe_stage.io.exe2mem

  // == MEM ==
  mem_stage.io.exe2mem  := exe2mem_r
  dcache.io.req_valid := mem_stage.io.dmem_read || mem_stage.io.dmem_write
  dcache.io.req_op    := mem_stage.io.dmem_write
  dcache.io.req_addr  := mem_stage.io.dmem_addr
  dcache.io.req_wdata := mem_stage.io.dmem_wdata
  dcache.io.req_wstrb := mem_stage.io.dmem_wstrb
  mem_stage.io.dmem_rdata := dcache.io.rsp_data
  mem_stage.io.dmem_valid := dcache.io.rsp_valid
  val dmem_stall = mem_stage.io.dmem_read && !dcache.io.rsp_valid
  stall_if := dmem_stall; stall_id := dmem_stall
  mem2wb_r := mem_stage.io.mem2wb

  // == WB ==
  wb_stage.io.mem2wb := mem2wb_r
  regfile.io.wen   := wb_stage.io.rf_wen
  regfile.io.wnum  := wb_stage.io.rf_wnum
  regfile.io.wdata := wb_stage.io.rf_wdata
  io.debug_wb_pc       := mem2wb_r.pc
  io.debug_wb_rf_wen   := wb_stage.io.rf_wen
  io.debug_wb_rf_wnum  := wb_stage.io.rf_wnum
  io.debug_wb_rf_wdata := wb_stage.io.rf_wdata

  // AXI (placeholder)
  io.axi_araddr := U(0); io.axi_arvalid := False; io.axi_rready := False
  io.axi_awaddr := U(0); io.axi_awvalid := False; io.axi_wdata := U(0)
  io.axi_wstrb := U(0); io.axi_wvalid := False; io.axi_bready := False
}

object MyCPUTopGen extends App {
  SpinalConfig(targetDirectory = "gen").generateVerilog(new MyCPUTop)
}
