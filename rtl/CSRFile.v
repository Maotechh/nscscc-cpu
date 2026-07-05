module CSRFile(input io_clk, io_reset, input [13:0] io_csr_num, input [31:0] io_csr_wdata,
    input io_csr_rd, io_csr_wr, io_csr_xchg, io_excp_valid, input [31:0] io_excp_era, input [5:0] io_excp_code,
    input [8:0] io_excp_subcode, input [31:0] io_excp_badv, input io_ertn_valid, io_ext_int,
    output [31:0] io_csr_rdata, output io_in_kernel, io_da_mod, io_pg_mod, io_user_mode,
    output [31:0] io_dmw0_base, io_dmw1_base, io_dmw0_mask, io_dmw1_mask, output io_has_int, output [7:0] io_int_vector);
assign io_csr_rdata=0; assign io_in_kernel=1; assign io_da_mod=1; assign io_pg_mod=0; assign io_user_mode=0;
assign io_dmw0_base=32'h80000000; assign io_dmw1_base=32'ha0000000; assign io_dmw0_mask=32'hfffff000;
assign io_dmw1_mask=32'hfffff000; assign io_has_int=0; assign io_int_vector=0; endmodule