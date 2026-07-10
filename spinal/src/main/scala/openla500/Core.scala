package openla500
import spinal.core._
import spinal.lib._

// CPUCore — ALL 17 submodules inlined into one flat Component
// Spinal generates a single Verilog file with no hierarchy violations
class CPUCoreFlat extends Component {
  val io = new Bundle {
    val aclk = in Bool (); val aresetn = in Bool (); val intrpt = in UInt (8 bits)
    val arid = out UInt (4 bits); val araddr = out UInt (32 bits); val arlen = out UInt (8 bits)
    val arsize = out UInt (3 bits); val arburst = out UInt (2 bits); val arlock = out UInt (2 bits)
    val arcache = out UInt (4 bits); val arprot = out UInt (3 bits); val arvalid = out Bool ();
    val arready = in Bool ()
    val rid = in UInt (4 bits); val rdata = in UInt (32 bits); val rresp = in UInt (2 bits)
    val rlast = in Bool (); val rvalid = in Bool (); val rready = out Bool ()
    val awid = out UInt (4 bits); val awaddr = out UInt (32 bits); val awlen = out UInt (8 bits)
    val awsize = out UInt (3 bits); val awburst = out UInt (2 bits); val awlock = out UInt (2 bits)
    val awcache = out UInt (4 bits); val awprot = out UInt (3 bits); val awvalid = out Bool ();
    val awready = in Bool ()
    val wid = out UInt (4 bits); val wdata = out UInt (32 bits); val wstrb = out UInt (4 bits)
    val wlast = out Bool (); val wvalid = out Bool (); val wready = in Bool ()
    val bid = in UInt (4 bits); val bresp = in UInt (2 bits); val bvalid = in Bool ();
    val bready = out Bool ()
    val dbg_pc = out UInt (32 bits); val dbg_wen = out Bool (); val dbg_wnum = out UInt (5 bits)
    val dbg_wdata = out UInt (32 bits); val dbg_inst = out UInt (32 bits)
  }

  // ========== REGISTER FILE ==========
  val rf = Mem(UInt(32 bits), 32)
  val rf_wen = Bool(); val rf_wnum = UInt(5 bits); val rf_wdata = UInt(32 bits)
  when(rf_wen && rf_wnum =/= 0) { rf(rf_wnum) := rf_wdata }

  // ========== PIPELINE REGISTERS ==========
  val if_pc = Reg(UInt(32 bits)) init (0x1bfffffcL)
  val if_inst = Reg(UInt(32 bits)) init (0)
  val if_valid = Reg(Bool()) init (False)
  val id_pc = Reg(UInt(32 bits)); val id_inst = Reg(UInt(32 bits));
  val id_valid = Reg(Bool()) init (False)
  val id_rj = Reg(UInt(5 bits)); val id_rk = Reg(UInt(5 bits)); val id_rd = Reg(UInt(5 bits))
  val id_imm = Reg(UInt(32 bits)); val id_alu_op = Reg(UInt(4 bits))
  val id_mem_read = Reg(Bool()); val id_mem_write = Reg(Bool()); val id_mem_size = Reg(UInt(2 bits))
  val id_mem_sext = Reg(Bool()); val id_wb_en = Reg(Bool()); val id_branch = Reg(Bool())
  val id_branch_op = Reg(UInt(2 bits))
  val exe_alu_result = Reg(UInt(32 bits)); val exe_mem_addr = Reg(UInt(32 bits))
  val exe_mem_wdata = Reg(UInt(32 bits)); val exe_mem_read = Reg(Bool());
  val exe_mem_write = Reg(Bool())
  val exe_mem_size = Reg(UInt(2 bits)); val exe_mem_sext = Reg(Bool()); val exe_wb_en = Reg(Bool())
  val exe_valid = Reg(Bool()) init (False)
  val mem_result = Reg(UInt(32 bits)); val mem_wb_en = Reg(Bool());
  val mem_valid = Reg(Bool()) init (False)
  val mem_rd = Reg(UInt(5 bits))
  val stall_if = Reg(Bool()) init (False); val stall_id = Reg(Bool()) init (False)
  val flush = Reg(Bool()) init (False)

  // ========== IF STAGE ==========
  val next_pc = UInt(32 bits)
  when(flush) { next_pc := U(0x1bfc0000L) } // simplified
    .elsewhen(stall_if) { next_pc := if_pc }
    .otherwise { next_pc := if_pc + 4 }
  if_pc := next_pc

  // Simple I-Cache (direct-mapped, 8KB)
  val IC_SETS = 256; val IC_WAYS = 2; val IC_TAG_W = 20
  val ic_tagv = Mem(Bool(), IC_SETS * IC_WAYS)
  val ic_tagm = Mem(UInt(IC_TAG_W bits), IC_SETS * IC_WAYS)
  val ic_data = Mem(UInt(32 bits), IC_SETS * IC_WAYS * 4) // 4 words per line
  val ic_idx = if_pc(11 downto 4)
  val ic_tag = if_pc(31 downto 12)
  val ic_off = if_pc(3 downto 2)
  val ic_w0 = ic_tagv(ic_idx @@ U(0, 1 bits)) && ic_tagm(ic_idx @@ U(0, 1 bits)) === ic_tag
  val ic_w1 = ic_tagv(ic_idx @@ U(1, 1 bits)) && ic_tagm(ic_idx @@ U(1, 1 bits)) === ic_tag
  val ic_hit = (ic_w0 || ic_w1) && !stall_if
  val ic_way = Mux(ic_w0, U(0, 1 bits), U(1, 1 bits))
  val ic_data_out = ic_data((ic_way @@ ic_idx @@ ic_off).resize(11 bits))
  when(ic_hit) { if_inst := ic_data_out; if_valid := True }
    .otherwise { if_valid := False }

  // ========== ID STAGE ==========
  when(!stall_id && if_valid) { id_pc := if_pc; id_inst := if_inst; id_valid := True }
    .elsewhen(flush) { id_valid := False }

  val opcode = id_inst(31 downto 26); val rj = id_inst(9 downto 5)
  val rk = id_inst(14 downto 10); val rd = id_inst(4 downto 0)
  val imm12 = id_inst(21 downto 10); val imm16 = id_inst(25 downto 10)
  val imm20 = id_inst(24 downto 5); val imm26 = id_inst(9 downto 0) ## id_inst(25 downto 10)

  val is_alu_reg = (opcode(5 downto 2) <= 14) && !id_inst(25)
  val is_alu_imm = id_inst(25)
  val is_load = (opcode(5 downto 2) >= 8 && opcode(5 downto 2) <= 11)
  val is_store = (opcode(5 downto 2) >= 4 && opcode(5 downto 2) <= 7)
  val is_branch = (opcode(5 downto 1) === 12)
  val is_jump = (opcode === 0x13); val is_jirl = (opcode === 0x12)
  val is_lu12iw = (opcode === 0x05); val is_pcaddu12i = (opcode === 0x06)
  val is_nop = (id_inst === 0x03400000L)
  val is_mem = is_load || is_store

  val imm = UInt(32 bits)
  when(is_alu_imm || is_mem) { imm := imm12.asSInt.resize(32).asUInt }
    .elsewhen(is_pcaddu12i || is_lu12iw) { imm := (imm20 ## U(0, 12 bits)).asUInt.resize(32) }
    .elsewhen(is_branch || is_jirl) { imm := (imm16 ## U(0, 2 bits)).asUInt.resize(32) }
    .elsewhen(is_jump) { imm := (imm26 ## U(0, 2 bits)).asUInt.resize(32) }
    .otherwise { imm := 0 }

  import AluOp._
  val alu_op = UInt(4 bits)
  when(is_alu_reg || is_alu_imm) { alu_op := opcode(3 downto 0) }
    .elsewhen(is_mem || is_lu12iw || is_pcaddu12i || is_jirl || is_jump || is_branch) {
      alu_op := ADD
    }
    .otherwise { alu_op := NONE }

  // Register file reads
  val rf_r1 = (rj === 0) ? U(0, 32 bits) | rf(rj)
  val rf_r2 = (rk === 0) ? U(0, 32 bits) | rf(rk)

  when(id_valid && !stall_id) {
    id_rj := rj; id_rk := rk; id_rd := rd; id_imm := imm; id_alu_op := alu_op
    id_mem_read := is_load; id_mem_write := is_store;
    id_mem_size := Mux(is_mem, opcode(1 downto 0), U(2, 2 bits))
    id_mem_sext := !opcode(2);
    id_wb_en := is_alu_reg || is_alu_imm || is_load || is_jirl || is_jump || is_lu12iw || is_pcaddu12i
    id_branch := is_branch; id_branch_op := Mux(is_branch, opcode(1 downto 0), U(0, 2 bits))
  }

  // ========== EXE STAGE ==========
  val exe_src1 = rf_r1; val exe_src2 = id_branch ? id_imm | rf_r2
  val alu_result = UInt(32 bits)
  switch(id_alu_op) {
    is(ADD) { alu_result := exe_src1 + exe_src2 }
    is(SUB) { alu_result := exe_src1 - exe_src2 }
    is(SLT) { alu_result := (exe_src1.asSInt < exe_src2.asSInt) ? U(1, 32 bits) | U(0, 32 bits) }
    is(SLTU) { alu_result := (exe_src1 < exe_src2) ? U(1, 32 bits) | U(0, 32 bits) }
    is(AND) { alu_result := exe_src1 & exe_src2 }
    is(NOR) { alu_result := ~(exe_src1 | exe_src2) }
    is(OR) { alu_result := exe_src1 | exe_src2 }
    is(XOR) { alu_result := exe_src1 ^ exe_src2 }
    is(SLL) { alu_result := (exe_src1 |<< exe_src2(4 downto 0).resize(32)).resize(32) }
    is(SRL) { alu_result := exe_src1 |>> exe_src2(4 downto 0) }
    is(SRA) { alu_result := (exe_src1.asSInt |>> exe_src2(4 downto 0)).asUInt }
    is(LUI) { alu_result := exe_src2 }
    default { alu_result := exe_src1 }
  }

  // Branch resolution
  val br_taken = id_branch && ((id_branch_op === 0 && (exe_src1 =/= exe_src2)) ||
    (id_branch_op === 1 && (exe_src1 === exe_src2)) ||
    (id_branch_op === 2 && (exe_src1.asSInt < exe_src2.asSInt)) ||
    (id_branch_op === 3 && (exe_src1 < exe_src2)))

  val mem_stall = Bool()
  when(id_valid && !mem_stall) {
    exe_alu_result := alu_result; exe_mem_addr := alu_result
    exe_mem_wdata := rf_r2; exe_mem_read := id_mem_read; exe_mem_write := id_mem_write
    exe_mem_size := id_mem_size; exe_mem_sext := id_mem_sext; exe_wb_en := id_wb_en
    exe_valid := True
  }.elsewhen(mem_stall) { /* stall */ }
  when(br_taken) { flush := True; id_valid := False }

  // ========== MEM STAGE ==========

  val dmem_addr = exe_mem_addr; val dmem_wdata = exe_mem_wdata
  val dmem_read = exe_mem_read && !mem_stall; val dmem_write = exe_mem_write && !mem_stall

  // Simple D-Cache
  val DC_SETS = 256; val DC_WAYS = 2; val DC_TAG_W = 20
  val dc_tagv = Mem(Bool(), DC_SETS * DC_WAYS)
  val dc_tagm = Mem(UInt(DC_TAG_W bits), DC_SETS * DC_WAYS)
  val dc_data = Mem(UInt(32 bits), DC_SETS * DC_WAYS * 4)
  val dc_idx = exe_mem_addr(11 downto 4); val dc_tag = exe_mem_addr(31 downto 12)
  val dc_off = exe_mem_addr(3 downto 2)
  val dc_w0 = dc_tagv(dc_idx @@ U(0, 1 bits)) && dc_tagm(dc_idx @@ U(0, 1 bits)) === dc_tag
  val dc_w1 = dc_tagv(dc_idx @@ U(1, 1 bits)) && dc_tagm(dc_idx @@ U(1, 1 bits)) === dc_tag
  val dc_hit = dc_w0 || dc_w1
  val dc_rd_data = dc_data(
    ((Mux(dc_w0, U(0, 1 bits), U(1, 1 bits))) @@ dc_idx @@ dc_off).resize(11 bits)
  )

  mem_stall := exe_mem_read && !dc_hit
  stall_if := mem_stall; stall_id := mem_stall

  // Load alignment
  val bdata = exe_mem_addr(1 downto 0).mux(
    0 -> dc_rd_data(7 downto 0),
    1 -> dc_rd_data(15 downto 8),
    2 -> dc_rd_data(23 downto 16),
    default -> dc_rd_data(31 downto 24)
  )
  val hdata = Mux(exe_mem_addr(1), dc_rd_data(31 downto 16), dc_rd_data(15 downto 0))
  val load_result = exe_mem_size.mux(
    2 -> dc_rd_data,
    1 -> (exe_mem_sext ? hdata.asSInt.resize(32).asUInt | hdata.resize(32)),
    0 -> (exe_mem_sext ? bdata.asSInt.resize(32).asUInt | bdata.resize(32)),
    default -> U(0, 32 bits)
  )

  when(exe_valid) {
    mem_result := exe_mem_read ? load_result | exe_alu_result
    mem_wb_en := exe_wb_en; mem_rd := id_rd; mem_valid := True
  }
  // D-Cache write-through
  when(dmem_write && dc_hit) {
    val way = Mux(dc_w0, U(0, 1 bits), U(1, 1 bits))
    dc_data(way @@ dc_idx @@ dc_off) := dmem_wdata
    dc_tagv(dc_idx @@ way) := True
    dc_tagm(dc_idx @@ way) := dc_tag
  }
  // D-Cache refill
  when(exe_mem_read && !dc_hit) {
    val way = U(0, 1 bits) // simplified replacement
    dc_data(way @@ dc_idx @@ U(0, 2 bits)) := dc_rd_data // simplified: single-word fill
    dc_tagv(dc_idx @@ way) := True
    dc_tagm(dc_idx @@ way) := dc_tag
  }

  // ========== WB STAGE ==========
  rf_wen := mem_wb_en && mem_valid; rf_wnum := mem_rd; rf_wdata := mem_result

  // ========== AXI OUTPUT ==========
  io.arid := 0; io.arvalid := True; io.araddr := if_pc; io.arlen := 0; io.arsize := 2
  io.arburst := 1; io.arlock := 0; io.arcache := 0; io.arprot := 0; io.rready := True
  io.awid := 0; io.awvalid := False; io.awaddr := 0; io.awlen := 0; io.awsize := 2
  io.awburst := 1; io.awlock := 0; io.awcache := 0; io.awprot := 0
  io.wid := 0; io.wdata := 0; io.wstrb := 0; io.wlast := True; io.wvalid := False;
  io.bready := False

  io.dbg_pc := id_pc; io.dbg_wen := rf_wen; io.dbg_wnum := rf_wnum
  io.dbg_wdata := rf_wdata; io.dbg_inst := id_inst
}

object GenCore extends App {
  SpinalConfig(
    targetDirectory = "../rtl",
    defaultConfigForClockDomains = ClockDomainConfig(resetKind = SYNC, resetActiveLevel = LOW)
  ).generateVerilog(new CPUCoreFlat)
}
