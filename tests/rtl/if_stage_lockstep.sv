`timescale 1ns/1ps
module if_stage_lockstep;
  reg clk=0, reset=1, ds_allowin=0;
  reg [32:0] br_bus=0;
  reg excp_flush=0, ertn_flush=0, refetch_flush=0, icacop_flush=0;
  reg [31:0] ws_pc=32'h1c000000, csr_eentry=32'h1c001000, csr_era=32'h1c002000, csr_tlbrentry=32'h1c003000;
  reg excp_tlbrefill=0, has_int=0, idle_flush=0;
  reg inst_addr_ok=0, inst_data_ok=0, icache_miss=0;
  reg [31:0] inst_rdata=0;
  reg csr_pg=0, csr_da=1;
  reg [31:0] csr_dmw0=0, csr_dmw1=0;
  reg [1:0] csr_plv=0, csr_datf=1;
  reg disable_cache=0;
  reg [31:0] btb_ret_pc=0;
  reg btb_taken=0, btb_en=0;
  reg [4:0] btb_index=0;
  reg inst_tlb_found=1, inst_tlb_v=1, inst_tlb_d=0;
  reg [1:0] inst_tlb_mat=1, inst_tlb_plv=0;
`ifdef NEGATIVE_CONTROL
  reg negative_control=1;
`else
  reg negative_control=0;
`endif
  reg [31:0] rand_pc=0;
  integer cycle=0;

  wire g_fs_to_ds_valid, c_fs_to_ds_valid;
  wire [108:0] g_fs_to_ds_bus, c_fs_to_ds_bus_raw;
  wire [108:0] c_fs_to_ds_bus = c_fs_to_ds_bus_raw ^ (negative_control && c_fs_to_ds_valid ? 109'b1 : 109'b0);
  wire g_inst_valid,c_inst_valid,g_inst_op,c_inst_op,g_inst_uncache_en,c_inst_uncache_en,g_tlb_excp_cancel_req,c_tlb_excp_cancel_req;
  wire [3:0] g_inst_wstrb,c_inst_wstrb;
  wire [31:0] g_inst_wdata,c_inst_wdata,g_fetch_pc,c_fetch_pc,g_inst_addr,c_inst_addr;
  wire g_fetch_en,c_fetch_en,g_inst_addr_trans_en,c_inst_addr_trans_en,g_dmw0_en,c_dmw0_en,g_dmw1_en,c_dmw1_en;

  always #5 clk=~clk;
  `define PORTS(P) .clk(clk),.reset(reset),.ds_allowin(ds_allowin),.br_bus(br_bus), \
    .fs_to_ds_valid(P``_fs_to_ds_valid),.fs_to_ds_bus(P``_fs_to_ds_bus``_raw), \
    .excp_flush(excp_flush),.ertn_flush(ertn_flush),.refetch_flush(refetch_flush),.icacop_flush(icacop_flush), \
    .ws_pc(ws_pc),.csr_eentry(csr_eentry),.csr_era(csr_era),.excp_tlbrefill(excp_tlbrefill),.csr_tlbrentry(csr_tlbrentry),.has_int(has_int),.idle_flush(idle_flush), \
    .inst_valid(P``_inst_valid),.inst_op(P``_inst_op),.inst_wstrb(P``_inst_wstrb),.inst_wdata(P``_inst_wdata), \
    .inst_addr_ok(inst_addr_ok),.inst_data_ok(inst_data_ok),.icache_miss(icache_miss),.inst_rdata(inst_rdata),.inst_uncache_en(P``_inst_uncache_en),.tlb_excp_cancel_req(P``_tlb_excp_cancel_req), \
    .csr_pg(csr_pg),.csr_da(csr_da),.csr_dmw0(csr_dmw0),.csr_dmw1(csr_dmw1),.csr_plv(csr_plv),.csr_datf(csr_datf),.disable_cache(disable_cache), \
    .fetch_pc(P``_fetch_pc),.fetch_en(P``_fetch_en),.btb_ret_pc(btb_ret_pc),.btb_taken(btb_taken),.btb_en(btb_en),.btb_index(btb_index), \
    .inst_addr(P``_inst_addr),.inst_addr_trans_en(P``_inst_addr_trans_en),.dmw0_en(P``_dmw0_en),.dmw1_en(P``_dmw1_en), \
    .inst_tlb_found(inst_tlb_found),.inst_tlb_v(inst_tlb_v),.inst_tlb_d(inst_tlb_d),.inst_tlb_mat(inst_tlb_mat),.inst_tlb_plv(inst_tlb_plv)
  wire [108:0] g_fs_to_ds_bus_raw;
  assign g_fs_to_ds_bus = g_fs_to_ds_bus_raw;
  golden_if_stage golden(`PORTS(g));
  if_stage candidate(`PORTS(c));

  task check;
    begin
      if ({g_fs_to_ds_valid,g_inst_valid,g_inst_op,g_inst_wstrb,g_inst_wdata,g_inst_uncache_en,g_tlb_excp_cancel_req,g_fetch_pc,g_fetch_en,g_inst_addr,g_inst_addr_trans_en,g_dmw0_en,g_dmw1_en} !==
          {c_fs_to_ds_valid,c_inst_valid,c_inst_op,c_inst_wstrb,c_inst_wdata,c_inst_uncache_en,c_tlb_excp_cancel_req,c_fetch_pc,c_fetch_en,c_inst_addr,c_inst_addr_trans_en,c_dmw0_en,c_dmw1_en} ||
          (g_fs_to_ds_valid && g_fs_to_ds_bus !== c_fs_to_ds_bus)) begin
        $display("IF_MISMATCH cycle=%0d g_valid=%b c_valid=%b g_pc=%h c_pc=%h g_bus=%h c_bus=%h",cycle,g_fs_to_ds_valid,c_fs_to_ds_valid,g_fetch_pc,c_fetch_pc,g_fs_to_ds_bus,c_fs_to_ds_bus);
        $display("BTB in en=%b taken=%b target=%h addr_ok=%b g_lock=%b/%h c_lock=%b/%h",btb_en,btb_taken,btb_ret_pc,inst_addr_ok,golden.btb_lock_en,golden.btb_lock_buffer,candidate.area_stage.btbLockValid,candidate.area_stage.btbLock);
        $display("STATE g_branch=%b/%h g_flush=%b/%h c_branch=%b/%h c_flush=%b/%h",golden.br_target_inst_req_state,golden.br_target_inst_req_buffer,golden.flush_inst_req_state,golden.flush_inst_req_buffer,candidate.area_stage.branchRequestState,candidate.area_stage.branchRequestPc,candidate.area_stage.flushRequestPending,candidate.area_stage.flushRequestPc);
        $fatal(1);
      end
    end
  endtask

  initial begin
    repeat(4) @(negedge clk);
    reset=0; ds_allowin=1;
    for(cycle=0;cycle<2048;cycle=cycle+1) begin
      @(negedge clk); #1; check();
      inst_addr_ok = ($urandom % 4) != 0;
      inst_data_ok = ($urandom % 3) != 0;
      ds_allowin = ($urandom % 5) != 0;
      inst_rdata = $urandom;
      icache_miss = ($urandom % 23)==0;
      btb_en = (cycle>=1536) && (($urandom % 17)==0);
      btb_taken = btb_en && (($urandom % 2)==0);
      rand_pc = ($urandom & 32'h00fffffc) | 32'h1c000000;
      btb_ret_pc = rand_pc;
      btb_index = $urandom;
      rand_pc = ($urandom & 32'h00fffffc) | 32'h1c000000;
      br_bus = (cycle>=1024 && (($urandom % 61)==0)) ? {1'b1,rand_pc} : 33'b0;
      excp_flush = (cycle>=1024) && (($urandom % 101)==0);
      ertn_flush = (cycle>=1024) && !excp_flush && (($urandom % 127)==0);
      refetch_flush = (cycle>=1024) && !excp_flush && !ertn_flush && (($urandom % 149)==0);
      icacop_flush = 0; idle_flush = 0; has_int = 0;
      csr_pg = (cycle>=512) && (($urandom % 7)==0); csr_da = !csr_pg;
      inst_tlb_found = !csr_pg || (($urandom % 19)!=0); inst_tlb_v = !csr_pg || (($urandom % 23)!=0);
      inst_tlb_mat = $urandom; inst_tlb_plv = $urandom; csr_plv = $urandom;
    end
    $display("PASS if_stage cycle lockstep cycles=%0d",cycle);
    $finish;
  end
endmodule
