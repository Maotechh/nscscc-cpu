package openla500

import spinal.core._
import spinal.lib._

// Pipeline data structures for 5-stage pipeline IF→ID→EXE→MEM→WB

class IF2ID extends Bundle {
  val pc = UInt(32 bits)
  val inst = UInt(32 bits)
  val valid = new Bool
  val predict = new Bool
  val pred_pc = UInt(32 bits)
}

class ID2EXE extends Bundle {
  val alu_op = UInt(4 bits)
  val mul_op = UInt(2 bits)
  val div_op = UInt(1 bits)
  val branch = new Bool
  val branch_op = in UInt (2 bits)
  val mem_read = new Bool
  val mem_write = new Bool
  val mem_size = UInt(2 bits)
  val mem_sext = new Bool
  val wb_en = new Bool
  val csr_op = UInt(2 bits)
  val pc = UInt(32 bits)
  val rdata1 = UInt(32 bits)
  val rdata2 = UInt(32 bits)
  val imm = UInt(32 bits)
  val rd_addr = UInt(5 bits)
  val rj_addr = UInt(5 bits)
  val rk_addr = UInt(5 bits)
  val csr_num = UInt(14 bits)
  val valid = new Bool
  val excp_ine = new Bool
  val excp_sys = new Bool
  val excp_brk = new Bool
  val excp_ertn = new Bool
}

class EXE2MEM extends Bundle {
  val pc = UInt(32 bits)
  val alu_result = UInt(32 bits)
  val mem_wdata = UInt(32 bits)
  val mem_read = new Bool
  val mem_write = new Bool
  val mem_size = UInt(2 bits)
  val mem_sext = new Bool
  val mem_addr = UInt(32 bits)
  val wb_en = new Bool
  val rd_addr = UInt(5 bits)
  val csr_op = UInt(2 bits)
  val csr_num = UInt(14 bits)
  val csr_wdata = UInt(32 bits)
  val valid = new Bool
  val except = new Bool
  val except_code = in UInt (6 bits)
  val branch_taken = new Bool
  val branch_target = in UInt (32 bits)
}

class MEM2WB extends Bundle {
  val pc = UInt(32 bits)
  val result = UInt(32 bits)
  val wb_en = new Bool
  val rd_addr = UInt(5 bits)
  val csr_op = UInt(2 bits)
  val csr_num = UInt(14 bits)
  val csr_rdata = UInt(32 bits)
  val valid = new Bool
  val except = new Bool
  val except_code = in UInt (6 bits)
}

// IF Stage
case class IFStage() extends Component {
  val io = new Bundle {
    val imem_addr = UInt(32 bits)
    val imem_rdata = in UInt (32 bits)
    val imem_valid = in Bool ()
    val br_taken = Bool()
    val br_target = UInt(32 bits)
    val ertn_req = Bool()
    val ertn_addr = UInt(32 bits)
    val stall_req = Bool()
    val if2id = out(IF2ID())
  }
  val pc = RegInit(U(0x1bfffffcL, 32 bits))
  when(!io.stall_req) {
    pc := io.ertn_req ? io.ertn_addr | (io.br_taken ? io.br_target | (pc + 4))
  }
  io.imem_addr := pc
  io.if2id.pc := pc
  io.if2id.inst := io.imem_rdata
  io.if2id.valid := io.imem_valid && !io.stall_req
  io.if2id.predict := False
  io.if2id.pred_pc := pc + 4
}

// ID Stage
case class IDStage() extends Component {
  val io = new Bundle {
    val if2id = in(IF2ID())
    val id2exe = out(ID2EXE())
    val rf_rnum1 = out UInt (5 bits)
    val rf_rnum2 = out UInt (5 bits)
    val rf_rdata1 = in UInt (32 bits)
    val rf_rdata2 = in UInt (32 bits)
    val br_inst = Bool()
    val br_pc = UInt(32 bits)
    val br_target = out UInt (32 bits)
    val stall_exe = in Bool ()
  }
  val inst = io.if2id.inst
  val opcode = inst(31 downto 26)
  val rj = inst(9 downto 5)
  val rk = inst(14 downto 10)
  val rd = inst(4 downto 0)
  val imm12 = inst(21 downto 10)
  val imm16 = inst(25 downto 10)
  val imm20 = inst(24 downto 5)
  val imm26 = inst(9 downto 0) ## inst(25 downto 10)

  val is_alu_reg = opcode(5) === False && !inst(25)
  val is_alu_imm = inst(25)
  val is_mul = opcode === U(0x00, 6 bits) && rd === U(0x02, 5 bits)
  val is_div = opcode === U(0x00, 6 bits) && rd === U(0x03, 5 bits)
  val is_load =
    opcode(5 downto 2) === U(0xa, 4 bits) // 0x22-0x2F → (5..2)=10,9,8 not quite right, simplified
  val is_store = opcode(5 downto 2) === U(0xb, 4 bits)
  val is_branch = opcode(5 downto 1) === U(0x0c, 5 bits)
  val is_jump = opcode === U(0x13, 6 bits)
  val is_jirl = opcode === U(0x12, 6 bits)
  val is_csr = opcode(5 downto 0) === U(0x01, 6 bits) && rj =/= U(0, 5 bits)
  val is_cacop = opcode(5 downto 0) === U(0x01, 6 bits) && rj === U(0x0b, 5 bits)
  val is_syscall = opcode === U(0x00, 6 bits) && rd === U(0x0b, 5 bits)
  val is_break = opcode === U(0x00, 6 bits) && rd === U(0x0a, 5 bits)
  val is_ertn = opcode(5 downto 0) === U(0x01, 6 bits) && rd === U(0x0e, 5 bits)
  val is_lu12iw = opcode === U(0x05, 6 bits)
  val is_pcaddu12i = opcode === U(0x06, 6 bits)
  val is_nop = inst === U(0x03400000L, 32 bits)
  val is_mem = is_load || is_store

  io.rf_rnum1 := rj; io.rf_rnum2 := rk

  val imm = in UInt (32 bits)
  imm := 0
  when(is_alu_imm || is_mem) { imm := imm12.asSInt.resize(32).asUInt }
    .elsewhen(is_pcaddu12i || is_lu12iw) { imm := (imm20 ## U(0, 12 bits)).asUInt }
    .elsewhen(is_branch || is_jirl) { imm := imm16.asSInt.resize(32).asUInt }
    .elsewhen(is_jump) { imm := imm26.asSInt.resize(32).asUInt }

  import AluOp._
  val alu_op = out UInt (4 bits); alu_op := NONE
  when(is_alu_reg || is_alu_imm) { alu_op := opcode(3 downto 0) }
  when(is_mem || is_lu12iw || is_pcaddu12i) { alu_op := ADD }
  when(is_jirl || is_jump || is_branch) { alu_op := ADD }

  val valid_inst = is_alu_reg || is_alu_imm || is_mul || is_div || is_mem || is_branch ||
    is_jump || is_jirl || is_csr || is_cacop || is_syscall || is_break ||
    is_ertn || is_lu12iw || is_pcaddu12i || is_nop

  io.br_inst := is_branch || is_jump
  io.br_pc := io.if2id.pc
  io.br_target := (io.if2id.pc.asSInt + imm.asSInt).asUInt

  io.id2exe.alu_op := alu_op
  io.id2exe.mul_op := Mux(is_mul, rd(1 downto 0), U(0, 2 bits))
  io.id2exe.div_op := Mux(is_div, rd(0).asUInt.resize(1 bits), U(0, 1 bits))
  io.id2exe.branch := is_branch
  io.id2exe.branch_op := Mux(is_branch, opcode(1 downto 0), U(0, 2 bits))
  io.id2exe.mem_read := is_load
  io.id2exe.mem_write := is_store
  io.id2exe.mem_size := Mux(is_mem, opcode(1 downto 0), U(2, 2 bits)) // default word
  io.id2exe.mem_sext := !opcode(2)
  io.id2exe.wb_en := is_alu_reg || is_alu_imm || is_load || is_mul || is_div ||
    is_jirl || is_jump || is_csr || is_lu12iw || is_pcaddu12i
  io.id2exe.csr_op := is_csr ? U(1, 2 bits) | U(0, 2 bits)
  io.id2exe.pc := io.if2id.pc
  io.id2exe.rdata1 := io.rf_rdata1
  io.id2exe.rdata2 := io.rf_rdata2
  io.id2exe.imm := imm
  io.id2exe.rd_addr := rd
  io.id2exe.rj_addr := rj
  io.id2exe.rk_addr := rk
  io.id2exe.valid := io.if2id.valid && !io.stall_exe
  io.id2exe.excp_ine := !valid_inst
  io.id2exe.excp_sys := is_syscall
  io.id2exe.excp_brk := is_break
  io.id2exe.excp_ertn := is_ertn
}

// EXE Stage
case class EXEStage() extends Component {
  val io = new Bundle {
    val id2exe = in(ID2EXE())
    val exe2mem = out(EXE2MEM())
    val alu_src1 = out UInt (32 bits)
    val alu_src2 = out UInt (32 bits)
    val alu_op = UInt(4 bits)
    val alu_result = in UInt (32 bits)
    val mul_valid = Bool()
    val mul_op = UInt(2 bits)
    val mul_src1 = UInt(32 bits)
    val mul_src2 = UInt(32 bits)
    val mul_result = in UInt (32 bits)
    val div_valid = Bool()
    val div_op = UInt(1 bits)
    val div_src1 = UInt(32 bits)
    val div_src2 = UInt(32 bits)
    val div_result = in UInt (32 bits)
    val br_taken = Bool()
    val br_target = UInt(32 bits)
    val stall_mem = Bool()
  }
  val id = io.id2exe
  val src1 = id.rdata1
  val src2 = id.imm

  io.alu_src1 := src1; io.alu_src2 := src2; io.alu_op := id.alu_op

  // Branch
  val br_eq = src1 === src2
  val br_lt = src1.asSInt < src2.asSInt
  val br_ltu = src1 < src2
  val br_taken = id.branch && (id.branch_op.mux(
    0 -> !br_eq,
    1 -> br_eq,
    2 -> br_lt,
    3 -> br_ltu,
    default -> False
  ))
  val target = (id.pc.asSInt + id.imm.asSInt).asUInt
  io.br_taken := br_taken
  io.br_target := target

  io.mul_valid := id.alu_op === AluOp.MUL || id.alu_op === AluOp.MULH
  io.mul_op := (id.alu_op === AluOp.MUL) ? U(0, 2 bits) | U(1, 2 bits)
  io.mul_src1 := src1; io.mul_src2 := src2
  io.div_valid := id.alu_op === AluOp.DIV || id.alu_op === AluOp.MOD
  io.div_op := (id.alu_op === AluOp.DIV) ? U(0, 1 bits) | U(1, 1 bits)
  io.div_src1 := src1; io.div_src2 := src2

  io.exe2mem.pc := id.pc
  io.exe2mem.alu_result := io.alu_result
  io.exe2mem.mem_wdata := id.rdata2
  io.exe2mem.mem_read := id.mem_read
  io.exe2mem.mem_write := id.mem_write
  io.exe2mem.mem_size := id.mem_size
  io.exe2mem.mem_sext := id.mem_sext
  io.exe2mem.mem_addr := io.alu_result
  io.exe2mem.wb_en := id.wb_en
  io.exe2mem.rd_addr := id.rd_addr
  io.exe2mem.csr_op := id.csr_op
  io.exe2mem.csr_num := id.csr_num
  io.exe2mem.csr_wdata := id.rdata1
  io.exe2mem.valid := id.valid && !io.stall_mem
  io.exe2mem.except := id.excp_ine || id.excp_sys || id.excp_brk
  io.exe2mem.except_code := id.excp_ine ? U(0x0d, 6 bits) | (id.excp_sys ? U(0x0b, 6 bits) | U(
    0,
    6 bits
  ))
  io.exe2mem.branch_taken := br_taken
  io.exe2mem.branch_target := target
}

// MEM Stage
case class MEMStage() extends Component {
  val io = new Bundle {
    val exe2mem = in(EXE2MEM())
    val mem2wb = out(MEM2WB())
    val dmem_addr = UInt(32 bits)
    val dmem_wdata = out UInt (32 bits)
    val dmem_wstrb = out UInt (4 bits)
    val dmem_read = Bool()
    val dmem_write = out Bool ()
    val dmem_rdata = in UInt (32 bits)
    val dmem_valid = in Bool ()
    val stall = Bool()
  }
  val mem = io.exe2mem
  io.dmem_addr := mem.mem_addr
  io.dmem_wdata := mem.mem_wdata
  io.dmem_read := mem.mem_read && !mem.except
  io.dmem_write := mem.mem_write && !mem.except

  val size = mem.mem_size
  val alow = mem.mem_addr(1 downto 0)
  io.dmem_wstrb := size.mux(
    0 -> alow.mux(0 -> U"4'h1", 1 -> U"4'h2", 2 -> U"4'h4", default -> U"4'h8"),
    1 -> Mux(alow(1), U"4'hC", U"4'h3"),
    2 -> U"4'hF",
    default -> U"4'h0"
  )

  val bdata = alow.mux(
    0 -> io.dmem_rdata(7 downto 0),
    1 -> io.dmem_rdata(15 downto 8),
    2 -> io.dmem_rdata(23 downto 16),
    default -> io.dmem_rdata(31 downto 24)
  )
  val hdata = Mux(alow(1), io.dmem_rdata(31 downto 16), io.dmem_rdata(15 downto 0))

  val load_data = size.mux(
    2 -> io.dmem_rdata,
    1 -> hdata.asSInt.resize(32).asUInt,
    0 -> (mem.mem_sext ? bdata.asSInt.resize(32).asUInt | bdata.resize(32)),
    default -> U(0, 32 bits)
  )
  io.stall := mem.mem_read && !io.dmem_valid

  io.mem2wb.pc := mem.pc
  io.mem2wb.result := mem.mem_read ? load_data | mem.alu_result
  io.mem2wb.wb_en := mem.wb_en
  io.mem2wb.rd_addr := mem.rd_addr
  io.mem2wb.csr_op := mem.csr_op
  io.mem2wb.csr_num := mem.csr_num
  io.mem2wb.csr_rdata := mem.alu_result
  io.mem2wb.valid := mem.valid
  io.mem2wb.except := mem.except
  io.mem2wb.except_code := mem.except_code
}

// WB Stage
case class WBStage() extends Component {
  val io = new Bundle {
    val mem2wb = in(MEM2WB())
    val rf_wen = Bool()
    val rf_wnum = UInt(5 bits)
    val rf_wdata = out UInt (32 bits)
  }
  io.rf_wen := io.mem2wb.wb_en && io.mem2wb.valid && !io.mem2wb.except
  io.rf_wnum := io.mem2wb.rd_addr
  io.rf_wdata := (io.mem2wb.csr_op === U(1, 2 bits)) ? io.mem2wb.csr_rdata | io.mem2wb.result
}

object IF2ID { def apply() = new IF2ID }
object ID2EXE { def apply() = new ID2EXE }
object EXE2MEM { def apply() = new EXE2MEM }
object MEM2WB { def apply() = new MEM2WB }
