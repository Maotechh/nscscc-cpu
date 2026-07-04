// Dual-issue register file: 4-read, 2-write
// Supports 2 instructions per cycle with full WAW forwarding
module regfile_dual(
    input         clk,
    // READ PORTS (4 ports for 2 instructions × 2 operands each)
    input  [ 4:0] raddr_a1,  // inst A, operand 1 (rj)
    input  [ 4:0] raddr_a2,  // inst A, operand 2 (rk)
    output [31:0] rdata_a1,
    output [31:0] rdata_a2,
    input  [ 4:0] raddr_b1,  // inst B, operand 1 (rj)
    input  [ 4:0] raddr_b2,  // inst B, operand 2 (rk)
    output [31:0] rdata_b1,
    output [31:0] rdata_b2,
    // WRITE PORTS (2 ports for 2 instructions)
    input         we_a,       // write enable inst A
    input  [ 4:0] waddr_a,
    input  [31:0] wdata_a,
    input         we_b,       // write enable inst B
    input  [ 4:0] waddr_b,
    input  [31:0] wdata_b
);

reg [31:0] rf[31:0];

// Dual write ports with priority (A before B if same address)
always @(posedge clk) begin
    if (we_a) rf[waddr_a] <= wdata_a;
    if (we_b) rf[waddr_b] <= wdata_b;
end

// READ PORT A1
assign rdata_a1 = (raddr_a1 == 5'b0) ? 32'b0 :
    // WAW forwarding from write ports
    ((raddr_a1 == waddr_a) && we_a) ? wdata_a :
    ((raddr_a1 == waddr_b) && we_b) ? wdata_b :
    rf[raddr_a1];

// READ PORT A2
assign rdata_a2 = (raddr_a2 == 5'b0) ? 32'b0 :
    ((raddr_a2 == waddr_a) && we_a) ? wdata_a :
    ((raddr_a2 == waddr_b) && we_b) ? wdata_b :
    rf[raddr_a2];

// READ PORT B1
assign rdata_b1 = (raddr_b1 == 5'b0) ? 32'b0 :
    ((raddr_b1 == waddr_a) && we_a) ? wdata_a :
    ((raddr_b1 == waddr_b) && we_b) ? wdata_b :
    rf[raddr_b1];

// READ PORT B2
assign rdata_b2 = (raddr_b2 == 5'b0) ? 32'b0 :
    ((raddr_b2 == waddr_a) && we_a) ? wdata_a :
    ((raddr_b2 == waddr_b) && we_b) ? wdata_b :
    rf[raddr_b2];

endmodule
