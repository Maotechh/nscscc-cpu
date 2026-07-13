// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : wb_stage



module wb_stage (
  input  wire          clk,
  input  wire          reset,
  output wire          ws_allowin,
  input  wire          ms_to_ws_valid,
  input  wire [492:0]  ms_to_ws_bus,
  output wire [37:0]   ws_to_rf_bus,
  output wire          ws_to_ds_valid,
  output wire [31:0]   csr_era,
  output wire [8:0]    csr_esubcode,
  output wire [5:0]    csr_ecode,
  output wire          excp_flush,
  output wire          ertn_flush,
  output wire          refetch_flush,
  output wire          icacop_flush,
  output wire          csr_wr_en,
  output wire [13:0]   wr_csr_addr,
  output wire [31:0]   wr_csr_data,
  output wire          va_error,
  output wire [31:0]   bad_va,
  output wire          excp_tlbrefill,
  output wire          excp_tlb,
  output wire [18:0]   excp_tlb_vppn,
  output wire          idle_flush,
  output wire          ws_llbit_set,
  output wire          ws_llbit,
  output wire          ws_lladdr_set,
  output wire [27:0]   ws_lladdr,
  output wire          tlb_inst_stall,
  output wire          tlbsrch_en,
  output wire          tlbsrch_found,
  output wire [4:0]    tlbsrch_index,
  output wire          tlbfill_en,
  output wire          tlbwr_en,
  output wire          tlbrd_en,
  output wire          invtlb_en,
  output wire [9:0]    invtlb_asid,
  output wire [18:0]   invtlb_vpn,
  output wire [4:0]    invtlb_op,
  output wire          real_valid,
  output wire          real_br_inst,
  output wire          real_icache_miss,
  output wire          real_dcache_miss,
  output wire          real_mem_inst,
  output wire          real_br_pre,
  output wire          real_br_pre_error,
  output wire          debug_ws_valid,
  input  wire          debug_break_point,
  output wire [31:0]   debug_wb_pc,
  output wire [3:0]    debug_wb_rf_wen,
  output wire [4:0]    debug_wb_rf_wnum,
  output wire [31:0]   debug_wb_rf_wdata,
  output wire [31:0]   debug_wb_inst,
  output wire          ws_valid_diff,
  output wire          ws_cnt_inst_diff,
  output wire [63:0]   ws_timer_64_diff,
  output wire [7:0]    ws_inst_ld_en_diff,
  output wire [31:0]   ws_ld_paddr_diff,
  output wire [31:0]   ws_ld_vaddr_diff,
  output wire [7:0]    ws_inst_st_en_diff,
  output wire [31:0]   ws_st_paddr_diff,
  output wire [31:0]   ws_st_vaddr_diff,
  output wire [31:0]   ws_st_data_diff,
  output wire          ws_csr_rstat_en_diff,
  output wire [31:0]   ws_csr_data_diff
);

  wire                area_stage_io_input_ready;
  wire                area_stage_io_stageValid;
  wire                area_stage_io_realValid;
  wire                area_stage_io_registerWrite_valid;
  wire       [4:0]    area_stage_io_registerWrite_index;
  wire       [31:0]   area_stage_io_registerWrite_data;
  wire                area_stage_io_csrWrite_valid;
  wire       [13:0]   area_stage_io_csrWrite_address;
  wire       [31:0]   area_stage_io_csrWrite_data;
  wire                area_stage_io_flush_exception;
  wire                area_stage_io_flush_ertn;
  wire                area_stage_io_flush_refetch;
  wire                area_stage_io_flush_instructionCacheOperation;
  wire                area_stage_io_flush_idle;
  wire                area_stage_io_exception_valid;
  wire       [5:0]    area_stage_io_exception_ecode;
  wire       [8:0]    area_stage_io_exception_esubcode;
  wire                area_stage_io_exception_badVAddrValid;
  wire       [31:0]   area_stage_io_exception_badVAddr;
  wire                area_stage_io_exception_tlbRefill;
  wire                area_stage_io_exception_tlbException;
  wire       [18:0]   area_stage_io_exception_tlbVppn;
  wire                area_stage_io_tlb_instructionStall;
  wire                area_stage_io_tlb_search;
  wire                area_stage_io_tlb_searchFound;
  wire       [4:0]    area_stage_io_tlb_searchIndex;
  wire                area_stage_io_tlb_fill;
  wire                area_stage_io_tlb_write;
  wire                area_stage_io_tlb_read;
  wire                area_stage_io_tlb_invalidate;
  wire       [9:0]    area_stage_io_tlb_invalidateAsid;
  wire       [18:0]   area_stage_io_tlb_invalidateVpn;
  wire       [4:0]    area_stage_io_tlb_invalidateOperation;
  wire                area_stage_io_reservation_bitSet;
  wire                area_stage_io_reservation_bitValue;
  wire                area_stage_io_reservation_addressSet;
  wire       [27:0]   area_stage_io_reservation_lineAddress;
  wire                area_stage_io_perf_retired;
  wire                area_stage_io_perf_branch;
  wire                area_stage_io_perf_instructionCacheMiss;
  wire                area_stage_io_perf_dataCacheMiss;
  wire                area_stage_io_perf_memoryAccess;
  wire                area_stage_io_perf_predictedBranch;
  wire                area_stage_io_perf_predictionError;
  wire                area_stage_io_debug_stageValid;
  wire       [31:0]   area_stage_io_debug_pc;
  wire       [3:0]    area_stage_io_debug_gprWriteMask;
  wire       [4:0]    area_stage_io_debug_gprIndex;
  wire       [31:0]   area_stage_io_debug_gprData;
  wire       [31:0]   area_stage_io_debug_instruction;
  wire                area_stage_io_observation_isCounterInstruction;
  wire       [63:0]   area_stage_io_observation_timer;
  wire       [7:0]    area_stage_io_observation_loadEvent;
  wire       [31:0]   area_stage_io_observation_memoryPhysicalAddress;
  wire       [31:0]   area_stage_io_observation_memoryVirtualAddress;
  wire       [7:0]    area_stage_io_observation_storeEvent;
  wire       [31:0]   area_stage_io_observation_storeData;
  wire                area_stage_io_observation_csrRstatEvent;
  wire       [31:0]   area_stage_io_observation_csrData;
  wire       [31:0]   memoryPayload_pc;
  wire       [31:0]   memoryPayload_finalResult;
  wire       [4:0]    memoryPayload_destination;
  wire                memoryPayload_gprWrite;
  wire                memoryPayload_hasException;
  wire                memoryPayload_isErtn;
  wire       [31:0]   memoryPayload_csrResult;
  wire       [13:0]   memoryPayload_csrAddress;
  wire                memoryPayload_csrWrite;
  wire       [15:0]   memoryPayload_exceptionCode;
  wire                memoryPayload_isLl;
  wire                memoryPayload_isSc;
  wire       [31:0]   memoryPayload_errorVirtualAddress;
  wire                memoryPayload_tlbSearch;
  wire                memoryPayload_tlbFound;
  wire       [4:0]    memoryPayload_tlbIndex;
  wire                memoryPayload_tlbWrite;
  wire                memoryPayload_tlbFill;
  wire                memoryPayload_refetch;
  wire                memoryPayload_tlbRead;
  wire                memoryPayload_invalidateTlb;
  wire       [9:0]    memoryPayload_invalidateTlbAsid;
  wire       [18:0]   memoryPayload_invalidateTlbVpn;
  wire                memoryPayload_instructionCacheOperation;
  wire                memoryPayload_isBranch;
  wire                memoryPayload_instructionCacheMiss;
  wire                memoryPayload_accessesMemory;
  wire                memoryPayload_dataCacheMiss;
  wire                memoryPayload_isPredictableBranch;
  wire                memoryPayload_predictionError;
  wire                memoryPayload_idle;
  wire       [31:0]   memoryPayload_physicalAddress;
  wire                memoryPayload_dataUncached;
  wire       [31:0]   memoryPayload_instruction;
  wire       [63:0]   memoryPayload_timer;
  wire                memoryPayload_isCounterInstruction;
  wire       [7:0]    memoryPayload_loadEvent;
  wire       [31:0]   memoryPayload_memoryPhysicalAddress;
  wire       [31:0]   memoryPayload_memoryVirtualAddress;
  wire       [7:0]    memoryPayload_storeEvent;
  wire       [31:0]   memoryPayload_storeData;
  wire                memoryPayload_csrRstatEvent;
  wire       [31:0]   memoryPayload_csrData;

  WritebackStage area_stage (
    .io_input_valid                             (ms_to_ws_valid                                       ), //i
    .io_input_ready                             (area_stage_io_input_ready                            ), //o
    .io_input_payload_pc                        (memoryPayload_pc[31:0]                               ), //i
    .io_input_payload_finalResult               (memoryPayload_finalResult[31:0]                      ), //i
    .io_input_payload_destination               (memoryPayload_destination[4:0]                       ), //i
    .io_input_payload_gprWrite                  (memoryPayload_gprWrite                               ), //i
    .io_input_payload_hasException              (memoryPayload_hasException                           ), //i
    .io_input_payload_isErtn                    (memoryPayload_isErtn                                 ), //i
    .io_input_payload_csrResult                 (memoryPayload_csrResult[31:0]                        ), //i
    .io_input_payload_csrAddress                (memoryPayload_csrAddress[13:0]                       ), //i
    .io_input_payload_csrWrite                  (memoryPayload_csrWrite                               ), //i
    .io_input_payload_exceptionCode             (memoryPayload_exceptionCode[15:0]                    ), //i
    .io_input_payload_isLl                      (memoryPayload_isLl                                   ), //i
    .io_input_payload_isSc                      (memoryPayload_isSc                                   ), //i
    .io_input_payload_errorVirtualAddress       (memoryPayload_errorVirtualAddress[31:0]              ), //i
    .io_input_payload_tlbSearch                 (memoryPayload_tlbSearch                              ), //i
    .io_input_payload_tlbFound                  (memoryPayload_tlbFound                               ), //i
    .io_input_payload_tlbIndex                  (memoryPayload_tlbIndex[4:0]                          ), //i
    .io_input_payload_tlbWrite                  (memoryPayload_tlbWrite                               ), //i
    .io_input_payload_tlbFill                   (memoryPayload_tlbFill                                ), //i
    .io_input_payload_refetch                   (memoryPayload_refetch                                ), //i
    .io_input_payload_tlbRead                   (memoryPayload_tlbRead                                ), //i
    .io_input_payload_invalidateTlb             (memoryPayload_invalidateTlb                          ), //i
    .io_input_payload_invalidateTlbAsid         (memoryPayload_invalidateTlbAsid[9:0]                 ), //i
    .io_input_payload_invalidateTlbVpn          (memoryPayload_invalidateTlbVpn[18:0]                 ), //i
    .io_input_payload_instructionCacheOperation (memoryPayload_instructionCacheOperation              ), //i
    .io_input_payload_isBranch                  (memoryPayload_isBranch                               ), //i
    .io_input_payload_instructionCacheMiss      (memoryPayload_instructionCacheMiss                   ), //i
    .io_input_payload_accessesMemory            (memoryPayload_accessesMemory                         ), //i
    .io_input_payload_dataCacheMiss             (memoryPayload_dataCacheMiss                          ), //i
    .io_input_payload_isPredictableBranch       (memoryPayload_isPredictableBranch                    ), //i
    .io_input_payload_predictionError           (memoryPayload_predictionError                        ), //i
    .io_input_payload_idle                      (memoryPayload_idle                                   ), //i
    .io_input_payload_physicalAddress           (memoryPayload_physicalAddress[31:0]                  ), //i
    .io_input_payload_dataUncached              (memoryPayload_dataUncached                           ), //i
    .io_input_payload_instruction               (memoryPayload_instruction[31:0]                      ), //i
    .io_input_payload_timer                     (memoryPayload_timer[63:0]                            ), //i
    .io_input_payload_isCounterInstruction      (memoryPayload_isCounterInstruction                   ), //i
    .io_input_payload_loadEvent                 (memoryPayload_loadEvent[7:0]                         ), //i
    .io_input_payload_memoryPhysicalAddress     (memoryPayload_memoryPhysicalAddress[31:0]            ), //i
    .io_input_payload_memoryVirtualAddress      (memoryPayload_memoryVirtualAddress[31:0]             ), //i
    .io_input_payload_storeEvent                (memoryPayload_storeEvent[7:0]                        ), //i
    .io_input_payload_storeData                 (memoryPayload_storeData[31:0]                        ), //i
    .io_input_payload_csrRstatEvent             (memoryPayload_csrRstatEvent                          ), //i
    .io_input_payload_csrData                   (memoryPayload_csrData[31:0]                          ), //i
    .io_debugBreakPoint                         (debug_break_point                                    ), //i
    .io_stageValid                              (area_stage_io_stageValid                             ), //o
    .io_realValid                               (area_stage_io_realValid                              ), //o
    .io_registerWrite_valid                     (area_stage_io_registerWrite_valid                    ), //o
    .io_registerWrite_index                     (area_stage_io_registerWrite_index[4:0]               ), //o
    .io_registerWrite_data                      (area_stage_io_registerWrite_data[31:0]               ), //o
    .io_csrWrite_valid                          (area_stage_io_csrWrite_valid                         ), //o
    .io_csrWrite_address                        (area_stage_io_csrWrite_address[13:0]                 ), //o
    .io_csrWrite_data                           (area_stage_io_csrWrite_data[31:0]                    ), //o
    .io_flush_exception                         (area_stage_io_flush_exception                        ), //o
    .io_flush_ertn                              (area_stage_io_flush_ertn                             ), //o
    .io_flush_refetch                           (area_stage_io_flush_refetch                          ), //o
    .io_flush_instructionCacheOperation         (area_stage_io_flush_instructionCacheOperation        ), //o
    .io_flush_idle                              (area_stage_io_flush_idle                             ), //o
    .io_exception_valid                         (area_stage_io_exception_valid                        ), //o
    .io_exception_ecode                         (area_stage_io_exception_ecode[5:0]                   ), //o
    .io_exception_esubcode                      (area_stage_io_exception_esubcode[8:0]                ), //o
    .io_exception_badVAddrValid                 (area_stage_io_exception_badVAddrValid                ), //o
    .io_exception_badVAddr                      (area_stage_io_exception_badVAddr[31:0]               ), //o
    .io_exception_tlbRefill                     (area_stage_io_exception_tlbRefill                    ), //o
    .io_exception_tlbException                  (area_stage_io_exception_tlbException                 ), //o
    .io_exception_tlbVppn                       (area_stage_io_exception_tlbVppn[18:0]                ), //o
    .io_tlb_instructionStall                    (area_stage_io_tlb_instructionStall                   ), //o
    .io_tlb_search                              (area_stage_io_tlb_search                             ), //o
    .io_tlb_searchFound                         (area_stage_io_tlb_searchFound                        ), //o
    .io_tlb_searchIndex                         (area_stage_io_tlb_searchIndex[4:0]                   ), //o
    .io_tlb_fill                                (area_stage_io_tlb_fill                               ), //o
    .io_tlb_write                               (area_stage_io_tlb_write                              ), //o
    .io_tlb_read                                (area_stage_io_tlb_read                               ), //o
    .io_tlb_invalidate                          (area_stage_io_tlb_invalidate                         ), //o
    .io_tlb_invalidateAsid                      (area_stage_io_tlb_invalidateAsid[9:0]                ), //o
    .io_tlb_invalidateVpn                       (area_stage_io_tlb_invalidateVpn[18:0]                ), //o
    .io_tlb_invalidateOperation                 (area_stage_io_tlb_invalidateOperation[4:0]           ), //o
    .io_reservation_bitSet                      (area_stage_io_reservation_bitSet                     ), //o
    .io_reservation_bitValue                    (area_stage_io_reservation_bitValue                   ), //o
    .io_reservation_addressSet                  (area_stage_io_reservation_addressSet                 ), //o
    .io_reservation_lineAddress                 (area_stage_io_reservation_lineAddress[27:0]          ), //o
    .io_perf_retired                            (area_stage_io_perf_retired                           ), //o
    .io_perf_branch                             (area_stage_io_perf_branch                            ), //o
    .io_perf_instructionCacheMiss               (area_stage_io_perf_instructionCacheMiss              ), //o
    .io_perf_dataCacheMiss                      (area_stage_io_perf_dataCacheMiss                     ), //o
    .io_perf_memoryAccess                       (area_stage_io_perf_memoryAccess                      ), //o
    .io_perf_predictedBranch                    (area_stage_io_perf_predictedBranch                   ), //o
    .io_perf_predictionError                    (area_stage_io_perf_predictionError                   ), //o
    .io_debug_stageValid                        (area_stage_io_debug_stageValid                       ), //o
    .io_debug_pc                                (area_stage_io_debug_pc[31:0]                         ), //o
    .io_debug_gprWriteMask                      (area_stage_io_debug_gprWriteMask[3:0]                ), //o
    .io_debug_gprIndex                          (area_stage_io_debug_gprIndex[4:0]                    ), //o
    .io_debug_gprData                           (area_stage_io_debug_gprData[31:0]                    ), //o
    .io_debug_instruction                       (area_stage_io_debug_instruction[31:0]                ), //o
    .io_observation_isCounterInstruction        (area_stage_io_observation_isCounterInstruction       ), //o
    .io_observation_timer                       (area_stage_io_observation_timer[63:0]                ), //o
    .io_observation_loadEvent                   (area_stage_io_observation_loadEvent[7:0]             ), //o
    .io_observation_memoryPhysicalAddress       (area_stage_io_observation_memoryPhysicalAddress[31:0]), //o
    .io_observation_memoryVirtualAddress        (area_stage_io_observation_memoryVirtualAddress[31:0] ), //o
    .io_observation_storeEvent                  (area_stage_io_observation_storeEvent[7:0]            ), //o
    .io_observation_storeData                   (area_stage_io_observation_storeData[31:0]            ), //o
    .io_observation_csrRstatEvent               (area_stage_io_observation_csrRstatEvent              ), //o
    .io_observation_csrData                     (area_stage_io_observation_csrData[31:0]              ), //o
    .clk                                        (clk                                                  ), //i
    .reset                                      (reset                                                )  //i
  );
  assign memoryPayload_pc = ms_to_ws_bus[31 : 0];
  assign memoryPayload_finalResult = ms_to_ws_bus[63 : 32];
  assign memoryPayload_destination = ms_to_ws_bus[68 : 64];
  assign memoryPayload_gprWrite = ms_to_ws_bus[69];
  assign memoryPayload_hasException = ms_to_ws_bus[70];
  assign memoryPayload_isErtn = ms_to_ws_bus[71];
  assign memoryPayload_csrResult = ms_to_ws_bus[103 : 72];
  assign memoryPayload_csrAddress = ms_to_ws_bus[117 : 104];
  assign memoryPayload_csrWrite = ms_to_ws_bus[118];
  assign memoryPayload_exceptionCode = ms_to_ws_bus[134 : 119];
  assign memoryPayload_isLl = ms_to_ws_bus[135];
  assign memoryPayload_isSc = ms_to_ws_bus[136];
  assign memoryPayload_errorVirtualAddress = ms_to_ws_bus[168 : 137];
  assign memoryPayload_tlbSearch = ms_to_ws_bus[169];
  assign memoryPayload_tlbFound = ms_to_ws_bus[170];
  assign memoryPayload_tlbIndex = ms_to_ws_bus[175 : 171];
  assign memoryPayload_tlbWrite = ms_to_ws_bus[176];
  assign memoryPayload_tlbFill = ms_to_ws_bus[177];
  assign memoryPayload_refetch = ms_to_ws_bus[178];
  assign memoryPayload_tlbRead = ms_to_ws_bus[179];
  assign memoryPayload_invalidateTlb = ms_to_ws_bus[180];
  assign memoryPayload_invalidateTlbAsid = ms_to_ws_bus[190 : 181];
  assign memoryPayload_invalidateTlbVpn = ms_to_ws_bus[209 : 191];
  assign memoryPayload_instructionCacheOperation = ms_to_ws_bus[210];
  assign memoryPayload_isBranch = ms_to_ws_bus[211];
  assign memoryPayload_instructionCacheMiss = ms_to_ws_bus[212];
  assign memoryPayload_accessesMemory = ms_to_ws_bus[213];
  assign memoryPayload_dataCacheMiss = ms_to_ws_bus[214];
  assign memoryPayload_isPredictableBranch = ms_to_ws_bus[215];
  assign memoryPayload_predictionError = ms_to_ws_bus[216];
  assign memoryPayload_idle = ms_to_ws_bus[217];
  assign memoryPayload_physicalAddress = ms_to_ws_bus[249 : 218];
  assign memoryPayload_dataUncached = ms_to_ws_bus[250];
  assign memoryPayload_instruction = ms_to_ws_bus[282 : 251];
  assign memoryPayload_timer = ms_to_ws_bus[346 : 283];
  assign memoryPayload_isCounterInstruction = ms_to_ws_bus[347];
  assign memoryPayload_loadEvent = ms_to_ws_bus[355 : 348];
  assign memoryPayload_memoryPhysicalAddress = ms_to_ws_bus[387 : 356];
  assign memoryPayload_memoryVirtualAddress = ms_to_ws_bus[419 : 388];
  assign memoryPayload_storeEvent = ms_to_ws_bus[427 : 420];
  assign memoryPayload_storeData = ms_to_ws_bus[459 : 428];
  assign memoryPayload_csrRstatEvent = ms_to_ws_bus[460];
  assign memoryPayload_csrData = ms_to_ws_bus[492 : 461];
  assign ws_allowin = area_stage_io_input_ready;
  assign ws_to_ds_valid = area_stage_io_stageValid;
  assign ws_to_rf_bus = {{area_stage_io_registerWrite_valid,area_stage_io_registerWrite_index},area_stage_io_registerWrite_data};
  assign csr_era = area_stage_io_debug_pc;
  assign csr_esubcode = area_stage_io_exception_esubcode;
  assign csr_ecode = area_stage_io_exception_ecode;
  assign excp_flush = (debug_break_point ? area_stage_io_flush_exception : area_stage_io_exception_valid);
  assign ertn_flush = area_stage_io_flush_ertn;
  assign refetch_flush = area_stage_io_flush_refetch;
  assign icacop_flush = area_stage_io_flush_instructionCacheOperation;
  assign csr_wr_en = area_stage_io_csrWrite_valid;
  assign wr_csr_addr = area_stage_io_csrWrite_address;
  assign wr_csr_data = area_stage_io_csrWrite_data;
  assign va_error = area_stage_io_exception_badVAddrValid;
  assign bad_va = area_stage_io_exception_badVAddr;
  assign excp_tlbrefill = area_stage_io_exception_tlbRefill;
  assign excp_tlb = area_stage_io_exception_tlbException;
  assign excp_tlb_vppn = area_stage_io_exception_tlbVppn;
  assign idle_flush = area_stage_io_flush_idle;
  assign ws_llbit_set = area_stage_io_reservation_bitSet;
  assign ws_llbit = area_stage_io_reservation_bitValue;
  assign ws_lladdr_set = area_stage_io_reservation_addressSet;
  assign ws_lladdr = area_stage_io_reservation_lineAddress;
  assign tlb_inst_stall = area_stage_io_tlb_instructionStall;
  assign tlbsrch_en = area_stage_io_tlb_search;
  assign tlbsrch_found = area_stage_io_tlb_searchFound;
  assign tlbsrch_index = area_stage_io_tlb_searchIndex;
  assign tlbfill_en = area_stage_io_tlb_fill;
  assign tlbwr_en = area_stage_io_tlb_write;
  assign tlbrd_en = area_stage_io_tlb_read;
  assign invtlb_en = area_stage_io_tlb_invalidate;
  assign invtlb_asid = area_stage_io_tlb_invalidateAsid;
  assign invtlb_vpn = area_stage_io_tlb_invalidateVpn;
  assign invtlb_op = area_stage_io_tlb_invalidateOperation;
  assign real_valid = area_stage_io_perf_retired;
  assign real_br_inst = area_stage_io_perf_branch;
  assign real_icache_miss = area_stage_io_perf_instructionCacheMiss;
  assign real_dcache_miss = area_stage_io_perf_dataCacheMiss;
  assign real_mem_inst = area_stage_io_perf_memoryAccess;
  assign real_br_pre = area_stage_io_perf_predictedBranch;
  assign real_br_pre_error = area_stage_io_perf_predictionError;
  assign debug_ws_valid = area_stage_io_debug_stageValid;
  assign debug_wb_pc = area_stage_io_debug_pc;
  assign debug_wb_rf_wen = area_stage_io_debug_gprWriteMask;
  assign debug_wb_rf_wnum = area_stage_io_debug_gprIndex;
  assign debug_wb_rf_wdata = area_stage_io_debug_gprData;
  assign debug_wb_inst = area_stage_io_debug_instruction;
  assign ws_valid_diff = area_stage_io_realValid;
  assign ws_cnt_inst_diff = area_stage_io_observation_isCounterInstruction;
  assign ws_timer_64_diff = area_stage_io_observation_timer;
  assign ws_inst_ld_en_diff = area_stage_io_observation_loadEvent;
  assign ws_ld_paddr_diff = area_stage_io_observation_memoryPhysicalAddress;
  assign ws_ld_vaddr_diff = area_stage_io_observation_memoryVirtualAddress;
  assign ws_inst_st_en_diff = area_stage_io_observation_storeEvent;
  assign ws_st_paddr_diff = area_stage_io_observation_memoryPhysicalAddress;
  assign ws_st_vaddr_diff = area_stage_io_observation_memoryVirtualAddress;
  assign ws_st_data_diff = area_stage_io_observation_storeData;
  assign ws_csr_rstat_en_diff = area_stage_io_observation_csrRstatEvent;
  assign ws_csr_data_diff = area_stage_io_observation_csrData;

endmodule

module WritebackStage (
  input  wire          io_input_valid,
  output wire          io_input_ready,
  input  wire [31:0]   io_input_payload_pc,
  input  wire [31:0]   io_input_payload_finalResult,
  input  wire [4:0]    io_input_payload_destination,
  input  wire          io_input_payload_gprWrite,
  input  wire          io_input_payload_hasException,
  input  wire          io_input_payload_isErtn,
  input  wire [31:0]   io_input_payload_csrResult,
  input  wire [13:0]   io_input_payload_csrAddress,
  input  wire          io_input_payload_csrWrite,
  input  wire [15:0]   io_input_payload_exceptionCode,
  input  wire          io_input_payload_isLl,
  input  wire          io_input_payload_isSc,
  input  wire [31:0]   io_input_payload_errorVirtualAddress,
  input  wire          io_input_payload_tlbSearch,
  input  wire          io_input_payload_tlbFound,
  input  wire [4:0]    io_input_payload_tlbIndex,
  input  wire          io_input_payload_tlbWrite,
  input  wire          io_input_payload_tlbFill,
  input  wire          io_input_payload_refetch,
  input  wire          io_input_payload_tlbRead,
  input  wire          io_input_payload_invalidateTlb,
  input  wire [9:0]    io_input_payload_invalidateTlbAsid,
  input  wire [18:0]   io_input_payload_invalidateTlbVpn,
  input  wire          io_input_payload_instructionCacheOperation,
  input  wire          io_input_payload_isBranch,
  input  wire          io_input_payload_instructionCacheMiss,
  input  wire          io_input_payload_accessesMemory,
  input  wire          io_input_payload_dataCacheMiss,
  input  wire          io_input_payload_isPredictableBranch,
  input  wire          io_input_payload_predictionError,
  input  wire          io_input_payload_idle,
  input  wire [31:0]   io_input_payload_physicalAddress,
  input  wire          io_input_payload_dataUncached,
  input  wire [31:0]   io_input_payload_instruction,
  input  wire [63:0]   io_input_payload_timer,
  input  wire          io_input_payload_isCounterInstruction,
  input  wire [7:0]    io_input_payload_loadEvent,
  input  wire [31:0]   io_input_payload_memoryPhysicalAddress,
  input  wire [31:0]   io_input_payload_memoryVirtualAddress,
  input  wire [7:0]    io_input_payload_storeEvent,
  input  wire [31:0]   io_input_payload_storeData,
  input  wire          io_input_payload_csrRstatEvent,
  input  wire [31:0]   io_input_payload_csrData,
  input  wire          io_debugBreakPoint,
  output wire          io_stageValid,
  output wire          io_realValid,
  output wire          io_registerWrite_valid,
  output wire [4:0]    io_registerWrite_index,
  output wire [31:0]   io_registerWrite_data,
  output wire          io_csrWrite_valid,
  output wire [13:0]   io_csrWrite_address,
  output wire [31:0]   io_csrWrite_data,
  output wire          io_flush_exception,
  output wire          io_flush_ertn,
  output wire          io_flush_refetch,
  output wire          io_flush_instructionCacheOperation,
  output wire          io_flush_idle,
  output wire          io_exception_valid,
  output reg  [5:0]    io_exception_ecode,
  output wire [8:0]    io_exception_esubcode,
  output reg           io_exception_badVAddrValid,
  output reg  [31:0]   io_exception_badVAddr,
  output reg           io_exception_tlbRefill,
  output reg           io_exception_tlbException,
  output reg  [18:0]   io_exception_tlbVppn,
  output wire          io_tlb_instructionStall,
  output wire          io_tlb_search,
  output wire          io_tlb_searchFound,
  output wire [4:0]    io_tlb_searchIndex,
  output wire          io_tlb_fill,
  output wire          io_tlb_write,
  output wire          io_tlb_read,
  output wire          io_tlb_invalidate,
  output wire [9:0]    io_tlb_invalidateAsid,
  output wire [18:0]   io_tlb_invalidateVpn,
  output wire [4:0]    io_tlb_invalidateOperation,
  output wire          io_reservation_bitSet,
  output wire          io_reservation_bitValue,
  output wire          io_reservation_addressSet,
  output wire [27:0]   io_reservation_lineAddress,
  output wire          io_perf_retired,
  output wire          io_perf_branch,
  output wire          io_perf_instructionCacheMiss,
  output wire          io_perf_dataCacheMiss,
  output wire          io_perf_memoryAccess,
  output wire          io_perf_predictedBranch,
  output wire          io_perf_predictionError,
  output wire          io_debug_stageValid,
  output wire [31:0]   io_debug_pc,
  output wire [3:0]    io_debug_gprWriteMask,
  output wire [4:0]    io_debug_gprIndex,
  output wire [31:0]   io_debug_gprData,
  output wire [31:0]   io_debug_instruction,
  output wire          io_observation_isCounterInstruction,
  output wire [63:0]   io_observation_timer,
  output wire [7:0]    io_observation_loadEvent,
  output wire [31:0]   io_observation_memoryPhysicalAddress,
  output wire [31:0]   io_observation_memoryVirtualAddress,
  output wire [7:0]    io_observation_storeEvent,
  output wire [31:0]   io_observation_storeData,
  output wire          io_observation_csrRstatEvent,
  output wire [31:0]   io_observation_csrData,
  input  wire          clk,
  input  wire          reset
);

  reg                 valid;
  reg        [31:0]   payload_pc;
  reg        [31:0]   payload_finalResult;
  reg        [4:0]    payload_destination;
  reg                 payload_gprWrite;
  reg                 payload_hasException;
  reg                 payload_isErtn;
  reg        [31:0]   payload_csrResult;
  reg        [13:0]   payload_csrAddress;
  reg                 payload_csrWrite;
  reg        [15:0]   payload_exceptionCode;
  reg                 payload_isLl;
  reg                 payload_isSc;
  reg        [31:0]   payload_errorVirtualAddress;
  reg                 payload_tlbSearch;
  reg                 payload_tlbFound;
  reg        [4:0]    payload_tlbIndex;
  reg                 payload_tlbWrite;
  reg                 payload_tlbFill;
  reg                 payload_refetch;
  reg                 payload_tlbRead;
  reg                 payload_invalidateTlb;
  reg        [9:0]    payload_invalidateTlbAsid;
  reg        [18:0]   payload_invalidateTlbVpn;
  reg                 payload_instructionCacheOperation;
  reg                 payload_isBranch;
  reg                 payload_instructionCacheMiss;
  reg                 payload_accessesMemory;
  reg                 payload_dataCacheMiss;
  reg                 payload_isPredictableBranch;
  reg                 payload_predictionError;
  reg                 payload_idle;
  reg        [31:0]   payload_physicalAddress;
  reg                 payload_dataUncached;
  reg        [31:0]   payload_instruction;
  reg        [63:0]   payload_timer;
  reg                 payload_isCounterInstruction;
  reg        [7:0]    payload_loadEvent;
  reg        [31:0]   payload_memoryPhysicalAddress;
  reg        [31:0]   payload_memoryVirtualAddress;
  reg        [7:0]    payload_storeEvent;
  reg        [31:0]   payload_storeData;
  reg                 payload_csrRstatEvent;
  reg        [31:0]   payload_csrData;
  wire                readyGo;
  wire                realValid;
  wire                registerWriteValid;
  wire                when_WritebackStage_l138;
  wire                when_WritebackStage_l140;
  wire                when_WritebackStage_l144;
  wire                when_WritebackStage_l151;
  wire                when_WritebackStage_l157;
  wire                when_WritebackStage_l163;
  wire                when_WritebackStage_l165;
  wire                when_WritebackStage_l167;
  wire                when_WritebackStage_l169;
  wire                when_WritebackStage_l171;
  wire                when_WritebackStage_l175;
  wire                when_WritebackStage_l182;
  wire                when_WritebackStage_l188;
  wire                when_WritebackStage_l194;
  wire                when_WritebackStage_l200;
  wire                when_WritebackStage_l292;
  wire                io_input_fire;

  assign readyGo = (! io_debugBreakPoint);
  assign io_input_ready = ((! valid) || readyGo);
  assign realValid = (valid && (! payload_hasException));
  assign registerWriteValid = (payload_gprWrite && realValid);
  assign io_stageValid = valid;
  assign io_realValid = realValid;
  assign io_registerWrite_valid = registerWriteValid;
  assign io_registerWrite_index = payload_destination;
  assign io_registerWrite_data = payload_finalResult;
  assign io_csrWrite_valid = (payload_csrWrite && realValid);
  assign io_csrWrite_address = payload_csrAddress;
  assign io_csrWrite_data = payload_csrResult;
  assign io_flush_exception = (payload_hasException && valid);
  assign io_flush_ertn = (payload_isErtn && realValid);
  assign io_flush_refetch = (((payload_csrWrite || ((payload_isLl || payload_isSc) && (! payload_hasException))) || payload_refetch) && valid);
  assign io_flush_instructionCacheOperation = (payload_instructionCacheOperation && valid);
  assign io_flush_idle = (payload_idle && realValid);
  assign io_exception_valid = io_flush_exception;
  always @(*) begin
    io_exception_ecode = 6'h0;
    if(when_WritebackStage_l138) begin
      io_exception_ecode = 6'h0;
    end else begin
      if(when_WritebackStage_l140) begin
        io_exception_ecode = 6'h08;
      end else begin
        if(when_WritebackStage_l144) begin
          io_exception_ecode = 6'h3f;
        end else begin
          if(when_WritebackStage_l151) begin
            io_exception_ecode = 6'h03;
          end else begin
            if(when_WritebackStage_l157) begin
              io_exception_ecode = 6'h07;
            end else begin
              if(when_WritebackStage_l163) begin
                io_exception_ecode = 6'h0b;
              end else begin
                if(when_WritebackStage_l165) begin
                  io_exception_ecode = 6'h0c;
                end else begin
                  if(when_WritebackStage_l167) begin
                    io_exception_ecode = 6'h0d;
                  end else begin
                    if(when_WritebackStage_l169) begin
                      io_exception_ecode = 6'h0e;
                    end else begin
                      if(when_WritebackStage_l171) begin
                        io_exception_ecode = 6'h09;
                      end else begin
                        if(when_WritebackStage_l175) begin
                          io_exception_ecode = 6'h3f;
                        end else begin
                          if(when_WritebackStage_l182) begin
                            io_exception_ecode = 6'h04;
                          end else begin
                            if(when_WritebackStage_l188) begin
                              io_exception_ecode = 6'h07;
                            end else begin
                              if(when_WritebackStage_l194) begin
                                io_exception_ecode = 6'h02;
                              end else begin
                                if(when_WritebackStage_l200) begin
                                  io_exception_ecode = 6'h01;
                                end
                              end
                            end
                          end
                        end
                      end
                    end
                  end
                end
              end
            end
          end
        end
      end
    end
  end

  assign io_exception_esubcode = 9'h0;
  always @(*) begin
    io_exception_badVAddrValid = 1'b0;
    if(!when_WritebackStage_l138) begin
      if(when_WritebackStage_l140) begin
        io_exception_badVAddrValid = valid;
      end else begin
        if(when_WritebackStage_l144) begin
          io_exception_badVAddrValid = valid;
        end else begin
          if(when_WritebackStage_l151) begin
            io_exception_badVAddrValid = valid;
          end else begin
            if(when_WritebackStage_l157) begin
              io_exception_badVAddrValid = valid;
            end else begin
              if(!when_WritebackStage_l163) begin
                if(!when_WritebackStage_l165) begin
                  if(!when_WritebackStage_l167) begin
                    if(!when_WritebackStage_l169) begin
                      if(when_WritebackStage_l171) begin
                        io_exception_badVAddrValid = valid;
                      end else begin
                        if(when_WritebackStage_l175) begin
                          io_exception_badVAddrValid = valid;
                        end else begin
                          if(when_WritebackStage_l182) begin
                            io_exception_badVAddrValid = valid;
                          end else begin
                            if(when_WritebackStage_l188) begin
                              io_exception_badVAddrValid = valid;
                            end else begin
                              if(when_WritebackStage_l194) begin
                                io_exception_badVAddrValid = valid;
                              end else begin
                                if(when_WritebackStage_l200) begin
                                  io_exception_badVAddrValid = valid;
                                end
                              end
                            end
                          end
                        end
                      end
                    end
                  end
                end
              end
            end
          end
        end
      end
    end
  end

  always @(*) begin
    io_exception_badVAddr = 32'h0;
    if(!when_WritebackStage_l138) begin
      if(when_WritebackStage_l140) begin
        io_exception_badVAddr = payload_pc;
      end else begin
        if(when_WritebackStage_l144) begin
          io_exception_badVAddr = payload_pc;
        end else begin
          if(when_WritebackStage_l151) begin
            io_exception_badVAddr = payload_pc;
          end else begin
            if(when_WritebackStage_l157) begin
              io_exception_badVAddr = payload_pc;
            end else begin
              if(!when_WritebackStage_l163) begin
                if(!when_WritebackStage_l165) begin
                  if(!when_WritebackStage_l167) begin
                    if(!when_WritebackStage_l169) begin
                      if(when_WritebackStage_l171) begin
                        io_exception_badVAddr = payload_errorVirtualAddress;
                      end else begin
                        if(when_WritebackStage_l175) begin
                          io_exception_badVAddr = payload_errorVirtualAddress;
                        end else begin
                          if(when_WritebackStage_l182) begin
                            io_exception_badVAddr = payload_errorVirtualAddress;
                          end else begin
                            if(when_WritebackStage_l188) begin
                              io_exception_badVAddr = payload_errorVirtualAddress;
                            end else begin
                              if(when_WritebackStage_l194) begin
                                io_exception_badVAddr = payload_errorVirtualAddress;
                              end else begin
                                if(when_WritebackStage_l200) begin
                                  io_exception_badVAddr = payload_errorVirtualAddress;
                                end
                              end
                            end
                          end
                        end
                      end
                    end
                  end
                end
              end
            end
          end
        end
      end
    end
  end

  always @(*) begin
    io_exception_tlbRefill = 1'b0;
    if(!when_WritebackStage_l138) begin
      if(!when_WritebackStage_l140) begin
        if(when_WritebackStage_l144) begin
          io_exception_tlbRefill = valid;
        end else begin
          if(!when_WritebackStage_l151) begin
            if(!when_WritebackStage_l157) begin
              if(!when_WritebackStage_l163) begin
                if(!when_WritebackStage_l165) begin
                  if(!when_WritebackStage_l167) begin
                    if(!when_WritebackStage_l169) begin
                      if(!when_WritebackStage_l171) begin
                        if(when_WritebackStage_l175) begin
                          io_exception_tlbRefill = valid;
                        end
                      end
                    end
                  end
                end
              end
            end
          end
        end
      end
    end
  end

  always @(*) begin
    io_exception_tlbException = 1'b0;
    if(!when_WritebackStage_l138) begin
      if(!when_WritebackStage_l140) begin
        if(when_WritebackStage_l144) begin
          io_exception_tlbException = valid;
        end else begin
          if(when_WritebackStage_l151) begin
            io_exception_tlbException = valid;
          end else begin
            if(when_WritebackStage_l157) begin
              io_exception_tlbException = valid;
            end else begin
              if(!when_WritebackStage_l163) begin
                if(!when_WritebackStage_l165) begin
                  if(!when_WritebackStage_l167) begin
                    if(!when_WritebackStage_l169) begin
                      if(!when_WritebackStage_l171) begin
                        if(when_WritebackStage_l175) begin
                          io_exception_tlbException = valid;
                        end else begin
                          if(when_WritebackStage_l182) begin
                            io_exception_tlbException = valid;
                          end else begin
                            if(when_WritebackStage_l188) begin
                              io_exception_tlbException = valid;
                            end else begin
                              if(when_WritebackStage_l194) begin
                                io_exception_tlbException = valid;
                              end else begin
                                if(when_WritebackStage_l200) begin
                                  io_exception_tlbException = valid;
                                end
                              end
                            end
                          end
                        end
                      end
                    end
                  end
                end
              end
            end
          end
        end
      end
    end
  end

  always @(*) begin
    io_exception_tlbVppn = 19'h0;
    if(!when_WritebackStage_l138) begin
      if(!when_WritebackStage_l140) begin
        if(when_WritebackStage_l144) begin
          io_exception_tlbVppn = payload_pc[31 : 13];
        end else begin
          if(when_WritebackStage_l151) begin
            io_exception_tlbVppn = payload_pc[31 : 13];
          end else begin
            if(when_WritebackStage_l157) begin
              io_exception_tlbVppn = payload_pc[31 : 13];
            end else begin
              if(!when_WritebackStage_l163) begin
                if(!when_WritebackStage_l165) begin
                  if(!when_WritebackStage_l167) begin
                    if(!when_WritebackStage_l169) begin
                      if(!when_WritebackStage_l171) begin
                        if(when_WritebackStage_l175) begin
                          io_exception_tlbVppn = payload_errorVirtualAddress[31 : 13];
                        end else begin
                          if(when_WritebackStage_l182) begin
                            io_exception_tlbVppn = payload_errorVirtualAddress[31 : 13];
                          end else begin
                            if(when_WritebackStage_l188) begin
                              io_exception_tlbVppn = payload_errorVirtualAddress[31 : 13];
                            end else begin
                              if(when_WritebackStage_l194) begin
                                io_exception_tlbVppn = payload_errorVirtualAddress[31 : 13];
                              end else begin
                                if(when_WritebackStage_l200) begin
                                  io_exception_tlbVppn = payload_errorVirtualAddress[31 : 13];
                                end
                              end
                            end
                          end
                        end
                      end
                    end
                  end
                end
              end
            end
          end
        end
      end
    end
  end

  assign when_WritebackStage_l138 = payload_exceptionCode[0];
  assign when_WritebackStage_l140 = payload_exceptionCode[1];
  assign when_WritebackStage_l144 = payload_exceptionCode[2];
  assign when_WritebackStage_l151 = payload_exceptionCode[3];
  assign when_WritebackStage_l157 = payload_exceptionCode[4];
  assign when_WritebackStage_l163 = payload_exceptionCode[5];
  assign when_WritebackStage_l165 = payload_exceptionCode[6];
  assign when_WritebackStage_l167 = payload_exceptionCode[7];
  assign when_WritebackStage_l169 = payload_exceptionCode[8];
  assign when_WritebackStage_l171 = payload_exceptionCode[9];
  assign when_WritebackStage_l175 = payload_exceptionCode[11];
  assign when_WritebackStage_l182 = payload_exceptionCode[12];
  assign when_WritebackStage_l188 = payload_exceptionCode[13];
  assign when_WritebackStage_l194 = payload_exceptionCode[14];
  assign when_WritebackStage_l200 = payload_exceptionCode[15];
  assign io_tlb_instructionStall = ((payload_tlbSearch || payload_tlbRead) && valid);
  assign io_tlb_search = (payload_tlbSearch && realValid);
  assign io_tlb_searchFound = payload_tlbFound;
  assign io_tlb_searchIndex = payload_tlbIndex;
  assign io_tlb_fill = (payload_tlbFill && realValid);
  assign io_tlb_write = (payload_tlbWrite && realValid);
  assign io_tlb_read = (payload_tlbRead && realValid);
  assign io_tlb_invalidate = (payload_invalidateTlb && realValid);
  assign io_tlb_invalidateAsid = payload_invalidateTlbAsid;
  assign io_tlb_invalidateVpn = payload_invalidateTlbVpn;
  assign io_tlb_invalidateOperation = payload_destination;
  assign io_reservation_bitSet = ((payload_isLl || payload_isSc) && realValid);
  assign io_reservation_bitValue = (payload_isLl && (! payload_dataUncached));
  assign io_reservation_addressSet = ((payload_isLl && (! payload_dataUncached)) && realValid);
  assign io_reservation_lineAddress = payload_physicalAddress[31 : 4];
  assign io_perf_retired = realValid;
  assign io_perf_branch = (payload_isBranch && realValid);
  assign io_perf_instructionCacheMiss = (payload_instructionCacheMiss && realValid);
  assign io_perf_dataCacheMiss = (payload_dataCacheMiss && realValid);
  assign io_perf_memoryAccess = (payload_accessesMemory && realValid);
  assign io_perf_predictedBranch = (payload_isPredictableBranch && realValid);
  assign io_perf_predictionError = (payload_predictionError && realValid);
  assign io_debug_stageValid = valid;
  assign io_debug_pc = payload_pc;
  assign io_debug_gprWriteMask = (registerWriteValid ? 4'b1111 : 4'b0000);
  assign io_debug_gprIndex = payload_destination;
  assign io_debug_gprData = payload_finalResult;
  assign io_debug_instruction = payload_instruction;
  assign io_observation_isCounterInstruction = payload_isCounterInstruction;
  assign io_observation_timer = payload_timer;
  assign io_observation_loadEvent = payload_loadEvent;
  assign io_observation_memoryPhysicalAddress = payload_memoryPhysicalAddress;
  assign io_observation_memoryVirtualAddress = payload_memoryVirtualAddress;
  assign io_observation_storeEvent = payload_storeEvent;
  assign io_observation_storeData = payload_storeData;
  assign io_observation_csrRstatEvent = payload_csrRstatEvent;
  assign io_observation_csrData = payload_csrData;
  assign when_WritebackStage_l292 = ((((io_flush_exception || io_flush_ertn) || io_flush_refetch) || io_flush_instructionCacheOperation) || io_flush_idle);
  assign io_input_fire = (io_input_valid && io_input_ready);
  always @(posedge clk) begin
    if(reset) begin
      valid <= 1'b0;
    end else begin
      if(when_WritebackStage_l292) begin
        valid <= 1'b0;
      end else begin
        if(io_input_ready) begin
          valid <= io_input_valid;
        end
      end
    end
  end

  always @(posedge clk) begin
    if(io_input_fire) begin
      payload_pc <= io_input_payload_pc;
      payload_finalResult <= io_input_payload_finalResult;
      payload_destination <= io_input_payload_destination;
      payload_gprWrite <= io_input_payload_gprWrite;
      payload_hasException <= io_input_payload_hasException;
      payload_isErtn <= io_input_payload_isErtn;
      payload_csrResult <= io_input_payload_csrResult;
      payload_csrAddress <= io_input_payload_csrAddress;
      payload_csrWrite <= io_input_payload_csrWrite;
      payload_exceptionCode <= io_input_payload_exceptionCode;
      payload_isLl <= io_input_payload_isLl;
      payload_isSc <= io_input_payload_isSc;
      payload_errorVirtualAddress <= io_input_payload_errorVirtualAddress;
      payload_tlbSearch <= io_input_payload_tlbSearch;
      payload_tlbFound <= io_input_payload_tlbFound;
      payload_tlbIndex <= io_input_payload_tlbIndex;
      payload_tlbWrite <= io_input_payload_tlbWrite;
      payload_tlbFill <= io_input_payload_tlbFill;
      payload_refetch <= io_input_payload_refetch;
      payload_tlbRead <= io_input_payload_tlbRead;
      payload_invalidateTlb <= io_input_payload_invalidateTlb;
      payload_invalidateTlbAsid <= io_input_payload_invalidateTlbAsid;
      payload_invalidateTlbVpn <= io_input_payload_invalidateTlbVpn;
      payload_instructionCacheOperation <= io_input_payload_instructionCacheOperation;
      payload_isBranch <= io_input_payload_isBranch;
      payload_instructionCacheMiss <= io_input_payload_instructionCacheMiss;
      payload_accessesMemory <= io_input_payload_accessesMemory;
      payload_dataCacheMiss <= io_input_payload_dataCacheMiss;
      payload_isPredictableBranch <= io_input_payload_isPredictableBranch;
      payload_predictionError <= io_input_payload_predictionError;
      payload_idle <= io_input_payload_idle;
      payload_physicalAddress <= io_input_payload_physicalAddress;
      payload_dataUncached <= io_input_payload_dataUncached;
      payload_instruction <= io_input_payload_instruction;
      payload_timer <= io_input_payload_timer;
      payload_isCounterInstruction <= io_input_payload_isCounterInstruction;
      payload_loadEvent <= io_input_payload_loadEvent;
      payload_memoryPhysicalAddress <= io_input_payload_memoryPhysicalAddress;
      payload_memoryVirtualAddress <= io_input_payload_memoryVirtualAddress;
      payload_storeEvent <= io_input_payload_storeEvent;
      payload_storeData <= io_input_payload_storeData;
      payload_csrRstatEvent <= io_input_payload_csrRstatEvent;
      payload_csrData <= io_input_payload_csrData;
    end
  end


endmodule
