module IDStage(input [31:0] io_if2id_pc, io_if2id_inst, input io_if2id_valid, io_if2id_predict,
    input [31:0] io_if2id_pred_pc, input [31:0] io_rf_rdata1, io_rf_rdata2, input io_stall_exe,
    output [31:0] io_id2exe_pc, io_id2exe_rdata1, io_id2exe_rdata2, io_id2exe_imm,
    output [3:0] io_id2exe_alu_op, output [1:0] io_id2exe_mul_op, io_id2exe_branch_op, io_id2exe_mem_size, io_id2exe_csr_op,
    output io_id2exe_valid, io_id2exe_branch, io_id2exe_mem_read, io_id2exe_mem_write, io_id2exe_mem_sext, io_id2exe_wb_en,
    output io_id2exe_excp_ine, io_id2exe_excp_sys, io_id2exe_excp_brk, io_id2exe_excp_ertn,
    output [4:0] io_id2exe_rd_addr, io_id2exe_rj_addr, io_id2exe_rk_addr, output [13:0] io_id2exe_csr_num,
    output [4:0] io_rf_rnum1, io_rf_rnum2,
    output io_br_inst, output [31:0] io_br_pc, io_br_target);
assign io_id2exe_pc=0; assign io_id2exe_rdata1=0; assign io_id2exe_rdata2=0; assign io_id2exe_imm=0;
assign io_id2exe_alu_op=4'hf; assign io_id2exe_mul_op=0; assign io_id2exe_branch_op=0;
assign io_id2exe_mem_size=2; assign io_id2exe_csr_op=0; assign io_id2exe_valid=0;
assign io_id2exe_branch=0; assign io_id2exe_mem_read=0; assign io_id2exe_mem_write=0;
assign io_id2exe_mem_sext=0; assign io_id2exe_wb_en=0;
assign io_id2exe_excp_ine=0; assign io_id2exe_excp_sys=0; assign io_id2exe_excp_brk=0; assign io_id2exe_excp_ertn=0;
assign io_id2exe_rd_addr=0; assign io_id2exe_rj_addr=0; assign io_id2exe_rk_addr=0; assign io_id2exe_csr_num=0;
assign io_rf_rnum1=0; assign io_rf_rnum2=0; assign io_br_inst=0; assign io_br_pc=0; assign io_br_target=0; endmodule