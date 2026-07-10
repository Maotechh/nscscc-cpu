package openla500

import spinal.core._

// Current simplified 4-bit encoding; this is not the golden openLA500 ALU contract.
object AluOp {
  val ADD = 0x0 // Addition
  val SUB = 0x1 // Subtraction
  val SLT = 0x2 // Set Less Than (signed)
  val SLTU = 0x3 // Set Less Than Unsigned
  val AND = 0x4 // Bitwise AND
  val NOR = 0x5 // Bitwise NOR
  val OR = 0x6 // Bitwise OR
  val XOR = 0x7 // Bitwise XOR
  val SLL = 0x8 // Shift Left Logical
  val SRL = 0x9 // Shift Right Logical
  val SRA = 0xa // Shift Right Arithmetic
  val LUI = 0xb // Load Upper Immediate
  val MUL = 0xc // Multiply (sent to mul unit)
  val MULH = 0xd // Multiply High
  val DIV = 0xe // Divide
  val MOD = 0xe // Modulo (same op, different div_op)
  val NONE = 0xf // No operation (pass through src2)
}

case class ALU() extends Component {
  val io = new Bundle {
    val alu_op = in UInt (4 bits)
    val src1 = in UInt (32 bits)
    val src2 = in UInt (32 bits)
    val result = out UInt (32 bits)
    val overflow = out Bool ()
    val cmp_sub = out Bool () // src1 < src2 (signed)
  }

  import AluOp._

  // Shifter
  val shamt = io.src2(4 downto 0)
  val sll_r = (io.src1 |<< shamt).resize(32)
  val srl_r = io.src1 |>> shamt
  val sra_r = (io.src1.asSInt |>> shamt)

  // ALU result multiplexer
  io.result := io.src1
  when(io.alu_op === ADD) { io.result := io.src1 + io.src2 }
    .elsewhen(io.alu_op === SUB) { io.result := (io.src1 - io.src2) }
    .elsewhen(io.alu_op === SLT) {
      io.result := ((io.src1.asSInt < io.src2.asSInt) ? U(1, 32 bits) | U(0, 32 bits))
    }
    .elsewhen(io.alu_op === SLTU) {
      io.result := ((io.src1 < io.src2) ? U(1, 32 bits) | U(0, 32 bits))
    }
    .elsewhen(io.alu_op === AND) { io.result := io.src1 & io.src2 }
    .elsewhen(io.alu_op === NOR) { io.result := ~(io.src1 | io.src2) }
    .elsewhen(io.alu_op === OR) { io.result := io.src1 | io.src2 }
    .elsewhen(io.alu_op === XOR) { io.result := io.src1 ^ io.src2 }
    .elsewhen(io.alu_op === SLL) { io.result := sll_r }
    .elsewhen(io.alu_op === SRL) { io.result := srl_r }
    .elsewhen(io.alu_op === SRA) { io.result := sra_r.asUInt }
    .elsewhen(io.alu_op === LUI) { io.result := io.src2 }

  // Overflow detection (for signed ADD/SUB)
  io.overflow := False
  when(io.alu_op === ADD) {
    io.overflow := (io.src1(31) === io.src2(31)) && (io.result(31) =/= io.src1(31))
  }.elsewhen(io.alu_op === SUB) {
    io.overflow := (io.src1(31) =/= io.src2(31)) && (io.result(31) =/= io.src1(31))
  }

  io.cmp_sub := io.src1.asSInt < io.src2.asSInt
}
