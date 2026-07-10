package openla500

import spinal.core._
import spinal.lib._

// ============================================================================
// Register File — 32-entry x 32-bit, 2-read 1-write
// Functionally equivalent to openLA500's regfile.v
//
// Key characteristics:
//   - Combinational reads (no read latency — data available same cycle as addr)
//   - Synchronous write on posedge clk, active-high wen
//   - WAW (Write-After-Write) forwarding: when rnum == wnum and wen is high,
//     the read port returns wdata directly instead of the stale register value.
//     This handles the rk==rd hazard where a register is both read and written
//     in the same cycle.
//   - Register 0 (GR[0]) is hardwired to 0 — writes to it are silently ignored,
//     reads from it always return 0.
//   - Port names match regfile.v exactly: wen, wnum, wdata, rnum1, rdata1,
//     rnum2, rdata2
// ============================================================================

case class RegFile() extends Component {
  val io = new Bundle {
    // ---- Write port ----
    val wen = in Bool () // Write enable (active-high)
    val wnum = in UInt (5 bits) // Write register number (rd)
    val wdata = in UInt (32 bits) // Write data

    // ---- Read port 1 (rj) ----
    val rnum1 = in UInt (5 bits) // Read register number 1
    val rdata1 = out UInt (32 bits) // Read data 1

    // ---- Read port 2 (rk) ----
    val rnum2 = in UInt (5 bits) // Read register number 2
    val rdata2 = out UInt (32 bits) // Read data 2
  }

  // ------------------------------------------------------------------
  // Register array: 32 x 32-bit registers
  // Vec of Reg gives combinational reads (matching Verilog async reads)
  // and synchronous writes (posedge clk).
  // All registers initialize to 0 after reset.
  // ------------------------------------------------------------------
  val rf = Vec(Reg(UInt(32 bits)) init (0), 32)

  // ------------------------------------------------------------------
  // Synchronous write
  // Register 0 is architecturally hardwired to 0, so writes to it
  // are silently ignored (matching LA32R ISA specification).
  // ------------------------------------------------------------------
  when(io.wen && io.wnum =/= 0) {
    rf(io.wnum) := io.wdata
  }

  // ------------------------------------------------------------------
  // Combinational reads — raw register values from the array
  // ------------------------------------------------------------------
  val rdata1_raw = rf(io.rnum1)
  val rdata2_raw = rf(io.rnum2)

  // ------------------------------------------------------------------
  // Register 0 hardwire: GR[0] always reads as 0
  // ------------------------------------------------------------------
  val rdata1_r0 = (io.rnum1 === 0) ? U(0, 32 bits) | rdata1_raw
  val rdata2_r0 = (io.rnum2 === 0) ? U(0, 32 bits) | rdata2_raw

  // ------------------------------------------------------------------
  // WAW (Write-After-Write) forwarding
  //
  // When the same register is being read and written in the same cycle
  // (e.g., rk == rd for a single-cycle bypass), the read port must
  // return the write data rather than the stale register value.
  //
  // Condition: wen is high AND the read register number matches the
  // write register number AND the write target is not register 0.
  //
  // This check covers the critical rk==rd hazard:
  //   - If an instruction writes rd and reads rk, and rk == rd, the
  //     read port must see the updated value.
  // ------------------------------------------------------------------
  val waw_active = io.wen && io.wnum =/= 0

  io.rdata1 := (waw_active && io.rnum1 === io.wnum) ? io.wdata | rdata1_r0
  io.rdata2 := (waw_active && io.rnum2 === io.wnum) ? io.wdata | rdata2_r0
}
