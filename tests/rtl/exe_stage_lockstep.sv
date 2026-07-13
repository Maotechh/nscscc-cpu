`include "mycpu.h"

module exe_stage_lockstep;
  reg clk = 0;
  always #1 clk = ~clk;

  reg reset;
  reg ms_allowin;
  reg ds_to_es_valid;
  reg [`DS_TO_ES_BUS_WD-1:0] ds_to_es_bus;
  reg div_complete;
  reg excp_flush;
  reg ertn_flush;
  reg refetch_flush;
  reg icacop_flush;
  reg idle_flush;
  reg icache_unbusy;
  reg data_addr_ok;
  reg [18:0] csr_vppn;
  reg ms_wr_tlbehi;
  reg ms_flush;
`ifdef HAS_LACC
  reg lacc_req_ready;
  reg lacc_data_valid;
  reg lacc_data_read;
  reg [31:0] lacc_data_addr;
  reg [31:0] lacc_data_wdata;
  reg [1:0] lacc_data_size;
  reg lacc_rsp_valid;
  reg [31:0] lacc_rsp_rdat;
  reg data_data_ok;
`endif

  wire g_es_allowin, c_es_allowin;
  wire g_es_to_ms_valid, c_es_to_ms_valid;
  wire [424:0] g_es_to_ms_bus, c_es_to_ms_bus;
  wire [38:0] g_es_to_ds_forward_bus, c_es_to_ds_forward_bus;
  wire g_es_to_ds_valid, c_es_to_ds_valid;
  wire g_es_div_enable, c_es_div_enable;
  wire g_es_mul_div_sign, c_es_mul_div_sign;
  wire [31:0] g_es_rj_value, c_es_rj_value;
  wire [31:0] g_es_rkd_value, c_es_rkd_value;
  wire g_tlb_inst_stall, c_tlb_inst_stall;
  wire g_icacop_op_en, c_icacop_op_en;
  wire g_dcacop_op_en, c_dcacop_op_en;
  wire [1:0] g_cacop_op_mode, c_cacop_op_mode;
  wire [4:0] g_preld_hint, c_preld_hint;
  wire g_preld_en, c_preld_en;
  wire g_data_valid, c_data_valid;
  wire g_data_op, c_data_op;
  wire [2:0] g_data_size, c_data_size;
  wire [3:0] g_data_wstrb, c_data_wstrb;
  wire [31:0] g_data_wdata, c_data_wdata;
  wire [31:0] g_data_addr, c_data_addr;
  wire g_data_fetch, c_data_fetch;
`ifdef HAS_LACC
  wire g_es_lacc_req, c_es_lacc_req;
  wire [1:0] g_es_lacc_command, c_es_lacc_command;
  wire [6:0] g_lacc_req_imm, c_lacc_req_imm;
  wire g_lacc_flush, c_lacc_flush;
  wire g_lacc_drsp_valid, c_lacc_drsp_valid;
`endif

`define COMMON_INPUTS \
    .clk(clk), .reset(reset), .ms_allowin(ms_allowin), \
    .ds_to_es_valid(ds_to_es_valid), .ds_to_es_bus(ds_to_es_bus), \
    .div_complete(div_complete), .excp_flush(excp_flush), .ertn_flush(ertn_flush), \
    .refetch_flush(refetch_flush), .icacop_flush(icacop_flush), .idle_flush(idle_flush), \
    .icache_unbusy(icache_unbusy), .data_addr_ok(data_addr_ok), .csr_vppn(csr_vppn), \
    .ms_wr_tlbehi(ms_wr_tlbehi), .ms_flush(ms_flush)
`ifdef HAS_LACC
`define LACC_INPUTS \
    .lacc_req_ready(lacc_req_ready), .lacc_data_valid(lacc_data_valid), \
    .lacc_data_read(lacc_data_read), .lacc_data_addr(lacc_data_addr), \
    .lacc_data_wdata(lacc_data_wdata), .lacc_data_size(lacc_data_size), \
    .lacc_rsp_valid(lacc_rsp_valid), .lacc_rsp_rdat(lacc_rsp_rdat), \
    .data_data_ok(data_data_ok),
`else
`define LACC_INPUTS
`endif

  golden_exe_stage golden (
    `COMMON_INPUTS,
    `LACC_INPUTS
    .es_allowin(g_es_allowin), .es_to_ms_valid(g_es_to_ms_valid),
    .es_to_ms_bus(g_es_to_ms_bus), .es_to_ds_forward_bus(g_es_to_ds_forward_bus),
    .es_to_ds_valid(g_es_to_ds_valid), .es_div_enable(g_es_div_enable),
    .es_mul_div_sign(g_es_mul_div_sign), .es_rj_value(g_es_rj_value),
    .es_rkd_value(g_es_rkd_value), .tlb_inst_stall(g_tlb_inst_stall),
    .icacop_op_en(g_icacop_op_en), .dcacop_op_en(g_dcacop_op_en),
    .cacop_op_mode(g_cacop_op_mode), .preld_hint(g_preld_hint), .preld_en(g_preld_en),
    .data_valid(g_data_valid), .data_op(g_data_op), .data_size(g_data_size),
    .data_wstrb(g_data_wstrb), .data_wdata(g_data_wdata), .data_addr(g_data_addr),
    .data_fetch(g_data_fetch)
`ifdef HAS_LACC
    , .es_lacc_req(g_es_lacc_req), .es_lacc_command(g_es_lacc_command),
    .lacc_req_imm(g_lacc_req_imm), .lacc_flush(g_lacc_flush),
    .lacc_drsp_valid(g_lacc_drsp_valid)
`endif
  );

  exe_stage candidate (
    `COMMON_INPUTS,
    `LACC_INPUTS
    .es_allowin(c_es_allowin), .es_to_ms_valid(c_es_to_ms_valid),
    .es_to_ms_bus(c_es_to_ms_bus), .es_to_ds_forward_bus(c_es_to_ds_forward_bus),
    .es_to_ds_valid(c_es_to_ds_valid), .es_div_enable(c_es_div_enable),
    .es_mul_div_sign(c_es_mul_div_sign), .es_rj_value(c_es_rj_value),
    .es_rkd_value(c_es_rkd_value), .tlb_inst_stall(c_tlb_inst_stall),
    .icacop_op_en(c_icacop_op_en), .dcacop_op_en(c_dcacop_op_en),
    .cacop_op_mode(c_cacop_op_mode), .preld_hint(c_preld_hint), .preld_en(c_preld_en),
    .data_valid(c_data_valid), .data_op(c_data_op), .data_size(c_data_size),
    .data_wstrb(c_data_wstrb), .data_wdata(c_data_wdata), .data_addr(c_data_addr),
    .data_fetch(c_data_fetch)
`ifdef HAS_LACC
    , .es_lacc_req(c_es_lacc_req), .es_lacc_command(c_es_lacc_command),
    .lacc_req_imm(c_lacc_req_imm), .lacc_flush(c_lacc_flush),
    .lacc_drsp_valid(c_lacc_drsp_valid)
`endif
  );

  integer cycle;
  integer seed;
  reg [1023:0] golden_outputs;
  reg [1023:0] candidate_outputs;

  task capture_outputs;
    begin
      golden_outputs = {
        g_es_allowin, g_es_to_ms_valid, g_es_to_ms_bus, g_es_to_ds_forward_bus,
        g_es_to_ds_valid, g_es_div_enable, g_es_mul_div_sign, g_es_rj_value,
        g_es_rkd_value, g_tlb_inst_stall, g_icacop_op_en, g_dcacop_op_en,
        g_cacop_op_mode, g_preld_hint, g_preld_en, g_data_valid, g_data_op,
        g_data_size, g_data_wstrb, g_data_wdata, g_data_addr, g_data_fetch
`ifdef HAS_LACC
        , g_es_lacc_req, g_es_lacc_command, g_lacc_req_imm, g_lacc_flush,
        g_lacc_drsp_valid
`endif
      };
      candidate_outputs = {
        c_es_allowin, c_es_to_ms_valid, c_es_to_ms_bus, c_es_to_ds_forward_bus,
        c_es_to_ds_valid, c_es_div_enable, c_es_mul_div_sign, c_es_rj_value,
        c_es_rkd_value, c_tlb_inst_stall, c_icacop_op_en, c_dcacop_op_en,
        c_cacop_op_mode, c_preld_hint, c_preld_en, c_data_valid, c_data_op,
        c_data_size, c_data_wstrb, c_data_wdata, c_data_addr, c_data_fetch
`ifdef HAS_LACC
        , c_es_lacc_req, c_es_lacc_command, c_lacc_req_imm, c_lacc_flush,
        c_lacc_drsp_valid
`endif
      };
    end
  endtask

  task randomize_inputs;
    begin
      ms_allowin = $urandom;
      ds_to_es_valid = $urandom;
      ds_to_es_bus = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                      $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
      div_complete = $urandom;
      excp_flush = ($urandom_range(0, 63) == 0);
      ertn_flush = ($urandom_range(0, 63) == 0);
      refetch_flush = ($urandom_range(0, 63) == 0);
      icacop_flush = ($urandom_range(0, 63) == 0);
      idle_flush = ($urandom_range(0, 63) == 0);
      icache_unbusy = $urandom;
      data_addr_ok = $urandom;
      csr_vppn = $urandom;
      ms_wr_tlbehi = $urandom;
      ms_flush = ($urandom_range(0, 15) == 0);
`ifdef HAS_LACC
      lacc_req_ready = $urandom;
      lacc_data_valid = $urandom;
      lacc_data_read = $urandom;
      lacc_data_addr = $urandom;
      lacc_data_wdata = $urandom;
      lacc_data_size = $urandom;
      lacc_rsp_valid = $urandom;
      lacc_rsp_rdat = $urandom;
      data_data_ok = $urandom;
`endif
    end
  endtask

  initial begin
    seed = 32'h00158aa8;
    seed = $urandom(seed);
    reset = 1;
    ms_allowin = 0;
    ds_to_es_valid = 0;
    ds_to_es_bus = 0;
    div_complete = 0;
    excp_flush = 0;
    ertn_flush = 0;
    refetch_flush = 0;
    icacop_flush = 0;
    idle_flush = 0;
    icache_unbusy = 0;
    data_addr_ok = 0;
    csr_vppn = 0;
    ms_wr_tlbehi = 0;
    ms_flush = 0;
`ifdef HAS_LACC
    lacc_req_ready = 0;
    lacc_data_valid = 0;
    lacc_data_read = 0;
    lacc_data_addr = 0;
    lacc_data_wdata = 0;
    lacc_data_size = 0;
    lacc_rsp_valid = 0;
    lacc_rsp_rdat = 0;
    data_data_ok = 0;
`endif

    repeat (3) @(negedge clk);
    reset = 0;
    for (cycle = 0; cycle < 8192; cycle = cycle + 1) begin
      randomize_inputs();
      @(negedge clk);
      capture_outputs();
      if (golden_outputs !== candidate_outputs) begin
        $display("MISMATCH cycle=%0d golden=%h candidate=%h ds_bus=%h", cycle,
                 golden_outputs, candidate_outputs, ds_to_es_bus);
        $display("ms_bus_xor=%h forward_xor=%h", g_es_to_ms_bus ^ c_es_to_ms_bus,
                 g_es_to_ds_forward_bus ^ c_es_to_ds_forward_bus);
        $display("ms mem_size=%h/%h exception=%h/%h error_va=%h/%h",
                 g_es_to_ms_bus[76:75], c_es_to_ms_bus[76:75],
                 g_es_to_ms_bus[135:126], c_es_to_ms_bus[135:126],
                 g_es_to_ms_bus[214:183], c_es_to_ms_bus[214:183]);
        $display("golden internal access=%b mem_size=%h alu=%h ale=%b",
                 golden.access_mem, golden.es_mem_size, golden.es_alu_result,
                 golden.excp_ale);
        $display("data: valid=%b/%b op=%b/%b size=%h/%h strb=%h/%h wdata=%h/%h addr=%h/%h fetch=%b/%b",
                 g_data_valid, c_data_valid, g_data_op, c_data_op, g_data_size, c_data_size,
                 g_data_wstrb, c_data_wstrb, g_data_wdata, c_data_wdata, g_data_addr,
                 c_data_addr, g_data_fetch, c_data_fetch);
        $fatal(1);
      end
    end
    $display("PASS exe_stage cycle lockstep cycles=%0d seed=0x00158aa8", cycle);
    $finish;
  end
endmodule
