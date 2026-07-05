module WBStage(input [31:0] io_mem2wb_pc, io_mem2wb_result, input io_mem2wb_valid, io_mem2wb_wb_en, io_mem2wb_except,
    input [5:0] io_mem2wb_except_code, input [4:0] io_mem2wb_rd_addr, input [1:0] io_mem2wb_csr_op,
    input [13:0] io_mem2wb_csr_num, input [31:0] io_mem2wb_csr_rdata,
    output io_rf_wen, output [4:0] io_rf_wnum, output [31:0] io_rf_wdata);
assign io_rf_wen=0; assign io_rf_wnum=0; assign io_rf_wdata=0; endmodule