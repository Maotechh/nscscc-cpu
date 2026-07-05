// Spinal-equivalent: wb_stage ← spinal/src/.../wbstage.scala
// From Spinal source (WBStage in Pipeline.scala)
module wb_stage(
    input         clk, reset,
    input  [31:0] mem2wb_pc, mem2wb_result,
    input         mem2wb_valid, mem2wb_wb_en, mem2wb_except, input [5:0] mem2wb_except_code,
    input  [ 4:0] mem2wb_rd_addr,
    input  [ 1:0] mem2wb_csr_op, input [13:0] mem2wb_csr_num, input [31:0] mem2wb_csr_rdata,
    // Register file write
    output        rf_wen, output [4:0] rf_wnum, output [31:0] rf_wdata
);
    assign rf_wen = mem2wb_wb_en && mem2wb_valid && ~mem2wb_except;
    assign rf_wnum = mem2wb_rd_addr;
    assign rf_wdata = (mem2wb_csr_op == 2'd1) ? mem2wb_csr_rdata : mem2wb_result;
endmodule
