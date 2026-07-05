module MEMStage(input [31:0] io_exe2mem_pc, io_exe2mem_alu_result, io_exe2mem_mem_wdata, io_exe2mem_mem_addr,
    input io_exe2mem_valid, io_exe2mem_mem_read, io_exe2mem_mem_write, io_exe2mem_mem_sext, io_exe2mem_wb_en,
    input io_exe2mem_except, input [5:0] io_exe2mem_except_code, input io_exe2mem_branch_taken,
    input [31:0] io_exe2mem_branch_target, input [31:0] io_dmem_rdata, input io_dmem_valid,
    output [31:0] io_mem2wb_pc, io_mem2wb_result, output io_mem2wb_valid, io_mem2wb_wb_en, io_mem2wb_except,
    output [5:0] io_mem2wb_except_code, output [31:0] io_dmem_addr, io_dmem_wdata, output [3:0] io_dmem_wstrb,
    output io_dmem_read, io_dmem_write, io_stall);
assign io_mem2wb_pc=0; assign io_mem2wb_result=0; assign io_mem2wb_valid=0; assign io_mem2wb_wb_en=0;
assign io_mem2wb_except=0; assign io_mem2wb_except_code=0; assign io_dmem_addr=0; assign io_dmem_wdata=0;
assign io_dmem_wstrb=0; assign io_dmem_read=0; assign io_dmem_write=0; assign io_stall=0; endmodule