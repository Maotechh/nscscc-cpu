// Spinal-equivalent: mem_stage ← spinal/src/.../memstage.scala
// From Spinal source (MEMStage in Pipeline.scala)
module mem_stage(
    input         clk, reset,
    input  [31:0] exe2mem_pc, exe2mem_alu_result, exe2mem_mem_wdata, exe2mem_mem_addr,
    input         exe2mem_valid, exe2mem_mem_read, exe2mem_mem_write, exe2mem_mem_sext, exe2mem_wb_en,
    input         exe2mem_except, input [5:0] exe2mem_except_code,
    input         exe2mem_branch_taken, input [31:0] exe2mem_branch_target,
    // D-Cache interface
    output [31:0] dmem_addr, dmem_wdata, output [3:0] dmem_wstrb,
    output        dmem_read, dmem_write, input [31:0] dmem_rdata, input dmem_valid,
    output        stall,
    // To WB
    output [31:0] mem2wb_pc, mem2wb_result,
    output        mem2wb_valid, mem2wb_wb_en, mem2wb_except, output [5:0] mem2wb_except_code
);
    wire [1:0] size = exe2mem_mem_size;
    wire [1:0] alow = exe2mem_mem_addr[1:0];
    
    assign dmem_addr = exe2mem_mem_addr;
    assign dmem_wdata = exe2mem_mem_wdata;
    assign dmem_read = exe2mem_mem_read && ~exe2mem_except;
    assign dmem_write = exe2mem_mem_write && ~exe2mem_except;
    
    // Write strobe
    wire [3:0] wstrb_byte = (alow == 2'd0) ? 4'b0001 : (alow == 2'd1) ? 4'b0010 : (alow == 2'd2) ? 4'b0100 : 4'b1000;
    wire [3:0] wstrb_half = alow[1] ? 4'b1100 : 4'b0011;
    assign dmem_wstrb = (size == 2'd2) ? 4'b1111 : ((size == 2'd1) ? wstrb_half : wstrb_byte);
    
    // Load alignment
    wire [7:0] bdata = (alow == 2'd0) ? dmem_rdata[7:0] : (alow == 2'd1) ? dmem_rdata[15:8] : (alow == 2'd2) ? dmem_rdata[23:16] : dmem_rdata[31:24];
    wire [15:0] hdata = alow[1] ? dmem_rdata[31:16] : dmem_rdata[15:0];
    wire [31:0] ld_word = dmem_rdata;
    wire [31:0] ld_half = exe2mem_mem_sext ? {{16{hdata[15]}}, hdata} : {16'd0, hdata};
    wire [31:0] ld_byte = exe2mem_mem_sext ? {{24{bdata[7]}}, bdata} : {24'd0, bdata};
    wire [31:0] load_data = (size == 2'd2) ? ld_word : ((size == 2'd1) ? ld_half : ld_byte);
    
    assign stall = exe2mem_mem_read && ~dmem_valid;
    assign mem2wb_pc = exe2mem_pc;
    assign mem2wb_result = exe2mem_mem_read ? load_data : exe2mem_alu_result;
    assign mem2wb_valid = exe2mem_valid;
    assign mem2wb_wb_en = exe2mem_wb_en;
    assign mem2wb_except = exe2mem_except;
    assign mem2wb_except_code = exe2mem_except_code;
endmodule
