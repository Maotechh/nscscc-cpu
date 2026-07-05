package openla500
import spinal.core._
import openla500.CSR._

case class CSRFile() extends Component {
  val io = new Bundle {
    val clk = in Bool(); val reset = in Bool()
    val csr_rd = in Bool(); val csr_wr = in Bool(); val csr_xchg = in Bool()
    val csr_num = in UInt(14 bits); val csr_wdata = in UInt(32 bits); val csr_rdata = out UInt(32 bits)
    val excp_valid = in Bool(); val excp_era = in UInt(32 bits)
    val excp_code = in UInt(6 bits); val excp_subcode = in UInt(9 bits); val excp_badv = in UInt(32 bits)
    val ertn_valid = in Bool()
    val in_kernel = out Bool(); val da_mod = out Bool(); val pg_mod = out Bool(); val user_mode = out Bool()
    val dmw0_base = out UInt(32 bits); val dmw1_base = out UInt(32 bits)
    val dmw0_mask = out UInt(32 bits); val dmw1_mask = out UInt(32 bits)
    val ext_int = in Bool(); val has_int = out Bool(); val int_vector = out UInt(8 bits)
  }
  val crmd_plv = Reg(UInt(2 bits)) init(0); val crmd_da = Reg(Bool()) init(True); val crmd_pg = Reg(Bool()) init(False)
  val prmd_pplv = Reg(UInt(2 bits)) init(0); val euen_fpe = Reg(Bool()) init(False)
  val ecfg_lie = Reg(UInt(13 bits)) init(0)
  val estat_ecode = Reg(UInt(6 bits)) init(0); val estat_is = Reg(UInt(13 bits)) init(0)
  val era = Reg(UInt(32 bits)) init(0); val badv = Reg(UInt(32 bits)) init(0)
  val eentry = Reg(UInt(32 bits)) init(0x1c000000L)
  val tlbidx_index = Reg(UInt(5 bits)) init(0); val tlbehi_vppn = Reg(UInt(19 bits)) init(0)
  val tlbelo0_ppn = Reg(UInt(20 bits)) init(0); val tlbelo1_ppn = Reg(UInt(20 bits)) init(0)
  val asid_asid = Reg(UInt(10 bits)) init(0); val asid_asidbits = Reg(UInt(8 bits)) init(10)
  val pgdl = Reg(UInt(32 bits)) init(0); val pgdh = Reg(UInt(32 bits)) init(0)
  val save0 = Reg(UInt(32 bits)) init(0); val save1 = Reg(UInt(32 bits)) init(0)
  val save2 = Reg(UInt(32 bits)) init(0); val save3 = Reg(UInt(32 bits)) init(0)
  val tid = Reg(UInt(32 bits)) init(0); val tcfg_en = Reg(Bool()) init(False)
  val tval = Reg(UInt(32 bits)) init(0)

  io.dmw0_base := U"32'h80000000"; io.dmw0_mask := U"32'hFFFFF000"
  io.dmw1_base := U"32'hA0000000"; io.dmw1_mask := U"32'hFFFFF000"

  io.csr_rdata := U(0)
  when(io.csr_rd) {
    switch(io.csr_num) {
      is(CRMD)    { io.csr_rdata := crmd_plv.resize(32) | (crmd_da.asUInt(32 bits) |<< 3) | (crmd_pg.asUInt(32 bits) |<< 4) }
      is(PRMD)    { io.csr_rdata := prmd_pplv.resize(32) }
      is(EUEN)    { io.csr_rdata := euen_fpe.asUInt(32 bits) }
      is(ECFG)    { io.csr_rdata := ecfg_lie.resize(32) }
      is(ESTAT)   { io.csr_rdata := estat_ecode.resize(32) }
      is(ERA)     { io.csr_rdata := era }
      is(BADV)    { io.csr_rdata := badv }
      is(EENTRY)  { io.csr_rdata := eentry }
      is(TLBIDX)  { io.csr_rdata := tlbidx_index.resize(32) }
      is(TLBEHI)  { io.csr_rdata := tlbehi_vppn.resize(32) }
      is(TLBELO0) { io.csr_rdata := tlbelo0_ppn.resize(32) }
      is(TLBELO1) { io.csr_rdata := tlbelo1_ppn.resize(32) }
      is(ASID)    { io.csr_rdata := asid_asid.resize(32) }
      is(PGDL)    { io.csr_rdata := pgdl }
      is(PGDH)    { io.csr_rdata := pgdh }
      is(SAVE0)   { io.csr_rdata := save0 }
      is(SAVE1)   { io.csr_rdata := save1 }
      is(SAVE2)   { io.csr_rdata := save2 }
      is(SAVE3)   { io.csr_rdata := save3 }
      is(TID)     { io.csr_rdata := tid }
      is(TCFG)    { io.csr_rdata := tcfg_en.asUInt(32 bits) }
      is(TVAL)    { io.csr_rdata := tval }
    }
  }

  when(io.csr_wr || io.csr_xchg) {
    val w = io.csr_wdata
    switch(io.csr_num) {
      is(CRMD)    { crmd_plv := w(1 downto 0); crmd_da := w(3); crmd_pg := w(4) }
      is(PRMD)    { prmd_pplv := w(1 downto 0) }
      is(EUEN)    { euen_fpe := w(0) }
      is(ECFG)    { ecfg_lie := w(12 downto 0) }
      is(ERA)     { era := w }
      is(EENTRY)  { eentry := w }
      is(TLBIDX)  { tlbidx_index := w(4 downto 0) }
      is(TLBEHI)  { tlbehi_vppn := w(31 downto 13) }
      is(TLBELO0) { tlbelo0_ppn := w(31 downto 12) }
      is(TLBELO1) { tlbelo1_ppn := w(31 downto 12) }
      is(ASID)    { asid_asid := w(9 downto 0); asid_asidbits := w(23 downto 16) }
      is(PGDL)    { pgdl := w }
      is(PGDH)    { pgdh := w }
      is(SAVE0)   { save0 := w }
      is(SAVE1)   { save1 := w }
      is(SAVE2)   { save2 := w }
      is(SAVE3)   { save3 := w }
      is(TID)     { tid := w }
      is(TCFG)    { tcfg_en := w(0) }
    }
  }

  when(io.excp_valid) {
    crmd_plv := 0; prmd_pplv := crmd_plv
    era := io.excp_era; estat_ecode := io.excp_code
    badv := io.excp_badv
  }
  when(io.ertn_valid) { crmd_plv := prmd_pplv; prmd_pplv := 0 }

  io.in_kernel := crmd_plv === 0; io.da_mod := crmd_da; io.pg_mod := crmd_pg
  io.user_mode := crmd_plv === 3
  io.has_int := (ecfg_lie & estat_is).orR && crmd_plv =/= 3
  io.int_vector := U(0, 8 bits)
}
