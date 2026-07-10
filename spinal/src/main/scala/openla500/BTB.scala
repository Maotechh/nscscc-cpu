package openla500

import spinal.core._
import openla500.BTBConfig._

// Branch Target Buffer: 32-entry simple BTB with RAS
// Matches openLA500 btb.v exactly
case class BTB() extends Component {
  val io = new Bundle {
    // Lookup
    val lookup_pc = UInt(32 bits)
    val predict_taken = out Bool ()
    val predict_target = out UInt (32 bits)

    // Update (from execute stage)
    val update_valid = Bool()
    val update_pc = UInt(32 bits)
    val update_target = in UInt (32 bits)
    val update_taken = Bool()
    val update_is_br = Bool()

    // RAS (Return Address Stack)
    val is_call = Bool()
    val is_ret = Bool()
    val call_pc = UInt(32 bits) // PC of call (for RAS push)
    val ras_pop = Bool()
    val ras_target = UInt(32 bits)
  }

  val btb_valid = Mem(Bool(), ENTRIES)
  val btb_tag = Mem(UInt((32 - INDEX_BITS - 2) bits), ENTRIES)
  val btb_target = Mem(UInt(32 bits), ENTRIES)

  // RAS: 8-entry return address stack
  val ras_depth = 8
  val ras = Mem(UInt(32 bits), ras_depth)
  val ras_ptr = Reg(UInt(3 bits)) init (0) // 0-7
  val ras_full = Reg(Bool()) init (False)

  // Lookup
  val lookup_idx = io.lookup_pc(INDEX_BITS + 1 downto 2)
  val lookup_tag = io.lookup_pc(31 downto INDEX_BITS + 2)

  io.predict_taken := False
  io.predict_target := io.lookup_pc + 4

  when(btb_valid(lookup_idx) && btb_tag(lookup_idx) === lookup_tag) {
    io.predict_taken := True
    io.predict_target := btb_target(lookup_idx)
  }

  // Update
  when(io.update_valid && io.update_is_br) {
    val upd_idx = io.update_pc(INDEX_BITS + 1 downto 2)
    when(io.update_taken) {
      btb_valid(upd_idx) := True
      btb_tag(upd_idx) := io.update_pc(31 downto INDEX_BITS + 2)
      btb_target(upd_idx) := io.update_target
    }.otherwise {
      btb_valid(upd_idx) := False
    }
  }

  // RAS: push on call
  when(io.is_call) {
    ras(ras_ptr) := io.call_pc + 4 // return address
    ras_ptr := ras_ptr + 1
    when(ras_ptr === ras_depth - 1) { ras_full := True }
  }

  // RAS: pop on return
  io.ras_pop := io.is_ret && (ras_ptr =/= 0 || ras_full)
  when(io.is_ret && (ras_ptr =/= 0 || ras_full)) {
    when(!ras_full) { ras_ptr := ras_ptr - 1 }
      .otherwise { ras_full := False }
    io.ras_target := ras(ras_ptr - U(!ras_full, 1 bits))
    io.predict_taken := True
  }
}
