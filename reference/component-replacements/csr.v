// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : csr



module csr #(
  parameter integer TLBNUM = 32
) (
  input  wire          clk,
  input  wire          reset,
  input  wire [13:0]   rd_addr,
  output reg  [31:0]   rd_data,
  output wire [63:0]   timer_64_out,
  output wire [31:0]   tid_out,
  input  wire          csr_wr_en,
  input  wire [13:0]   wr_addr,
  input  wire [31:0]   wr_data,
  input  wire [7:0]    interrupt,
  output wire          has_int,
  input  wire          excp_flush,
  input  wire          ertn_flush,
  input  wire [31:0]   era_in,
  input  wire [8:0]    esubcode_in,
  input  wire [5:0]    ecode_in,
  input  wire          va_error_in,
  input  wire [31:0]   bad_va_in,
  input  wire          tlbsrch_en,
  input  wire          tlbsrch_found,
  input  wire [4:0]    tlbsrch_index,
  input  wire          excp_tlbrefill,
  input  wire          excp_tlb,
  input  wire [18:0]   excp_tlb_vppn,
  input  wire          llbit_in,
  input  wire          llbit_set_in,
  input  wire [27:0]   lladdr_in,
  input  wire          lladdr_set_in,
  output wire          llbit_out,
  output wire [18:0]   vppn_out,
  output wire [27:0]   lladdr_out,
  output wire [31:0]   eentry_out,
  output wire [31:0]   era_out,
  output wire [31:0]   tlbrentry_out,
  output wire          disable_cache_out,
  output wire [9:0]    asid_out,
  output wire [4:0]    rand_index,
  output wire [31:0]   tlbehi_out,
  output wire [31:0]   tlbelo0_out,
  output wire [31:0]   tlbelo1_out,
  output wire [31:0]   tlbidx_out,
  output wire          pg_out,
  output wire          da_out,
  output wire [31:0]   dmw0_out,
  output wire [31:0]   dmw1_out,
  output wire [1:0]    datf_out,
  output wire [1:0]    datm_out,
  output wire [5:0]    ecode_out,
  input  wire          tlbrd_en,
  input  wire [31:0]   tlbehi_in,
  input  wire [31:0]   tlbelo0_in,
  input  wire [31:0]   tlbelo1_in,
  input  wire [31:0]   tlbidx_in,
  input  wire [9:0]    asid_in,
  output wire [1:0]    plv_out,
  output wire [31:0]   csr_crmd_diff,
  output wire [31:0]   csr_prmd_diff,
  output wire [31:0]   csr_ectl_diff,
  output wire [31:0]   csr_estat_diff,
  output wire [31:0]   csr_era_diff,
  output wire [31:0]   csr_badv_diff,
  output wire [31:0]   csr_eentry_diff,
  output wire [31:0]   csr_tlbidx_diff,
  output wire [31:0]   csr_tlbehi_diff,
  output wire [31:0]   csr_tlbelo0_diff,
  output wire [31:0]   csr_tlbelo1_diff,
  output wire [31:0]   csr_asid_diff,
  output wire [31:0]   csr_save0_diff,
  output wire [31:0]   csr_save1_diff,
  output wire [31:0]   csr_save2_diff,
  output wire [31:0]   csr_save3_diff,
  output wire [31:0]   csr_tid_diff,
  output wire [31:0]   csr_tcfg_diff,
  output wire [31:0]   csr_tval_diff,
  output wire [31:0]   csr_ticlr_diff,
  output wire [31:0]   csr_llbctl_diff,
  output wire [31:0]   csr_tlbrentry_diff,
  output wire [31:0]   csr_dmw0_diff,
  output wire [31:0]   csr_dmw1_diff,
  output wire [31:0]   csr_pgdl_diff,
  output wire [31:0]   csr_pgdh_diff
);

  wire       [31:0]   _zz_logic_tval;
  wire       [63:0]   _zz_timer_64_out;
  wire       [63:0]   _zz_timer_64_out_1;
  wire       [31:0]   _zz_timer_64_out_2;
  reg        [31:0]   logic_crmd;
  reg        [31:0]   logic_prmd;
  reg        [31:0]   logic_ectl;
  reg        [31:0]   logic_estat;
  reg        [31:0]   logic_era;
  reg        [31:0]   logic_badv;
  reg        [31:0]   logic_eentry;
  reg        [31:0]   logic_tlbidx;
  reg        [31:0]   logic_tlbehi;
  reg        [31:0]   logic_tlbelo0;
  reg        [31:0]   logic_tlbelo1;
  reg        [31:0]   logic_asid;
  reg        [31:0]   logic_cpuid;
  reg        [31:0]   logic_save0;
  reg        [31:0]   logic_save1;
  reg        [31:0]   logic_save2;
  reg        [31:0]   logic_save3;
  reg        [31:0]   logic_tid;
  reg        [31:0]   logic_tcfg;
  reg        [31:0]   logic_tval;
  reg        [31:0]   logic_cntc;
  reg        [31:0]   logic_ticlr;
  reg        [31:0]   logic_llbctl;
  reg        [31:0]   logic_tlbrentry;
  reg        [31:0]   logic_dmw0;
  reg        [31:0]   logic_dmw1;
  reg        [31:0]   logic_pgdl;
  reg        [31:0]   logic_pgdh;
  reg        [31:0]   logic_brk;
  reg        [31:0]   logic_disableCache;
  reg        [31:0]   logic_cpucfg1;
  reg        [31:0]   logic_cpucfg2;
  reg        [31:0]   logic_cpucfg10;
  reg        [31:0]   logic_cpucfg11;
  reg        [31:0]   logic_cpucfg12;
  reg        [31:0]   logic_cpucfg13;
  reg                 logic_timerEnabled;
  reg        [63:0]   logic_timer64;
  reg                 logic_llbit;
  reg        [27:0]   logic_lladdr;
  wire       [13:0]   _zz_dmw0_out;
  wire       [13:0]   _zz_dmw1_out;
  wire                logic_crmdWrite;
  wire                logic_tlbehiWrite;
  wire                logic_tcfgWrite;
  wire                logic_ticlrWrite;
  wire                logic_llbctlWrite;
  wire                logic_tlbrdValid;
  wire                logic_tlbrdInvalid;
  wire                logic_returningFromRefill;
  wire                when_OpenLa500Csr_l234;
  wire                when_OpenLa500Csr_l240;
  wire                when_OpenLa500Csr_l254;
  wire                when_OpenLa500Csr_l258;
  wire                when_OpenLa500Csr_l266;
  wire                when_OpenLa500Csr_l271;
  wire                when_OpenLa500Csr_l272;
  wire                when_OpenLa500Csr_l276;
  wire                when_OpenLa500Csr_l284;
  wire                when_OpenLa500Csr_l320;
  wire                when_OpenLa500Csr_l320_1;
  wire                when_OpenLa500Csr_l335;
  wire                when_OpenLa500Csr_l345;
  wire                when_OpenLa500Csr_l354;
  wire                when_OpenLa500Csr_l354_1;
  wire                when_OpenLa500Csr_l366;
  wire                when_OpenLa500Csr_l367;
  wire                when_OpenLa500Csr_l368;
  wire                when_OpenLa500Csr_l369;
  wire                when_OpenLa500Csr_l370;
  wire                when_OpenLa500Csr_l375;
  wire                when_OpenLa500Csr_l379;
  wire                when_OpenLa500Csr_l393;
  wire                when_OpenLa500Csr_l396;
  wire                when_OpenLa500Csr_l403;
  wire                when_OpenLa500Csr_l404;
  wire                when_OpenLa500Csr_l407;
  wire                when_OpenLa500Csr_l409;
  wire                refillReturn;
  wire                noForward;

  assign _zz_logic_tval = (logic_tval - 32'h00000001);
  assign _zz_timer_64_out = (logic_timer64 + _zz_timer_64_out_1);
  assign _zz_timer_64_out_2 = logic_cntc;
  assign _zz_timer_64_out_1 = {{32{_zz_timer_64_out_2[31]}}, _zz_timer_64_out_2};
  assign _zz_dmw0_out = 14'h0180;
  assign _zz_dmw1_out = 14'h0181;
  assign logic_crmdWrite = (csr_wr_en && (wr_addr == 14'h0));
  assign logic_tlbehiWrite = (csr_wr_en && (wr_addr == 14'h0011));
  assign logic_tcfgWrite = (csr_wr_en && (wr_addr == 14'h0041));
  assign logic_ticlrWrite = (csr_wr_en && (wr_addr == 14'h0044));
  assign logic_llbctlWrite = (csr_wr_en && (wr_addr == 14'h0060));
  assign logic_tlbrdValid = (tlbrd_en && (! tlbidx_in[31]));
  assign logic_tlbrdInvalid = (tlbrd_en && tlbidx_in[31]);
  assign logic_returningFromRefill = (logic_estat[21 : 16] == 6'h3f);
  assign when_OpenLa500Csr_l234 = (csr_wr_en && (wr_addr == 14'h0001));
  assign when_OpenLa500Csr_l240 = (csr_wr_en && (wr_addr == 14'h0004));
  assign when_OpenLa500Csr_l254 = (logic_ticlrWrite && wr_data[0]);
  assign when_OpenLa500Csr_l258 = (logic_timerEnabled && (logic_tval == 32'h0));
  assign when_OpenLa500Csr_l266 = (csr_wr_en && (wr_addr == 14'h0005));
  assign when_OpenLa500Csr_l271 = (csr_wr_en && (wr_addr == 14'h0006));
  assign when_OpenLa500Csr_l272 = (csr_wr_en && (wr_addr == 14'h0007));
  assign when_OpenLa500Csr_l276 = (csr_wr_en && (wr_addr == 14'h000c));
  assign when_OpenLa500Csr_l284 = (csr_wr_en && (wr_addr == 14'h0010));
  assign when_OpenLa500Csr_l320 = (csr_wr_en && (wr_addr == 14'h0012));
  assign when_OpenLa500Csr_l320_1 = (csr_wr_en && (wr_addr == 14'h0013));
  assign when_OpenLa500Csr_l335 = (csr_wr_en && (wr_addr == 14'h0018));
  assign when_OpenLa500Csr_l345 = (csr_wr_en && (wr_addr == 14'h0088));
  assign when_OpenLa500Csr_l354 = (csr_wr_en && (wr_addr == _zz_dmw0_out));
  assign when_OpenLa500Csr_l354_1 = (csr_wr_en && (wr_addr == _zz_dmw1_out));
  assign when_OpenLa500Csr_l366 = (csr_wr_en && (wr_addr == 14'h0030));
  assign when_OpenLa500Csr_l367 = (csr_wr_en && (wr_addr == 14'h0031));
  assign when_OpenLa500Csr_l368 = (csr_wr_en && (wr_addr == 14'h0032));
  assign when_OpenLa500Csr_l369 = (csr_wr_en && (wr_addr == 14'h0033));
  assign when_OpenLa500Csr_l370 = (csr_wr_en && (wr_addr == 14'h0040));
  assign when_OpenLa500Csr_l375 = (csr_wr_en && (wr_addr == 14'h0043));
  assign when_OpenLa500Csr_l379 = (logic_tval != 32'h0);
  assign when_OpenLa500Csr_l393 = logic_llbctl[2];
  assign when_OpenLa500Csr_l396 = wr_data[1];
  assign when_OpenLa500Csr_l403 = (csr_wr_en && (wr_addr == 14'h0019));
  assign when_OpenLa500Csr_l404 = (csr_wr_en && (wr_addr == 14'h001a));
  assign when_OpenLa500Csr_l407 = (csr_wr_en && (wr_addr == 14'h0100));
  assign when_OpenLa500Csr_l409 = (csr_wr_en && (wr_addr == 14'h0101));
  always @(*) begin
    rd_data = 32'h0;
    case(rd_addr)
      14'h0 : begin
        rd_data = logic_crmd;
      end
      14'h0001 : begin
        rd_data = logic_prmd;
      end
      14'h0004 : begin
        rd_data = logic_ectl;
      end
      14'h0005 : begin
        rd_data = logic_estat;
      end
      14'h0006 : begin
        rd_data = logic_era;
      end
      14'h0007 : begin
        rd_data = logic_badv;
      end
      14'h000c : begin
        rd_data = logic_eentry;
      end
      14'h0010 : begin
        rd_data = logic_tlbidx;
      end
      14'h0011 : begin
        rd_data = logic_tlbehi;
      end
      14'h0012 : begin
        rd_data = logic_tlbelo0;
      end
      14'h0013 : begin
        rd_data = logic_tlbelo1;
      end
      14'h0018 : begin
        rd_data = logic_asid;
      end
      14'h0019 : begin
        rd_data = logic_pgdl;
      end
      14'h001a : begin
        rd_data = logic_pgdh;
      end
      14'h001b : begin
        rd_data = (logic_badv[31] ? logic_pgdh : logic_pgdl);
      end
      14'h0020 : begin
        rd_data = logic_cpuid;
      end
      14'h0030 : begin
        rd_data = logic_save0;
      end
      14'h0031 : begin
        rd_data = logic_save1;
      end
      14'h0032 : begin
        rd_data = logic_save2;
      end
      14'h0033 : begin
        rd_data = logic_save3;
      end
      14'h0040 : begin
        rd_data = logic_tid;
      end
      14'h0041 : begin
        rd_data = logic_tcfg;
      end
      14'h0042 : begin
        rd_data = logic_tval;
      end
      14'h0043 : begin
        rd_data = logic_cntc;
      end
      14'h0044 : begin
        rd_data = logic_ticlr;
      end
      14'h0060 : begin
        rd_data = {logic_llbctl[31 : 1],logic_llbit};
      end
      14'h0088 : begin
        rd_data = logic_tlbrentry;
      end
      14'h0180 : begin
        rd_data = logic_dmw0;
      end
      14'h0181 : begin
        rd_data = logic_dmw1;
      end
      14'h00b1 : begin
        rd_data = logic_cpucfg1;
      end
      14'h00b2 : begin
        rd_data = logic_cpucfg2;
      end
      14'h00c0 : begin
        rd_data = logic_cpucfg10;
      end
      14'h00c1 : begin
        rd_data = logic_cpucfg11;
      end
      14'h00c2 : begin
        rd_data = logic_cpucfg12;
      end
      14'h00c3 : begin
        rd_data = logic_cpucfg13;
      end
      default : begin
      end
    endcase
  end

  assign has_int = ((|(logic_ectl[12 : 0] & logic_estat[12 : 0])) && logic_crmd[2]);
  assign eentry_out = logic_eentry;
  assign era_out = logic_era;
  assign timer_64_out = _zz_timer_64_out;
  assign tid_out = logic_tid;
  assign llbit_out = logic_llbit;
  assign lladdr_out = logic_lladdr;
  assign asid_out = logic_asid[9 : 0];
  assign vppn_out = (logic_tlbehiWrite ? wr_data[31 : 13] : logic_tlbehi[31 : 13]);
  assign tlbehi_out = logic_tlbehi;
  assign tlbelo0_out = logic_tlbelo0;
  assign tlbelo1_out = logic_tlbelo1;
  assign tlbidx_out = logic_tlbidx;
  assign rand_index = logic_timer64[4 : 0];
  assign disable_cache_out = logic_disableCache[0];
  assign refillReturn = (logic_returningFromRefill && ertn_flush);
  assign noForward = (((! excp_tlbrefill) && (! refillReturn)) && (! logic_crmdWrite));
  assign pg_out = ((refillReturn || (logic_crmdWrite && wr_data[4])) || (noForward && logic_crmd[4]));
  assign da_out = ((excp_tlbrefill || (logic_crmdWrite && wr_data[3])) || (noForward && logic_crmd[3]));
  assign dmw0_out = ((csr_wr_en && (wr_addr == _zz_dmw0_out)) ? wr_data : logic_dmw0);
  assign dmw1_out = ((csr_wr_en && (wr_addr == _zz_dmw1_out)) ? wr_data : logic_dmw1);
  assign plv_out = ((((ertn_flush ? 2'b11 : 2'b00) & logic_prmd[1 : 0]) | ((logic_crmdWrite ? 2'b11 : 2'b00) & wr_data[1 : 0])) | (((((! excp_flush) && (! ertn_flush)) && (! logic_crmdWrite)) ? 2'b11 : 2'b00) & logic_crmd[1 : 0]));
  assign tlbrentry_out = logic_tlbrentry;
  assign datf_out = logic_crmd[6 : 5];
  assign datm_out = logic_crmd[8 : 7];
  assign ecode_out = logic_estat[21 : 16];
  assign csr_crmd_diff = logic_crmd;
  assign csr_prmd_diff = logic_prmd;
  assign csr_ectl_diff = logic_ectl;
  assign csr_estat_diff = logic_estat;
  assign csr_era_diff = logic_era;
  assign csr_badv_diff = logic_badv;
  assign csr_eentry_diff = logic_eentry;
  assign csr_tlbidx_diff = logic_tlbidx;
  assign csr_tlbehi_diff = logic_tlbehi;
  assign csr_tlbelo0_diff = logic_tlbelo0;
  assign csr_tlbelo1_diff = logic_tlbelo1;
  assign csr_asid_diff = logic_asid;
  assign csr_save0_diff = logic_save0;
  assign csr_save1_diff = logic_save1;
  assign csr_save2_diff = logic_save2;
  assign csr_save3_diff = logic_save3;
  assign csr_tid_diff = logic_tid;
  assign csr_tcfg_diff = logic_tcfg;
  assign csr_tval_diff = logic_tval;
  assign csr_ticlr_diff = logic_ticlr;
  assign csr_llbctl_diff = {logic_llbctl[31 : 1],logic_llbit};
  assign csr_tlbrentry_diff = logic_tlbrentry;
  assign csr_dmw0_diff = logic_dmw0;
  assign csr_dmw1_diff = logic_dmw1;
  assign csr_pgdl_diff = logic_pgdl;
  assign csr_pgdh_diff = logic_pgdh;
  always @(posedge clk) begin
    logic_tlbelo0[31 : 28] <= logic_tlbelo0[31 : 28];
    logic_tlbelo1[31 : 28] <= logic_tlbelo1[31 : 28];
    logic_llbctl[0] <= logic_llbctl[0];
    logic_pgdl[11 : 0] <= logic_pgdl[11 : 0];
    logic_pgdh[11 : 0] <= logic_pgdh[11 : 0];
    if(reset) begin
      logic_crmd <= 32'h00000008;
    end else begin
      if(excp_flush) begin
        logic_crmd[1 : 0] <= 2'b00;
        logic_crmd[2] <= 1'b0;
        if(excp_tlbrefill) begin
          logic_crmd[3] <= 1'b1;
          logic_crmd[4] <= 1'b0;
        end
      end else begin
        if(ertn_flush) begin
          logic_crmd[1 : 0] <= logic_prmd[1 : 0];
          logic_crmd[2] <= logic_prmd[2];
          if(logic_returningFromRefill) begin
            logic_crmd[3] <= 1'b0;
            logic_crmd[4] <= 1'b1;
          end
        end else begin
          if(logic_crmdWrite) begin
            logic_crmd[8 : 0] <= wr_data[8 : 0];
          end
        end
      end
    end
    if(reset) begin
      logic_prmd[31 : 3] <= 29'h0;
    end else begin
      if(excp_flush) begin
        logic_prmd[1 : 0] <= logic_crmd[1 : 0];
        logic_prmd[2] <= logic_crmd[2];
      end else begin
        if(when_OpenLa500Csr_l234) begin
          logic_prmd[2 : 0] <= wr_data[2 : 0];
        end
      end
    end
    if(reset) begin
      logic_ectl <= 32'h0;
    end else begin
      if(when_OpenLa500Csr_l240) begin
        logic_ectl[9 : 0] <= wr_data[9 : 0];
        logic_ectl[12 : 11] <= wr_data[12 : 11];
      end
    end
    if(reset) begin
      logic_estat[1 : 0] <= 2'b00;
      logic_estat[10] <= 1'b0;
      logic_estat[12] <= 1'b0;
      logic_estat[15 : 13] <= 3'b000;
      logic_estat[21 : 16] <= 6'h0;
      logic_estat[31] <= 1'b0;
      logic_timerEnabled <= 1'b0;
    end else begin
      if(when_OpenLa500Csr_l254) begin
        logic_estat[11] <= 1'b0;
      end else begin
        if(logic_tcfgWrite) begin
          logic_timerEnabled <= wr_data[0];
        end else begin
          if(when_OpenLa500Csr_l258) begin
            logic_estat[11] <= 1'b1;
            logic_timerEnabled <= logic_tcfg[1];
          end
        end
      end
      logic_estat[9 : 2] <= interrupt;
      if(excp_flush) begin
        logic_estat[21 : 16] <= ecode_in;
        logic_estat[30 : 22] <= esubcode_in;
      end else begin
        if(when_OpenLa500Csr_l266) begin
          logic_estat[1 : 0] <= wr_data[1 : 0];
        end
      end
    end
    if(excp_flush) begin
      logic_era <= era_in;
    end else begin
      if(when_OpenLa500Csr_l271) begin
        logic_era <= wr_data;
      end
    end
    if(when_OpenLa500Csr_l272) begin
      logic_badv <= wr_data;
    end else begin
      if(va_error_in) begin
        logic_badv <= bad_va_in;
      end
    end
    if(reset) begin
      logic_eentry[5 : 0] <= 6'h0;
    end else begin
      if(when_OpenLa500Csr_l276) begin
        logic_eentry[31 : 6] <= wr_data[31 : 6];
      end
    end
    if(reset) begin
      logic_tlbidx[4 : 0] <= 5'h0;
      logic_tlbidx[23 : 5] <= 19'h0;
      logic_tlbidx[30] <= 1'b0;
    end else begin
      if(when_OpenLa500Csr_l284) begin
        logic_tlbidx[4 : 0] <= wr_data[4 : 0];
        logic_tlbidx[29 : 24] <= wr_data[29 : 24];
        logic_tlbidx[31] <= wr_data[31];
      end else begin
        if(tlbsrch_en) begin
          if(tlbsrch_found) begin
            logic_tlbidx[4 : 0] <= tlbsrch_index;
            logic_tlbidx[31] <= 1'b0;
          end else begin
            logic_tlbidx[31] <= 1'b1;
          end
        end else begin
          if(logic_tlbrdValid) begin
            logic_tlbidx[29 : 24] <= tlbidx_in[29 : 24];
            logic_tlbidx[31] <= tlbidx_in[31];
          end else begin
            if(logic_tlbrdInvalid) begin
              logic_tlbidx[29 : 24] <= 6'h0;
              logic_tlbidx[31] <= tlbidx_in[31];
            end
          end
        end
      end
    end
    if(reset) begin
      logic_tlbehi[12 : 0] <= 13'h0;
    end else begin
      if(logic_tlbehiWrite) begin
        logic_tlbehi[31 : 13] <= wr_data[31 : 13];
      end else begin
        if(logic_tlbrdValid) begin
          logic_tlbehi[31 : 13] <= tlbehi_in[31 : 13];
        end else begin
          if(logic_tlbrdInvalid) begin
            logic_tlbehi[31 : 13] <= 19'h0;
          end else begin
            if(excp_tlb) begin
              logic_tlbehi[31 : 13] <= excp_tlb_vppn;
            end
          end
        end
      end
    end
    if(reset) begin
      logic_tlbelo0[7] <= 1'b0;
    end else begin
      if(when_OpenLa500Csr_l320) begin
        logic_tlbelo0[6 : 0] <= wr_data[6 : 0];
        logic_tlbelo0[27 : 8] <= wr_data[27 : 8];
      end else begin
        if(logic_tlbrdValid) begin
          logic_tlbelo0[6 : 0] <= tlbelo0_in[6 : 0];
          logic_tlbelo0[27 : 8] <= tlbelo0_in[27 : 8];
        end else begin
          if(logic_tlbrdInvalid) begin
            logic_tlbelo0[6 : 0] <= 7'h0;
            logic_tlbelo0[27 : 8] <= 20'h0;
          end
        end
      end
    end
    if(reset) begin
      logic_tlbelo1[7] <= 1'b0;
    end else begin
      if(when_OpenLa500Csr_l320_1) begin
        logic_tlbelo1[6 : 0] <= wr_data[6 : 0];
        logic_tlbelo1[27 : 8] <= wr_data[27 : 8];
      end else begin
        if(logic_tlbrdValid) begin
          logic_tlbelo1[6 : 0] <= tlbelo1_in[6 : 0];
          logic_tlbelo1[27 : 8] <= tlbelo1_in[27 : 8];
        end else begin
          if(logic_tlbrdInvalid) begin
            logic_tlbelo1[6 : 0] <= 7'h0;
            logic_tlbelo1[27 : 8] <= 20'h0;
          end
        end
      end
    end
    if(reset) begin
      logic_asid[31 : 10] <= 22'h000280;
    end else begin
      if(when_OpenLa500Csr_l335) begin
        logic_asid[9 : 0] <= wr_data[9 : 0];
      end else begin
        if(logic_tlbrdValid) begin
          logic_asid[9 : 0] <= asid_in;
        end else begin
          if(logic_tlbrdInvalid) begin
            logic_asid[9 : 0] <= 10'h0;
          end
        end
      end
    end
    if(reset) begin
      logic_tlbrentry[5 : 0] <= 6'h0;
    end else begin
      if(when_OpenLa500Csr_l345) begin
        logic_tlbrentry[31 : 6] <= wr_data[31 : 6];
      end
    end
    if(reset) begin
      logic_dmw0[2 : 1] <= 2'b00;
      logic_dmw0[24 : 6] <= 19'h0;
      logic_dmw0[28] <= 1'b0;
    end else begin
      if(when_OpenLa500Csr_l354) begin
        logic_dmw0[0] <= wr_data[0];
        logic_dmw0[3] <= wr_data[3];
        logic_dmw0[5 : 4] <= wr_data[5 : 4];
        logic_dmw0[27 : 25] <= wr_data[27 : 25];
        logic_dmw0[31 : 29] <= wr_data[31 : 29];
      end
    end
    if(reset) begin
      logic_dmw1[2 : 1] <= 2'b00;
      logic_dmw1[24 : 6] <= 19'h0;
      logic_dmw1[28] <= 1'b0;
    end else begin
      if(when_OpenLa500Csr_l354_1) begin
        logic_dmw1[0] <= wr_data[0];
        logic_dmw1[3] <= wr_data[3];
        logic_dmw1[5 : 4] <= wr_data[5 : 4];
        logic_dmw1[27 : 25] <= wr_data[27 : 25];
        logic_dmw1[31 : 29] <= wr_data[31 : 29];
      end
    end
    if(reset) begin
      logic_cpuid <= 32'h0;
    end
    if(when_OpenLa500Csr_l366) begin
      logic_save0 <= wr_data;
    end
    if(when_OpenLa500Csr_l367) begin
      logic_save1 <= wr_data;
    end
    if(when_OpenLa500Csr_l368) begin
      logic_save2 <= wr_data;
    end
    if(when_OpenLa500Csr_l369) begin
      logic_save3 <= wr_data;
    end
    if(reset) begin
      logic_tid <= 32'h0;
    end else begin
      if(when_OpenLa500Csr_l370) begin
        logic_tid <= wr_data;
      end
    end
    if(reset) begin
      logic_tcfg[0] <= 1'b0;
    end else begin
      if(logic_tcfgWrite) begin
        logic_tcfg <= wr_data;
      end
    end
    if(reset) begin
      logic_cntc <= 32'h0;
    end else begin
      if(when_OpenLa500Csr_l375) begin
        logic_cntc <= wr_data;
      end
    end
    if(logic_tcfgWrite) begin
      logic_tval <= {wr_data[31 : 2],2'b00};
    end else begin
      if(logic_timerEnabled) begin
        if(when_OpenLa500Csr_l379) begin
          logic_tval <= _zz_logic_tval;
        end else begin
          logic_tval <= (logic_tcfg[1] ? {logic_tcfg[31 : 2],2'b00} : 32'hffffffff);
        end
      end
    end
    if(reset) begin
      logic_ticlr <= 32'h0;
    end
    if(reset) begin
      logic_llbctl[31 : 3] <= 29'h0;
      logic_llbctl[2] <= 1'b0;
      logic_llbctl[1] <= 1'b0;
      logic_llbit <= 1'b0;
    end else begin
      if(ertn_flush) begin
        if(when_OpenLa500Csr_l393) begin
          logic_llbctl[2] <= 1'b0;
        end else begin
          logic_llbit <= 1'b0;
        end
      end else begin
        if(logic_llbctlWrite) begin
          logic_llbctl[2] <= wr_data[2];
          if(when_OpenLa500Csr_l396) begin
            logic_llbit <= 1'b0;
          end
        end else begin
          if(llbit_set_in) begin
            logic_llbit <= llbit_in;
          end
        end
      end
    end
    if(reset) begin
      logic_lladdr <= 28'h0;
    end else begin
      if(lladdr_set_in) begin
        logic_lladdr <= lladdr_in;
      end
    end
    if(reset) begin
      logic_timer64 <= 64'h0;
    end else begin
      logic_timer64 <= (logic_timer64 + 64'h0000000000000001);
    end
    if(when_OpenLa500Csr_l403) begin
      logic_pgdl[31 : 12] <= wr_data[31 : 12];
    end
    if(when_OpenLa500Csr_l404) begin
      logic_pgdh[31 : 12] <= wr_data[31 : 12];
    end
    if(reset) begin
      logic_brk <= 32'h0;
    end
    if(when_OpenLa500Csr_l407) begin
      logic_brk <= wr_data;
    end
    if(reset) begin
      logic_disableCache <= 32'h0;
    end
    if(when_OpenLa500Csr_l409) begin
      logic_disableCache <= wr_data;
    end
    if(reset) begin
      logic_cpucfg1 <= 32'h0001f1f4;
      logic_cpucfg2 <= 32'h0;
      logic_cpucfg10 <= 32'h00000005;
      logic_cpucfg11 <= 32'h04080001;
      logic_cpucfg12 <= 32'h04080001;
      logic_cpucfg13 <= 32'h0;
    end
  end


endmodule
