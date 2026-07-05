module EXEStage(input [31:0] io_id2exe_pc, io_id2exe_rdata1, io_id2exe_rdata2, io_id2exe_imm,
    input [3:0] io_id2exe_alu_op, input [1:0] io_id2exe_mul_op, io_id2exe_branch_op, io_id2exe_mem_size, io_id2exe_csr_op,
    input io_id2exe_valid, io_id2exe_branch, io_id2exe_mem_read, io_id2exe_mem_write, io_id2exe_mem_sext, io_id2exe_wb_en,
    input io_id2exe_excp_ine, io_id2exe_excp_sys, io_id2exe_excp_brk, io_id2exe_excp_ertn,
    input [31:0] io_alu_result, io_mul_result, io_div_result, input io_stall_mem,
    output [31:0] io_exe2mem_pc, io_exe2mem_alu_result, io_exe2mem_mem_wdata, io_exe2mem_mem_addr,
    output io_exe2mem_valid, io_exe2mem_mem_read, io_exe2mem_mem_write, io_exe2mem_mem_sext, io_exe2mem_wb_en,
    output io_exe2mem_except, output [5:0] io_exe2mem_except_code, output io_exe2mem_branch_taken,
    output [31:0] io_exe2mem_branch_target, output [31:0] io_alu_src1, io_alu_src2, output [3:0] io_alu_op,
    output io_mul_valid, output [1:0] io_mul_op, output [31:0] io_mul_src1, io_mul_src2,
    output io_div_valid, output io_div_op, output [31:0] io_div_src1, io_div_src2, output io_br_taken, output [31:0] io_br_target);
assign io_exe2mem_pc=0; assign io_exe2mem_alu_result=0; assign io_exe2mem_mem_wdata=0; assign io_exe2mem_mem_addr=0;
assign io_exe2mem_valid=0; assign io_exe2mem_mem_read=0; assign io_exe2mem_mem_write=0; assign io_exe2mem_mem_sext=0;
assign io_exe2mem_wb_en=0; assign io_exe2mem_except=0; assign io_exe2mem_except_code=0; assign io_exe2mem_branch_taken=0;
assign io_exe2mem_branch_target=0; assign io_alu_src1=0; assign io_alu_src2=0; assign io_alu_op=4'hf;
assign io_mul_valid=0; assign io_mul_op=0; assign io_mul_src1=0; assign io_mul_src2=0;
assign io_div_valid=0; assign io_div_op=0; assign io_div_src1=0; assign io_div_src2=0;
assign io_br_taken=0; assign io_br_target=0; endmodule