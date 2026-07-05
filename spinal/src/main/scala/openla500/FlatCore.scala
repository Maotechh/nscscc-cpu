package openla500
import spinal.core._

// Minimal stub: generates a valid Verilog file with correct structure
// Replace with actual inlined CPUCore once hierarchy approach confirmed
class FlatCore extends Component {
  val io = new Bundle {
    val aclk = in Bool(); val aresetn = in Bool()
    val araddr = out UInt(32 bits); val arvalid = out Bool(); val arready = in Bool()
    val rdata = in UInt(32 bits); val rvalid = in Bool(); val rready = out Bool()
    val awaddr = out UInt(32 bits); val awvalid = out Bool(); val awready = in Bool()
    val wdata = out UInt(32 bits); val wvalid = out Bool(); val wready = in Bool()
    val bvalid = in Bool(); val bready = out Bool()
  }
  // PC + instruction fetch
  val pc = Reg(UInt(32 bits)) init(0x1bfffffcL)
  val inst = Reg(UInt(32 bits)) init(0)
  val rf = Mem(UInt(32 bits), 32)
  val rf_wen = False; val rf_wnum = U(0, 5 bits); val rf_wdata = U(0, 32 bits)
  when(rf_wen) { rf(rf_wnum) := rf_wdata }
  
  io.araddr := pc; io.arvalid := True; io.rready := True
  io.awaddr := U(0); io.awvalid := False; io.wdata := U(0); io.wvalid := False; io.bready := False
  
  val fetch = Reg(Bool()) init(False)
  when(io.arready) { inst := io.rdata; fetch := True }
  when(io.rvalid) { pc := pc + 4; fetch := True }
}
object GenFlatCore extends App {
  SpinalConfig(targetDirectory = "../rtl").generateVerilog(new FlatCore)
}
