`timescale 1ns/1ps
`ifndef ID_RANDOM_CYCLES
`define ID_RANDOM_CYCLES 8192
`endif
module tb;
  reg clk, reset, es_allowin, fs_to_ds_valid;
  reg [108:0] fs_to_ds_bus;
  reg [38:0] es_to_ds_forward_bus, ms_to_ds_forward_bus;
  reg excp_flush, ertn_flush, refetch_flush, icacop_flush, idle_flush;
  reg es_tlb_inst_stall, ms_tlb_inst_stall, ws_tlb_inst_stall, has_int;
  wire [13:0] g_rd_csr_addr, c_rd_csr_addr;
  reg [31:0] rd_csr_data; reg [1:0] csr_plv; reg [63:0] timer_64; reg [31:0] csr_tid;
  reg ds_llbit, es_to_ds_valid, ms_to_ds_valid, ws_to_ds_valid;
  reg write_buffer_empty, dcache_empty;
  reg infor_flag; reg [4:0] reg_num; reg [37:0] ws_to_rf_bus;
  wire g_ds_allowin, c_ds_allowin, g_ds_to_es_valid, c_ds_to_es_valid;
`ifdef HAS_LACC
  wire [352:0] g_ds_to_es_bus, c_ds_to_es_bus;
`else
  wire [349:0] g_ds_to_es_bus, c_ds_to_es_bus;
`endif
  wire [32:0] g_br_bus, c_br_bus;
  wire g_btb_operate_en, c_btb_operate_en, g_btb_pop_ras, c_btb_pop_ras, g_btb_push_ras, c_btb_push_ras;
  wire g_btb_add_entry, c_btb_add_entry, g_btb_delete_entry, c_btb_delete_entry;
  wire g_btb_pre_error, c_btb_pre_error, g_btb_pre_right, c_btb_pre_right, g_btb_target_error, c_btb_target_error;
  wire g_btb_right_orien, c_btb_right_orien; wire [31:0] g_btb_right_target, c_btb_right_target;
  wire [31:0] g_btb_operate_pc, c_btb_operate_pc; wire [4:0] g_btb_operate_index, c_btb_operate_index;
  wire [31:0] g_debug_rf_rdata1, c_debug_rf_rdata1;
`ifdef DIFFTEST_EN
  wire [31:0] g_rf_to_diff [31:0];
  wire [31:0] c_rf_to_diff [31:0];
`endif

  id_stage_golden golden(
    .clk(clk),.reset(reset),.es_allowin(es_allowin),.ds_allowin(g_ds_allowin),.fs_to_ds_valid(fs_to_ds_valid),.fs_to_ds_bus(fs_to_ds_bus),
    .es_to_ds_forward_bus(es_to_ds_forward_bus),.ms_to_ds_forward_bus(ms_to_ds_forward_bus),.ds_to_es_valid(g_ds_to_es_valid),.ds_to_es_bus(g_ds_to_es_bus),.br_bus(g_br_bus),
    .excp_flush(excp_flush),.ertn_flush(ertn_flush),.refetch_flush(refetch_flush),.icacop_flush(icacop_flush),.idle_flush(idle_flush),
    .es_tlb_inst_stall(es_tlb_inst_stall),.ms_tlb_inst_stall(ms_tlb_inst_stall),.ws_tlb_inst_stall(ws_tlb_inst_stall),.has_int(has_int),.rd_csr_addr(g_rd_csr_addr),.rd_csr_data(rd_csr_data),.csr_plv(csr_plv),.timer_64(timer_64),.csr_tid(csr_tid),.ds_llbit(ds_llbit),
    .es_to_ds_valid(es_to_ds_valid),.ms_to_ds_valid(ms_to_ds_valid),.ws_to_ds_valid(ws_to_ds_valid),.write_buffer_empty(write_buffer_empty),.dcache_empty(dcache_empty),
    .btb_operate_en(g_btb_operate_en),.btb_pop_ras(g_btb_pop_ras),.btb_push_ras(g_btb_push_ras),.btb_add_entry(g_btb_add_entry),.btb_delete_entry(g_btb_delete_entry),.btb_pre_error(g_btb_pre_error),.btb_pre_right(g_btb_pre_right),.btb_target_error(g_btb_target_error),.btb_right_orien(g_btb_right_orien),.btb_right_target(g_btb_right_target),.btb_operate_pc(g_btb_operate_pc),.btb_operate_index(g_btb_operate_index),.infor_flag(infor_flag),.reg_num(reg_num),.debug_rf_rdata1(g_debug_rf_rdata1),.ws_to_rf_bus(ws_to_rf_bus)
`ifdef DIFFTEST_EN
    ,.rf_to_diff(g_rf_to_diff)
`endif
  );
  id_stage_candidate candidate(
    .clk(clk),.reset(reset),.es_allowin(es_allowin),.ds_allowin(c_ds_allowin),.fs_to_ds_valid(fs_to_ds_valid),.fs_to_ds_bus(fs_to_ds_bus),
    .es_to_ds_forward_bus(es_to_ds_forward_bus),.ms_to_ds_forward_bus(ms_to_ds_forward_bus),.ds_to_es_valid(c_ds_to_es_valid),.ds_to_es_bus(c_ds_to_es_bus),.br_bus(c_br_bus),
    .excp_flush(excp_flush),.ertn_flush(ertn_flush),.refetch_flush(refetch_flush),.icacop_flush(icacop_flush),.idle_flush(idle_flush),
    .es_tlb_inst_stall(es_tlb_inst_stall),.ms_tlb_inst_stall(ms_tlb_inst_stall),.ws_tlb_inst_stall(ws_tlb_inst_stall),.has_int(has_int),.rd_csr_addr(c_rd_csr_addr),.rd_csr_data(rd_csr_data),.csr_plv(csr_plv),.timer_64(timer_64),.csr_tid(csr_tid),.ds_llbit(ds_llbit),
    .es_to_ds_valid(es_to_ds_valid),.ms_to_ds_valid(ms_to_ds_valid),.ws_to_ds_valid(ws_to_ds_valid),.write_buffer_empty(write_buffer_empty),.dcache_empty(dcache_empty),
    .btb_operate_en(c_btb_operate_en),.btb_pop_ras(c_btb_pop_ras),.btb_push_ras(c_btb_push_ras),.btb_add_entry(c_btb_add_entry),.btb_delete_entry(c_btb_delete_entry),.btb_pre_error(c_btb_pre_error),.btb_pre_right(c_btb_pre_right),.btb_target_error(c_btb_target_error),.btb_right_orien(c_btb_right_orien),.btb_right_target(c_btb_right_target),.btb_operate_pc(c_btb_operate_pc),.btb_operate_index(c_btb_operate_index),.infor_flag(infor_flag),.reg_num(reg_num),.debug_rf_rdata1(c_debug_rf_rdata1),.ws_to_rf_bus(ws_to_rf_bus)
`ifdef DIFFTEST_EN
    ,.rf_to_diff(c_rf_to_diff)
`endif
  );

  integer cycle, register_index; reg [31:0] lfsr; reg negative_control;
`ifdef HAS_LACC
  wire [511:0] golden_vector = {g_ds_allowin,g_ds_to_es_valid,g_ds_to_es_bus,g_br_bus,g_rd_csr_addr,g_btb_operate_en,g_btb_pop_ras,g_btb_push_ras,g_btb_add_entry,g_btb_delete_entry,g_btb_pre_error,g_btb_pre_right,g_btb_target_error,g_btb_right_orien,g_btb_right_target,g_btb_operate_pc,g_btb_operate_index,g_debug_rf_rdata1};
  wire [511:0] candidate_vector = {c_ds_allowin,c_ds_to_es_valid,c_ds_to_es_bus,c_br_bus,c_rd_csr_addr,c_btb_operate_en,c_btb_pop_ras,c_btb_push_ras,c_btb_add_entry,c_btb_delete_entry,c_btb_pre_error,c_btb_pre_right,c_btb_target_error,c_btb_right_orien,c_btb_right_target,c_btb_operate_pc,c_btb_operate_index,(negative_control ? (c_debug_rf_rdata1 ^ 32'h1) : c_debug_rf_rdata1)};
`else
  wire [508:0] golden_vector = {g_ds_allowin,g_ds_to_es_valid,g_ds_to_es_bus,g_br_bus,g_rd_csr_addr,g_btb_operate_en,g_btb_pop_ras,g_btb_push_ras,g_btb_add_entry,g_btb_delete_entry,g_btb_pre_error,g_btb_pre_right,g_btb_target_error,g_btb_right_orien,g_btb_right_target,g_btb_operate_pc,g_btb_operate_index,g_debug_rf_rdata1};
  wire [508:0] candidate_vector = {c_ds_allowin,c_ds_to_es_valid,c_ds_to_es_bus,c_br_bus,c_rd_csr_addr,c_btb_operate_en,c_btb_pop_ras,c_btb_push_ras,c_btb_add_entry,c_btb_delete_entry,c_btb_pre_error,c_btb_pre_right,c_btb_target_error,c_btb_right_orien,c_btb_right_target,c_btb_operate_pc,c_btb_operate_index,(negative_control ? (c_debug_rf_rdata1 ^ 32'h1) : c_debug_rf_rdata1)};
`endif
  task check; begin
    if (golden_vector !== candidate_vector) begin
      $display("ID_MISMATCH cycle=%0d g_allow=%b c_allow=%b g_valid=%b c_valid=%b xor=%h neg=%b",cycle,g_ds_allowin,c_ds_allowin,g_ds_to_es_valid,c_ds_to_es_valid,(golden_vector ^ candidate_vector),negative_control); $fatal(1);
    end
`ifdef DIFFTEST_EN
    for (register_index=0; register_index<32; register_index=register_index+1)
      if (g_rf_to_diff[register_index] !== c_rf_to_diff[register_index]) begin
        $display("ID_RF_MISMATCH cycle=%0d register=%0d golden=%h candidate=%h",cycle,register_index,g_rf_to_diff[register_index],c_rf_to_diff[register_index]); $fatal(1);
      end
`endif
  end endtask
  task step; begin #1; check; #1 clk=1; #1; check; #2 clk=0; #1; check; cycle=cycle+1; end endtask
  task rand_inputs; begin
    lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]}; fs_to_ds_bus=lfsr*32'h9e3779b9; fs_to_ds_bus[31:0]=lfsr; fs_to_ds_bus[63:32]=lfsr^32'h1000;
    case (cycle[3:0])
      4'h0: fs_to_ds_bus[63:32]={6'h00,4'h0,2'h1,cycle[4:0],5'h13,5'h12,5'h11};
      4'h1: fs_to_ds_bus[63:32]={6'h00,4'h0,2'h2,cycle[4:0],5'h13,5'h12,5'h11};
      4'h2: fs_to_ds_bus[63:32]={6'h00,4'h1,2'h0,cycle[4:0],5'h13,5'h12,5'h11};
      4'h3: fs_to_ds_bus[63:32]={6'h01,4'h9,2'h0,5'h10,cycle[4:0],5'h00,5'h00};
      4'h4: fs_to_ds_bus[63:32]={lfsr[5:0],lfsr[25:0]};
      4'h5: fs_to_ds_bus[63:32]={6'h0a,lfsr[25:0]};
      4'h6: fs_to_ds_bus[63:32]={6'h08,lfsr[25:0]};
      4'h7: fs_to_ds_bus[63:32]={6'h01,lfsr[25:0]};
      default: ;
    endcase
    fs_to_ds_bus[67:64]=lfsr[3:0]; fs_to_ds_bus[68]=lfsr[4]; fs_to_ds_bus[69]=lfsr[5]; fs_to_ds_bus[70]=lfsr[6]; fs_to_ds_bus[71]=lfsr[7]; fs_to_ds_bus[76:72]=lfsr[12:8]; fs_to_ds_bus[108:77]=lfsr;
    es_to_ds_forward_bus={$urandom,$urandom}; ms_to_ds_forward_bus={$urandom,$urandom}; rd_csr_data=$urandom; csr_plv=lfsr[1:0]; timer_64={$urandom,$urandom}; csr_tid=$urandom; ws_to_rf_bus={$urandom,$urandom};
    es_allowin=lfsr[13]; fs_to_ds_valid=lfsr[14]; excp_flush=lfsr[15]&&lfsr[0]; ertn_flush=0; refetch_flush=0; icacop_flush=0; idle_flush=0; es_tlb_inst_stall=lfsr[16]&&lfsr[1]; ms_tlb_inst_stall=0; ws_tlb_inst_stall=0; has_int=lfsr[17]&&lfsr[2]; ds_llbit=lfsr[18]; es_to_ds_valid=lfsr[19]; ms_to_ds_valid=lfsr[20]; ws_to_ds_valid=lfsr[21]; write_buffer_empty=lfsr[22]; dcache_empty=lfsr[23]; infor_flag=lfsr[24]; reg_num=lfsr[29:25];
  end endtask
  initial begin cycle=0; lfsr=32'h158aa8; negative_control=$test$plusargs("negative-control"); clk=0; reset=1; es_allowin=0; fs_to_ds_valid=0; fs_to_ds_bus=0; es_to_ds_forward_bus=0; ms_to_ds_forward_bus=0; excp_flush=0; ertn_flush=0; refetch_flush=0; icacop_flush=0; idle_flush=0; es_tlb_inst_stall=0; ms_tlb_inst_stall=0; ws_tlb_inst_stall=0; has_int=0; rd_csr_data=0; csr_plv=0; timer_64=0; csr_tid=0; ds_llbit=0; es_to_ds_valid=0; ms_to_ds_valid=0; ws_to_ds_valid=0; write_buffer_empty=1; dcache_empty=1; infor_flag=0; reg_num=0; ws_to_rf_bus=0;
    step; step; reset=0;
    repeat(64) begin rand_inputs; step; end
    reset=1; step; reset=0;
    repeat(`ID_RANDOM_CYCLES) begin rand_inputs; step; end
    if (negative_control) begin $display("NEGATIVE_CONTROL_DID_NOT_FAIL"); $fatal(1); end
    $display("ID_DIFF_PASS cycles=%0d",cycle); $finish;
  end
endmodule
