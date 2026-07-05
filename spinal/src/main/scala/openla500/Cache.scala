package openla500
import spinal.core._
import openla500.CacheConfig._

// ICache: 8KB, 2-way, 16B line with cacop fix
case class ICache() extends Component {
  val io = new Bundle {
    val req_valid = in Bool(); val req_op = in Bool()
    val req_addr = in UInt(32 bits); val req_wdata = in UInt(32 bits); val req_wstrb = in UInt(4 bits)
    val rsp_valid = out Bool(); val rsp_data = out UInt(32 bits); val cache_miss = out Bool()
    val cacop_en = in Bool(); val cacop_mode = in UInt(2 bits); val cacop_vaddr = in UInt(32 bits)
    val cacop_flush = out Bool()
    val refill_req = out Bool(); val refill_addr = out UInt(32 bits)
    val refill_valid = in Bool(); val refill_data = in UInt(32 bits)
    val refill_last = in Bool(); val refill_ready = out Bool()
  }
  val idx = io.req_addr(ICACHE_INDEX + 3 downto 4)
  val tg = io.req_addr(31 downto ICACHE_INDEX + 4)
  val ci = io.cacop_vaddr(ICACHE_INDEX + 3 downto 4)
  val wo = io.req_addr(3 downto 2)

  val N = ICACHE_SETS * ICACHE_WAYS  // 512
  val tagv = Mem(Bool(), N); val tagm = Mem(UInt(ICACHE_TAG bits), N)
  val db  = Mem(UInt(32 bits), N * (ICACHE_LINE / 4))

  val rbv = RegInit(False); val rba = Reg(UInt(32 bits)); val rbo = Reg(Bool())
  val rbc = Reg(Bool()); val rbcm = Reg(UInt(2 bits))

  val IDLE = U(0, 3 bits); val LOOKUP = U(1, 3 bits); val RPL = U(2, 3 bits); val RFL = U(3, 3 bits)
  val st = RegInit(IDLE)
  val ma = Reg(UInt(32 bits)); val mw = Reg(UInt(1 bits)); val mr = Reg(UInt(2 bits)); val mi = Reg(UInt(ICACHE_INDEX bits))

  val cap = rbc
  val c0 = cap && rbcm === U(0, 2 bits); val c1 = cap && (rbcm === U(1, 2 bits) || rbcm === U(3, 2 bits))

  val w0 = tagv(idx @@ U(0, 1 bits)) && tagm(idx @@ U(0, 1 bits)) === tg
  val w1 = tagv(idx @@ U(1, 1 bits)) && tagm(idx @@ U(1, 1 bits)) === tg
  val ch = ((w0 || w1) && !cap) || cap  // cacop fix

  io.cache_miss := False; io.rsp_valid := False
  io.refill_req := False; io.refill_addr := ma; io.refill_ready := True; io.cacop_flush := False

  val lo = rba(3 downto 2)
  io.rsp_data := db((mw @@ mr @@ lo).resize(log2Up(N * (ICACHE_LINE / 4)) bits))

  when(cap && c0) { tagv(ci @@ U(0, 1 bits)) := False; tagv(ci @@ U(1, 1 bits)) := False }

  switch(st) {
    is(IDLE) { when(io.req_valid || io.cacop_en) {
      rbv := True; rba := io.cacop_en ? io.cacop_vaddr | io.req_addr
      rbo := io.req_op; rbc := io.cacop_en; rbcm := io.cacop_mode; st := LOOKUP
    }}
    is(LOOKUP) { when(cap) {
      st := IDLE; io.rsp_valid := True; io.cacop_flush := True; rbc := False
    }.elsewhen(ch) {
      st := IDLE; io.rsp_valid := True
    }.otherwise {
      io.cache_miss := True; ma := rba; mw := mw + U(1, 1 bits); mr := U(0, 2 bits); mi := idx; st := RFL
    }}
    is(RFL) { when(io.refill_valid) {
      mr := mr + 1
      when(io.refill_last) {
        st := IDLE; tagv(mi @@ mw) := True; tagm(mi @@ mw) := rba(31 downto ICACHE_INDEX + 4)
        io.rsp_valid := True
      }
    }}
  }
}

// DCache: 8KB, 2-way, 16B line writethrough with cacop fix
case class DCache() extends Component {
  val io = new Bundle {
    val req_valid = in Bool(); val req_op = in Bool()
    val req_addr = in UInt(32 bits); val req_wdata = in UInt(32 bits); val req_wstrb = in UInt(4 bits)
    val req_uncached = in Bool()
    val rsp_valid = out Bool(); val rsp_data = out UInt(32 bits); val cache_miss = out Bool()
    val cacop_en = in Bool(); val cacop_mode = in UInt(2 bits); val cacop_vaddr = in UInt(32 bits)
    val refill_req = out Bool(); val refill_addr = out UInt(32 bits)
    val refill_valid = in Bool(); val refill_data = in UInt(32 bits)
    val refill_last = in Bool(); val refill_ready = out Bool()
    val wb_req = out Bool(); val wb_addr = out UInt(32 bits); val wb_data = out UInt(32 bits); val wb_valid = in Bool()
  }
  val idx = io.req_addr(DCACHE_INDEX + 3 downto 4)
  val tg = io.req_addr(31 downto DCACHE_INDEX + 4)
  val ci = io.cacop_vaddr(DCACHE_INDEX + 3 downto 4)

  val N = DCACHE_SETS * DCACHE_WAYS
  val tagv = Mem(Bool(), N); val tagm = Mem(UInt(DCACHE_TAG bits), N)
  val dirty = Mem(Bool(), N)
  val db = Mem(UInt(32 bits), N * (DCACHE_LINE / 4))

  val rbv = RegInit(False); val rba = Reg(UInt(32 bits)); val rbo = Reg(Bool())
  val rbc = Reg(Bool()); val rbcm = Reg(UInt(2 bits)); val rbu = Reg(Bool())

  val IDLE = U(0, 3 bits); val LOOKUP = U(1, 3 bits); val WB = U(2, 3 bits); val RFL = U(3, 3 bits)
  val st = RegInit(IDLE)
  val ma = Reg(UInt(32 bits)); val mw = Reg(UInt(1 bits)); val mr = Reg(UInt(2 bits)); val mi = Reg(UInt(DCACHE_INDEX bits))

  val cap = rbc; val c0 = cap && rbcm === U(0, 2 bits)
  val w0 = tagv(idx @@ U(0, 1 bits)) && tagm(idx @@ U(0, 1 bits)) === tg
  val w1 = tagv(idx @@ U(1, 1 bits)) && tagm(idx @@ U(1, 1 bits)) === tg
  val ch = ((w0 || w1) && !rbu) || cap

  io.cache_miss := False; io.rsp_valid := False
  io.refill_req := False; io.refill_addr := ma; io.refill_ready := True
  io.wb_req := False; io.wb_addr := U(0); io.wb_data := U(0)

  val lo = rba(3 downto 2)
  io.rsp_data := db((mw @@ mr @@ lo).resize(log2Up(N * (DCACHE_LINE / 4)) bits))

  when(cap && c0) { tagv(ci @@ U(0, 1 bits)) := False; tagv(ci @@ U(1, 1 bits)) := False
                     dirty(ci @@ U(0, 1 bits)) := False; dirty(ci @@ U(1, 1 bits)) := False }

  switch(st) {
    is(IDLE) { when(io.req_valid || io.cacop_en) {
      rbv := True; rba := io.cacop_en ? io.cacop_vaddr | io.req_addr
      rbo := io.req_op; rbc := io.cacop_en; rbcm := io.cacop_mode; rbu := io.req_uncached; st := LOOKUP
    }}
    is(LOOKUP) { when(cap) {
      st := IDLE; io.rsp_valid := True; rbc := False
    }.elsewhen(ch) {
      st := IDLE; io.rsp_valid := True
    }.otherwise {
      io.cache_miss := True; ma := rba; mw := mw + U(1, 1 bits); mr := U(0, 2 bits); mi := idx
      st := dirty(mi @@ mw) ? WB | RFL
    }}
    is(WB) { io.wb_req := True; when(io.wb_valid) { st := RFL } }
    is(RFL) { when(io.refill_valid) {
      mr := mr + 1
      when(io.refill_last) {
        st := IDLE; tagv(mi @@ mw) := True; tagm(mi @@ mw) := rba(31 downto DCACHE_INDEX + 4)
        dirty(mi @@ mw) := False; io.rsp_valid := True
      }
    }}
  }
}
