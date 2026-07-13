package openla500.pipeline

import openla500.config.CoreConfig
import spinal.core._

/** Active openLA500 2R1W GPR file.
  *
  * Reads are combinational with same-cycle write bypass. Storage intentionally has no reset,
  * matching the golden module. Address zero reads as zero, while the physical slot remains
  * observable in the optional legacy DiffTest array.
  */
final class OpenLa500RegFile(
    config: CoreConfig = CoreConfig.Locked,
    definitionName: String = "regfile"
) extends Component {
  setDefinitionName(definitionName)

  val io = new Bundle {
    val clk = in(Bool())
    val raddr1 = in(UInt(5 bits))
    val rdata1 = out(Bits(32 bits))
    val raddr2 = in(UInt(5 bits))
    val rdata2 = out(Bits(32 bits))
    val we = in(Bool())
    val waddr = in(UInt(5 bits))
    val wdata = in(Bits(32 bits))
    val rf_o = config.diffTestEnabled generate out(Vec(Bits(32 bits), 32))
  }
  noIoPrefix()

  private val registerDomain = ClockDomain(clock = io.clk)
  private val storage = new ClockingArea(registerDomain) {
    val registers = Vec.fill(32)(Reg(Bits(32 bits)))
    when(io.we) {
      registers(io.waddr) := io.wdata
    }
  }

  private def read(address: UInt): Bits =
    Mux(
      address === 0,
      B(0, 32 bits),
      Mux(io.we && address === io.waddr, io.wdata, storage.registers(address))
    )

  io.rdata1 := read(io.raddr1)
  io.rdata2 := read(io.raddr2)

  if (config.diffTestEnabled) {
    for (index <- 0 until 32) io.rf_o(index) := storage.registers(index)
  }
}
