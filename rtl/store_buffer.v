// Store Buffer: decouples CPU stores from AXI write latency
// 4-entry FIFO, allows CPU to continue during store-miss
module store_buffer #(
    parameter DEPTH = 4,
    parameter ADDR_W = 32,
    parameter DATA_W = 32
)(
    input               clk,
    input               reset,
    // CPU side (producer)
    input               cpu_valid,
    input  [ADDR_W-1:0] cpu_addr,
    input  [DATA_W-1:0] cpu_wdata,
    input  [3:0]        cpu_wstrb,
    output              cpu_ready,  // can accept new store
    // AXI side (consumer)
    output              axi_valid,
    output [ADDR_W-1:0] axi_addr,
    output [DATA_W-1:0] axi_wdata,
    output [3:0]        axi_wstrb,
    input               axi_ready,  // AXI accepted this write
    // Bypass (coherency)
    input  [ADDR_W-1:0] load_addr,  // load address from MEM stage
    output              load_bypass, // load hits buffered store
    output [DATA_W-1:0] bypass_data
);

reg [ADDR_W-1:0] sb_addr   [DEPTH-1:0];
reg [DATA_W-1:0] sb_wdata  [DEPTH-1:0];
reg [3:0]        sb_wstrb  [DEPTH-1:0];
reg [DEPTH-1:0]  sb_valid;

wire [DEPTH-1:0] sb_ready;
wire full  = &sb_valid;
wire empty = ~|sb_valid;

// Write pointer management
reg [$clog2(DEPTH)-1:0] wr_ptr, rd_ptr;
reg [DEPTH:0] count;  // 0..DEPTH

assign cpu_ready = !full;

// CPU write
always @(posedge clk) begin
    if (reset) begin
        wr_ptr <= 0;
        count <= 0;
        sb_valid <= 0;
    end else begin
        if (cpu_valid && !full) begin
            sb_addr[wr_ptr]  <= cpu_addr;
            sb_wdata[wr_ptr] <= cpu_wdata;
            sb_wstrb[wr_ptr] <= cpu_wstrb;
            sb_valid[wr_ptr] <= 1'b1;
            wr_ptr <= wr_ptr + 1'b1;
            count <= count + 1'b1;
        end
        if (axi_valid && axi_ready) begin
            sb_valid[rd_ptr] <= 1'b0;
            rd_ptr <= rd_ptr + 1'b1;
            count <= count - 1'b1;
        end
    end
end

// AXI output
assign axi_valid = !empty;
assign axi_addr  = sb_addr[rd_ptr];
assign axi_wdata = sb_wdata[rd_ptr];
assign axi_wstrb = sb_wstrb[rd_ptr];

// Load bypass: check all entries for matching address
wire [DEPTH-1:0] match;
genvar i;
generate
    for (i = 0; i < DEPTH; i = i + 1) begin : gen_bypass
        assign match[i] = sb_valid[i] && (sb_addr[i] == load_addr);
    end
endgenerate

// Find youngest matching entry
wire [DEPTH-1:0] youngest;
assign youngest[0] = match[0];
genvar j;
generate
    for (j = 1; j < DEPTH; j = j + 1) begin : gen_youngest
        assign youngest[j] = match[j] && ~|match[j-1:0];
    end
endgenerate

assign load_bypass = |match;
assign bypass_data = youngest[0] ? sb_wdata[0] :
                     youngest[1] ? sb_wdata[1] :
                     youngest[2] ? sb_wdata[2] :
                                   sb_wdata[3];

endmodule
