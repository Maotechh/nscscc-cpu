module AxiBridge(input io_cpu_req, io_cpu_wr, input [31:0] io_cpu_addr, io_cpu_wdata,
    input [3:0] io_cpu_wstrb, input [1:0] io_cpu_size, input io_awready, io_wready, io_arready, io_rvalid, io_rlast, io_bvalid,
    input [31:0] io_rdata, input [3:0] io_bid, io_rid, input [1:0] io_bresp, io_rresp,
    output io_cpu_ready, io_cpu_data_ok, output [31:0] io_cpu_rdata,
    output [3:0] io_awid, io_arid, output [31:0] io_awaddr, io_araddr,
    output [7:0] io_awlen, io_arlen, output [2:0] io_awsize, io_arsize, output [1:0] io_awburst, io_arburst,
    output io_awvalid, io_arvalid, output [31:0] io_wdata, output [3:0] io_wstrb, output io_wlast, io_wvalid, io_bready, io_rready);
assign io_cpu_ready=0; assign io_cpu_data_ok=0; assign io_cpu_rdata=0; assign io_awid=0; assign io_arid=0;
assign io_awaddr=0; assign io_araddr=0; assign io_awlen=0; assign io_arlen=0; assign io_awsize=2; assign io_arsize=2;
assign io_awburst=2; assign io_arburst=2; assign io_awvalid=0; assign io_arvalid=0; assign io_wdata=0;
assign io_wstrb=0; assign io_wlast=0; assign io_wvalid=0; assign io_bready=0; assign io_rready=0; endmodule