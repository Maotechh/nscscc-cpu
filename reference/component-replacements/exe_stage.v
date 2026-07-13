// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : exe_stage



module exe_stage (
  input  wire          clk,
  input  wire          reset,
  input  wire          ms_allowin,
  output wire          es_allowin,
  input  wire          ds_to_es_valid,
  input  wire [349:0]  ds_to_es_bus,
  output wire          es_to_ms_valid,
  output wire [424:0]  es_to_ms_bus,
  output wire [38:0]   es_to_ds_forward_bus,
  output wire          es_to_ds_valid,
  output wire          es_div_enable,
  output wire          es_mul_div_sign,
  output wire [31:0]   es_rj_value,
  output wire [31:0]   es_rkd_value,
  input  wire          div_complete,
  input  wire          excp_flush,
  input  wire          ertn_flush,
  input  wire          refetch_flush,
  input  wire          icacop_flush,
  input  wire          idle_flush,
  output wire          tlb_inst_stall,
  output wire          icacop_op_en,
  output wire          dcacop_op_en,
  output wire [1:0]    cacop_op_mode,
  input  wire          icache_unbusy,
  output wire [4:0]    preld_hint,
  output wire          preld_en,
  output wire          data_valid,
  output wire          data_op,
  output wire [2:0]    data_size,
  output wire [3:0]    data_wstrb,
  output wire [31:0]   data_wdata,
  input  wire          data_addr_ok,
  input  wire [18:0]   csr_vppn,
  output wire [31:0]   data_addr,
  output wire          data_fetch,
  input  wire          ms_wr_tlbehi,
  input  wire          ms_flush
);

  wire       [31:0]   area_stage_io_input_payload_pc;
  wire       [31:0]   area_stage_io_input_payload_registerDataKOrD;
  wire       [31:0]   area_stage_io_input_payload_registerDataJ;
  wire       [31:0]   area_stage_io_input_payload_immediate;
  wire       [4:0]    area_stage_io_input_payload_destination;
  wire                area_stage_io_input_payload_isStore;
  wire                area_stage_io_input_payload_gprWrite;
  wire                area_stage_io_input_payload_source2IsFour;
  wire                area_stage_io_input_payload_source2IsImmediate;
  wire                area_stage_io_input_payload_source1IsPc;
  wire                area_stage_io_input_payload_isLoad;
  wire       [13:0]   area_stage_io_input_payload_aluOperation;
  wire                area_stage_io_input_payload_mulDivSigned;
  wire       [3:0]    area_stage_io_input_payload_mulDivOperation;
  wire       [1:0]    area_stage_io_input_payload_memorySize;
  wire                area_stage_io_input_payload_hasException;
  wire                area_stage_io_input_payload_isErtn;
  wire       [31:0]   area_stage_io_input_payload_csrReadData;
  wire                area_stage_io_input_payload_resultFromCsr;
  wire       [13:0]   area_stage_io_input_payload_csrAddress;
  wire                area_stage_io_input_payload_csrWrite;
  wire                area_stage_io_input_payload_csrMask;
  wire       [8:0]    area_stage_io_input_payload_exceptionCode;
  wire                area_stage_io_input_payload_isLl;
  wire                area_stage_io_input_payload_isSc;
  wire                area_stage_io_input_payload_tlbSearch;
  wire                area_stage_io_input_payload_tlbWrite;
  wire                area_stage_io_input_payload_tlbFill;
  wire                area_stage_io_input_payload_refetch;
  wire                area_stage_io_input_payload_tlbRead;
  wire                area_stage_io_input_payload_invalidateTlb;
  wire                area_stage_io_input_payload_memorySignExtend;
  wire                area_stage_io_input_payload_cacheOperation;
  wire                area_stage_io_input_payload_preload;
  wire                area_stage_io_input_payload_isBranch;
  wire                area_stage_io_input_payload_instructionCacheMiss;
  wire                area_stage_io_input_payload_isPredictableBranch;
  wire                area_stage_io_input_payload_predictionError;
  wire                area_stage_io_input_payload_idle;
  wire       [31:0]   area_stage_io_input_payload_instruction;
  wire       [63:0]   area_stage_io_input_payload_timer;
  wire                area_stage_io_input_payload_isCounterInstruction;
  wire       [7:0]    area_stage_io_input_payload_loadEvent;
  wire       [7:0]    area_stage_io_input_payload_storeEvent;
  wire                area_stage_io_input_payload_csrRstatEvent;
  wire       [18:0]   area_stage_io_csrVirtualPageNumber;
  wire                area_stage_io_input_ready;
  wire                area_stage_io_output_valid;
  wire       [31:0]   area_stage_io_output_payload_pc;
  wire       [31:0]   area_stage_io_output_payload_executeResult;
  wire       [4:0]    area_stage_io_output_payload_destination;
  wire                area_stage_io_output_payload_gprWrite;
  wire                area_stage_io_output_payload_isLoad;
  wire       [3:0]    area_stage_io_output_payload_mulDivOperation;
  wire       [1:0]    area_stage_io_output_payload_memorySize;
  wire                area_stage_io_output_payload_hasException;
  wire                area_stage_io_output_payload_isErtn;
  wire       [31:0]   area_stage_io_output_payload_csrResult;
  wire       [13:0]   area_stage_io_output_payload_csrAddress;
  wire                area_stage_io_output_payload_csrWrite;
  wire       [9:0]    area_stage_io_output_payload_exceptionCode;
  wire                area_stage_io_output_payload_isLl;
  wire                area_stage_io_output_payload_isSc;
  wire                area_stage_io_output_payload_isStore;
  wire                area_stage_io_output_payload_tlbSearch;
  wire                area_stage_io_output_payload_tlbWrite;
  wire                area_stage_io_output_payload_tlbFill;
  wire                area_stage_io_output_payload_refetch;
  wire                area_stage_io_output_payload_tlbRead;
  wire                area_stage_io_output_payload_invalidateTlb;
  wire       [9:0]    area_stage_io_output_payload_invalidateTlbAsid;
  wire       [18:0]   area_stage_io_output_payload_invalidateTlbVpn;
  wire                area_stage_io_output_payload_memorySignExtend;
  wire                area_stage_io_output_payload_instructionCacheOperation;
  wire                area_stage_io_output_payload_isBranch;
  wire                area_stage_io_output_payload_instructionCacheMiss;
  wire                area_stage_io_output_payload_isPredictableBranch;
  wire                area_stage_io_output_payload_predictionError;
  wire                area_stage_io_output_payload_preload;
  wire                area_stage_io_output_payload_cacheOperation;
  wire                area_stage_io_output_payload_idle;
  wire       [31:0]   area_stage_io_output_payload_errorVirtualAddress;
  wire       [31:0]   area_stage_io_output_payload_instruction;
  wire       [63:0]   area_stage_io_output_payload_timer;
  wire                area_stage_io_output_payload_isCounterInstruction;
  wire       [7:0]    area_stage_io_output_payload_loadEvent;
  wire       [31:0]   area_stage_io_output_payload_memoryVirtualAddress;
  wire       [7:0]    area_stage_io_output_payload_storeEvent;
  wire       [31:0]   area_stage_io_output_payload_storeData;
  wire                area_stage_io_output_payload_csrRstatEvent;
  wire       [31:0]   area_stage_io_output_payload_csrData;
  wire                area_stage_io_forward_valid;
  wire                area_stage_io_forward_dependencyNeedsStall;
  wire                area_stage_io_forward_writeEnabled;
  wire       [4:0]    area_stage_io_forward_destination;
  wire       [31:0]   area_stage_io_forward_result;
  wire                area_stage_io_mulDiv_divideEnable;
  wire                area_stage_io_mulDiv_signed;
  wire       [31:0]   area_stage_io_mulDiv_operandJ;
  wire       [31:0]   area_stage_io_mulDiv_operandKOrD;
  wire                area_stage_io_memory_valid;
  wire                area_stage_io_memory_isWrite;
  wire       [2:0]    area_stage_io_memory_size;
  wire       [3:0]    area_stage_io_memory_byteMask;
  wire       [31:0]   area_stage_io_memory_writeData;
  wire       [31:0]   area_stage_io_memory_virtualAddress;
  wire                area_stage_io_cache_instructionOperationEnable;
  wire                area_stage_io_cache_dataOperationEnable;
  wire       [1:0]    area_stage_io_cache_operationMode;
  wire                area_stage_io_cache_preloadEnable;
  wire       [4:0]    area_stage_io_cache_preloadHint;
  wire                area_stage_io_tlbInstructionStall;
  wire                area_stage_io_dataFetch;
  wire       [298:0]  _zz_es_to_ms_bus;
  wire       [269:0]  _zz_es_to_ms_bus_1;
  wire       [177:0]  _zz_es_to_ms_bus_2;
  wire       [0:0]    _zz_es_to_ms_bus_3;

  assign _zz_es_to_ms_bus = {{{{{{{{{{{_zz_es_to_ms_bus_1,area_stage_io_output_payload_invalidateTlbAsid},area_stage_io_output_payload_invalidateTlb},area_stage_io_output_payload_tlbRead},area_stage_io_output_payload_refetch},area_stage_io_output_payload_tlbFill},area_stage_io_output_payload_tlbWrite},area_stage_io_output_payload_tlbSearch},area_stage_io_output_payload_isStore},area_stage_io_output_payload_isSc},area_stage_io_output_payload_isLl},area_stage_io_output_payload_exceptionCode};
  assign _zz_es_to_ms_bus_3 = area_stage_io_output_payload_csrWrite;
  assign _zz_es_to_ms_bus_1 = {{{{{{{{{{{{_zz_es_to_ms_bus_2,area_stage_io_output_payload_instruction},area_stage_io_output_payload_errorVirtualAddress},area_stage_io_output_payload_idle},area_stage_io_output_payload_cacheOperation},area_stage_io_output_payload_preload},area_stage_io_output_payload_predictionError},area_stage_io_output_payload_isPredictableBranch},area_stage_io_output_payload_instructionCacheMiss},area_stage_io_output_payload_isBranch},area_stage_io_output_payload_instructionCacheOperation},area_stage_io_output_payload_memorySignExtend},area_stage_io_output_payload_invalidateTlbVpn};
  assign _zz_es_to_ms_bus_2 = {{{{{{{area_stage_io_output_payload_csrData,area_stage_io_output_payload_csrRstatEvent},area_stage_io_output_payload_storeData},area_stage_io_output_payload_storeEvent},area_stage_io_output_payload_memoryVirtualAddress},area_stage_io_output_payload_loadEvent},area_stage_io_output_payload_isCounterInstruction},area_stage_io_output_payload_timer};
  ExecuteStage area_stage (
    .io_input_valid                              (ds_to_es_valid                                         ), //i
    .io_input_ready                              (area_stage_io_input_ready                              ), //o
    .io_input_payload_pc                         (area_stage_io_input_payload_pc[31:0]                   ), //i
    .io_input_payload_registerDataKOrD           (area_stage_io_input_payload_registerDataKOrD[31:0]     ), //i
    .io_input_payload_registerDataJ              (area_stage_io_input_payload_registerDataJ[31:0]        ), //i
    .io_input_payload_immediate                  (area_stage_io_input_payload_immediate[31:0]            ), //i
    .io_input_payload_destination                (area_stage_io_input_payload_destination[4:0]           ), //i
    .io_input_payload_isStore                    (area_stage_io_input_payload_isStore                    ), //i
    .io_input_payload_gprWrite                   (area_stage_io_input_payload_gprWrite                   ), //i
    .io_input_payload_source2IsFour              (area_stage_io_input_payload_source2IsFour              ), //i
    .io_input_payload_source2IsImmediate         (area_stage_io_input_payload_source2IsImmediate         ), //i
    .io_input_payload_source1IsPc                (area_stage_io_input_payload_source1IsPc                ), //i
    .io_input_payload_isLoad                     (area_stage_io_input_payload_isLoad                     ), //i
    .io_input_payload_aluOperation               (area_stage_io_input_payload_aluOperation[13:0]         ), //i
    .io_input_payload_mulDivSigned               (area_stage_io_input_payload_mulDivSigned               ), //i
    .io_input_payload_mulDivOperation            (area_stage_io_input_payload_mulDivOperation[3:0]       ), //i
    .io_input_payload_memorySize                 (area_stage_io_input_payload_memorySize[1:0]            ), //i
    .io_input_payload_hasException               (area_stage_io_input_payload_hasException               ), //i
    .io_input_payload_isErtn                     (area_stage_io_input_payload_isErtn                     ), //i
    .io_input_payload_csrReadData                (area_stage_io_input_payload_csrReadData[31:0]          ), //i
    .io_input_payload_resultFromCsr              (area_stage_io_input_payload_resultFromCsr              ), //i
    .io_input_payload_csrAddress                 (area_stage_io_input_payload_csrAddress[13:0]           ), //i
    .io_input_payload_csrWrite                   (area_stage_io_input_payload_csrWrite                   ), //i
    .io_input_payload_csrMask                    (area_stage_io_input_payload_csrMask                    ), //i
    .io_input_payload_exceptionCode              (area_stage_io_input_payload_exceptionCode[8:0]         ), //i
    .io_input_payload_isLl                       (area_stage_io_input_payload_isLl                       ), //i
    .io_input_payload_isSc                       (area_stage_io_input_payload_isSc                       ), //i
    .io_input_payload_tlbSearch                  (area_stage_io_input_payload_tlbSearch                  ), //i
    .io_input_payload_tlbWrite                   (area_stage_io_input_payload_tlbWrite                   ), //i
    .io_input_payload_tlbFill                    (area_stage_io_input_payload_tlbFill                    ), //i
    .io_input_payload_refetch                    (area_stage_io_input_payload_refetch                    ), //i
    .io_input_payload_tlbRead                    (area_stage_io_input_payload_tlbRead                    ), //i
    .io_input_payload_invalidateTlb              (area_stage_io_input_payload_invalidateTlb              ), //i
    .io_input_payload_memorySignExtend           (area_stage_io_input_payload_memorySignExtend           ), //i
    .io_input_payload_cacheOperation             (area_stage_io_input_payload_cacheOperation             ), //i
    .io_input_payload_preload                    (area_stage_io_input_payload_preload                    ), //i
    .io_input_payload_isBranch                   (area_stage_io_input_payload_isBranch                   ), //i
    .io_input_payload_instructionCacheMiss       (area_stage_io_input_payload_instructionCacheMiss       ), //i
    .io_input_payload_isPredictableBranch        (area_stage_io_input_payload_isPredictableBranch        ), //i
    .io_input_payload_predictionError            (area_stage_io_input_payload_predictionError            ), //i
    .io_input_payload_idle                       (area_stage_io_input_payload_idle                       ), //i
    .io_input_payload_instruction                (area_stage_io_input_payload_instruction[31:0]          ), //i
    .io_input_payload_timer                      (area_stage_io_input_payload_timer[63:0]                ), //i
    .io_input_payload_isCounterInstruction       (area_stage_io_input_payload_isCounterInstruction       ), //i
    .io_input_payload_loadEvent                  (area_stage_io_input_payload_loadEvent[7:0]             ), //i
    .io_input_payload_storeEvent                 (area_stage_io_input_payload_storeEvent[7:0]            ), //i
    .io_input_payload_csrRstatEvent              (area_stage_io_input_payload_csrRstatEvent              ), //i
    .io_output_valid                             (area_stage_io_output_valid                             ), //o
    .io_output_ready                             (ms_allowin                                             ), //i
    .io_output_payload_pc                        (area_stage_io_output_payload_pc[31:0]                  ), //o
    .io_output_payload_executeResult             (area_stage_io_output_payload_executeResult[31:0]       ), //o
    .io_output_payload_destination               (area_stage_io_output_payload_destination[4:0]          ), //o
    .io_output_payload_gprWrite                  (area_stage_io_output_payload_gprWrite                  ), //o
    .io_output_payload_isLoad                    (area_stage_io_output_payload_isLoad                    ), //o
    .io_output_payload_mulDivOperation           (area_stage_io_output_payload_mulDivOperation[3:0]      ), //o
    .io_output_payload_memorySize                (area_stage_io_output_payload_memorySize[1:0]           ), //o
    .io_output_payload_hasException              (area_stage_io_output_payload_hasException              ), //o
    .io_output_payload_isErtn                    (area_stage_io_output_payload_isErtn                    ), //o
    .io_output_payload_csrResult                 (area_stage_io_output_payload_csrResult[31:0]           ), //o
    .io_output_payload_csrAddress                (area_stage_io_output_payload_csrAddress[13:0]          ), //o
    .io_output_payload_csrWrite                  (area_stage_io_output_payload_csrWrite                  ), //o
    .io_output_payload_exceptionCode             (area_stage_io_output_payload_exceptionCode[9:0]        ), //o
    .io_output_payload_isLl                      (area_stage_io_output_payload_isLl                      ), //o
    .io_output_payload_isSc                      (area_stage_io_output_payload_isSc                      ), //o
    .io_output_payload_isStore                   (area_stage_io_output_payload_isStore                   ), //o
    .io_output_payload_tlbSearch                 (area_stage_io_output_payload_tlbSearch                 ), //o
    .io_output_payload_tlbWrite                  (area_stage_io_output_payload_tlbWrite                  ), //o
    .io_output_payload_tlbFill                   (area_stage_io_output_payload_tlbFill                   ), //o
    .io_output_payload_refetch                   (area_stage_io_output_payload_refetch                   ), //o
    .io_output_payload_tlbRead                   (area_stage_io_output_payload_tlbRead                   ), //o
    .io_output_payload_invalidateTlb             (area_stage_io_output_payload_invalidateTlb             ), //o
    .io_output_payload_invalidateTlbAsid         (area_stage_io_output_payload_invalidateTlbAsid[9:0]    ), //o
    .io_output_payload_invalidateTlbVpn          (area_stage_io_output_payload_invalidateTlbVpn[18:0]    ), //o
    .io_output_payload_memorySignExtend          (area_stage_io_output_payload_memorySignExtend          ), //o
    .io_output_payload_instructionCacheOperation (area_stage_io_output_payload_instructionCacheOperation ), //o
    .io_output_payload_isBranch                  (area_stage_io_output_payload_isBranch                  ), //o
    .io_output_payload_instructionCacheMiss      (area_stage_io_output_payload_instructionCacheMiss      ), //o
    .io_output_payload_isPredictableBranch       (area_stage_io_output_payload_isPredictableBranch       ), //o
    .io_output_payload_predictionError           (area_stage_io_output_payload_predictionError           ), //o
    .io_output_payload_preload                   (area_stage_io_output_payload_preload                   ), //o
    .io_output_payload_cacheOperation            (area_stage_io_output_payload_cacheOperation            ), //o
    .io_output_payload_idle                      (area_stage_io_output_payload_idle                      ), //o
    .io_output_payload_errorVirtualAddress       (area_stage_io_output_payload_errorVirtualAddress[31:0] ), //o
    .io_output_payload_instruction               (area_stage_io_output_payload_instruction[31:0]         ), //o
    .io_output_payload_timer                     (area_stage_io_output_payload_timer[63:0]               ), //o
    .io_output_payload_isCounterInstruction      (area_stage_io_output_payload_isCounterInstruction      ), //o
    .io_output_payload_loadEvent                 (area_stage_io_output_payload_loadEvent[7:0]            ), //o
    .io_output_payload_memoryVirtualAddress      (area_stage_io_output_payload_memoryVirtualAddress[31:0]), //o
    .io_output_payload_storeEvent                (area_stage_io_output_payload_storeEvent[7:0]           ), //o
    .io_output_payload_storeData                 (area_stage_io_output_payload_storeData[31:0]           ), //o
    .io_output_payload_csrRstatEvent             (area_stage_io_output_payload_csrRstatEvent             ), //o
    .io_output_payload_csrData                   (area_stage_io_output_payload_csrData[31:0]             ), //o
    .io_forward_valid                            (area_stage_io_forward_valid                            ), //o
    .io_forward_dependencyNeedsStall             (area_stage_io_forward_dependencyNeedsStall             ), //o
    .io_forward_writeEnabled                     (area_stage_io_forward_writeEnabled                     ), //o
    .io_forward_destination                      (area_stage_io_forward_destination[4:0]                 ), //o
    .io_forward_result                           (area_stage_io_forward_result[31:0]                     ), //o
    .io_mulDiv_divideEnable                      (area_stage_io_mulDiv_divideEnable                      ), //o
    .io_mulDiv_signed                            (area_stage_io_mulDiv_signed                            ), //o
    .io_mulDiv_operandJ                          (area_stage_io_mulDiv_operandJ[31:0]                    ), //o
    .io_mulDiv_operandKOrD                       (area_stage_io_mulDiv_operandKOrD[31:0]                 ), //o
    .io_divideComplete                           (div_complete                                           ), //i
    .io_flush_exception                          (excp_flush                                             ), //i
    .io_flush_ertn                               (ertn_flush                                             ), //i
    .io_flush_refetch                            (refetch_flush                                          ), //i
    .io_flush_instructionCacheOperation          (icacop_flush                                           ), //i
    .io_flush_idle                               (idle_flush                                             ), //i
    .io_memoryFlush                              (ms_flush                                               ), //i
    .io_memoryWritesTlbEntryHigh                 (ms_wr_tlbehi                                           ), //i
    .io_instructionCacheUnbusy                   (icache_unbusy                                          ), //i
    .io_memoryAddressAccepted                    (data_addr_ok                                           ), //i
    .io_csrVirtualPageNumber                     (area_stage_io_csrVirtualPageNumber[18:0]               ), //i
    .io_memory_valid                             (area_stage_io_memory_valid                             ), //o
    .io_memory_isWrite                           (area_stage_io_memory_isWrite                           ), //o
    .io_memory_size                              (area_stage_io_memory_size[2:0]                         ), //o
    .io_memory_byteMask                          (area_stage_io_memory_byteMask[3:0]                     ), //o
    .io_memory_writeData                         (area_stage_io_memory_writeData[31:0]                   ), //o
    .io_memory_virtualAddress                    (area_stage_io_memory_virtualAddress[31:0]              ), //o
    .io_cache_instructionOperationEnable         (area_stage_io_cache_instructionOperationEnable         ), //o
    .io_cache_dataOperationEnable                (area_stage_io_cache_dataOperationEnable                ), //o
    .io_cache_operationMode                      (area_stage_io_cache_operationMode[1:0]                 ), //o
    .io_cache_preloadEnable                      (area_stage_io_cache_preloadEnable                      ), //o
    .io_cache_preloadHint                        (area_stage_io_cache_preloadHint[4:0]                   ), //o
    .io_tlbInstructionStall                      (area_stage_io_tlbInstructionStall                      ), //o
    .io_dataFetch                                (area_stage_io_dataFetch                                ), //o
    .clk                                         (clk                                                    ), //i
    .reset                                       (reset                                                  )  //i
  );
  assign area_stage_io_input_payload_pc = ds_to_es_bus[31 : 0];
  assign area_stage_io_input_payload_registerDataKOrD = ds_to_es_bus[63 : 32];
  assign area_stage_io_input_payload_registerDataJ = ds_to_es_bus[95 : 64];
  assign area_stage_io_input_payload_immediate = ds_to_es_bus[127 : 96];
  assign area_stage_io_input_payload_destination = ds_to_es_bus[132 : 128];
  assign area_stage_io_input_payload_isStore = ds_to_es_bus[133];
  assign area_stage_io_input_payload_gprWrite = ds_to_es_bus[134];
  assign area_stage_io_input_payload_source2IsFour = ds_to_es_bus[135];
  assign area_stage_io_input_payload_source2IsImmediate = ds_to_es_bus[136];
  assign area_stage_io_input_payload_source1IsPc = ds_to_es_bus[137];
  assign area_stage_io_input_payload_isLoad = ds_to_es_bus[138];
  assign area_stage_io_input_payload_aluOperation = ds_to_es_bus[152 : 139];
  assign area_stage_io_input_payload_mulDivSigned = ds_to_es_bus[153];
  assign area_stage_io_input_payload_mulDivOperation = ds_to_es_bus[157 : 154];
  assign area_stage_io_input_payload_memorySize = ds_to_es_bus[159 : 158];
  assign area_stage_io_input_payload_hasException = ds_to_es_bus[160];
  assign area_stage_io_input_payload_isErtn = ds_to_es_bus[161];
  assign area_stage_io_input_payload_csrReadData = ds_to_es_bus[193 : 162];
  assign area_stage_io_input_payload_resultFromCsr = ds_to_es_bus[194];
  assign area_stage_io_input_payload_csrAddress = ds_to_es_bus[208 : 195];
  assign area_stage_io_input_payload_csrWrite = ds_to_es_bus[209];
  assign area_stage_io_input_payload_csrMask = ds_to_es_bus[210];
  assign area_stage_io_input_payload_exceptionCode = ds_to_es_bus[219 : 211];
  assign area_stage_io_input_payload_isLl = ds_to_es_bus[220];
  assign area_stage_io_input_payload_isSc = ds_to_es_bus[221];
  assign area_stage_io_input_payload_tlbSearch = ds_to_es_bus[222];
  assign area_stage_io_input_payload_tlbWrite = ds_to_es_bus[223];
  assign area_stage_io_input_payload_tlbFill = ds_to_es_bus[224];
  assign area_stage_io_input_payload_refetch = ds_to_es_bus[225];
  assign area_stage_io_input_payload_tlbRead = ds_to_es_bus[226];
  assign area_stage_io_input_payload_invalidateTlb = ds_to_es_bus[227];
  assign area_stage_io_input_payload_memorySignExtend = ds_to_es_bus[228];
  assign area_stage_io_input_payload_cacheOperation = ds_to_es_bus[229];
  assign area_stage_io_input_payload_preload = ds_to_es_bus[230];
  assign area_stage_io_input_payload_isBranch = ds_to_es_bus[231];
  assign area_stage_io_input_payload_instructionCacheMiss = ds_to_es_bus[232];
  assign area_stage_io_input_payload_isPredictableBranch = ds_to_es_bus[233];
  assign area_stage_io_input_payload_predictionError = ds_to_es_bus[234];
  assign area_stage_io_input_payload_idle = ds_to_es_bus[235];
  assign area_stage_io_input_payload_instruction = ds_to_es_bus[267 : 236];
  assign area_stage_io_input_payload_timer = ds_to_es_bus[331 : 268];
  assign area_stage_io_input_payload_isCounterInstruction = ds_to_es_bus[332];
  assign area_stage_io_input_payload_loadEvent = ds_to_es_bus[340 : 333];
  assign area_stage_io_input_payload_storeEvent = ds_to_es_bus[348 : 341];
  assign area_stage_io_input_payload_csrRstatEvent = ds_to_es_bus[349];
  assign es_allowin = area_stage_io_input_ready;
  assign es_to_ms_valid = area_stage_io_output_valid;
  assign es_to_ms_bus = {{{{{{{{{{{{_zz_es_to_ms_bus,_zz_es_to_ms_bus_3},area_stage_io_output_payload_csrAddress},area_stage_io_output_payload_csrResult},area_stage_io_output_payload_isErtn},area_stage_io_output_payload_hasException},area_stage_io_output_payload_memorySize},area_stage_io_output_payload_mulDivOperation},area_stage_io_output_payload_isLoad},area_stage_io_output_payload_gprWrite},area_stage_io_output_payload_destination},area_stage_io_output_payload_executeResult},area_stage_io_output_payload_pc};
  assign es_to_ds_valid = area_stage_io_forward_valid;
  assign es_to_ds_forward_bus = {{{area_stage_io_forward_dependencyNeedsStall,area_stage_io_forward_writeEnabled},area_stage_io_forward_destination},area_stage_io_forward_result};
  assign es_div_enable = area_stage_io_mulDiv_divideEnable;
  assign es_mul_div_sign = area_stage_io_mulDiv_signed;
  assign es_rj_value = area_stage_io_mulDiv_operandJ;
  assign es_rkd_value = area_stage_io_mulDiv_operandKOrD;
  assign area_stage_io_csrVirtualPageNumber = csr_vppn;
  assign data_valid = area_stage_io_memory_valid;
  assign data_op = area_stage_io_memory_isWrite;
  assign data_size = area_stage_io_memory_size;
  assign data_wstrb = area_stage_io_memory_byteMask;
  assign data_wdata = area_stage_io_memory_writeData;
  assign data_addr = area_stage_io_memory_virtualAddress;
  assign data_fetch = area_stage_io_dataFetch;
  assign tlb_inst_stall = area_stage_io_tlbInstructionStall;
  assign icacop_op_en = area_stage_io_cache_instructionOperationEnable;
  assign dcacop_op_en = area_stage_io_cache_dataOperationEnable;
  assign cacop_op_mode = area_stage_io_cache_operationMode;
  assign preld_hint = area_stage_io_cache_preloadHint;
  assign preld_en = area_stage_io_cache_preloadEnable;

endmodule

module ExecuteStage (
  input  wire          io_input_valid,
  output wire          io_input_ready,
  input  wire [31:0]   io_input_payload_pc,
  input  wire [31:0]   io_input_payload_registerDataKOrD,
  input  wire [31:0]   io_input_payload_registerDataJ,
  input  wire [31:0]   io_input_payload_immediate,
  input  wire [4:0]    io_input_payload_destination,
  input  wire          io_input_payload_isStore,
  input  wire          io_input_payload_gprWrite,
  input  wire          io_input_payload_source2IsFour,
  input  wire          io_input_payload_source2IsImmediate,
  input  wire          io_input_payload_source1IsPc,
  input  wire          io_input_payload_isLoad,
  input  wire [13:0]   io_input_payload_aluOperation,
  input  wire          io_input_payload_mulDivSigned,
  input  wire [3:0]    io_input_payload_mulDivOperation,
  input  wire [1:0]    io_input_payload_memorySize,
  input  wire          io_input_payload_hasException,
  input  wire          io_input_payload_isErtn,
  input  wire [31:0]   io_input_payload_csrReadData,
  input  wire          io_input_payload_resultFromCsr,
  input  wire [13:0]   io_input_payload_csrAddress,
  input  wire          io_input_payload_csrWrite,
  input  wire          io_input_payload_csrMask,
  input  wire [8:0]    io_input_payload_exceptionCode,
  input  wire          io_input_payload_isLl,
  input  wire          io_input_payload_isSc,
  input  wire          io_input_payload_tlbSearch,
  input  wire          io_input_payload_tlbWrite,
  input  wire          io_input_payload_tlbFill,
  input  wire          io_input_payload_refetch,
  input  wire          io_input_payload_tlbRead,
  input  wire          io_input_payload_invalidateTlb,
  input  wire          io_input_payload_memorySignExtend,
  input  wire          io_input_payload_cacheOperation,
  input  wire          io_input_payload_preload,
  input  wire          io_input_payload_isBranch,
  input  wire          io_input_payload_instructionCacheMiss,
  input  wire          io_input_payload_isPredictableBranch,
  input  wire          io_input_payload_predictionError,
  input  wire          io_input_payload_idle,
  input  wire [31:0]   io_input_payload_instruction,
  input  wire [63:0]   io_input_payload_timer,
  input  wire          io_input_payload_isCounterInstruction,
  input  wire [7:0]    io_input_payload_loadEvent,
  input  wire [7:0]    io_input_payload_storeEvent,
  input  wire          io_input_payload_csrRstatEvent,
  output wire          io_output_valid,
  input  wire          io_output_ready,
  output wire [31:0]   io_output_payload_pc,
  output wire [31:0]   io_output_payload_executeResult,
  output wire [4:0]    io_output_payload_destination,
  output wire          io_output_payload_gprWrite,
  output wire          io_output_payload_isLoad,
  output wire [3:0]    io_output_payload_mulDivOperation,
  output wire [1:0]    io_output_payload_memorySize,
  output wire          io_output_payload_hasException,
  output wire          io_output_payload_isErtn,
  output wire [31:0]   io_output_payload_csrResult,
  output wire [13:0]   io_output_payload_csrAddress,
  output wire          io_output_payload_csrWrite,
  output wire [9:0]    io_output_payload_exceptionCode,
  output wire          io_output_payload_isLl,
  output wire          io_output_payload_isSc,
  output wire          io_output_payload_isStore,
  output wire          io_output_payload_tlbSearch,
  output wire          io_output_payload_tlbWrite,
  output wire          io_output_payload_tlbFill,
  output wire          io_output_payload_refetch,
  output wire          io_output_payload_tlbRead,
  output wire          io_output_payload_invalidateTlb,
  output wire [9:0]    io_output_payload_invalidateTlbAsid,
  output wire [18:0]   io_output_payload_invalidateTlbVpn,
  output wire          io_output_payload_memorySignExtend,
  output wire          io_output_payload_instructionCacheOperation,
  output wire          io_output_payload_isBranch,
  output wire          io_output_payload_instructionCacheMiss,
  output wire          io_output_payload_isPredictableBranch,
  output wire          io_output_payload_predictionError,
  output wire          io_output_payload_preload,
  output wire          io_output_payload_cacheOperation,
  output wire          io_output_payload_idle,
  output wire [31:0]   io_output_payload_errorVirtualAddress,
  output wire [31:0]   io_output_payload_instruction,
  output wire [63:0]   io_output_payload_timer,
  output wire          io_output_payload_isCounterInstruction,
  output wire [7:0]    io_output_payload_loadEvent,
  output wire [31:0]   io_output_payload_memoryVirtualAddress,
  output wire [7:0]    io_output_payload_storeEvent,
  output wire [31:0]   io_output_payload_storeData,
  output wire          io_output_payload_csrRstatEvent,
  output wire [31:0]   io_output_payload_csrData,
  output wire          io_forward_valid,
  output wire          io_forward_dependencyNeedsStall,
  output wire          io_forward_writeEnabled,
  output wire [4:0]    io_forward_destination,
  output wire [31:0]   io_forward_result,
  output wire          io_mulDiv_divideEnable,
  output wire          io_mulDiv_signed,
  output wire [31:0]   io_mulDiv_operandJ,
  output wire [31:0]   io_mulDiv_operandKOrD,
  input  wire          io_divideComplete,
  input  wire          io_flush_exception,
  input  wire          io_flush_ertn,
  input  wire          io_flush_refetch,
  input  wire          io_flush_instructionCacheOperation,
  input  wire          io_flush_idle,
  input  wire          io_memoryFlush,
  input  wire          io_memoryWritesTlbEntryHigh,
  input  wire          io_instructionCacheUnbusy,
  input  wire          io_memoryAddressAccepted,
  input  wire [18:0]   io_csrVirtualPageNumber,
  output wire          io_memory_valid,
  output wire          io_memory_isWrite,
  output wire [2:0]    io_memory_size,
  output wire [3:0]    io_memory_byteMask,
  output wire [31:0]   io_memory_writeData,
  output wire [31:0]   io_memory_virtualAddress,
  output wire          io_cache_instructionOperationEnable,
  output wire          io_cache_dataOperationEnable,
  output wire [1:0]    io_cache_operationMode,
  output wire          io_cache_preloadEnable,
  output wire [4:0]    io_cache_preloadHint,
  output wire          io_tlbInstructionStall,
  output wire          io_dataFetch,
  input  wire          clk,
  input  wire          reset
);

  wire       [31:0]   alu_alu_src1;
  wire       [31:0]   alu_alu_src2;
  wire       [31:0]   alu_alu_result;
  wire       [2:0]    _zz_io_memory_size;
  reg                 occupied;
  reg        [31:0]   payload_pc;
  reg        [31:0]   payload_registerDataKOrD;
  reg        [31:0]   payload_registerDataJ;
  reg        [31:0]   payload_immediate;
  reg        [4:0]    payload_destination;
  reg                 payload_isStore;
  reg                 payload_gprWrite;
  reg                 payload_source2IsFour;
  reg                 payload_source2IsImmediate;
  reg                 payload_source1IsPc;
  reg                 payload_isLoad;
  reg        [13:0]   payload_aluOperation;
  reg                 payload_mulDivSigned;
  reg        [3:0]    payload_mulDivOperation;
  reg        [1:0]    payload_memorySize;
  reg                 payload_hasException;
  reg                 payload_isErtn;
  reg        [31:0]   payload_csrReadData;
  reg                 payload_resultFromCsr;
  reg        [13:0]   payload_csrAddress;
  reg                 payload_csrWrite;
  reg                 payload_csrMask;
  reg        [8:0]    payload_exceptionCode;
  reg                 payload_isLl;
  reg                 payload_isSc;
  reg                 payload_tlbSearch;
  reg                 payload_tlbWrite;
  reg                 payload_tlbFill;
  reg                 payload_refetch;
  reg                 payload_tlbRead;
  reg                 payload_invalidateTlb;
  reg                 payload_memorySignExtend;
  reg                 payload_cacheOperation;
  reg                 payload_preload;
  reg                 payload_isBranch;
  reg                 payload_instructionCacheMiss;
  reg                 payload_isPredictableBranch;
  reg                 payload_predictionError;
  reg                 payload_idle;
  reg        [31:0]   payload_instruction;
  reg        [63:0]   payload_timer;
  reg                 payload_isCounterInstruction;
  reg        [7:0]    payload_loadEvent;
  reg        [7:0]    payload_storeEvent;
  reg                 payload_csrRstatEvent;
  wire                laccRequest;
  wire                laccResponseValid;
  wire                laccDataValid;
  wire                laccDataRead;
  wire       [31:0]   laccDataAddress;
  wire       [31:0]   laccDataWriteData;
  wire       [1:0]    laccDataSize;
  wire       [31:0]   executeResult;
  wire                accessMemory;
  wire       [1:0]    addressLow;
  wire                alignmentException;
  wire                hasException;
  wire       [9:0]    exceptionCode;
  wire                divideEnable;
  wire                multiplyEnable;
  wire                divideStall;
  wire                sideEffectEnable;
  wire                instructionCacheOperation;
  wire                dataCacheOperation;
  wire                preloadInstruction;
  wire                instructionCacheStall;
  wire                tlbSearchStall;
  wire                laccStall;
  wire                waitsForAddress;
  wire                addressReady;
  wire                readyGo;
  wire                when_ExecuteStage_l183;
  wire                when_ExecuteStage_l188;
  wire       [3:0]    byteMask;
  reg        [3:0]    halfMask;
  wire       [6:0]    byteSizeTerm;
  wire       [6:0]    halfSizeTerm;
  wire       [6:0]    wordSizeTerm;
  wire       [6:0]    maskAndSize;
  reg        [31:0]   byteContent;
  reg        [31:0]   halfContent;
  wire       [31:0]   storeData;
  wire       [3:0]    laccByteMask;
  reg        [3:0]    laccHalfMask;
  wire       [3:0]    selectedLaccMask;
  wire       [31:0]   csrMaskResult;

  assign _zz_io_memory_size = {1'd0, laccDataSize};
  OpenLa500Alu alu (
    .alu_op     (payload_aluOperation[13:0]), //i
    .alu_src1   (alu_alu_src1[31:0]        ), //i
    .alu_src2   (alu_alu_src2[31:0]        ), //i
    .alu_result (alu_alu_result[31:0]      )  //o
  );
  assign alu_alu_src1 = (payload_source1IsPc ? payload_pc : payload_registerDataJ);
  assign alu_alu_src2 = (payload_source2IsImmediate ? payload_immediate : (payload_source2IsFour ? 32'h00000004 : payload_registerDataKOrD));
  assign laccRequest = 1'b0;
  assign laccResponseValid = 1'b0;
  assign laccDataValid = 1'b0;
  assign laccDataRead = 1'b0;
  assign laccDataAddress = 32'h0;
  assign laccDataWriteData = 32'h0;
  assign laccDataSize = 2'b00;
  assign executeResult = (payload_resultFromCsr ? payload_csrReadData : alu_alu_result);
  assign accessMemory = (payload_isLoad || payload_isStore);
  assign addressLow = alu_alu_result[1 : 0];
  assign alignmentException = (accessMemory && ((payload_memorySize[1] && addressLow[0]) || ((! (|payload_memorySize)) && (|addressLow))));
  assign hasException = (payload_hasException || alignmentException);
  assign exceptionCode = {alignmentException,payload_exceptionCode};
  assign divideEnable = ((payload_mulDivOperation[2] || payload_mulDivOperation[3]) && occupied);
  assign multiplyEnable = (payload_mulDivOperation[0] || payload_mulDivOperation[1]);
  assign divideStall = (divideEnable && (! io_divideComplete));
  assign sideEffectEnable = ((((occupied && (! hasException)) && io_output_ready) && (! ((((io_flush_exception || io_flush_ertn) || io_flush_refetch) || io_flush_instructionCacheOperation) || io_flush_idle))) && (! io_memoryFlush));
  assign instructionCacheOperation = (payload_cacheOperation && (payload_destination[2 : 0] == 3'b000));
  assign dataCacheOperation = (payload_cacheOperation && (payload_destination[2 : 0] == 3'b001));
  assign preloadInstruction = (payload_preload && ((payload_destination == 5'h0) || (payload_destination == 5'h08)));
  assign instructionCacheStall = ((instructionCacheOperation && sideEffectEnable) && (! io_instructionCacheUnbusy));
  assign tlbSearchStall = (payload_tlbSearch && io_memoryWritesTlbEntryHigh);
  assign laccStall = (laccRequest && (! laccResponseValid));
  assign waitsForAddress = ((accessMemory || dataCacheOperation) || preloadInstruction);
  assign addressReady = (sideEffectEnable && io_memoryAddressAccepted);
  assign readyGo = ((((! divideStall) && (! laccStall)) && (((addressReady || (! waitsForAddress)) && (! tlbSearchStall)) && (! instructionCacheStall))) || hasException);
  assign io_input_ready = ((! occupied) || (readyGo && io_output_ready));
  assign io_output_valid = (occupied && readyGo);
  assign when_ExecuteStage_l183 = ((((io_flush_exception || io_flush_ertn) || io_flush_refetch) || io_flush_instructionCacheOperation) || io_flush_idle);
  assign when_ExecuteStage_l188 = (io_input_valid && io_input_ready);
  assign byteMask = (4'b0001 <<< addressLow);
  always @(*) begin
    halfMask[0] = (addressLow == 2'b00);
    halfMask[1] = (addressLow == 2'b00);
    halfMask[2] = (addressLow == 2'b10);
    halfMask[3] = (addressLow == 2'b10);
  end

  assign byteSizeTerm = (payload_memorySize[0] ? {byteMask,3'b000} : 7'h0);
  assign halfSizeTerm = (payload_memorySize[1] ? {halfMask,3'b001} : 7'h0);
  assign wordSizeTerm = ((! (|payload_memorySize)) ? {4'b1111,3'b010} : 7'h0);
  assign maskAndSize = ((byteSizeTerm | halfSizeTerm) | wordSizeTerm);
  always @(*) begin
    byteContent[7 : 0] = (byteMask[0] ? payload_registerDataKOrD[7 : 0] : 8'h0);
    byteContent[15 : 8] = (byteMask[1] ? payload_registerDataKOrD[7 : 0] : 8'h0);
    byteContent[23 : 16] = (byteMask[2] ? payload_registerDataKOrD[7 : 0] : 8'h0);
    byteContent[31 : 24] = (byteMask[3] ? payload_registerDataKOrD[7 : 0] : 8'h0);
  end

  always @(*) begin
    halfContent[15 : 0] = (halfMask[0] ? payload_registerDataKOrD[15 : 0] : 16'h0);
    halfContent[31 : 16] = (halfMask[3] ? payload_registerDataKOrD[15 : 0] : 16'h0);
  end

  assign storeData = (((payload_memorySize[0] ? byteContent : 32'h0) | (payload_memorySize[1] ? halfContent : 32'h0)) | ((! (|payload_memorySize)) ? payload_registerDataKOrD : 32'h0));
  assign laccByteMask = (4'b0001 <<< laccDataAddress[1 : 0]);
  always @(*) begin
    laccHalfMask[0] = (! (|laccDataAddress));
    laccHalfMask[1] = (! laccDataAddress[1]);
    laccHalfMask[2] = (^laccDataAddress);
    laccHalfMask[3] = laccDataAddress[1];
  end

  assign selectedLaccMask = ((laccDataSize == 2'b00) ? laccByteMask : ((laccDataSize == 2'b01) ? laccHalfMask : 4'b1111));
  assign io_memory_valid = ((accessMemory && sideEffectEnable) || laccDataValid);
  assign io_memory_isWrite = (laccDataValid ? (! laccDataRead) : ((payload_isStore && (! payload_cacheOperation)) && (! payload_preload)));
  assign io_memory_size = (laccDataValid ? _zz_io_memory_size : maskAndSize[2 : 0]);
  assign io_memory_byteMask = (laccDataValid ? selectedLaccMask : maskAndSize[6 : 3]);
  assign io_memory_writeData = (laccDataValid ? laccDataWriteData : storeData);
  assign io_memory_virtualAddress = (laccDataValid ? laccDataAddress : (payload_tlbSearch ? {io_csrVirtualPageNumber,13'h0} : alu_alu_result));
  assign io_cache_instructionOperationEnable = (instructionCacheOperation && sideEffectEnable);
  assign io_cache_dataOperationEnable = (dataCacheOperation && sideEffectEnable);
  assign io_cache_operationMode = payload_destination[4 : 3];
  assign io_cache_preloadHint = payload_destination;
  assign io_cache_preloadEnable = (preloadInstruction && sideEffectEnable);
  assign io_dataFetch = (((((io_memory_valid || dataCacheOperation) || io_cache_preloadEnable) && io_memoryAddressAccepted) || (((instructionCacheOperation || payload_tlbSearch) && readyGo) && io_output_ready)) || laccDataValid);
  assign io_tlbInstructionStall = ((payload_tlbSearch || payload_tlbRead) && occupied);
  assign io_mulDiv_divideEnable = divideEnable;
  assign io_mulDiv_signed = payload_mulDivSigned;
  assign io_mulDiv_operandJ = payload_registerDataJ;
  assign io_mulDiv_operandKOrD = payload_registerDataKOrD;
  assign io_forward_valid = occupied;
  assign io_forward_dependencyNeedsStall = ((payload_isLoad || divideEnable) || multiplyEnable);
  assign io_forward_writeEnabled = ((payload_gprWrite && (payload_destination != 5'h0)) && occupied);
  assign io_forward_destination = payload_destination;
  assign io_forward_result = executeResult;
  assign csrMaskResult = ((payload_registerDataJ & payload_registerDataKOrD) | ((~ payload_registerDataJ) & payload_csrReadData));
  assign io_output_payload_pc = payload_pc;
  assign io_output_payload_executeResult = executeResult;
  assign io_output_payload_destination = payload_destination;
  assign io_output_payload_gprWrite = payload_gprWrite;
  assign io_output_payload_isLoad = payload_isLoad;
  assign io_output_payload_mulDivOperation = payload_mulDivOperation;
  assign io_output_payload_memorySize = payload_memorySize;
  assign io_output_payload_hasException = hasException;
  assign io_output_payload_isErtn = payload_isErtn;
  assign io_output_payload_csrResult = (payload_csrMask ? csrMaskResult : payload_registerDataKOrD);
  assign io_output_payload_csrAddress = payload_csrAddress;
  assign io_output_payload_csrWrite = payload_csrWrite;
  assign io_output_payload_exceptionCode = exceptionCode;
  assign io_output_payload_isLl = payload_isLl;
  assign io_output_payload_isSc = payload_isSc;
  assign io_output_payload_isStore = payload_isStore;
  assign io_output_payload_tlbSearch = payload_tlbSearch;
  assign io_output_payload_tlbWrite = payload_tlbWrite;
  assign io_output_payload_tlbFill = payload_tlbFill;
  assign io_output_payload_refetch = payload_refetch;
  assign io_output_payload_tlbRead = payload_tlbRead;
  assign io_output_payload_invalidateTlb = payload_invalidateTlb;
  assign io_output_payload_invalidateTlbAsid = payload_registerDataJ[9 : 0];
  assign io_output_payload_invalidateTlbVpn = payload_registerDataKOrD[31 : 13];
  assign io_output_payload_memorySignExtend = payload_memorySignExtend;
  assign io_output_payload_instructionCacheOperation = io_cache_instructionOperationEnable;
  assign io_output_payload_isBranch = payload_isBranch;
  assign io_output_payload_instructionCacheMiss = payload_instructionCacheMiss;
  assign io_output_payload_isPredictableBranch = payload_isPredictableBranch;
  assign io_output_payload_predictionError = payload_predictionError;
  assign io_output_payload_preload = preloadInstruction;
  assign io_output_payload_cacheOperation = payload_cacheOperation;
  assign io_output_payload_idle = payload_idle;
  assign io_output_payload_errorVirtualAddress = alu_alu_result;
  assign io_output_payload_instruction = payload_instruction;
  assign io_output_payload_timer = payload_timer;
  assign io_output_payload_isCounterInstruction = payload_isCounterInstruction;
  assign io_output_payload_loadEvent = payload_loadEvent;
  assign io_output_payload_memoryVirtualAddress = io_memory_virtualAddress;
  assign io_output_payload_storeEvent = payload_storeEvent;
  assign io_output_payload_storeData = io_memory_writeData;
  assign io_output_payload_csrRstatEvent = payload_csrRstatEvent;
  assign io_output_payload_csrData = payload_csrReadData;
  always @(posedge clk) begin
    if(reset) begin
      occupied <= 1'b0;
    end else begin
      if(when_ExecuteStage_l183) begin
        occupied <= 1'b0;
      end else begin
        if(io_input_ready) begin
          occupied <= io_input_valid;
        end
      end
    end
  end

  always @(posedge clk) begin
    if(when_ExecuteStage_l188) begin
      payload_pc <= io_input_payload_pc;
      payload_registerDataKOrD <= io_input_payload_registerDataKOrD;
      payload_registerDataJ <= io_input_payload_registerDataJ;
      payload_immediate <= io_input_payload_immediate;
      payload_destination <= io_input_payload_destination;
      payload_isStore <= io_input_payload_isStore;
      payload_gprWrite <= io_input_payload_gprWrite;
      payload_source2IsFour <= io_input_payload_source2IsFour;
      payload_source2IsImmediate <= io_input_payload_source2IsImmediate;
      payload_source1IsPc <= io_input_payload_source1IsPc;
      payload_isLoad <= io_input_payload_isLoad;
      payload_aluOperation <= io_input_payload_aluOperation;
      payload_mulDivSigned <= io_input_payload_mulDivSigned;
      payload_mulDivOperation <= io_input_payload_mulDivOperation;
      payload_memorySize <= io_input_payload_memorySize;
      payload_hasException <= io_input_payload_hasException;
      payload_isErtn <= io_input_payload_isErtn;
      payload_csrReadData <= io_input_payload_csrReadData;
      payload_resultFromCsr <= io_input_payload_resultFromCsr;
      payload_csrAddress <= io_input_payload_csrAddress;
      payload_csrWrite <= io_input_payload_csrWrite;
      payload_csrMask <= io_input_payload_csrMask;
      payload_exceptionCode <= io_input_payload_exceptionCode;
      payload_isLl <= io_input_payload_isLl;
      payload_isSc <= io_input_payload_isSc;
      payload_tlbSearch <= io_input_payload_tlbSearch;
      payload_tlbWrite <= io_input_payload_tlbWrite;
      payload_tlbFill <= io_input_payload_tlbFill;
      payload_refetch <= io_input_payload_refetch;
      payload_tlbRead <= io_input_payload_tlbRead;
      payload_invalidateTlb <= io_input_payload_invalidateTlb;
      payload_memorySignExtend <= io_input_payload_memorySignExtend;
      payload_cacheOperation <= io_input_payload_cacheOperation;
      payload_preload <= io_input_payload_preload;
      payload_isBranch <= io_input_payload_isBranch;
      payload_instructionCacheMiss <= io_input_payload_instructionCacheMiss;
      payload_isPredictableBranch <= io_input_payload_isPredictableBranch;
      payload_predictionError <= io_input_payload_predictionError;
      payload_idle <= io_input_payload_idle;
      payload_instruction <= io_input_payload_instruction;
      payload_timer <= io_input_payload_timer;
      payload_isCounterInstruction <= io_input_payload_isCounterInstruction;
      payload_loadEvent <= io_input_payload_loadEvent;
      payload_storeEvent <= io_input_payload_storeEvent;
      payload_csrRstatEvent <= io_input_payload_csrRstatEvent;
    end
  end


endmodule

module OpenLa500Alu (
  input  wire [13:0]   alu_op,
  input  wire [31:0]   alu_src1,
  input  wire [31:0]   alu_src2,
  output wire [31:0]   alu_result
);

  wire       [32:0]   _zz_adder;
  wire       [32:0]   _zz_adder_1;
  wire       [31:0]   _zz_adder_2;
  wire       [32:0]   _zz_adder_3;
  wire       [31:0]   _zz_adder_4;
  wire       [32:0]   _zz_adder_5;
  wire       [0:0]    _zz_adder_6;
  wire       [0:0]    _zz_sltResult;
  wire       [0:0]    _zz_sltuResult;
  wire       [31:0]   _zz_sllResult;
  wire       [31:0]   _zz_logicalRightResult;
  wire       [31:0]   _zz_arithmeticRightResult;
  wire       [31:0]   _zz_arithmeticRightResult_1;
  wire                subtract;
  wire       [31:0]   adderB;
  wire       [32:0]   adder;
  wire       [31:0]   addSubResult;
  wire                signedLess;
  wire       [31:0]   sltResult;
  wire       [31:0]   sltuResult;
  wire       [31:0]   andResult;
  wire       [31:0]   andnResult;
  wire       [31:0]   orResult;
  wire       [31:0]   ornResult;
  wire       [31:0]   norResult;
  wire       [31:0]   xorResult;
  wire       [4:0]    shiftAmount;
  wire       [31:0]   sllResult;
  wire       [31:0]   logicalRightResult;
  wire       [31:0]   arithmeticRightResult;
  wire       [31:0]   shiftRightResult;
  wire                when_OpenLa500Alu_l71;
  reg        [31:0]   resultTerms_0;
  wire                when_OpenLa500Alu_l71_1;
  reg        [31:0]   resultTerms_1;
  wire                when_OpenLa500Alu_l71_2;
  reg        [31:0]   resultTerms_2;
  wire                when_OpenLa500Alu_l71_3;
  reg        [31:0]   resultTerms_3;
  wire                when_OpenLa500Alu_l71_4;
  reg        [31:0]   resultTerms_4;
  wire                when_OpenLa500Alu_l71_5;
  reg        [31:0]   resultTerms_5;
  wire                when_OpenLa500Alu_l71_6;
  reg        [31:0]   resultTerms_6;
  wire                when_OpenLa500Alu_l71_7;
  reg        [31:0]   resultTerms_7;
  wire                when_OpenLa500Alu_l71_8;
  reg        [31:0]   resultTerms_8;
  wire                when_OpenLa500Alu_l71_9;
  reg        [31:0]   resultTerms_9;
  wire                when_OpenLa500Alu_l71_10;
  reg        [31:0]   resultTerms_10;
  wire                when_OpenLa500Alu_l71_11;
  reg        [31:0]   resultTerms_11;

  assign _zz_adder = (_zz_adder_1 + _zz_adder_3);
  assign _zz_adder_2 = alu_src1;
  assign _zz_adder_1 = {1'd0, _zz_adder_2};
  assign _zz_adder_4 = adderB;
  assign _zz_adder_3 = {1'd0, _zz_adder_4};
  assign _zz_adder_6 = subtract;
  assign _zz_adder_5 = {32'd0, _zz_adder_6};
  assign _zz_sltResult = signedLess;
  assign _zz_sltuResult = (! adder[32]);
  assign _zz_sllResult = (alu_src1 <<< shiftAmount);
  assign _zz_logicalRightResult = (alu_src1 >>> shiftAmount);
  assign _zz_arithmeticRightResult = ($signed(_zz_arithmeticRightResult_1) >>> shiftAmount);
  assign _zz_arithmeticRightResult_1 = alu_src1;
  assign subtract = ((alu_op[1] || alu_op[2]) || alu_op[3]);
  assign adderB = (subtract ? (~ alu_src2) : alu_src2);
  assign adder = (_zz_adder + _zz_adder_5);
  assign addSubResult = adder[31 : 0];
  assign signedLess = ((alu_src1[31] && (! alu_src2[31])) || ((alu_src1[31] == alu_src2[31]) && addSubResult[31]));
  assign sltResult = {31'd0, _zz_sltResult};
  assign sltuResult = {31'd0, _zz_sltuResult};
  assign andResult = (alu_src1 & alu_src2);
  assign andnResult = (alu_src1 & (~ alu_src2));
  assign orResult = (alu_src1 | alu_src2);
  assign ornResult = (alu_src1 | (~ alu_src2));
  assign norResult = (~ orResult);
  assign xorResult = (alu_src1 ^ alu_src2);
  assign shiftAmount = alu_src2[4 : 0];
  assign sllResult = _zz_sllResult;
  assign logicalRightResult = _zz_logicalRightResult;
  assign arithmeticRightResult = _zz_arithmeticRightResult;
  assign shiftRightResult = (alu_op[10] ? arithmeticRightResult : logicalRightResult);
  assign when_OpenLa500Alu_l71 = (alu_op[0] || alu_op[1]);
  always @(*) begin
    resultTerms_0 = 32'h0;
    if(when_OpenLa500Alu_l71) begin
      resultTerms_0 = addSubResult;
    end
  end

  assign when_OpenLa500Alu_l71_1 = alu_op[2];
  always @(*) begin
    resultTerms_1 = 32'h0;
    if(when_OpenLa500Alu_l71_1) begin
      resultTerms_1 = sltResult;
    end
  end

  assign when_OpenLa500Alu_l71_2 = alu_op[3];
  always @(*) begin
    resultTerms_2 = 32'h0;
    if(when_OpenLa500Alu_l71_2) begin
      resultTerms_2 = sltuResult;
    end
  end

  assign when_OpenLa500Alu_l71_3 = alu_op[4];
  always @(*) begin
    resultTerms_3 = 32'h0;
    if(when_OpenLa500Alu_l71_3) begin
      resultTerms_3 = andResult;
    end
  end

  assign when_OpenLa500Alu_l71_4 = alu_op[12];
  always @(*) begin
    resultTerms_4 = 32'h0;
    if(when_OpenLa500Alu_l71_4) begin
      resultTerms_4 = andnResult;
    end
  end

  assign when_OpenLa500Alu_l71_5 = alu_op[5];
  always @(*) begin
    resultTerms_5 = 32'h0;
    if(when_OpenLa500Alu_l71_5) begin
      resultTerms_5 = norResult;
    end
  end

  assign when_OpenLa500Alu_l71_6 = alu_op[6];
  always @(*) begin
    resultTerms_6 = 32'h0;
    if(when_OpenLa500Alu_l71_6) begin
      resultTerms_6 = orResult;
    end
  end

  assign when_OpenLa500Alu_l71_7 = alu_op[13];
  always @(*) begin
    resultTerms_7 = 32'h0;
    if(when_OpenLa500Alu_l71_7) begin
      resultTerms_7 = ornResult;
    end
  end

  assign when_OpenLa500Alu_l71_8 = alu_op[7];
  always @(*) begin
    resultTerms_8 = 32'h0;
    if(when_OpenLa500Alu_l71_8) begin
      resultTerms_8 = xorResult;
    end
  end

  assign when_OpenLa500Alu_l71_9 = alu_op[11];
  always @(*) begin
    resultTerms_9 = 32'h0;
    if(when_OpenLa500Alu_l71_9) begin
      resultTerms_9 = alu_src2;
    end
  end

  assign when_OpenLa500Alu_l71_10 = alu_op[8];
  always @(*) begin
    resultTerms_10 = 32'h0;
    if(when_OpenLa500Alu_l71_10) begin
      resultTerms_10 = sllResult;
    end
  end

  assign when_OpenLa500Alu_l71_11 = (alu_op[9] || alu_op[10]);
  always @(*) begin
    resultTerms_11 = 32'h0;
    if(when_OpenLa500Alu_l71_11) begin
      resultTerms_11 = shiftRightResult;
    end
  end

  assign alu_result = (((((((((((resultTerms_0 | resultTerms_1) | resultTerms_2) | resultTerms_3) | resultTerms_4) | resultTerms_5) | resultTerms_6) | resultTerms_7) | resultTerms_8) | resultTerms_9) | resultTerms_10) | resultTerms_11);

endmodule
