package openla500

import spinal.core._

// Performance counters: matches openLA500 perf_counter.v
case class PerfCounter() extends Component {
  val io = new Bundle {
    // Input events
    val dcache_miss   = in Bool()
    val icache_miss   = in Bool()
    val commit_inst   = in Bool()
    val br_inst       = in Bool()
    val mem_inst      = in Bool()
    val br_pre        = in Bool()
    val br_pre_error  = in Bool()
  }

  // 32-bit counters
  val dcache_miss_counter  = Reg(UInt(32 bits)) init(0)
  val icache_miss_counter  = Reg(UInt(32 bits)) init(0)
  val commit_inst_counter  = Reg(UInt(32 bits)) init(0)
  val br_inst_counter      = Reg(UInt(32 bits)) init(0)
  val mem_inst_counter     = Reg(UInt(32 bits)) init(0)
  val br_pre_counter       = Reg(UInt(32 bits)) init(0)
  val br_pre_error_counter = Reg(UInt(32 bits)) init(0)

  // Increment on events
  when(io.dcache_miss)   { dcache_miss_counter  := dcache_miss_counter  + 1 }
  when(io.icache_miss)   { icache_miss_counter  := icache_miss_counter  + 1 }
  when(io.commit_inst)   { commit_inst_counter  := commit_inst_counter  + 1 }
  when(io.br_inst)       { br_inst_counter      := br_inst_counter      + 1 }
  when(io.mem_inst)      { mem_inst_counter     := mem_inst_counter     + 1 }
  when(io.br_pre)        { br_pre_counter       := br_pre_counter       + 1 }
  when(io.br_pre_error)  { br_pre_error_counter := br_pre_error_counter + 1 }
}
