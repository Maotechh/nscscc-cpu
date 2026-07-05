package openla500

import spinal.core._
import openla500.TLBConfig._

// 32-entry fully-associative TLB
case class TLBEntry() extends Component {
  val io = new Bundle {
    // Search
    val search_vpn   = UInt(19 bits)  // VPN[31:13]
    val search_asid  = UInt(10 bits)
    val search_valid = in Bool()

    // Results
    val hit          = Bool()
    val found_ppn    = UInt(20 bits)  // PPN[31:12] from TLB
    val found_ps     = UInt(6 bits)   // page size
    val found_g      = Bool()         // global
    val found_v      = Bool()         // valid
    val found_d      = Bool()         // dirty

    // Write
    val write_valid  = Bool()
    val write_index  = UInt(INDEX_BITS bits)
    val write_vpn    = UInt(19 bits)
    val write_ppn0   = UInt(20 bits)
    val write_ppn1   = UInt(20 bits)
    val write_ps     = UInt(6 bits)
    val write_asid   = UInt(10 bits)
    val write_g      = Bool()
    val write_v      = Bool()
    val write_d0     = Bool()
    val write_d1     = Bool()

    // Invalidate
    val inv_req      = Bool()
    val inv_vpn      = UInt(19 bits)
    val inv_asid     = UInt(10 bits)

    // Probe for tlbrd (read TLB entry)
    val probe_index  = UInt(INDEX_BITS bits)
    val probe_vpn    = UInt(19 bits)
    val probe_ppn0   = UInt(20 bits)
    val probe_ppn1   = UInt(20 bits)
    val probe_ps     = UInt(6 bits)
    val probe_asid   = UInt(10 bits)
    val probe_g      = Bool()
    val probe_v      = Bool()
    val probe_d0     = Bool()
    val probe_d1     = Bool()
  }

  // TLB storage arrays
  val vppn  = Vec(Reg(UInt(19 bits)) init(0), ENTRIES)
  val ppn0  = Vec(Reg(UInt(20 bits)) init(0), ENTRIES)
  val ppn1  = Vec(Reg(UInt(20 bits)) init(0), ENTRIES)
  val ps    = Vec(Reg(UInt(6 bits)) init(0), ENTRIES)
  val asid  = Vec(Reg(UInt(10 bits)) init(0), ENTRIES)
  val g     = Vec(Reg(Bool()) init(False), ENTRIES)
  val v     = Vec(Reg(Bool()) init(False), ENTRIES)
  val d0    = Vec(Reg(Bool()) init(False), ENTRIES)
  val d1    = Vec(Reg(Bool()) init(False), ENTRIES)

  // Full-associative search: compare VPN+ASID(unless G) against all entries
  io.hit := False
  io.found_ppn := U(0)
  io.found_ps  := U(0)
  io.found_g   := False
  io.found_v   := False
  io.found_d   := False

  when(io.search_valid) {
    for (i <- 0 until ENTRIES) {
      val vpn_match = vppn(i) === io.search_vpn
      val asid_match = g(i) || (asid(i) === io.search_asid)
      when(v(i) && vpn_match && asid_match) {
        io.hit        := True
        io.found_ppn  := ppn0(i)
        io.found_ps   := ps(i)
        io.found_g    := g(i)
        io.found_v    := v(i)
        io.found_d    := d0(i)
      }
    }
  }

  // Write
  when(io.write_valid) {
    vppn(io.write_index)  := io.write_vpn
    ppn0(io.write_index)  := io.write_ppn0
    ppn1(io.write_index)  := io.write_ppn1
    ps(io.write_index)    := io.write_ps
    asid(io.write_index)  := io.write_asid
    g(io.write_index)     := io.write_g
    v(io.write_index)     := io.write_v
    d0(io.write_index)    := io.write_d0
    d1(io.write_index)    := io.write_d1
  }

  // Invalidate entries matching VPN (+ ASID if not global)
  when(io.inv_req) {
    for (i <- 0 until ENTRIES) {
      val match_inv = vppn(i) === io.inv_vpn && (g(i) || asid(i) === io.inv_asid)
      when(match_inv) { v(i) := False }
    }
  }

  // Probe (TLBRD)
  io.probe_vpn  := vppn(io.probe_index)
  io.probe_ppn0 := ppn0(io.probe_index)
  io.probe_ppn1 := ppn1(io.probe_index)
  io.probe_ps   := ps(io.probe_index)
  io.probe_asid := asid(io.probe_index)
  io.probe_g    := g(io.probe_index)
  io.probe_v    := v(io.probe_index)
  io.probe_d0   := d0(io.probe_index)
  io.probe_d1   := d1(io.probe_index)
}
