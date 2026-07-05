// Spinal-equivalent: exe_stage ← spinal/src/.../exestage.scala
// From Spinal source (EXEStage in Pipeline.scala)
module exe_stage(
    input         clk, reset,
    input  [31:0] id2exe_pc, id2exe_rdata1, id2exe_rdata2, id2exe_imm,
    input  [ 3:0] id2exe_alu_op,
    input  [ 1:0] id2exe_mul_op, id2exe_branch_op, id2exe_mem_size, id2exe_csr_op,
    input         id2exe_valid, id2exe_branch, id2exe_mem_read, id2exe_mem_write,
    input         id2exe_mem_sext, id2exe_wb_en,
    input         id2exe_excp_ine, id2exe_excp_sys, id2exe_excp_brk, id2exe_excp_ertn,
    input  [ 4:0] id2exe_rd_addr, id2exe_rj_addr, id2exe_rk_addr,
    input  [13:0] id2exe_csr_num,
    input  [31:0] alu_result, mul_result, div_result,
    input         stall_mem,
    // ALU interface
    output [31:0] alu_src1, alu_src2,
    output [ 3:0] alu_op,
    // Mul/Div
    output        mul_valid, output [1:0] mul_op, output [31:0] mul_src1, mul_src2,
    output        div_valid, output       div_op, output [31:0] div_src1, div_src2,
    // Branch
    output        br_taken, output [31:0] br_target,
    // To MEM
    output [31:0] exe2mem_pc, exe2mem_alu_result, exe2mem_mem_wdata, exe2mem_mem_addr,
    output        exe2mem_valid, exe2mem_mem_read, exe2mem_mem_write, exe2mem_mem_sext, exe2mem_wb_en,
    output        exe2mem_except, output [5:0] exe2mem_except_code,
    output        exe2mem_branch_taken, output [31:0] exe2mem_branch_target
);
    wire [31:0] src1 = id2exe_rdata1;
    wire [31:0] src2 = id2exe_branch ? id2exe_imm : id2exe_rdata2;
    
    assign alu_src1 = src1; assign alu_src2 = src2; assign alu_op = id2exe_alu_op;
    
    // Branch resolution
    wire br_eq = (src1 == src2);
    wire br_lt = $signed(src1) < $signed(src2);
    wire br_ltu = src1 < src2;
    wire br_taken_w = id2exe_branch && (
        (id2exe_branch_op == 2'd0 && ~br_eq) ||  // BNE
        (id2exe_branch_op == 2'd1 &&  br_eq) ||  // BEQ
        (id2exe_branch_op == 2'd2 &&  br_lt) ||  // BLT
        (id2exe_branch_op == 2'd3 && br_ltu));    // BLTU
    assign br_taken = br_taken_w;
    assign br_target = id2exe_pc + id2exe_imm;
    
    // Mul/Div dispatch
    assign mul_valid = (id2exe_alu_op == 4'hC || id2exe_alu_op == 4'hD);
    assign mul_op = (id2exe_alu_op == 4'hC) ? 2'd0 : 2'd1;
    assign mul_src1 = src1; assign mul_src2 = src2;
    assign div_valid = (id2exe_alu_op == 4'hE);
    assign div_op = (id2exe_alu_op == 4'hE) ? 1'd0 : 1'd1;
    assign div_src1 = src1; assign div_src2 = src2;
    
    assign exe2mem_pc = id2exe_pc;
    assign exe2mem_alu_result = alu_result;
    assign exe2mem_mem_wdata = id2exe_rdata2;
    assign exe2mem_mem_read = id2exe_mem_read;
    assign exe2mem_mem_write = id2exe_mem_write;
    assign exe2mem_mem_size = id2exe_mem_size;
    assign exe2mem_mem_sext = id2exe_mem_sext;
    assign exe2mem_mem_addr = alu_result;
    assign exe2mem_wb_en = id2exe_wb_en;
    assign exe2mem_valid = id2exe_valid && ~stall_mem;
    assign exe2mem_except = id2exe_excp_ine || id2exe_excp_sys || id2exe_excp_brk;
    assign exe2mem_except_code = id2exe_excp_ine ? 6'h0D : (id2exe_excp_sys ? 6'h0B : 6'd0);
    assign exe2mem_branch_taken = br_taken_w;
    assign exe2mem_branch_target = br_target;
endmodule
