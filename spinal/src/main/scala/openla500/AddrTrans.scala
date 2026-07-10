package openla500
import spinal.core._
case class AddrTrans() extends Component {
  val io = new Bundle {
    val va = in UInt (32 bits); val is_load = in Bool ()
    val pa = out UInt (32 bits); val tlb_excp = out Bool ()
    val excp_code = out UInt (6 bits); val uncached = out Bool (); val mat = out UInt (2 bits)
  }
  io.pa := io.va; io.mat := U(1, 2 bits); io.uncached := False
  io.tlb_excp := False; io.excp_code := U(0, 6 bits)
  when(io.va(31 downto 28) === U(0x8, 4 bits)) {
    io.uncached := True; io.mat := U(0, 2 bits)
    io.pa := io.va(27 downto 0).resize(32)
  }.elsewhen(io.va(31 downto 28) === U(0xa, 4 bits)) {
    io.uncached := False; io.mat := U(1, 2 bits)
    io.pa := io.va(27 downto 0).resize(32)
  }
}
