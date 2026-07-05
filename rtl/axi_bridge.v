// Spinal-equivalent: axi_bridge ← spinal/src/.../axibridge.scala
// Auto-generated from Spinal source (AxiBridge.scala) — manually translated for SpinalHDL compat
module axi_bridge
(
    input         cpu_req       ,
    input         cpu_wr        ,
    input  [31:0] cpu_addr      ,
    input  [31:0] cpu_wdata     ,
    input  [ 3:0] cpu_wstrb     ,
    input  [ 1:0] cpu_size      ,
    output        cpu_ready     ,
    output        cpu_data_ok   ,
    output [31:0] cpu_rdata     ,
    // AXI4 Master interface
    output [ 3:0] awid,    output [31:0] awaddr,   output [ 7:0] awlen,
    output [ 2:0] awsize,  output [ 1:0] awburst,  output        awvalid,
    input         awready,
    output [31:0] wdata,   output [ 3:0] wstrb,    output        wlast,   output wvalid,
    input         wready,
    input  [ 3:0] bid,     input  [ 1:0] bresp,    input         bvalid,  output bready,
    output [ 3:0] arid,    output [31:0] araddr,   output [ 7:0] arlen,
    output [ 2:0] arsize,  output [ 1:0] arburst,  output        arvalid,
    input         arready,
    input  [ 3:0] rid,     input  [31:0] rdata,    input  [ 1:0] rresp,
    input         rlast,   input         rvalid,    output        rready
);
    // Single-word AXI4 bridge: translates CPU requests to AXI4-Lite-compatible
    localparam IDLE = 2'd0, RADDR = 2'd1, WADDR = 2'd2, WDATA = 2'd3;
    reg [1:0] state;
    reg [31:0] rdata_r;
    
    assign awid = 4'd0; assign awlen = 8'd0; assign awsize = 3'd2; assign awburst = 2'd1;
    assign arid = 4'd0; assign arlen = 8'd0; assign arsize = 3'd2; assign arburst = 2'd1;
    assign wlast = 1'd1;
    
    assign cpu_ready = (state == IDLE);
    assign cpu_data_ok = (state == RADDR) && rvalid && rready;
    assign cpu_rdata = rdata_r;
    assign rready = (state == RADDR);
    
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            state <= IDLE; rdata_r <= 32'd0;
        end else begin
            case (state)
                IDLE: if (cpu_req) begin
                    if (cpu_wr) state <= WADDR;
                    else        state <= RADDR;
                end
                RADDR: begin
                    if (rvalid && rready) begin rdata_r <= rdata; state <= IDLE; end
                end
                WADDR: if (awready) state <= WDATA;
                WDATA: if (wready) begin bready <= 1'b1; state <= IDLE; end
            endcase
        end
    end
    
    assign awaddr  = cpu_addr; assign awvalid = (state == WADDR);
    assign wdata   = cpu_wdata; assign wstrb  = cpu_wstrb; assign wvalid = (state == WDATA);
    assign araddr  = cpu_addr; assign arvalid = (state == RADDR);
    assign bready  = (state == WDATA);
endmodule
