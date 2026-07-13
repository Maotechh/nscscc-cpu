package openla500.compat

import spinal.core._

/** Locked compatibility boundary for the chiplab core_top interface. */
final case class CoreTopCompatConfig(tlbEntries: Int = 32) {
  require(tlbEntries == 32, "only the locked TLBNUM=32 configuration is currently verified")
}

final class CoreTopCompat(config: CoreTopCompatConfig = CoreTopCompatConfig()) extends Component {
  val io = new Bundle {
    val aclk = in Bool ()
    val aresetn = in Bool ()
    val intrpt = in Bits (8 bits)

    val arid = out Bits (4 bits)
    val araddr = out Bits (32 bits)
    val arlen = out Bits (8 bits)
    val arsize = out Bits (3 bits)
    val arburst = out Bits (2 bits)
    val arlock = out Bits (2 bits)
    val arcache = out Bits (4 bits)
    val arprot = out Bits (3 bits)
    val arvalid = out Bool ()
    val arready = in Bool ()

    val rid = in Bits (4 bits)
    val rdata = in Bits (32 bits)
    val rresp = in Bits (2 bits)
    val rlast = in Bool ()
    val rvalid = in Bool ()
    val rready = out Bool ()

    val awid = out Bits (4 bits)
    val awaddr = out Bits (32 bits)
    val awlen = out Bits (8 bits)
    val awsize = out Bits (3 bits)
    val awburst = out Bits (2 bits)
    val awlock = out Bits (2 bits)
    val awcache = out Bits (4 bits)
    val awprot = out Bits (3 bits)
    val awvalid = out Bool ()
    val awready = in Bool ()

    val wid = out Bits (4 bits)
    val wdata = out Bits (32 bits)
    val wstrb = out Bits (4 bits)
    val wlast = out Bool ()
    val wvalid = out Bool ()
    val wready = in Bool ()

    val bid = in Bits (4 bits)
    val bresp = in Bits (2 bits)
    val bvalid = in Bool ()
    val bready = out Bool ()

    val break_point = in Bool ()
    val infor_flag = in Bool ()
    val reg_num = in Bits (5 bits)
    val ws_valid = out Bool ()
    val rf_rdata = out Bits (32 bits)
    val debug0_wb_pc = out Bits (32 bits)
    val debug0_wb_rf_wen = out Bits (4 bits)
    val debug0_wb_rf_wnum = out Bits (5 bits)
    val debug0_wb_rf_wdata = out Bits (32 bits)
    val debug0_wb_inst = out Bits (32 bits)
  }

  noIoPrefix()

  // The golden wrapper registers ~aresetn once before presenting a synchronous active-high reset
  // to the core. The capture register intentionally has no reset or initialization of its own.
  val resetCaptureDomain = ClockDomain(
    clock = io.aclk,
    config = ClockDomainConfig(clockEdge = RISING)
  )
  val resetCapture = new ClockingArea(resetCaptureDomain) {
    val delayedActiveHigh = RegNext(!io.aresetn)
  }

  val coreClockDomain = ClockDomain(
    clock = io.aclk,
    reset = resetCapture.delayedActiveHigh,
    config = ClockDomainConfig(
      clockEdge = RISING,
      resetKind = SYNC,
      resetActiveLevel = HIGH
    )
  )

  val backendArea = new ClockingArea(coreClockDomain) {
    val core = new SpinalCoreBackend(
      openla500.config.CoreConfig.Locked.copy(tlbEntries = config.tlbEntries)
    )
  }
  val core = backendArea.core

  core.io.aclk := coreClockDomain.clock
  core.io.aresetn := !coreClockDomain.reset
  core.io.intrpt := io.intrpt
  core.io.arready := io.arready
  core.io.rid := io.rid
  core.io.rdata := io.rdata
  core.io.rresp := io.rresp
  core.io.rlast := io.rlast
  core.io.rvalid := io.rvalid
  core.io.awready := io.awready
  core.io.wready := io.wready
  core.io.bid := io.bid
  core.io.bresp := io.bresp
  core.io.bvalid := io.bvalid
  core.io.break_point := io.break_point
  core.io.infor_flag := io.infor_flag
  core.io.reg_num := io.reg_num

  io.arid := core.io.arid
  io.araddr := core.io.araddr
  io.arlen := core.io.arlen
  io.arsize := core.io.arsize
  io.arburst := core.io.arburst
  io.arlock := core.io.arlock
  io.arcache := core.io.arcache
  io.arprot := core.io.arprot
  io.arvalid := core.io.arvalid
  io.rready := core.io.rready
  io.awid := core.io.awid
  io.awaddr := core.io.awaddr
  io.awlen := core.io.awlen
  io.awsize := core.io.awsize
  io.awburst := core.io.awburst
  io.awlock := core.io.awlock
  io.awcache := core.io.awcache
  io.awprot := core.io.awprot
  io.awvalid := core.io.awvalid
  io.wid := core.io.wid
  io.wdata := core.io.wdata
  io.wstrb := core.io.wstrb
  io.wlast := core.io.wlast
  io.wvalid := core.io.wvalid
  io.bready := core.io.bready
  io.ws_valid := core.io.ws_valid
  io.rf_rdata := core.io.rf_rdata
  io.debug0_wb_pc := core.io.debug0_wb_pc
  io.debug0_wb_rf_wen := core.io.debug0_wb_rf_wen
  io.debug0_wb_rf_wnum := core.io.debug0_wb_rf_wnum
  io.debug0_wb_rf_wdata := core.io.debug0_wb_rf_wdata
  io.debug0_wb_inst := core.io.debug0_wb_inst
}
