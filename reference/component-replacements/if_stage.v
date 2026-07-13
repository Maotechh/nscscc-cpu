// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : if_stage

`timescale 1ns/1ps

module if_stage (
  input  wire          clk,
  input  wire          reset,
  input  wire          ds_allowin,
  input  wire [32:0]   br_bus,
  output wire          fs_to_ds_valid,
  output wire [108:0]  fs_to_ds_bus,
  input  wire          excp_flush,
  input  wire          ertn_flush,
  input  wire          refetch_flush,
  input  wire          icacop_flush,
  input  wire [31:0]   ws_pc,
  input  wire [31:0]   csr_eentry,
  input  wire [31:0]   csr_era,
  input  wire          excp_tlbrefill,
  input  wire [31:0]   csr_tlbrentry,
  input  wire          has_int,
  input  wire          idle_flush,
  output wire          inst_valid,
  output wire          inst_op,
  output wire [3:0]    inst_wstrb,
  output wire [31:0]   inst_wdata,
  input  wire          inst_addr_ok,
  input  wire          inst_data_ok,
  input  wire          icache_miss,
  input  wire [31:0]   inst_rdata,
  output wire          inst_uncache_en,
  output wire          tlb_excp_cancel_req,
  input  wire          csr_pg,
  input  wire          csr_da,
  input  wire [31:0]   csr_dmw0,
  input  wire [31:0]   csr_dmw1,
  input  wire [1:0]    csr_plv,
  input  wire [1:0]    csr_datf,
  input  wire          disable_cache,
  output wire [31:0]   fetch_pc,
  output wire          fetch_en,
  input  wire [31:0]   btb_ret_pc,
  input  wire          btb_taken,
  input  wire          btb_en,
  input  wire [4:0]    btb_index,
  output wire [31:0]   inst_addr,
  output wire          inst_addr_trans_en,
  output wire          dmw0_en,
  output wire          dmw1_en,
  input  wire          inst_tlb_found,
  input  wire          inst_tlb_v,
  input  wire          inst_tlb_d,
  input  wire [1:0]    inst_tlb_mat,
  input  wire [1:0]    inst_tlb_plv
);

  wire                area_stage_io_branchRepair;
  wire       [31:0]   area_stage_io_branchTarget;
  wire       [31:0]   area_stage_io_writebackPc;
  wire       [31:0]   area_stage_io_exceptionEntry;
  wire       [31:0]   area_stage_io_exceptionEra;
  wire       [31:0]   area_stage_io_tlbRefillEntry;
  wire       [1:0]    area_stage_io_currentPlv;
  wire       [31:0]   area_stage_io_btbTarget;
  wire       [4:0]    area_stage_io_btbIndex;
  wire       [1:0]    area_stage_io_tlbPlv;
  wire                area_stage_io_downstream_valid;
  wire       [31:0]   area_stage_io_downstream_payload_pc;
  wire       [31:0]   area_stage_io_downstream_payload_instruction;
  wire       [3:0]    area_stage_io_downstream_payload_exceptionCode;
  wire                area_stage_io_downstream_payload_hasException;
  wire                area_stage_io_downstream_payload_instructionCacheMiss;
  wire                area_stage_io_downstream_payload_btbEnabled;
  wire                area_stage_io_downstream_payload_btbTaken;
  wire       [4:0]    area_stage_io_downstream_payload_btbIndex;
  wire       [31:0]   area_stage_io_downstream_payload_btbTarget;
  wire                area_stage_io_instructionRequest;
  wire       [31:0]   area_stage_io_instructionAddress;
  wire                area_stage_io_instructionUncached;
  wire                area_stage_io_tlbCancel;
  wire                area_stage_io_addressTranslation;
  wire                area_stage_io_dmw0Enabled;
  wire                area_stage_io_dmw1Enabled;
  wire       [31:0]   area_stage_io_fetchPc;
  wire                area_stage_io_fetchEnable;

  FetchStage area_stage (
    .io_downstream_valid                        (area_stage_io_downstream_valid                       ), //o
    .io_downstream_ready                        (ds_allowin                                           ), //i
    .io_downstream_payload_pc                   (area_stage_io_downstream_payload_pc[31:0]            ), //o
    .io_downstream_payload_instruction          (area_stage_io_downstream_payload_instruction[31:0]   ), //o
    .io_downstream_payload_exceptionCode        (area_stage_io_downstream_payload_exceptionCode[3:0]  ), //o
    .io_downstream_payload_hasException         (area_stage_io_downstream_payload_hasException        ), //o
    .io_downstream_payload_instructionCacheMiss (area_stage_io_downstream_payload_instructionCacheMiss), //o
    .io_downstream_payload_btbEnabled           (area_stage_io_downstream_payload_btbEnabled          ), //o
    .io_downstream_payload_btbTaken             (area_stage_io_downstream_payload_btbTaken            ), //o
    .io_downstream_payload_btbIndex             (area_stage_io_downstream_payload_btbIndex[4:0]       ), //o
    .io_downstream_payload_btbTarget            (area_stage_io_downstream_payload_btbTarget[31:0]     ), //o
    .io_branchRepair                            (area_stage_io_branchRepair                           ), //i
    .io_branchTarget                            (area_stage_io_branchTarget[31:0]                     ), //i
    .io_exceptionFlush                          (excp_flush                                           ), //i
    .io_ertnFlush                               (ertn_flush                                           ), //i
    .io_refetchFlush                            (refetch_flush                                        ), //i
    .io_instructionCacheFlush                   (icacop_flush                                         ), //i
    .io_idleFlush                               (idle_flush                                           ), //i
    .io_writebackPc                             (area_stage_io_writebackPc[31:0]                      ), //i
    .io_exceptionEntry                          (area_stage_io_exceptionEntry[31:0]                   ), //i
    .io_exceptionEra                            (area_stage_io_exceptionEra[31:0]                     ), //i
    .io_exceptionTlbRefill                      (excp_tlbrefill                                       ), //i
    .io_tlbRefillEntry                          (area_stage_io_tlbRefillEntry[31:0]                   ), //i
    .io_interrupt                               (has_int                                              ), //i
    .io_instructionAddressAccepted              (inst_addr_ok                                         ), //i
    .io_instructionDataValid                    (inst_data_ok                                         ), //i
    .io_instructionData                         (inst_rdata[31:0]                                     ), //i
    .io_instructionMiss                         (icache_miss                                          ), //i
    .io_instructionRequest                      (area_stage_io_instructionRequest                     ), //o
    .io_instructionAddress                      (area_stage_io_instructionAddress[31:0]               ), //o
    .io_instructionUncached                     (area_stage_io_instructionUncached                    ), //o
    .io_tlbCancel                               (area_stage_io_tlbCancel                              ), //o
    .io_paging                                  (csr_pg                                               ), //i
    .io_directAddress                           (csr_da                                               ), //i
    .io_dmw0                                    (csr_dmw0[31:0]                                       ), //i
    .io_dmw1                                    (csr_dmw1[31:0]                                       ), //i
    .io_currentPlv                              (area_stage_io_currentPlv[1:0]                        ), //i
    .io_directFetchMat                          (csr_datf[1:0]                                        ), //i
    .io_disableCache                            (disable_cache                                        ), //i
    .io_btbTarget                               (area_stage_io_btbTarget[31:0]                        ), //i
    .io_btbTaken                                (btb_taken                                            ), //i
    .io_btbEnabled                              (btb_en                                               ), //i
    .io_btbIndex                                (area_stage_io_btbIndex[4:0]                          ), //i
    .io_addressTranslation                      (area_stage_io_addressTranslation                     ), //o
    .io_dmw0Enabled                             (area_stage_io_dmw0Enabled                            ), //o
    .io_dmw1Enabled                             (area_stage_io_dmw1Enabled                            ), //o
    .io_tlbFound                                (inst_tlb_found                                       ), //i
    .io_tlbValid                                (inst_tlb_v                                           ), //i
    .io_tlbMat                                  (inst_tlb_mat[1:0]                                    ), //i
    .io_tlbPlv                                  (area_stage_io_tlbPlv[1:0]                            ), //i
    .io_fetchPc                                 (area_stage_io_fetchPc[31:0]                          ), //o
    .io_fetchEnable                             (area_stage_io_fetchEnable                            ), //o
    .clk                                        (clk                                                  ), //i
    .reset                                      (reset                                                )  //i
  );
  assign area_stage_io_branchRepair = br_bus[32];
  assign area_stage_io_branchTarget = br_bus[31 : 0];
  assign area_stage_io_writebackPc = ws_pc;
  assign area_stage_io_exceptionEntry = csr_eentry;
  assign area_stage_io_exceptionEra = csr_era;
  assign area_stage_io_tlbRefillEntry = csr_tlbrentry;
  assign area_stage_io_currentPlv = csr_plv;
  assign area_stage_io_btbTarget = btb_ret_pc;
  assign area_stage_io_btbIndex = btb_index;
  assign area_stage_io_tlbPlv = inst_tlb_plv;
  assign fs_to_ds_valid = area_stage_io_downstream_valid;
  assign fs_to_ds_bus = {{{{{{{{area_stage_io_downstream_payload_btbTarget,area_stage_io_downstream_payload_btbIndex},area_stage_io_downstream_payload_btbTaken},area_stage_io_downstream_payload_btbEnabled},area_stage_io_downstream_payload_instructionCacheMiss},area_stage_io_downstream_payload_hasException},area_stage_io_downstream_payload_exceptionCode},area_stage_io_downstream_payload_instruction},area_stage_io_downstream_payload_pc};
  assign inst_valid = area_stage_io_instructionRequest;
  assign inst_op = 1'b0;
  assign inst_wstrb = 4'b0000;
  assign inst_wdata = 32'h0;
  assign inst_uncache_en = area_stage_io_instructionUncached;
  assign tlb_excp_cancel_req = area_stage_io_tlbCancel;
  assign fetch_pc = area_stage_io_fetchPc;
  assign fetch_en = area_stage_io_fetchEnable;
  assign inst_addr = area_stage_io_instructionAddress;
  assign inst_addr_trans_en = area_stage_io_addressTranslation;
  assign dmw0_en = area_stage_io_dmw0Enabled;
  assign dmw1_en = area_stage_io_dmw1Enabled;

endmodule

module FetchStage (
  output wire          io_downstream_valid,
  input  wire          io_downstream_ready,
  output wire [31:0]   io_downstream_payload_pc,
  output wire [31:0]   io_downstream_payload_instruction,
  output wire [3:0]    io_downstream_payload_exceptionCode,
  output wire          io_downstream_payload_hasException,
  output wire          io_downstream_payload_instructionCacheMiss,
  output wire          io_downstream_payload_btbEnabled,
  output wire          io_downstream_payload_btbTaken,
  output wire [4:0]    io_downstream_payload_btbIndex,
  output wire [31:0]   io_downstream_payload_btbTarget,
  input  wire          io_branchRepair,
  input  wire [31:0]   io_branchTarget,
  input  wire          io_exceptionFlush,
  input  wire          io_ertnFlush,
  input  wire          io_refetchFlush,
  input  wire          io_instructionCacheFlush,
  input  wire          io_idleFlush,
  input  wire [31:0]   io_writebackPc,
  input  wire [31:0]   io_exceptionEntry,
  input  wire [31:0]   io_exceptionEra,
  input  wire          io_exceptionTlbRefill,
  input  wire [31:0]   io_tlbRefillEntry,
  input  wire          io_interrupt,
  input  wire          io_instructionAddressAccepted,
  input  wire          io_instructionDataValid,
  input  wire [31:0]   io_instructionData,
  input  wire          io_instructionMiss,
  output wire          io_instructionRequest,
  output wire [31:0]   io_instructionAddress,
  output wire          io_instructionUncached,
  output wire          io_tlbCancel,
  input  wire          io_paging,
  input  wire          io_directAddress,
  input  wire [31:0]   io_dmw0,
  input  wire [31:0]   io_dmw1,
  input  wire [1:0]    io_currentPlv,
  input  wire [1:0]    io_directFetchMat,
  input  wire          io_disableCache,
  input  wire [31:0]   io_btbTarget,
  input  wire          io_btbTaken,
  input  wire          io_btbEnabled,
  input  wire [4:0]    io_btbIndex,
  output wire          io_addressTranslation,
  output wire          io_dmw0Enabled,
  output wire          io_dmw1Enabled,
  input  wire          io_tlbFound,
  input  wire          io_tlbValid,
  input  wire [1:0]    io_tlbMat,
  input  wire [1:0]    io_tlbPlv,
  output wire [31:0]   io_fetchPc,
  output wire          io_fetchEnable,
  input  wire          clk,
  input  wire          reset
);

  wire       [31:0]   _zz_instructionFlushPc;
  reg                 fsValid;
  reg        [31:0]   fsPc;
  reg                 fsException;
  reg                 fsExceptionNumber;
  reg        [31:0]   instructionBuffer;
  reg                 instructionBufferValid;
  reg                 idleLock;
  reg        [37:0]   btbLock;
  reg                 btbLockValid;
  reg        [31:0]   flushRequestPc;
  reg                 flushRequestPending;
  reg        [31:0]   branchRequestPc;
  reg        [2:0]    branchRequestState;
  wire       [2:0]    branchEmpty;
  wire       [2:0]    branchWaitSlot;
  wire       [2:0]    branchWaitTarget;
  wire                flush;
  wire                flushDelay;
  wire                flushDirty;
  wire       [31:0]   btbTargetLocked;
  wire       [4:0]    btbIndexLocked;
  wire                btbTakenLocked;
  wire                btbEnabledLocked;
  wire                fetchBtbTarget;
  wire       [31:0]   sequencePc;
  wire       [31:0]   architecturalExceptionEntry;
  wire       [31:0]   instructionFlushPc;
  reg        [31:0]   nextPc;
  wire                when_FetchStage_l101;
  wire                when_FetchStage_l103;
  wire                when_FetchStage_l105;
  wire                directMode;
  wire                pagingMode;
  wire                dmw0Enabled;
  wire                dmw1Enabled;
  wire                addressTranslation;
  wire                tlbRefill;
  wire                tlbInvalid;
  wire                tlbPrivilege;
  wire                tlbCancel;
  wire                tlbLockPc;
  wire                prefetchAlignmentException;
  wire                fsExceptionAny;
  wire                fsReady;
  wire                fsAllow;
  wire                instructionRequest;
  wire                prefetchReady;
  wire                when_FetchStage_l163;
  wire                when_FetchStage_l176;
  wire                when_FetchStage_l186;
  wire                when_FetchStage_l192;
  wire                when_FetchStage_l205;
  wire                when_FetchStage_l210;
  wire                when_FetchStage_l212;
  wire                when_FetchStage_l217;
  wire                when_FetchStage_l219;
  wire                when_FetchStage_l229;

  assign _zz_instructionFlushPc = (io_writebackPc + 32'h00000004);
  assign branchEmpty = 3'b001;
  assign branchWaitSlot = 3'b010;
  assign branchWaitTarget = 3'b100;
  assign flush = ((((io_ertnFlush || io_exceptionFlush) || io_refetchFlush) || io_instructionCacheFlush) || io_idleFlush);
  assign flushDelay = ((flush && (! io_instructionAddressAccepted)) || io_idleFlush);
  assign flushDirty = ((flush && io_instructionAddressAccepted) && (! io_idleFlush));
  assign btbTargetLocked = ((btbLockValid ? btbLock[31 : 0] : 32'h0) | io_btbTarget);
  assign btbIndexLocked = ((btbLockValid ? btbLock[36 : 32] : 5'h0) | io_btbIndex);
  assign btbTakenLocked = ((btbLockValid && btbLock[37]) || io_btbTaken);
  assign btbEnabledLocked = (btbLockValid || io_btbEnabled);
  assign fetchBtbTarget = ((io_btbTaken && io_btbEnabled) || (btbLockValid && btbLock[37]));
  assign sequencePc = (fsPc + 32'h00000004);
  assign architecturalExceptionEntry = (io_exceptionTlbRefill ? io_tlbRefillEntry : io_exceptionEntry);
  assign instructionFlushPc = (io_ertnFlush ? io_exceptionEra : _zz_instructionFlushPc);
  always @(*) begin
    nextPc = sequencePc;
    if(flushRequestPending) begin
      nextPc = flushRequestPc;
    end else begin
      if(io_exceptionFlush) begin
        nextPc = architecturalExceptionEntry;
      end else begin
        if(when_FetchStage_l101) begin
          nextPc = instructionFlushPc;
        end else begin
          if(when_FetchStage_l103) begin
            nextPc = branchRequestPc;
          end else begin
            if(when_FetchStage_l105) begin
              nextPc = io_branchTarget;
            end else begin
              if(fetchBtbTarget) begin
                nextPc = btbTargetLocked;
              end
            end
          end
        end
      end
    end
  end

  assign when_FetchStage_l101 = (((io_ertnFlush || io_refetchFlush) || io_instructionCacheFlush) || io_idleFlush);
  assign when_FetchStage_l103 = (branchRequestState == branchWaitTarget);
  assign when_FetchStage_l105 = (io_branchRepair && fsValid);
  assign directMode = (io_directAddress && (! io_paging));
  assign pagingMode = (io_paging && (! io_directAddress));
  assign dmw0Enabled = ((((io_dmw0[0] && (io_currentPlv == 2'b00)) || (io_dmw0[3] && (io_currentPlv == 2'b11))) && (fsPc[31 : 29] == io_dmw0[31 : 29])) && pagingMode);
  assign dmw1Enabled = ((((io_dmw1[0] && (io_currentPlv == 2'b00)) || (io_dmw1[3] && (io_currentPlv == 2'b11))) && (fsPc[31 : 29] == io_dmw1[31 : 29])) && pagingMode);
  assign addressTranslation = ((pagingMode && (! dmw0Enabled)) && (! dmw1Enabled));
  assign tlbRefill = ((! io_tlbFound) && addressTranslation);
  assign tlbInvalid = ((! io_tlbValid) && addressTranslation);
  assign tlbPrivilege = ((io_tlbPlv < io_currentPlv) && addressTranslation);
  assign tlbCancel = ((tlbRefill || tlbInvalid) || tlbPrivilege);
  assign tlbLockPc = ((tlbCancel && (branchRequestState != branchWaitTarget)) && (! flushRequestPending));
  assign prefetchAlignmentException = (nextPc[1 : 0] != 2'b00);
  assign fsExceptionAny = (((fsException || tlbRefill) || tlbInvalid) || tlbPrivilege);
  assign fsReady = ((io_instructionDataValid || instructionBufferValid) || fsExceptionAny);
  assign fsAllow = ((! fsValid) || (fsReady && io_downstream_ready));
  assign instructionRequest = (((((fsAllow && (! prefetchAlignmentException)) && (! tlbLockPc)) || flush) || io_branchRepair) && (! (io_idleFlush || idleLock)));
  assign prefetchReady = ((instructionRequest || prefetchAlignmentException) && io_instructionAddressAccepted);
  assign io_downstream_valid = (fsValid && fsReady);
  assign io_downstream_payload_pc = fsPc;
  assign io_downstream_payload_instruction = (instructionBufferValid ? instructionBuffer : io_instructionData);
  assign io_downstream_payload_exceptionCode = {{{tlbPrivilege,tlbInvalid},tlbRefill},fsExceptionNumber};
  assign io_downstream_payload_hasException = fsExceptionAny;
  assign io_downstream_payload_instructionCacheMiss = io_instructionMiss;
  assign io_downstream_payload_btbEnabled = btbEnabledLocked;
  assign io_downstream_payload_btbTaken = btbTakenLocked;
  assign io_downstream_payload_btbIndex = btbIndexLocked;
  assign io_downstream_payload_btbTarget = btbTargetLocked;
  assign io_instructionRequest = instructionRequest;
  assign io_instructionAddress = nextPc;
  assign io_instructionUncached = (((((directMode && (io_directFetchMat == 2'b00)) || (dmw0Enabled && (io_dmw0[5 : 4] == 2'b00))) || (dmw1Enabled && (io_dmw1[5 : 4] == 2'b00))) || (addressTranslation && (io_tlbMat == 2'b00))) || io_disableCache);
  assign io_tlbCancel = tlbCancel;
  assign io_addressTranslation = addressTranslation;
  assign io_dmw0Enabled = dmw0Enabled;
  assign io_dmw1Enabled = dmw1Enabled;
  assign io_fetchPc = nextPc;
  assign io_fetchEnable = (instructionRequest && io_instructionAddressAccepted);
  assign when_FetchStage_l163 = (! flushRequestPending);
  assign when_FetchStage_l176 = (io_idleFlush && (! io_interrupt));
  assign when_FetchStage_l186 = ((io_branchRepair && (! fsValid)) && (! io_instructionAddressAccepted));
  assign when_FetchStage_l192 = (((io_branchRepair && (! io_instructionAddressAccepted)) && fsValid) || ((io_branchRepair && io_instructionAddressAccepted) && (! fsValid)));
  assign when_FetchStage_l205 = (prefetchReady || flush);
  assign when_FetchStage_l210 = (flush || io_fetchEnable);
  assign when_FetchStage_l212 = (io_btbEnabled && (! prefetchReady));
  assign when_FetchStage_l217 = ((fsReady && io_downstream_ready) || flush);
  assign when_FetchStage_l219 = (io_instructionDataValid && (! io_downstream_ready));
  assign when_FetchStage_l229 = (prefetchReady && (fsAllow || flushDirty));
  always @(posedge clk) begin
    if(reset) begin
      fsValid <= 1'b0;
      fsPc <= 32'h1bfffffc;
      fsException <= 1'b0;
      fsExceptionNumber <= 1'b0;
      instructionBufferValid <= 1'b0;
      idleLock <= 1'b0;
      btbLockValid <= 1'b0;
      flushRequestPending <= 1'b0;
      branchRequestState <= 3'b001;
    end else begin
      if(when_FetchStage_l163) begin
        if(flushDelay) begin
          flushRequestPending <= 1'b1;
        end
      end else begin
        if(prefetchReady) begin
          flushRequestPending <= 1'b0;
        end
      end
      if(when_FetchStage_l176) begin
        idleLock <= 1'b1;
      end else begin
        if(io_interrupt) begin
          idleLock <= 1'b0;
        end
      end
      if((branchRequestState == branchEmpty)) begin
          if(flush) begin
            branchRequestState <= branchEmpty;
          end else begin
            if(when_FetchStage_l186) begin
              branchRequestState <= branchWaitSlot;
            end else begin
              if(when_FetchStage_l192) begin
                branchRequestState <= branchWaitTarget;
              end
            end
          end
      end else if((branchRequestState == branchWaitSlot)) begin
          if(flush) begin
            branchRequestState <= branchEmpty;
          end else begin
            if(prefetchReady) begin
              branchRequestState <= branchWaitTarget;
            end
          end
      end else if((branchRequestState == branchWaitTarget)) begin
          if(when_FetchStage_l205) begin
            branchRequestState <= branchEmpty;
          end
      end else begin
          branchRequestState <= branchEmpty;
      end
      if(when_FetchStage_l210) begin
        btbLockValid <= 1'b0;
      end else begin
        if(when_FetchStage_l212) begin
          btbLockValid <= 1'b1;
        end
      end
      if(when_FetchStage_l217) begin
        instructionBufferValid <= 1'b0;
      end else begin
        if(when_FetchStage_l219) begin
          instructionBufferValid <= 1'b1;
        end
      end
      if(flushDelay) begin
        fsValid <= 1'b0;
      end else begin
        if(fsAllow) begin
          fsValid <= prefetchReady;
        end
      end
      if(when_FetchStage_l229) begin
        fsPc <= nextPc;
        fsException <= prefetchAlignmentException;
        fsExceptionNumber <= prefetchAlignmentException;
      end
    end
  end

  always @(posedge clk) begin
    if(when_FetchStage_l163) begin
      if(flushDelay) begin
        flushRequestPc <= nextPc;
      end
    end else begin
      if(!prefetchReady) begin
        if(flush) begin
          flushRequestPc <= nextPc;
        end
      end
    end
    if((branchRequestState == branchEmpty)) begin
        if(!flush) begin
          if(when_FetchStage_l186) begin
            branchRequestPc <= io_branchTarget;
          end else begin
            if(when_FetchStage_l192) begin
              branchRequestPc <= io_branchTarget;
            end
          end
        end
    end else if((branchRequestState == branchWaitSlot)) begin
    end else if((branchRequestState == branchWaitTarget)) begin
    end else begin
    end
    if(!when_FetchStage_l210) begin
      if(when_FetchStage_l212) begin
        btbLock <= {{io_btbTaken,io_btbIndex},io_btbTarget};
      end
    end
    if(!when_FetchStage_l217) begin
      if(when_FetchStage_l219) begin
        instructionBuffer <= io_instructionData;
      end
    end
  end


endmodule
