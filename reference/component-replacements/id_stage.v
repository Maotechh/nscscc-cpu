// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : id_stage



module id_stage (
  input  wire          clk,
  input  wire          reset,
  input  wire          es_allowin,
  output wire          ds_allowin,
  input  wire          fs_to_ds_valid,
  input  wire [108:0]  fs_to_ds_bus,
  input  wire [38:0]   es_to_ds_forward_bus,
  input  wire [38:0]   ms_to_ds_forward_bus,
  output wire          ds_to_es_valid,
  output wire [349:0]  ds_to_es_bus,
  output wire [32:0]   br_bus,
  input  wire          excp_flush,
  input  wire          ertn_flush,
  input  wire          refetch_flush,
  input  wire          icacop_flush,
  input  wire          idle_flush,
  input  wire          es_tlb_inst_stall,
  input  wire          ms_tlb_inst_stall,
  input  wire          ws_tlb_inst_stall,
  input  wire          has_int,
  output wire [13:0]   rd_csr_addr,
  input  wire [31:0]   rd_csr_data,
  input  wire [1:0]    csr_plv,
  input  wire [63:0]   timer_64,
  input  wire [31:0]   csr_tid,
  input  wire          ds_llbit,
  input  wire          es_to_ds_valid,
  input  wire          ms_to_ds_valid,
  input  wire          ws_to_ds_valid,
  input  wire          write_buffer_empty,
  input  wire          dcache_empty,
  output wire          btb_operate_en,
  output wire          btb_pop_ras,
  output wire          btb_push_ras,
  output wire          btb_add_entry,
  output wire          btb_delete_entry,
  output wire          btb_pre_error,
  output wire          btb_pre_right,
  output wire          btb_target_error,
  output wire          btb_right_orien,
  output wire [31:0]   btb_right_target,
  output wire [31:0]   btb_operate_pc,
  output wire [4:0]    btb_operate_index,
  input  wire          infor_flag,
  input  wire [4:0]    reg_num,
  output wire [31:0]   debug_rf_rdata1,
  input  wire [37:0]   ws_to_rf_bus
);

  wire       [31:0]   area_stage_io_input_payload_pc;
  wire       [31:0]   area_stage_io_input_payload_instruction;
  wire       [3:0]    area_stage_io_input_payload_exceptionCode;
  wire                area_stage_io_input_payload_hasException;
  wire                area_stage_io_input_payload_instructionCacheMiss;
  wire                area_stage_io_input_payload_btbEnabled;
  wire                area_stage_io_input_payload_btbTaken;
  wire       [4:0]    area_stage_io_input_payload_btbIndex;
  wire       [31:0]   area_stage_io_input_payload_btbTarget;
  wire                area_stage_io_executeForward_dependencyNeedsStall;
  wire                area_stage_io_executeForward_valid;
  wire       [4:0]    area_stage_io_executeForward_destination;
  wire       [31:0]   area_stage_io_executeForward_data;
  wire                area_stage_io_memoryForward_dependencyNeedsStall;
  wire                area_stage_io_memoryForward_valid;
  wire       [4:0]    area_stage_io_memoryForward_destination;
  wire       [31:0]   area_stage_io_memoryForward_data;
  wire                area_stage_io_registerWrite_valid;
  wire       [4:0]    area_stage_io_registerWrite_destination;
  wire       [31:0]   area_stage_io_registerWrite_data;
  wire       [4:0]    area_stage_io_debugReadAddress;
  wire                area_stage_io_input_ready;
  wire                area_stage_io_output_valid;
  wire       [31:0]   area_stage_io_output_payload_pc;
  wire       [31:0]   area_stage_io_output_payload_registerDataKOrD;
  wire       [31:0]   area_stage_io_output_payload_registerDataJ;
  wire       [31:0]   area_stage_io_output_payload_immediate;
  wire       [4:0]    area_stage_io_output_payload_destination;
  wire                area_stage_io_output_payload_isStore;
  wire                area_stage_io_output_payload_gprWrite;
  wire                area_stage_io_output_payload_source2IsFour;
  wire                area_stage_io_output_payload_source2IsImmediate;
  wire                area_stage_io_output_payload_source1IsPc;
  wire                area_stage_io_output_payload_isLoad;
  wire       [13:0]   area_stage_io_output_payload_aluOperation;
  wire                area_stage_io_output_payload_mulDivSigned;
  wire       [3:0]    area_stage_io_output_payload_mulDivOperation;
  wire       [1:0]    area_stage_io_output_payload_memorySize;
  wire                area_stage_io_output_payload_hasException;
  wire                area_stage_io_output_payload_isErtn;
  wire       [31:0]   area_stage_io_output_payload_csrReadData;
  wire                area_stage_io_output_payload_resultFromCsr;
  wire       [13:0]   area_stage_io_output_payload_csrAddress;
  wire                area_stage_io_output_payload_csrWrite;
  wire                area_stage_io_output_payload_csrMask;
  wire       [8:0]    area_stage_io_output_payload_exceptionCode;
  wire                area_stage_io_output_payload_isLl;
  wire                area_stage_io_output_payload_isSc;
  wire                area_stage_io_output_payload_tlbSearch;
  wire                area_stage_io_output_payload_tlbWrite;
  wire                area_stage_io_output_payload_tlbFill;
  wire                area_stage_io_output_payload_refetch;
  wire                area_stage_io_output_payload_tlbRead;
  wire                area_stage_io_output_payload_invalidateTlb;
  wire                area_stage_io_output_payload_memorySignExtend;
  wire                area_stage_io_output_payload_cacheOperation;
  wire                area_stage_io_output_payload_preload;
  wire                area_stage_io_output_payload_isBranch;
  wire                area_stage_io_output_payload_instructionCacheMiss;
  wire                area_stage_io_output_payload_isPredictableBranch;
  wire                area_stage_io_output_payload_predictionError;
  wire                area_stage_io_output_payload_idle;
  wire       [31:0]   area_stage_io_output_payload_instruction;
  wire       [63:0]   area_stage_io_output_payload_timer;
  wire                area_stage_io_output_payload_isCounterInstruction;
  wire       [7:0]    area_stage_io_output_payload_loadEvent;
  wire       [7:0]    area_stage_io_output_payload_storeEvent;
  wire                area_stage_io_output_payload_csrRstatEvent;
  wire       [13:0]   area_stage_io_csrReadAddress;
  wire       [31:0]   area_stage_io_debugLegacyValue;
  wire                area_stage_io_branchRepair_active;
  wire       [31:0]   area_stage_io_branchRepair_target;
  wire                area_stage_io_btb_enable;
  wire                area_stage_io_btb_popReturnStack;
  wire                area_stage_io_btb_pushReturnStack;
  wire                area_stage_io_btb_addEntry;
  wire                area_stage_io_btb_deleteEntry;
  wire                area_stage_io_btb_predictionError;
  wire                area_stage_io_btb_predictionRight;
  wire                area_stage_io_btb_targetError;
  wire                area_stage_io_btb_actualTaken;
  wire       [31:0]   area_stage_io_btb_actualTarget;
  wire       [31:0]   area_stage_io_btb_pc;
  wire       [4:0]    area_stage_io_btb_index;
  wire       [196:0]  _zz_ds_to_es_bus;
  wire       [127:0]  _zz_ds_to_es_bus_1;
  wire       [116:0]  _zz_ds_to_es_bus_2;
  wire       [0:0]    _zz_ds_to_es_bus_3;
  wire       [0:0]    _zz_ds_to_es_bus_4;

  assign _zz_ds_to_es_bus = {{{{{{{{{{{{{_zz_ds_to_es_bus_1,_zz_ds_to_es_bus_4},area_stage_io_output_payload_isLl},area_stage_io_output_payload_exceptionCode},area_stage_io_output_payload_csrMask},area_stage_io_output_payload_csrWrite},area_stage_io_output_payload_csrAddress},area_stage_io_output_payload_resultFromCsr},area_stage_io_output_payload_csrReadData},area_stage_io_output_payload_isErtn},area_stage_io_output_payload_hasException},area_stage_io_output_payload_memorySize},area_stage_io_output_payload_mulDivOperation},area_stage_io_output_payload_mulDivSigned};
  assign _zz_ds_to_es_bus_1 = {{{{{{{{{{{_zz_ds_to_es_bus_2,_zz_ds_to_es_bus_3},area_stage_io_output_payload_isBranch},area_stage_io_output_payload_preload},area_stage_io_output_payload_cacheOperation},area_stage_io_output_payload_memorySignExtend},area_stage_io_output_payload_invalidateTlb},area_stage_io_output_payload_tlbRead},area_stage_io_output_payload_refetch},area_stage_io_output_payload_tlbFill},area_stage_io_output_payload_tlbWrite},area_stage_io_output_payload_tlbSearch};
  assign _zz_ds_to_es_bus_4 = area_stage_io_output_payload_isSc;
  assign _zz_ds_to_es_bus_2 = {{{{{{{{area_stage_io_output_payload_csrRstatEvent,area_stage_io_output_payload_storeEvent},area_stage_io_output_payload_loadEvent},area_stage_io_output_payload_isCounterInstruction},area_stage_io_output_payload_timer},area_stage_io_output_payload_instruction},area_stage_io_output_payload_idle},area_stage_io_output_payload_predictionError},area_stage_io_output_payload_isPredictableBranch};
  assign _zz_ds_to_es_bus_3 = area_stage_io_output_payload_instructionCacheMiss;
  DecodeStage area_stage (
    .io_input_valid                         (fs_to_ds_valid                                     ), //i
    .io_input_ready                         (area_stage_io_input_ready                          ), //o
    .io_input_payload_pc                    (area_stage_io_input_payload_pc[31:0]               ), //i
    .io_input_payload_instruction           (area_stage_io_input_payload_instruction[31:0]      ), //i
    .io_input_payload_exceptionCode         (area_stage_io_input_payload_exceptionCode[3:0]     ), //i
    .io_input_payload_hasException          (area_stage_io_input_payload_hasException           ), //i
    .io_input_payload_instructionCacheMiss  (area_stage_io_input_payload_instructionCacheMiss   ), //i
    .io_input_payload_btbEnabled            (area_stage_io_input_payload_btbEnabled             ), //i
    .io_input_payload_btbTaken              (area_stage_io_input_payload_btbTaken               ), //i
    .io_input_payload_btbIndex              (area_stage_io_input_payload_btbIndex[4:0]          ), //i
    .io_input_payload_btbTarget             (area_stage_io_input_payload_btbTarget[31:0]        ), //i
    .io_output_valid                        (area_stage_io_output_valid                         ), //o
    .io_output_ready                        (es_allowin                                         ), //i
    .io_output_payload_pc                   (area_stage_io_output_payload_pc[31:0]              ), //o
    .io_output_payload_registerDataKOrD     (area_stage_io_output_payload_registerDataKOrD[31:0]), //o
    .io_output_payload_registerDataJ        (area_stage_io_output_payload_registerDataJ[31:0]   ), //o
    .io_output_payload_immediate            (area_stage_io_output_payload_immediate[31:0]       ), //o
    .io_output_payload_destination          (area_stage_io_output_payload_destination[4:0]      ), //o
    .io_output_payload_isStore              (area_stage_io_output_payload_isStore               ), //o
    .io_output_payload_gprWrite             (area_stage_io_output_payload_gprWrite              ), //o
    .io_output_payload_source2IsFour        (area_stage_io_output_payload_source2IsFour         ), //o
    .io_output_payload_source2IsImmediate   (area_stage_io_output_payload_source2IsImmediate    ), //o
    .io_output_payload_source1IsPc          (area_stage_io_output_payload_source1IsPc           ), //o
    .io_output_payload_isLoad               (area_stage_io_output_payload_isLoad                ), //o
    .io_output_payload_aluOperation         (area_stage_io_output_payload_aluOperation[13:0]    ), //o
    .io_output_payload_mulDivSigned         (area_stage_io_output_payload_mulDivSigned          ), //o
    .io_output_payload_mulDivOperation      (area_stage_io_output_payload_mulDivOperation[3:0]  ), //o
    .io_output_payload_memorySize           (area_stage_io_output_payload_memorySize[1:0]       ), //o
    .io_output_payload_hasException         (area_stage_io_output_payload_hasException          ), //o
    .io_output_payload_isErtn               (area_stage_io_output_payload_isErtn                ), //o
    .io_output_payload_csrReadData          (area_stage_io_output_payload_csrReadData[31:0]     ), //o
    .io_output_payload_resultFromCsr        (area_stage_io_output_payload_resultFromCsr         ), //o
    .io_output_payload_csrAddress           (area_stage_io_output_payload_csrAddress[13:0]      ), //o
    .io_output_payload_csrWrite             (area_stage_io_output_payload_csrWrite              ), //o
    .io_output_payload_csrMask              (area_stage_io_output_payload_csrMask               ), //o
    .io_output_payload_exceptionCode        (area_stage_io_output_payload_exceptionCode[8:0]    ), //o
    .io_output_payload_isLl                 (area_stage_io_output_payload_isLl                  ), //o
    .io_output_payload_isSc                 (area_stage_io_output_payload_isSc                  ), //o
    .io_output_payload_tlbSearch            (area_stage_io_output_payload_tlbSearch             ), //o
    .io_output_payload_tlbWrite             (area_stage_io_output_payload_tlbWrite              ), //o
    .io_output_payload_tlbFill              (area_stage_io_output_payload_tlbFill               ), //o
    .io_output_payload_refetch              (area_stage_io_output_payload_refetch               ), //o
    .io_output_payload_tlbRead              (area_stage_io_output_payload_tlbRead               ), //o
    .io_output_payload_invalidateTlb        (area_stage_io_output_payload_invalidateTlb         ), //o
    .io_output_payload_memorySignExtend     (area_stage_io_output_payload_memorySignExtend      ), //o
    .io_output_payload_cacheOperation       (area_stage_io_output_payload_cacheOperation        ), //o
    .io_output_payload_preload              (area_stage_io_output_payload_preload               ), //o
    .io_output_payload_isBranch             (area_stage_io_output_payload_isBranch              ), //o
    .io_output_payload_instructionCacheMiss (area_stage_io_output_payload_instructionCacheMiss  ), //o
    .io_output_payload_isPredictableBranch  (area_stage_io_output_payload_isPredictableBranch   ), //o
    .io_output_payload_predictionError      (area_stage_io_output_payload_predictionError       ), //o
    .io_output_payload_idle                 (area_stage_io_output_payload_idle                  ), //o
    .io_output_payload_instruction          (area_stage_io_output_payload_instruction[31:0]     ), //o
    .io_output_payload_timer                (area_stage_io_output_payload_timer[63:0]           ), //o
    .io_output_payload_isCounterInstruction (area_stage_io_output_payload_isCounterInstruction  ), //o
    .io_output_payload_loadEvent            (area_stage_io_output_payload_loadEvent[7:0]        ), //o
    .io_output_payload_storeEvent           (area_stage_io_output_payload_storeEvent[7:0]       ), //o
    .io_output_payload_csrRstatEvent        (area_stage_io_output_payload_csrRstatEvent         ), //o
    .io_executeForward_dependencyNeedsStall (area_stage_io_executeForward_dependencyNeedsStall  ), //i
    .io_executeForward_valid                (area_stage_io_executeForward_valid                 ), //i
    .io_executeForward_destination          (area_stage_io_executeForward_destination[4:0]      ), //i
    .io_executeForward_data                 (area_stage_io_executeForward_data[31:0]            ), //i
    .io_memoryForward_dependencyNeedsStall  (area_stage_io_memoryForward_dependencyNeedsStall   ), //i
    .io_memoryForward_valid                 (area_stage_io_memoryForward_valid                  ), //i
    .io_memoryForward_destination           (area_stage_io_memoryForward_destination[4:0]       ), //i
    .io_memoryForward_data                  (area_stage_io_memoryForward_data[31:0]             ), //i
    .io_flush_exception                     (excp_flush                                         ), //i
    .io_flush_ertn                          (ertn_flush                                         ), //i
    .io_flush_refetch                       (refetch_flush                                      ), //i
    .io_flush_instructionCacheOperation     (icacop_flush                                       ), //i
    .io_flush_idle                          (idle_flush                                         ), //i
    .io_executeTlbStall                     (es_tlb_inst_stall                                  ), //i
    .io_memoryTlbStall                      (ms_tlb_inst_stall                                  ), //i
    .io_writebackTlbStall                   (ws_tlb_inst_stall                                  ), //i
    .io_interruptPending                    (has_int                                            ), //i
    .io_csrReadAddress                      (area_stage_io_csrReadAddress[13:0]                 ), //o
    .io_csrReadData                         (rd_csr_data[31:0]                                  ), //i
    .io_csrPrivilege                        (csr_plv[1:0]                                       ), //i
    .io_timer                               (timer_64[63:0]                                     ), //i
    .io_timerId                             (csr_tid[31:0]                                      ), //i
    .io_reservationValid                    (ds_llbit                                           ), //i
    .io_executeOccupied                     (es_to_ds_valid                                     ), //i
    .io_memoryOccupied                      (ms_to_ds_valid                                     ), //i
    .io_writebackOccupied                   (ws_to_ds_valid                                     ), //i
    .io_writeBufferEmpty                    (write_buffer_empty                                 ), //i
    .io_dataCacheEmpty                      (dcache_empty                                       ), //i
    .io_registerWrite_valid                 (area_stage_io_registerWrite_valid                  ), //i
    .io_registerWrite_destination           (area_stage_io_registerWrite_destination[4:0]       ), //i
    .io_registerWrite_data                  (area_stage_io_registerWrite_data[31:0]             ), //i
    .io_debugReadSelect                     (infor_flag                                         ), //i
    .io_debugReadAddress                    (area_stage_io_debugReadAddress[4:0]                ), //i
    .io_debugLegacyValue                    (area_stage_io_debugLegacyValue[31:0]               ), //o
    .io_branchRepair_active                 (area_stage_io_branchRepair_active                  ), //o
    .io_branchRepair_target                 (area_stage_io_branchRepair_target[31:0]            ), //o
    .io_btb_enable                          (area_stage_io_btb_enable                           ), //o
    .io_btb_popReturnStack                  (area_stage_io_btb_popReturnStack                   ), //o
    .io_btb_pushReturnStack                 (area_stage_io_btb_pushReturnStack                  ), //o
    .io_btb_addEntry                        (area_stage_io_btb_addEntry                         ), //o
    .io_btb_deleteEntry                     (area_stage_io_btb_deleteEntry                      ), //o
    .io_btb_predictionError                 (area_stage_io_btb_predictionError                  ), //o
    .io_btb_predictionRight                 (area_stage_io_btb_predictionRight                  ), //o
    .io_btb_targetError                     (area_stage_io_btb_targetError                      ), //o
    .io_btb_actualTaken                     (area_stage_io_btb_actualTaken                      ), //o
    .io_btb_actualTarget                    (area_stage_io_btb_actualTarget[31:0]               ), //o
    .io_btb_pc                              (area_stage_io_btb_pc[31:0]                         ), //o
    .io_btb_index                           (area_stage_io_btb_index[4:0]                       ), //o
    .clk                                    (clk                                                ), //i
    .reset                                  (reset                                              )  //i
  );
  assign area_stage_io_input_payload_pc = fs_to_ds_bus[31 : 0];
  assign area_stage_io_input_payload_instruction = fs_to_ds_bus[63 : 32];
  assign area_stage_io_input_payload_exceptionCode = fs_to_ds_bus[67 : 64];
  assign area_stage_io_input_payload_hasException = fs_to_ds_bus[68];
  assign area_stage_io_input_payload_instructionCacheMiss = fs_to_ds_bus[69];
  assign area_stage_io_input_payload_btbEnabled = fs_to_ds_bus[70];
  assign area_stage_io_input_payload_btbTaken = fs_to_ds_bus[71];
  assign area_stage_io_input_payload_btbIndex = fs_to_ds_bus[76 : 72];
  assign area_stage_io_input_payload_btbTarget = fs_to_ds_bus[108 : 77];
  assign ds_allowin = area_stage_io_input_ready;
  assign ds_to_es_valid = area_stage_io_output_valid;
  assign ds_to_es_bus = {{{{{{{{{{{{_zz_ds_to_es_bus,area_stage_io_output_payload_aluOperation},area_stage_io_output_payload_isLoad},area_stage_io_output_payload_source1IsPc},area_stage_io_output_payload_source2IsImmediate},area_stage_io_output_payload_source2IsFour},area_stage_io_output_payload_gprWrite},area_stage_io_output_payload_isStore},area_stage_io_output_payload_destination},area_stage_io_output_payload_immediate},area_stage_io_output_payload_registerDataJ},area_stage_io_output_payload_registerDataKOrD},area_stage_io_output_payload_pc};
  assign area_stage_io_executeForward_dependencyNeedsStall = es_to_ds_forward_bus[38];
  assign area_stage_io_executeForward_valid = es_to_ds_forward_bus[37];
  assign area_stage_io_executeForward_destination = es_to_ds_forward_bus[36 : 32];
  assign area_stage_io_executeForward_data = es_to_ds_forward_bus[31 : 0];
  assign area_stage_io_memoryForward_dependencyNeedsStall = ms_to_ds_forward_bus[38];
  assign area_stage_io_memoryForward_valid = ms_to_ds_forward_bus[37];
  assign area_stage_io_memoryForward_destination = ms_to_ds_forward_bus[36 : 32];
  assign area_stage_io_memoryForward_data = ms_to_ds_forward_bus[31 : 0];
  assign rd_csr_addr = area_stage_io_csrReadAddress;
  assign area_stage_io_registerWrite_valid = ws_to_rf_bus[37];
  assign area_stage_io_registerWrite_destination = ws_to_rf_bus[36 : 32];
  assign area_stage_io_registerWrite_data = ws_to_rf_bus[31 : 0];
  assign area_stage_io_debugReadAddress = reg_num;
  assign debug_rf_rdata1 = area_stage_io_debugLegacyValue;
  assign br_bus = {area_stage_io_branchRepair_active,area_stage_io_branchRepair_target};
  assign btb_operate_en = area_stage_io_btb_enable;
  assign btb_pop_ras = area_stage_io_btb_popReturnStack;
  assign btb_push_ras = area_stage_io_btb_pushReturnStack;
  assign btb_add_entry = area_stage_io_btb_addEntry;
  assign btb_delete_entry = area_stage_io_btb_deleteEntry;
  assign btb_pre_error = area_stage_io_btb_predictionError;
  assign btb_pre_right = area_stage_io_btb_predictionRight;
  assign btb_target_error = area_stage_io_btb_targetError;
  assign btb_right_orien = area_stage_io_btb_actualTaken;
  assign btb_right_target = area_stage_io_btb_actualTarget;
  assign btb_operate_pc = area_stage_io_btb_pc;
  assign btb_operate_index = area_stage_io_btb_index;

endmodule

module DecodeStage (
  input  wire          io_input_valid,
  output wire          io_input_ready,
  input  wire [31:0]   io_input_payload_pc,
  input  wire [31:0]   io_input_payload_instruction,
  input  wire [3:0]    io_input_payload_exceptionCode,
  input  wire          io_input_payload_hasException,
  input  wire          io_input_payload_instructionCacheMiss,
  input  wire          io_input_payload_btbEnabled,
  input  wire          io_input_payload_btbTaken,
  input  wire [4:0]    io_input_payload_btbIndex,
  input  wire [31:0]   io_input_payload_btbTarget,
  output wire          io_output_valid,
  input  wire          io_output_ready,
  output wire [31:0]   io_output_payload_pc,
  output wire [31:0]   io_output_payload_registerDataKOrD,
  output wire [31:0]   io_output_payload_registerDataJ,
  output wire [31:0]   io_output_payload_immediate,
  output wire [4:0]    io_output_payload_destination,
  output wire          io_output_payload_isStore,
  output wire          io_output_payload_gprWrite,
  output wire          io_output_payload_source2IsFour,
  output wire          io_output_payload_source2IsImmediate,
  output wire          io_output_payload_source1IsPc,
  output wire          io_output_payload_isLoad,
  output wire [13:0]   io_output_payload_aluOperation,
  output wire          io_output_payload_mulDivSigned,
  output wire [3:0]    io_output_payload_mulDivOperation,
  output wire [1:0]    io_output_payload_memorySize,
  output wire          io_output_payload_hasException,
  output wire          io_output_payload_isErtn,
  output wire [31:0]   io_output_payload_csrReadData,
  output wire          io_output_payload_resultFromCsr,
  output wire [13:0]   io_output_payload_csrAddress,
  output wire          io_output_payload_csrWrite,
  output wire          io_output_payload_csrMask,
  output wire [8:0]    io_output_payload_exceptionCode,
  output wire          io_output_payload_isLl,
  output wire          io_output_payload_isSc,
  output wire          io_output_payload_tlbSearch,
  output wire          io_output_payload_tlbWrite,
  output wire          io_output_payload_tlbFill,
  output wire          io_output_payload_refetch,
  output wire          io_output_payload_tlbRead,
  output wire          io_output_payload_invalidateTlb,
  output wire          io_output_payload_memorySignExtend,
  output wire          io_output_payload_cacheOperation,
  output wire          io_output_payload_preload,
  output wire          io_output_payload_isBranch,
  output wire          io_output_payload_instructionCacheMiss,
  output wire          io_output_payload_isPredictableBranch,
  output wire          io_output_payload_predictionError,
  output wire          io_output_payload_idle,
  output wire [31:0]   io_output_payload_instruction,
  output wire [63:0]   io_output_payload_timer,
  output wire          io_output_payload_isCounterInstruction,
  output wire [7:0]    io_output_payload_loadEvent,
  output wire [7:0]    io_output_payload_storeEvent,
  output wire          io_output_payload_csrRstatEvent,
  input  wire          io_executeForward_dependencyNeedsStall,
  input  wire          io_executeForward_valid,
  input  wire [4:0]    io_executeForward_destination,
  input  wire [31:0]   io_executeForward_data,
  input  wire          io_memoryForward_dependencyNeedsStall,
  input  wire          io_memoryForward_valid,
  input  wire [4:0]    io_memoryForward_destination,
  input  wire [31:0]   io_memoryForward_data,
  input  wire          io_flush_exception,
  input  wire          io_flush_ertn,
  input  wire          io_flush_refetch,
  input  wire          io_flush_instructionCacheOperation,
  input  wire          io_flush_idle,
  input  wire          io_executeTlbStall,
  input  wire          io_memoryTlbStall,
  input  wire          io_writebackTlbStall,
  input  wire          io_interruptPending,
  output wire [13:0]   io_csrReadAddress,
  input  wire [31:0]   io_csrReadData,
  input  wire [1:0]    io_csrPrivilege,
  input  wire [63:0]   io_timer,
  input  wire [31:0]   io_timerId,
  input  wire          io_reservationValid,
  input  wire          io_executeOccupied,
  input  wire          io_memoryOccupied,
  input  wire          io_writebackOccupied,
  input  wire          io_writeBufferEmpty,
  input  wire          io_dataCacheEmpty,
  input  wire          io_registerWrite_valid,
  input  wire [4:0]    io_registerWrite_destination,
  input  wire [31:0]   io_registerWrite_data,
  input  wire          io_debugReadSelect,
  input  wire [4:0]    io_debugReadAddress,
  output wire [31:0]   io_debugLegacyValue,
  output wire          io_branchRepair_active,
  output wire [31:0]   io_branchRepair_target,
  output wire          io_btb_enable,
  output wire          io_btb_popReturnStack,
  output wire          io_btb_pushReturnStack,
  output wire          io_btb_addEntry,
  output wire          io_btb_deleteEntry,
  output wire          io_btb_predictionError,
  output wire          io_btb_predictionRight,
  output wire          io_btb_targetError,
  output wire          io_btb_actualTaken,
  output wire [31:0]   io_btb_actualTarget,
  output wire [31:0]   io_btb_pc,
  output wire [4:0]    io_btb_index,
  input  wire          clk,
  input  wire          reset
);

  wire                _zz_aluOperation;
  wire       [4:0]    _zz_immediate;
  wire       [31:0]   _zz_immediate_1;
  wire       [11:0]   _zz_immediate_2;
  wire       [31:0]   _zz_immediate_3;
  wire       [15:0]   _zz_immediate_4;
  wire       [31:0]   _zz_immediate_5;
  wire       [17:0]   _zz_immediate_6;
  wire       [31:0]   _zz_immediate_7;
  wire       [21:0]   _zz_immediate_8;
  wire       [31:0]   _zz_immediate_9;
  wire       [27:0]   _zz_immediate_10;
  wire                _zz_source2IsImmediate;
  wire                _zz_gprWrite;
  wire                _zz_needRj;
  wire                _zz_needRj_1;
  wire                _zz_needRkd;
  reg        [31:0]   _zz_registerDataJ;
  reg        [31:0]   _zz_registerDataKOrD;
  wire       [31:0]   _zz_lessSigned;
  wire       [31:0]   _zz_lessSigned_1;
  wire       [31:0]   _zz_branchTarget;
  wire       [31:0]   _zz_branchTarget_1;
  wire                _zz_instructionValid;
  wire                _zz_instructionValid_1;
  wire                _zz_instructionValid_2;
  wire                _zz_instructionValid_3;
  wire       [31:0]   _zz_btbRepairTarget;
  wire       [13:0]   _zz_io_csrReadAddress;
  wire       [4:0]    _zz_io_debugLegacyValue;
  reg                 occupied;
  reg        [31:0]   fetch_pc;
  reg        [31:0]   fetch_instruction;
  reg        [3:0]    fetch_exceptionCode;
  reg                 fetch_hasException;
  reg                 fetch_instructionCacheMiss;
  reg                 fetch_btbEnabled;
  reg                 fetch_btbTaken;
  reg        [4:0]    fetch_btbIndex;
  reg        [31:0]   fetch_btbTarget;
  reg                 branchSlotCancel;
  reg        [31:0]   registerFile_0;
  reg        [31:0]   registerFile_1;
  reg        [31:0]   registerFile_2;
  reg        [31:0]   registerFile_3;
  reg        [31:0]   registerFile_4;
  reg        [31:0]   registerFile_5;
  reg        [31:0]   registerFile_6;
  reg        [31:0]   registerFile_7;
  reg        [31:0]   registerFile_8;
  reg        [31:0]   registerFile_9;
  reg        [31:0]   registerFile_10;
  reg        [31:0]   registerFile_11;
  reg        [31:0]   registerFile_12;
  reg        [31:0]   registerFile_13;
  reg        [31:0]   registerFile_14;
  reg        [31:0]   registerFile_15;
  reg        [31:0]   registerFile_16;
  reg        [31:0]   registerFile_17;
  reg        [31:0]   registerFile_18;
  reg        [31:0]   registerFile_19;
  reg        [31:0]   registerFile_20;
  reg        [31:0]   registerFile_21;
  reg        [31:0]   registerFile_22;
  reg        [31:0]   registerFile_23;
  reg        [31:0]   registerFile_24;
  reg        [31:0]   registerFile_25;
  reg        [31:0]   registerFile_26;
  reg        [31:0]   registerFile_27;
  reg        [31:0]   registerFile_28;
  reg        [31:0]   registerFile_29;
  reg        [31:0]   registerFile_30;
  reg        [31:0]   registerFile_31;
  wire       [31:0]   _zz_1;
  wire       [5:0]    op31To26;
  wire       [3:0]    op25To22;
  wire       [1:0]    op21To20;
  wire       [4:0]    op19To15;
  wire       [4:0]    rd;
  wire       [4:0]    rj;
  wire       [4:0]    rk;
  wire       [11:0]   i12;
  wire       [13:0]   i14;
  wire       [19:0]   i20;
  wire       [15:0]   i16;
  wire       [25:0]   i26;
  wire       [13:0]   csrIndex;
  wire                instAddW;
  wire                instSubW;
  wire                instSlt;
  wire                instSltu;
  wire                instNor;
  wire                instAnd;
  wire                instOr;
  wire                instXor;
  wire                instOrn;
  wire                instAndn;
  wire                instSllW;
  wire                instSrlW;
  wire                instSraW;
  wire                instMulW;
  wire                instMulhW;
  wire                instMulhWu;
  wire                instDivW;
  wire                instModW;
  wire                instDivWu;
  wire                instModWu;
  wire                instBreak;
  wire                instSyscall;
  wire                instSlliW;
  wire                instSrliW;
  wire                instSraiW;
  wire                instIdle;
  wire                instInvTlb;
  wire                instDbar;
  wire                instIbar;
  wire                instSlti;
  wire                instSltui;
  wire                instAddiW;
  wire                instAndi;
  wire                instOri;
  wire                instXori;
  wire                instLdB;
  wire                instLdH;
  wire                instLdW;
  wire                instStB;
  wire                instStH;
  wire                instStW;
  wire                instLdBu;
  wire                instLdHu;
  wire                instCacop;
  wire                instPreload;
  wire                instJirl;
  wire                instB;
  wire                instBl;
  wire                instBeq;
  wire                instBne;
  wire                instBlt;
  wire                instBge;
  wire                instBltu;
  wire                instBgeu;
  wire                instLu12iW;
  wire                instPcaddi;
  wire                instPcaddu12i;
  wire                baseCsr;
  wire                instCsrXchg;
  wire                instLlW;
  wire                instScW;
  wire                instCsrRead;
  wire                instCsrWrite;
  wire                counterBase;
  wire                instRdCntIdW;
  wire                instRdCntVlW;
  wire                instRdCntVhW;
  wire                privilegedBase;
  wire                instErtn;
  wire                instTlbSearch;
  wire                instTlbRead;
  wire                instTlbWrite;
  wire                instTlbFill;
  wire                instCpuCfg;
  wire       [4:0]    destination;
  wire                validCacop;
  wire                cacopNop;
  wire                laccRequest;
  wire                laccValid;
  reg        [13:0]   aluOperation;
  reg        [3:0]    mulDivOperation;
  wire                mulDivSigned;
  wire                needUi5;
  wire                needSi12;
  wire                needUi12;
  wire                needSi14Pc;
  wire                needSi16Pc;
  wire                needSi20;
  wire                needSi26Pc;
  reg        [31:0]   immediate;
  wire                sourceRegisterIsRd;
  wire                source1IsPc;
  wire                source2IsImmediate;
  wire                source2IsFour;
  wire                loadOperation;
  wire                byteMemory;
  wire                halfMemory;
  wire                memorySignExtend;
  wire                gprWrite;
  wire                storeOperation;
  wire                needRj;
  wire                needRkd;
  wire       [4:0]    readAddressJ;
  wire       [4:0]    readAddressKOrD;
  wire       [31:0]   registerDataJ;
  wire       [31:0]   registerDataKOrD;
  wire                branchNeedsRegisterData;
  wire                executeJHit;
  wire                memoryJHit;
  wire                executeKHit;
  wire                memoryKHit;
  wire       [31:0]   valueJ;
  wire       [31:0]   valueKOrD;
  wire       [31:0]   branchValueJ;
  wire       [31:0]   branchValueKOrD;
  wire                stallJ;
  wire                stallK;
  wire                equalOperands;
  wire                lessUnsigned;
  wire                lessSigned;
  wire                branchTakenRaw;
  wire                branchTaken;
  wire                branchInstruction;
  wire                predictableBranch;
  wire                pcRelativeBranch;
  wire       [31:0]   branchTarget;
  wire                instructionValid;
  wire                illegalInstruction;
  wire                kernelInstruction;
  wire                privilegeException;
  wire                hasException;
  wire       [8:0]    exceptionCode;
  wire                refetch;
  wire                pipelineNotEmpty;
  wire                barrierStall;
  wire                tlbStall;
  wire                readyGo;
  wire                btbAddEntry;
  wire                btbDeleteEntry;
  wire                btbPredictionError;
  wire                btbTargetError;
  wire                btbRepair;
  wire       [31:0]   btbRepairTarget;
  wire                when_DecodeStage_l633;
  wire                when_DecodeStage_l636;
  wire                when_DecodeStage_l642;
  wire                when_DecodeStage_l646;
  wire                when_DecodeStage_l648;
  wire                when_DecodeStage_l650;
  wire                counterEnabled;
  wire       [31:0]   counterResult;
  wire       [31:0]   csrData;

  assign _zz_immediate = rk;
  assign _zz_immediate_2 = i12;
  assign _zz_immediate_1 = {{20{_zz_immediate_2[11]}}, _zz_immediate_2};
  assign _zz_immediate_4 = {i14,2'b00};
  assign _zz_immediate_3 = {{16{_zz_immediate_4[15]}}, _zz_immediate_4};
  assign _zz_immediate_6 = {i16,2'b00};
  assign _zz_immediate_5 = {{14{_zz_immediate_6[17]}}, _zz_immediate_6};
  assign _zz_immediate_8 = {i20,2'b00};
  assign _zz_immediate_7 = {{10{_zz_immediate_8[21]}}, _zz_immediate_8};
  assign _zz_immediate_10 = {i26,2'b00};
  assign _zz_immediate_9 = {{4{_zz_immediate_10[27]}}, _zz_immediate_10};
  assign _zz_lessSigned = branchValueJ;
  assign _zz_lessSigned_1 = branchValueKOrD;
  assign _zz_branchTarget = (branchValueJ + immediate);
  assign _zz_branchTarget_1 = (fetch_pc + immediate);
  assign _zz_btbRepairTarget = (fetch_pc + 32'h00000004);
  assign _zz_io_csrReadAddress = (valueJ[13 : 0] + 14'h00b0);
  assign _zz_io_debugLegacyValue = readAddressJ;
  assign _zz_aluOperation = (instAddW || instAddiW);
  assign _zz_source2IsImmediate = (((((((instSlliW || instSrliW) || instSraiW) || instAddiW) || instSlti) || instSltui) || instAndi) || instOri);
  assign _zz_gprWrite = (((((instStB || instStH) || instStW) || instBeq) || instBne) || instBlt);
  assign _zz_needRj = (((((((((((((((((_zz_needRj_1 || instMulhWu) || instDivW) || instDivWu) || instModW) || instModWu) || instSllW) || instSrlW) || instSraW) || instSlliW) || instSrliW) || instSraiW) || instBeq) || instBne) || instBlt) || instBltu) || instBge) || instBgeu);
  assign _zz_needRj_1 = (((((((((((((((instAddW || instSubW) || instAddiW) || instSlt) || instSltu) || instSlti) || instSltui) || instAnd) || instOr) || instNor) || instXor) || instAndi) || instOri) || instXori) || instMulW) || instMulhW);
  assign _zz_needRkd = (((((((((((((((instAddW || instSubW) || instSlt) || instSltu) || instAnd) || instOr) || instNor) || instXor) || instMulW) || instMulhW) || instMulhWu) || instDivW) || instDivWu) || instModW) || instModWu) || instSllW);
  assign _zz_instructionValid = (((((((((((((((((_zz_instructionValid_1 || instJirl) || instB) || instBl) || instBeq) || instBne) || instBlt) || instBge) || instBltu) || instBgeu) || instLu12iW) || instPcaddu12i) || instCsrRead) || instCsrWrite) || instCsrXchg) || instRdCntIdW) || instRdCntVhW) || instRdCntVlW);
  assign _zz_instructionValid_1 = (((((((((((((((((_zz_instructionValid_2 || instIdle) || instSlti) || instSltui) || instAddiW) || instAndi) || instOri) || instXori) || instLdB) || instLdH) || instLdW) || instStB) || instStH) || instStW) || instLdBu) || instLdHu) || instLlW) || instScW);
  assign _zz_instructionValid_2 = (((((((((((((((((_zz_instructionValid_3 || instOr) || instXor) || instSllW) || instSrlW) || instSraW) || instMulW) || instMulhW) || instMulhWu) || instDivW) || instModW) || instDivWu) || instModWu) || instBreak) || instSyscall) || instSlliW) || instSrliW) || instSraiW);
  assign _zz_instructionValid_3 = (((((instAddW || instSubW) || instSlt) || instSltu) || instNor) || instAnd);
  always @(*) begin
    case(readAddressJ)
      5'b00000 : _zz_registerDataJ = registerFile_0;
      5'b00001 : _zz_registerDataJ = registerFile_1;
      5'b00010 : _zz_registerDataJ = registerFile_2;
      5'b00011 : _zz_registerDataJ = registerFile_3;
      5'b00100 : _zz_registerDataJ = registerFile_4;
      5'b00101 : _zz_registerDataJ = registerFile_5;
      5'b00110 : _zz_registerDataJ = registerFile_6;
      5'b00111 : _zz_registerDataJ = registerFile_7;
      5'b01000 : _zz_registerDataJ = registerFile_8;
      5'b01001 : _zz_registerDataJ = registerFile_9;
      5'b01010 : _zz_registerDataJ = registerFile_10;
      5'b01011 : _zz_registerDataJ = registerFile_11;
      5'b01100 : _zz_registerDataJ = registerFile_12;
      5'b01101 : _zz_registerDataJ = registerFile_13;
      5'b01110 : _zz_registerDataJ = registerFile_14;
      5'b01111 : _zz_registerDataJ = registerFile_15;
      5'b10000 : _zz_registerDataJ = registerFile_16;
      5'b10001 : _zz_registerDataJ = registerFile_17;
      5'b10010 : _zz_registerDataJ = registerFile_18;
      5'b10011 : _zz_registerDataJ = registerFile_19;
      5'b10100 : _zz_registerDataJ = registerFile_20;
      5'b10101 : _zz_registerDataJ = registerFile_21;
      5'b10110 : _zz_registerDataJ = registerFile_22;
      5'b10111 : _zz_registerDataJ = registerFile_23;
      5'b11000 : _zz_registerDataJ = registerFile_24;
      5'b11001 : _zz_registerDataJ = registerFile_25;
      5'b11010 : _zz_registerDataJ = registerFile_26;
      5'b11011 : _zz_registerDataJ = registerFile_27;
      5'b11100 : _zz_registerDataJ = registerFile_28;
      5'b11101 : _zz_registerDataJ = registerFile_29;
      5'b11110 : _zz_registerDataJ = registerFile_30;
      default : _zz_registerDataJ = registerFile_31;
    endcase
  end

  always @(*) begin
    case(readAddressKOrD)
      5'b00000 : _zz_registerDataKOrD = registerFile_0;
      5'b00001 : _zz_registerDataKOrD = registerFile_1;
      5'b00010 : _zz_registerDataKOrD = registerFile_2;
      5'b00011 : _zz_registerDataKOrD = registerFile_3;
      5'b00100 : _zz_registerDataKOrD = registerFile_4;
      5'b00101 : _zz_registerDataKOrD = registerFile_5;
      5'b00110 : _zz_registerDataKOrD = registerFile_6;
      5'b00111 : _zz_registerDataKOrD = registerFile_7;
      5'b01000 : _zz_registerDataKOrD = registerFile_8;
      5'b01001 : _zz_registerDataKOrD = registerFile_9;
      5'b01010 : _zz_registerDataKOrD = registerFile_10;
      5'b01011 : _zz_registerDataKOrD = registerFile_11;
      5'b01100 : _zz_registerDataKOrD = registerFile_12;
      5'b01101 : _zz_registerDataKOrD = registerFile_13;
      5'b01110 : _zz_registerDataKOrD = registerFile_14;
      5'b01111 : _zz_registerDataKOrD = registerFile_15;
      5'b10000 : _zz_registerDataKOrD = registerFile_16;
      5'b10001 : _zz_registerDataKOrD = registerFile_17;
      5'b10010 : _zz_registerDataKOrD = registerFile_18;
      5'b10011 : _zz_registerDataKOrD = registerFile_19;
      5'b10100 : _zz_registerDataKOrD = registerFile_20;
      5'b10101 : _zz_registerDataKOrD = registerFile_21;
      5'b10110 : _zz_registerDataKOrD = registerFile_22;
      5'b10111 : _zz_registerDataKOrD = registerFile_23;
      5'b11000 : _zz_registerDataKOrD = registerFile_24;
      5'b11001 : _zz_registerDataKOrD = registerFile_25;
      5'b11010 : _zz_registerDataKOrD = registerFile_26;
      5'b11011 : _zz_registerDataKOrD = registerFile_27;
      5'b11100 : _zz_registerDataKOrD = registerFile_28;
      5'b11101 : _zz_registerDataKOrD = registerFile_29;
      5'b11110 : _zz_registerDataKOrD = registerFile_30;
      default : _zz_registerDataKOrD = registerFile_31;
    endcase
  end

  assign _zz_1 = ({31'd0,1'b1} <<< io_registerWrite_destination);
  assign op31To26 = fetch_instruction[31 : 26];
  assign op25To22 = fetch_instruction[25 : 22];
  assign op21To20 = fetch_instruction[21 : 20];
  assign op19To15 = fetch_instruction[19 : 15];
  assign rd = fetch_instruction[4 : 0];
  assign rj = fetch_instruction[9 : 5];
  assign rk = fetch_instruction[14 : 10];
  assign i12 = fetch_instruction[21 : 10];
  assign i14 = fetch_instruction[23 : 10];
  assign i20 = fetch_instruction[24 : 5];
  assign i16 = fetch_instruction[25 : 10];
  assign i26 = {fetch_instruction[9 : 0],fetch_instruction[25 : 10]};
  assign csrIndex = fetch_instruction[23 : 10];
  assign instAddW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h0));
  assign instSubW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h02));
  assign instSlt = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h04));
  assign instSltu = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h05));
  assign instNor = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h08));
  assign instAnd = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h09));
  assign instOr = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h0a));
  assign instXor = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h0b));
  assign instOrn = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h0c));
  assign instAndn = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h0d));
  assign instSllW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h0e));
  assign instSrlW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h0f));
  assign instSraW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h10));
  assign instMulW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h18));
  assign instMulhW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h19));
  assign instMulhWu = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b01)) && (op19To15 == 5'h1a));
  assign instDivW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b10)) && (op19To15 == 5'h0));
  assign instModW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b10)) && (op19To15 == 5'h01));
  assign instDivWu = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b10)) && (op19To15 == 5'h02));
  assign instModWu = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b10)) && (op19To15 == 5'h03));
  assign instBreak = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b10)) && (op19To15 == 5'h14));
  assign instSyscall = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b10)) && (op19To15 == 5'h16));
  assign instSlliW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0001)) && (op21To20 == 2'b00)) && (op19To15 == 5'h01));
  assign instSrliW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0001)) && (op21To20 == 2'b00)) && (op19To15 == 5'h09));
  assign instSraiW = ((((op31To26 == 6'h0) && (op25To22 == 4'b0001)) && (op21To20 == 2'b00)) && (op19To15 == 5'h11));
  assign instIdle = ((((op31To26 == 6'h01) && (op25To22 == 4'b1001)) && (op21To20 == 2'b00)) && (op19To15 == 5'h11));
  assign instInvTlb = ((((op31To26 == 6'h01) && (op25To22 == 4'b1001)) && (op21To20 == 2'b00)) && (op19To15 == 5'h13));
  assign instDbar = ((((op31To26 == 6'h0e) && (op25To22 == 4'b0001)) && (op21To20 == 2'b11)) && (op19To15 == 5'h04));
  assign instIbar = ((((op31To26 == 6'h0e) && (op25To22 == 4'b0001)) && (op21To20 == 2'b11)) && (op19To15 == 5'h05));
  assign instSlti = ((op31To26 == 6'h0) && (op25To22 == 4'b1000));
  assign instSltui = ((op31To26 == 6'h0) && (op25To22 == 4'b1001));
  assign instAddiW = ((op31To26 == 6'h0) && (op25To22 == 4'b1010));
  assign instAndi = ((op31To26 == 6'h0) && (op25To22 == 4'b1101));
  assign instOri = ((op31To26 == 6'h0) && (op25To22 == 4'b1110));
  assign instXori = ((op31To26 == 6'h0) && (op25To22 == 4'b1111));
  assign instLdB = ((op31To26 == 6'h0a) && (op25To22 == 4'b0000));
  assign instLdH = ((op31To26 == 6'h0a) && (op25To22 == 4'b0001));
  assign instLdW = ((op31To26 == 6'h0a) && (op25To22 == 4'b0010));
  assign instStB = ((op31To26 == 6'h0a) && (op25To22 == 4'b0100));
  assign instStH = ((op31To26 == 6'h0a) && (op25To22 == 4'b0101));
  assign instStW = ((op31To26 == 6'h0a) && (op25To22 == 4'b0110));
  assign instLdBu = ((op31To26 == 6'h0a) && (op25To22 == 4'b1000));
  assign instLdHu = ((op31To26 == 6'h0a) && (op25To22 == 4'b1001));
  assign instCacop = ((op31To26 == 6'h01) && (op25To22 == 4'b1000));
  assign instPreload = ((op31To26 == 6'h0a) && (op25To22 == 4'b1011));
  assign instJirl = (op31To26 == 6'h13);
  assign instB = (op31To26 == 6'h14);
  assign instBl = (op31To26 == 6'h15);
  assign instBeq = (op31To26 == 6'h16);
  assign instBne = (op31To26 == 6'h17);
  assign instBlt = (op31To26 == 6'h18);
  assign instBge = (op31To26 == 6'h19);
  assign instBltu = (op31To26 == 6'h1a);
  assign instBgeu = (op31To26 == 6'h1b);
  assign instLu12iW = ((op31To26 == 6'h05) && (! fetch_instruction[25]));
  assign instPcaddi = ((op31To26 == 6'h06) && (! fetch_instruction[25]));
  assign instPcaddu12i = ((op31To26 == 6'h07) && (! fetch_instruction[25]));
  assign baseCsr = (((op31To26 == 6'h01) && (! fetch_instruction[25])) && (! fetch_instruction[24]));
  assign instCsrXchg = ((baseCsr && (rj != 5'h0)) && (rj != 5'h01));
  assign instLlW = (((op31To26 == 6'h08) && (! fetch_instruction[25])) && (! fetch_instruction[24]));
  assign instScW = (((op31To26 == 6'h08) && (! fetch_instruction[25])) && fetch_instruction[24]);
  assign instCsrRead = (baseCsr && (rj == 5'h0));
  assign instCsrWrite = (baseCsr && (rj == 5'h01));
  assign counterBase = ((((op31To26 == 6'h0) && (op25To22 == 4'b0000)) && (op21To20 == 2'b00)) && (op19To15 == 5'h0));
  assign instRdCntIdW = ((counterBase && (rk == 5'h18)) && (rd == 5'h0));
  assign instRdCntVlW = (((counterBase && (rk == 5'h18)) && (rj == 5'h0)) && (rd != 5'h0));
  assign instRdCntVhW = ((counterBase && (rk == 5'h19)) && (rj == 5'h0));
  assign privilegedBase = ((((((op31To26 == 6'h01) && (op25To22 == 4'b1001)) && (op21To20 == 2'b00)) && (op19To15 == 5'h10)) && (rj == 5'h0)) && (rd == 5'h0));
  assign instErtn = (privilegedBase && (rk == 5'h0e));
  assign instTlbSearch = (privilegedBase && (rk == 5'h0a));
  assign instTlbRead = (privilegedBase && (rk == 5'h0b));
  assign instTlbWrite = (privilegedBase && (rk == 5'h0c));
  assign instTlbFill = (privilegedBase && (rk == 5'h0d));
  assign instCpuCfg = (counterBase && (rk == 5'h1b));
  assign destination = (instBl ? 5'h01 : (instRdCntIdW ? rj : rd));
  assign validCacop = ((instCacop && ((destination[2 : 0] == 3'b000) || (destination[2 : 0] == 3'b001))) && (destination[4 : 3] != 2'b11));
  assign cacopNop = (instCacop && (((destination[2 : 0] != 3'b000) && (destination[2 : 0] != 3'b001)) || (destination[4 : 3] == 2'b11)));
  assign laccRequest = 1'b0;
  assign laccValid = 1'b0;
  always @(*) begin
    aluOperation = 14'h0;
    aluOperation[0] = ((((((((((((((((_zz_aluOperation || instLdB) || instLdH) || instLdW) || instStB) || instStH) || instStW) || instLdBu) || instLdHu) || instLlW) || instScW) || instJirl) || instBl) || instPcaddi) || instPcaddu12i) || validCacop) || instPreload);
    aluOperation[1] = instSubW;
    aluOperation[2] = (instSlt || instSlti);
    aluOperation[3] = (instSltu || instSltui);
    aluOperation[4] = (instAnd || instAndi);
    aluOperation[5] = instNor;
    aluOperation[6] = (instOr || instOri);
    aluOperation[7] = (instXor || instXori);
    aluOperation[8] = (instSllW || instSlliW);
    aluOperation[9] = (instSrlW || instSrliW);
    aluOperation[10] = (instSraW || instSraiW);
    aluOperation[11] = instLu12iW;
    aluOperation[12] = instAndn;
    aluOperation[13] = instOrn;
  end

  always @(*) begin
    mulDivOperation = {{{instModW,(instDivW || instDivWu)},(instMulhW || instMulhWu)},instMulW};
    mulDivOperation[3] = (instModW || instModWu);
  end

  assign mulDivSigned = (((instMulW || instMulhW) || instDivW) || instModW);
  assign needUi5 = ((instSlliW || instSrliW) || instSraiW);
  assign needSi12 = ((((((((((((instAddiW || instLdB) || instLdH) || instLdW) || instStB) || instStH) || instStW) || instLdBu) || instLdHu) || instSlti) || instSltui) || validCacop) || instPreload);
  assign needUi12 = (((instAndi || instOri) || instXori) || laccRequest);
  assign needSi14Pc = (instLlW || instScW);
  assign needSi16Pc = ((((((instJirl || instBeq) || instBne) || instBlt) || instBge) || instBltu) || instBgeu);
  assign needSi20 = (instLu12iW || instPcaddu12i);
  assign needSi26Pc = (instB || instBl);
  always @(*) begin
    immediate = 32'h0;
    if(needUi5) begin
      immediate = {27'd0, _zz_immediate};
    end
    if(needSi12) begin
      immediate = _zz_immediate_1;
    end
    if(needUi12) begin
      immediate = {20'd0, i12};
    end
    if(needSi14Pc) begin
      immediate = _zz_immediate_3;
    end
    if(needSi16Pc) begin
      immediate = _zz_immediate_5;
    end
    if(needSi20) begin
      immediate = {i20,12'h0};
    end
    if(instPcaddi) begin
      immediate = _zz_immediate_7;
    end
    if(needSi26Pc) begin
      immediate = _zz_immediate_9;
    end
  end

  assign sourceRegisterIsRd = (((((((((((instBeq || instBne) || instBlt) || instBltu) || instBge) || instBgeu) || instStB) || instStH) || instStW) || instScW) || instCsrWrite) || instCsrXchg);
  assign source1IsPc = (((instJirl || instBl) || instPcaddi) || instPcaddu12i);
  assign source2IsImmediate = ((((((((((((((((_zz_source2IsImmediate || instXori) || instPcaddi) || instPcaddu12i) || instLdB) || instLdH) || instLdW) || instLdBu) || instLdHu) || instStB) || instStH) || instStW) || instLlW) || instScW) || instLu12iW) || validCacop) || instPreload);
  assign source2IsFour = (instJirl || instBl);
  assign loadOperation = (((((instLdB || instLdH) || instLdW) || instLdBu) || instLdHu) || instLlW);
  assign byteMemory = ((instLdB || instLdBu) || instStB);
  assign halfMemory = ((instLdH || instLdHu) || instStH);
  assign memorySignExtend = (instLdB || instLdH);
  assign gprWrite = (! (((((((((((((((_zz_gprWrite || instBge) || instBltu) || instBgeu) || instB) || instSyscall) || instTlbSearch) || instTlbRead) || instTlbWrite) || instTlbFill) || instInvTlb) || validCacop) || instPreload) || instDbar) || instIbar) || cacopNop));
  assign storeOperation = (((instStB || instStH) || instStW) || (instScW && io_reservationValid));
  assign needRj = ((((((((((((((((_zz_needRj || instJirl) || instLdB) || instLdBu) || instLdH) || instLdHu) || instLdW) || instStB) || instStH) || instStW) || instPreload) || instLlW) || instScW) || instCsrXchg) || validCacop) || laccRequest) || instInvTlb);
  assign needRkd = ((((((((((((((((_zz_needRkd || instSrlW) || instSraW) || instBeq) || instBne) || instBlt) || instBltu) || instBge) || instBgeu) || instStB) || instStH) || instStW) || instScW) || instCsrWrite) || instCsrXchg) || laccRequest) || instInvTlb);
  assign readAddressJ = (io_debugReadSelect ? io_debugReadAddress : rj);
  assign readAddressKOrD = (sourceRegisterIsRd ? rd : rk);
  assign registerDataJ = ((readAddressJ == 5'h0) ? 32'h0 : ((io_registerWrite_valid && (readAddressJ == io_registerWrite_destination)) ? io_registerWrite_data : _zz_registerDataJ));
  assign registerDataKOrD = ((readAddressKOrD == 5'h0) ? 32'h0 : ((io_registerWrite_valid && (readAddressKOrD == io_registerWrite_destination)) ? io_registerWrite_data : _zz_registerDataKOrD));
  assign branchNeedsRegisterData = ((((((instBeq || instBne) || instBlt) || instBge) || instBltu) || instBgeu) || instJirl);
  assign executeJHit = (((readAddressJ == io_executeForward_destination) && io_executeForward_valid) && needRj);
  assign memoryJHit = (((readAddressJ == io_memoryForward_destination) && io_memoryForward_valid) && needRj);
  assign executeKHit = (((readAddressKOrD == io_executeForward_destination) && io_executeForward_valid) && needRkd);
  assign memoryKHit = (((readAddressKOrD == io_memoryForward_destination) && io_memoryForward_valid) && needRkd);
  assign valueJ = (executeJHit ? io_executeForward_data : (memoryJHit ? io_memoryForward_data : registerDataJ));
  assign valueKOrD = (executeKHit ? io_executeForward_data : (memoryKHit ? io_memoryForward_data : registerDataKOrD));
  assign branchValueJ = (executeJHit ? io_executeForward_data : registerDataJ);
  assign branchValueKOrD = (executeKHit ? io_executeForward_data : registerDataKOrD);
  assign stallJ = (executeJHit ? io_executeForward_dependencyNeedsStall : (memoryJHit ? (io_memoryForward_dependencyNeedsStall || branchNeedsRegisterData) : 1'b0));
  assign stallK = (executeKHit ? io_executeForward_dependencyNeedsStall : (memoryKHit ? (io_memoryForward_dependencyNeedsStall || branchNeedsRegisterData) : 1'b0));
  assign equalOperands = (branchValueJ == branchValueKOrD);
  assign lessUnsigned = (branchValueJ < branchValueKOrD);
  assign lessSigned = ($signed(_zz_lessSigned) < $signed(_zz_lessSigned_1));
  assign branchTakenRaw = (((((((((instBeq && equalOperands) || (instBne && (! equalOperands))) || (instBlt && lessSigned)) || (instBge && (! lessSigned))) || (instBltu && lessUnsigned)) || (instBgeu && (! lessUnsigned))) || instJirl) || instBl) || instB);
  assign branchTaken = ((branchTakenRaw && occupied) && (! fetch_hasException));
  assign branchInstruction = ((branchNeedsRegisterData || instBl) || instB);
  assign predictableBranch = ((((((((instBeq || instBne) || instBlt) || instBge) || instBltu) || instBgeu) || instBl) || instB) || instJirl);
  assign pcRelativeBranch = (((((((instBeq || instBne) || instBl) || instB) || instBlt) || instBge) || instBltu) || instBgeu);
  assign branchTarget = (instJirl ? _zz_branchTarget : (pcRelativeBranch ? _zz_branchTarget_1 : 32'h0));
  assign instructionValid = (((((((((((((_zz_instructionValid || instErtn) || validCacop) || instPreload) || instDbar) || instIbar) || instTlbSearch) || instTlbRead) || instTlbWrite) || instTlbFill) || cacopNop) || instCpuCfg) || (laccRequest && laccValid)) || (instInvTlb && (rd <= 5'h06)));
  assign illegalInstruction = (! instructionValid);
  assign kernelInstruction = ((((((((((instCsrRead || instCsrWrite) || instCsrXchg) || (validCacop && (destination[4 : 3] != 2'b10))) || instTlbSearch) || instTlbRead) || instTlbWrite) || instTlbFill) || instInvTlb) || instErtn) || instIdle);
  assign privilegeException = (kernelInstruction && (io_csrPrivilege == 2'b11));
  assign hasException = (((((privilegeException || instSyscall) || instBreak) || fetch_hasException) || illegalInstruction) || io_interruptPending);
  assign exceptionCode = {{{{{privilegeException,illegalInstruction},instBreak},instSyscall},fetch_exceptionCode},io_interruptPending};
  assign refetch = (((((instTlbWrite || instTlbFill) || instTlbRead) || instInvTlb) || instIbar) && occupied);
  assign pipelineNotEmpty = ((((io_executeOccupied || io_memoryOccupied) || io_writebackOccupied) || (! io_writeBufferEmpty)) || (! io_dataCacheEmpty));
  assign barrierStall = ((instDbar || instIbar) && pipelineNotEmpty);
  assign tlbStall = ((io_executeTlbStall || io_memoryTlbStall) || io_writebackTlbStall);
  assign readyGo = ((! (((stallJ || stallK) || tlbStall) || barrierStall)) || hasException);
  assign btbAddEntry = ((predictableBranch && (! fetch_btbEnabled)) && branchTaken);
  assign btbDeleteEntry = ((! predictableBranch) && fetch_btbEnabled);
  assign btbPredictionError = ((predictableBranch && fetch_btbEnabled) && (fetch_btbTaken ^ branchTaken));
  assign btbTargetError = ((((predictableBranch && fetch_btbEnabled) && fetch_btbTaken) && branchTaken) && (fetch_btbTarget != branchTarget));
  assign btbRepair = ((((((btbAddEntry || btbDeleteEntry) || btbPredictionError) || btbTargetError) && occupied) && readyGo) && (! fetch_hasException));
  assign btbRepairTarget = (branchTaken ? branchTarget : _zz_btbRepairTarget);
  assign io_input_ready = ((! occupied) || (readyGo && io_output_ready));
  assign io_output_valid = (occupied && readyGo);
  assign when_DecodeStage_l633 = ((((io_flush_exception || io_flush_ertn) || io_flush_refetch) || io_flush_instructionCacheOperation) || io_flush_idle);
  assign when_DecodeStage_l636 = ((btbRepair && io_output_ready) || branchSlotCancel);
  assign when_DecodeStage_l642 = (io_input_valid && io_input_ready);
  assign when_DecodeStage_l646 = ((((io_flush_exception || io_flush_ertn) || io_flush_refetch) || io_flush_instructionCacheOperation) || io_flush_idle);
  assign when_DecodeStage_l648 = ((btbRepair && io_output_ready) && (! io_input_valid));
  assign when_DecodeStage_l650 = (branchSlotCancel && io_input_valid);
  assign counterEnabled = ((instRdCntVlW || instRdCntVhW) || instRdCntIdW);
  assign counterResult = (instRdCntVlW ? io_timer[31 : 0] : (instRdCntVhW ? io_timer[63 : 32] : io_timerId));
  assign csrData = (counterEnabled ? counterResult : (instScW ? {31'h0,io_reservationValid} : io_csrReadData));
  assign io_output_payload_pc = fetch_pc;
  assign io_output_payload_registerDataKOrD = valueKOrD;
  assign io_output_payload_registerDataJ = valueJ;
  assign io_output_payload_immediate = immediate;
  assign io_output_payload_destination = destination;
  assign io_output_payload_isStore = storeOperation;
  assign io_output_payload_gprWrite = gprWrite;
  assign io_output_payload_source2IsFour = source2IsFour;
  assign io_output_payload_source2IsImmediate = source2IsImmediate;
  assign io_output_payload_source1IsPc = source1IsPc;
  assign io_output_payload_isLoad = loadOperation;
  assign io_output_payload_aluOperation = aluOperation;
  assign io_output_payload_mulDivSigned = mulDivSigned;
  assign io_output_payload_mulDivOperation = mulDivOperation;
  assign io_output_payload_memorySize = {halfMemory,byteMemory};
  assign io_output_payload_hasException = hasException;
  assign io_output_payload_isErtn = instErtn;
  assign io_output_payload_csrReadData = csrData;
  assign io_output_payload_resultFromCsr = (((((((instCsrRead || instCsrWrite) || instCsrXchg) || instRdCntIdW) || instRdCntVhW) || instRdCntVlW) || instScW) || instCpuCfg);
  assign io_output_payload_csrAddress = csrIndex;
  assign io_output_payload_csrWrite = (instCsrWrite || instCsrXchg);
  assign io_output_payload_csrMask = instCsrXchg;
  assign io_output_payload_exceptionCode = exceptionCode;
  assign io_output_payload_isLl = instLlW;
  assign io_output_payload_isSc = instScW;
  assign io_output_payload_tlbSearch = instTlbSearch;
  assign io_output_payload_tlbWrite = instTlbWrite;
  assign io_output_payload_tlbFill = instTlbFill;
  assign io_output_payload_refetch = refetch;
  assign io_output_payload_tlbRead = instTlbRead;
  assign io_output_payload_invalidateTlb = instInvTlb;
  assign io_output_payload_memorySignExtend = memorySignExtend;
  assign io_output_payload_cacheOperation = validCacop;
  assign io_output_payload_preload = instPreload;
  assign io_output_payload_isBranch = branchInstruction;
  assign io_output_payload_instructionCacheMiss = fetch_instructionCacheMiss;
  assign io_output_payload_isPredictableBranch = predictableBranch;
  assign io_output_payload_predictionError = btbRepair;
  assign io_output_payload_idle = instIdle;
  assign io_output_payload_instruction = fetch_instruction;
  assign io_output_payload_timer = io_timer;
  assign io_output_payload_isCounterInstruction = counterEnabled;
  assign io_output_payload_loadEvent = {{{{{{2'b00,instLlW},instLdW},instLdHu},instLdH},instLdBu},instLdB};
  assign io_output_payload_storeEvent = {{{{4'b0000,(io_reservationValid && instScW)},instStW},instStH},instStB};
  assign io_output_payload_csrRstatEvent = (((instCsrRead || instCsrWrite) || instCsrXchg) && (csrIndex == 14'h0005));
  assign io_csrReadAddress = (instCpuCfg ? _zz_io_csrReadAddress : csrIndex);
  assign io_debugLegacyValue = {27'd0, _zz_io_debugLegacyValue};
  assign io_branchRepair_active = btbRepair;
  assign io_branchRepair_target = btbRepairTarget;
  assign io_btb_enable = (((occupied && readyGo) && io_output_ready) && (! fetch_hasException));
  assign io_btb_popReturnStack = instJirl;
  assign io_btb_pushReturnStack = instBl;
  assign io_btb_addEntry = btbAddEntry;
  assign io_btb_deleteEntry = btbDeleteEntry;
  assign io_btb_predictionError = btbPredictionError;
  assign io_btb_predictionRight = ((predictableBranch && fetch_btbEnabled) && (! (fetch_btbTaken ^ branchTaken)));
  assign io_btb_targetError = btbTargetError;
  assign io_btb_actualTaken = branchTaken;
  assign io_btb_actualTarget = branchTarget;
  assign io_btb_pc = fetch_pc;
  assign io_btb_index = fetch_btbIndex;
  always @(posedge clk) begin
    if(reset) begin
      occupied <= 1'b0;
      branchSlotCancel <= 1'b0;
    end else begin
      if(when_DecodeStage_l633) begin
        occupied <= 1'b0;
      end else begin
        if(io_input_ready) begin
          if(when_DecodeStage_l636) begin
            occupied <= 1'b0;
          end else begin
            occupied <= io_input_valid;
          end
        end
      end
      if(when_DecodeStage_l646) begin
        branchSlotCancel <= 1'b0;
      end else begin
        if(when_DecodeStage_l648) begin
          branchSlotCancel <= 1'b1;
        end else begin
          if(when_DecodeStage_l650) begin
            branchSlotCancel <= 1'b0;
          end
        end
      end
    end
  end

  always @(posedge clk) begin
    if(io_registerWrite_valid) begin
      if(_zz_1[0]) begin
        registerFile_0 <= io_registerWrite_data;
      end
      if(_zz_1[1]) begin
        registerFile_1 <= io_registerWrite_data;
      end
      if(_zz_1[2]) begin
        registerFile_2 <= io_registerWrite_data;
      end
      if(_zz_1[3]) begin
        registerFile_3 <= io_registerWrite_data;
      end
      if(_zz_1[4]) begin
        registerFile_4 <= io_registerWrite_data;
      end
      if(_zz_1[5]) begin
        registerFile_5 <= io_registerWrite_data;
      end
      if(_zz_1[6]) begin
        registerFile_6 <= io_registerWrite_data;
      end
      if(_zz_1[7]) begin
        registerFile_7 <= io_registerWrite_data;
      end
      if(_zz_1[8]) begin
        registerFile_8 <= io_registerWrite_data;
      end
      if(_zz_1[9]) begin
        registerFile_9 <= io_registerWrite_data;
      end
      if(_zz_1[10]) begin
        registerFile_10 <= io_registerWrite_data;
      end
      if(_zz_1[11]) begin
        registerFile_11 <= io_registerWrite_data;
      end
      if(_zz_1[12]) begin
        registerFile_12 <= io_registerWrite_data;
      end
      if(_zz_1[13]) begin
        registerFile_13 <= io_registerWrite_data;
      end
      if(_zz_1[14]) begin
        registerFile_14 <= io_registerWrite_data;
      end
      if(_zz_1[15]) begin
        registerFile_15 <= io_registerWrite_data;
      end
      if(_zz_1[16]) begin
        registerFile_16 <= io_registerWrite_data;
      end
      if(_zz_1[17]) begin
        registerFile_17 <= io_registerWrite_data;
      end
      if(_zz_1[18]) begin
        registerFile_18 <= io_registerWrite_data;
      end
      if(_zz_1[19]) begin
        registerFile_19 <= io_registerWrite_data;
      end
      if(_zz_1[20]) begin
        registerFile_20 <= io_registerWrite_data;
      end
      if(_zz_1[21]) begin
        registerFile_21 <= io_registerWrite_data;
      end
      if(_zz_1[22]) begin
        registerFile_22 <= io_registerWrite_data;
      end
      if(_zz_1[23]) begin
        registerFile_23 <= io_registerWrite_data;
      end
      if(_zz_1[24]) begin
        registerFile_24 <= io_registerWrite_data;
      end
      if(_zz_1[25]) begin
        registerFile_25 <= io_registerWrite_data;
      end
      if(_zz_1[26]) begin
        registerFile_26 <= io_registerWrite_data;
      end
      if(_zz_1[27]) begin
        registerFile_27 <= io_registerWrite_data;
      end
      if(_zz_1[28]) begin
        registerFile_28 <= io_registerWrite_data;
      end
      if(_zz_1[29]) begin
        registerFile_29 <= io_registerWrite_data;
      end
      if(_zz_1[30]) begin
        registerFile_30 <= io_registerWrite_data;
      end
      if(_zz_1[31]) begin
        registerFile_31 <= io_registerWrite_data;
      end
    end
    if(when_DecodeStage_l642) begin
      fetch_pc <= io_input_payload_pc;
      fetch_instruction <= io_input_payload_instruction;
      fetch_exceptionCode <= io_input_payload_exceptionCode;
      fetch_hasException <= io_input_payload_hasException;
      fetch_instructionCacheMiss <= io_input_payload_instructionCacheMiss;
      fetch_btbEnabled <= io_input_payload_btbEnabled;
      fetch_btbTaken <= io_input_payload_btbTaken;
      fetch_btbIndex <= io_input_payload_btbIndex;
      fetch_btbTarget <= io_input_payload_btbTarget;
    end
  end


endmodule
