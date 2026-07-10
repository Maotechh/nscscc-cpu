package openla500
import spinal.core._

case class Multiplier() extends Component {
  val io = new Bundle {
    val mul_op = in UInt (2 bits); val mul_signed = in Bool ()
    val src1 = in UInt (32 bits); val src2 = in UInt (32 bits)
    val valid = in Bool (); val result = out UInt (32 bits); val ready = out Bool ()
  }
  val cnt = Reg(UInt(6 bits)) init (0); val busy = Reg(Bool()) init (False)
  val prod = Reg(UInt(65 bits)); val sign_a = Reg(Bool()); val sign_b = Reg(Bool())
  val is_signed = io.mul_op === U(0, 2 bits) || io.mul_op === U(1, 2 bits)

  when(io.valid && !busy) {
    busy := True; cnt := 0
    sign_a := is_signed && io.src1(31); sign_b := is_signed && io.src2(31)
    val a = (is_signed && io.src1(31)) ? (U(0, 32 bits) - io.src1) | io.src1
    val b = (is_signed && io.src2(31)) ? (U(0, 32 bits) - io.src2) | io.src2
    prod := a.resize(65); prod(0) := False
  }

  when(busy) {
    cnt := cnt + 1
    when(cnt < 32) {
      when(prod(0)) {
        prod := ((prod(64 downto 33) + io.src2.resize(33)).resize(33) ## prod(32 downto 1)).asUInt
      }.otherwise {
        prod := prod |>> 1
      }
    }
    when(cnt === 32) {
      busy := False
      when(sign_a ^ sign_b) {
        prod(63 downto 31) := (U(0, 33 bits) - prod(63 downto 31)).resize(33)
      }
    }
  }

  io.result := io.mul_op.mux(0 -> prod(31 downto 0), default -> prod(63 downto 32))
  io.ready := !busy
}
