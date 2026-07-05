package openla500

import spinal.core._
import spinal.lib._

// AXI4 bridge: CPU memory requests → AXI4 master
// Matches openLA500 axi_bridge.v
case class AxiBridge() extends Component {
  val io = new Bundle {
    // CPU side (simplified memory request)
    val cpu_req       = Bool()
    val cpu_wr        = Bool()
    val cpu_addr      = UInt(32 bits)
    val cpu_wdata     = UInt(32 bits)
    val cpu_wstrb     = UInt(4 bits)
    val cpu_size      = UInt(2 bits)  // 0=byte, 1=half, 2=word
    val cpu_rdata     = UInt(32 bits)
    val cpu_ready     = Bool()
    val cpu_data_ok   = Bool()

    // AXI4 master interface
    // AW channel
    val awid    = UInt(4 bits)
    val awaddr  = UInt(32 bits)
    val awlen   = UInt(8 bits)
    val awsize  = UInt(3 bits)
    val awburst = out UInt(2 bits)
    val awvalid = out Bool()
    val awready = in Bool()

    // W channel
    val wdata   = UInt(32 bits)
    val wstrb   = UInt(4 bits)
    val wlast   = Bool()
    val wvalid  = Bool()
    val wready  = Bool()

    // B channel
    val bid     = UInt(4 bits)
    val bresp   = UInt(2 bits)
    val bvalid  = Bool()
    val bready  = Bool()

    // AR channel
    val arid    = UInt(4 bits)
    val araddr  = UInt(32 bits)
    val arlen   = UInt(8 bits)
    val arsize  = UInt(3 bits)
    val arburst = out UInt(2 bits)
    val arvalid = out Bool()
    val arready = in Bool()

    // R channel
    val rid     = UInt(4 bits)
    val rdata   = UInt(32 bits)
    val rresp   = UInt(2 bits)
    val rlast   = Bool()
    val rvalid  = Bool()
    val rready  = Bool()
  }

  // FSM states
  val IDLE   = U(0, 2 bits); val RADDR  = U(1, 2 bits)
  val WADDR  = U(2, 2 bits); val WDATA  = U(3, 2 bits)
  val state  = RegInit(IDLE)

  io.cpu_data_ok := False
  io.cpu_ready   := False

  io.awid    := 0  ; io.awaddr  := 0  ; io.awlen   := 0
  io.awsize  := 2  ; io.awburst := 1  ; io.awvalid := False
    ; io.wstrb   := 0  ; io.wlast   := True
  io.wvalid  := False
  io.bready  := False
  io.arid    := 0  ; io.araddr  := 0  ; io.arlen   := 0
  io.arsize  := 2  ; io.arburst := 1  ; io.arvalid := False
  io.rready  := False

  switch(state) {
    is(IDLE) {
      when(io.cpu_req) {
        when(io.cpu_wr) {
          state := WADDR
          io.awaddr  := io.cpu_addr
          io.awvalid := True
          io.bready  := True
        }.otherwise {
          state := RADDR
          io.araddr  := io.cpu_addr
          io.arvalid := True
          io.rready  := True
        }
      }
    }

    is(RADDR) {
      io.araddr  := io.cpu_addr
      io.arvalid := True
      io.rready  := True
      when(io.arready) {
        state := IDLE
      }
    }

    is(WADDR) {
      io.awaddr  := io.cpu_addr
      io.awvalid := True
      when(io.awready) {
        state := WDATA
      }
    }

    is(WDATA) {
      io.wdata   := io.cpu_wdata
      io.wstrb   := io.cpu_wstrb
      io.wvalid  := True
      when(io.wready) {
        io.bready := True
        state := IDLE
      }
    }
  }

  // Read data capture
  val rdata_reg = RegNextWhen(io.rdata, io.rvalid && io.rready)
  io.cpu_rdata := rdata_reg

  when(state === RADDR && io.rvalid && io.rready) {
    io.cpu_data_ok := True
  }
  when(state === WADDR && io.bvalid) {
    state := IDLE
  }
}
