package openla500
import spinal.core._

case class Divider() extends Component {
  val io = new Bundle {
    val div_op = in UInt (1 bits); val div_signed = in Bool ()
    val src1 = in UInt (32 bits); val src2 = in UInt (32 bits)
    val valid = in Bool (); val result = out UInt (32 bits)
    val ready = out Bool (); val div_by_zero = out Bool ()
  }
  val cnt = Reg(UInt(6 bits)) init (0); val busy = Reg(Bool()) init (False)
  val quotient = Reg(UInt(32 bits)); val remainder = Reg(UInt(32 bits))
  val divisor = Reg(UInt(32 bits)); val sign_q = Reg(Bool()); val sign_r = Reg(Bool())

  when(io.valid && !busy) {
    busy := True; cnt := 0
    sign_q := io.div_signed && (io.src1(31) ^ io.src2(31))
    sign_r := io.div_signed && io.src1(31)
    val a = (io.div_signed && io.src1(31)) ? (U(0, 32 bits) - io.src1) | io.src1
    val b = (io.div_signed && io.src2(31)) ? (U(0, 32 bits) - io.src2) | io.src2
    when(io.src2 === U(0)) { quotient := U(0); remainder := io.src1; busy := False }
      .otherwise { quotient := U(0); remainder := a; divisor := b }
  }

  when(busy) {
    cnt := cnt + 1
    remainder := (remainder(30 downto 0) ## quotient(31)).asUInt
    val sd = remainder.asSInt - divisor.asSInt
    quotient(0) := !sd(31)
    when(!sd(31)) { remainder := sd.asUInt }
    when(cnt === 31) {
      busy := False
      when(sign_q) { quotient := (0 - quotient.asSInt).asUInt }
      when(sign_r) { remainder := (0 - remainder.asSInt).asUInt }
    }
  }

  io.result := io.div_op.mux(0 -> quotient, 1 -> remainder)
  io.ready := !busy; io.div_by_zero := io.src2 === U(0)
}
