// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : mem_stage



module mem_stage (
  input  wire          clk,
  input  wire          reset,
  input  wire          ws_allowin,
  output wire          ms_allowin,
  input  wire          es_to_ms_valid,
  input  wire [424:0]  es_to_ms_bus,
  output wire          ms_to_ws_valid,
  output wire [492:0]  ms_to_ws_bus,
  output wire [38:0]   ms_to_ds_forward_bus,
  output wire          ms_to_ds_valid,
  input  wire [31:0]   div_result,
  input  wire [31:0]   mod_result,
  input  wire [63:0]   mul_result,
  input  wire          excp_flush,
  input  wire          ertn_flush,
  input  wire          refetch_flush,
  input  wire          icacop_flush,
  input  wire          idle_flush,
  output wire          tlb_inst_stall,
  output wire          ms_wr_tlbehi,
  output wire          ms_flush,
  input  wire          data_data_ok,
  input  wire          dcache_miss,
  input  wire [31:0]   data_rdata,
  output wire          data_uncache_en,
  output wire          tlb_excp_cancel_req,
  output wire          sc_cancel_req,
  input  wire          csr_pg,
  input  wire          csr_da,
  input  wire [31:0]   csr_dmw0,
  input  wire [31:0]   csr_dmw1,
  input  wire [1:0]    csr_plv,
  input  wire [1:0]    csr_datm,
  input  wire          disable_cache,
  input  wire [27:0]   lladdr,
  input  wire [7:0]    data_index_diff,
  input  wire [19:0]   data_tag_diff,
  input  wire [3:0]    data_offset_diff,
  output wire          data_addr_trans_en,
  output wire          dmw0_en,
  output wire          dmw1_en,
  output wire          cacop_op_mode_di,
  input  wire          data_tlb_found,
  input  wire [4:0]    data_tlb_index,
  input  wire          data_tlb_v,
  input  wire          data_tlb_d,
  input  wire [1:0]    data_tlb_mat,
  input  wire [1:0]    data_tlb_plv,
  input  wire [19:0]   data_tlb_ppn
);

  wire       [31:0]   area_stage_io_input_payload_pc;
  wire       [31:0]   area_stage_io_input_payload_executeResult;
  wire       [4:0]    area_stage_io_input_payload_destination;
  wire                area_stage_io_input_payload_gprWrite;
  wire                area_stage_io_input_payload_isLoad;
  wire       [3:0]    area_stage_io_input_payload_mulDivOperation;
  wire       [1:0]    area_stage_io_input_payload_memorySize;
  wire                area_stage_io_input_payload_hasException;
  wire                area_stage_io_input_payload_isErtn;
  wire       [31:0]   area_stage_io_input_payload_csrResult;
  wire       [13:0]   area_stage_io_input_payload_csrAddress;
  wire                area_stage_io_input_payload_csrWrite;
  wire       [9:0]    area_stage_io_input_payload_exceptionCode;
  wire                area_stage_io_input_payload_isLl;
  wire                area_stage_io_input_payload_isSc;
  wire                area_stage_io_input_payload_isStore;
  wire                area_stage_io_input_payload_tlbSearch;
  wire                area_stage_io_input_payload_tlbWrite;
  wire                area_stage_io_input_payload_tlbFill;
  wire                area_stage_io_input_payload_refetch;
  wire                area_stage_io_input_payload_tlbRead;
  wire                area_stage_io_input_payload_invalidateTlb;
  wire       [9:0]    area_stage_io_input_payload_invalidateTlbAsid;
  wire       [18:0]   area_stage_io_input_payload_invalidateTlbVpn;
  wire                area_stage_io_input_payload_memorySignExtend;
  wire                area_stage_io_input_payload_instructionCacheOperation;
  wire                area_stage_io_input_payload_isBranch;
  wire                area_stage_io_input_payload_instructionCacheMiss;
  wire                area_stage_io_input_payload_isPredictableBranch;
  wire                area_stage_io_input_payload_predictionError;
  wire                area_stage_io_input_payload_preload;
  wire                area_stage_io_input_payload_cacheOperation;
  wire                area_stage_io_input_payload_idle;
  wire       [31:0]   area_stage_io_input_payload_errorVirtualAddress;
  wire       [31:0]   area_stage_io_input_payload_instruction;
  wire       [63:0]   area_stage_io_input_payload_timer;
  wire                area_stage_io_input_payload_isCounterInstruction;
  wire       [7:0]    area_stage_io_input_payload_loadEvent;
  wire       [31:0]   area_stage_io_input_payload_memoryVirtualAddress;
  wire       [7:0]    area_stage_io_input_payload_storeEvent;
  wire       [31:0]   area_stage_io_input_payload_storeData;
  wire                area_stage_io_input_payload_csrRstatEvent;
  wire       [31:0]   area_stage_io_input_payload_csrData;
  wire                area_stage_io_csrDmw0Plv0;
  wire                area_stage_io_csrDmw0Plv3;
  wire       [2:0]    area_stage_io_csrDmw0VirtualSegment;
  wire       [1:0]    area_stage_io_csrDmw0MemoryAttribute;
  wire                area_stage_io_csrDmw1Plv0;
  wire                area_stage_io_csrDmw1Plv3;
  wire       [2:0]    area_stage_io_csrDmw1VirtualSegment;
  wire       [1:0]    area_stage_io_csrDmw1MemoryAttribute;
  wire       [4:0]    area_stage_io_dataTlbIndex;
  wire                area_stage_io_input_ready;
  wire                area_stage_io_output_valid;
  wire       [31:0]   area_stage_io_output_payload_pc;
  wire       [31:0]   area_stage_io_output_payload_finalResult;
  wire       [4:0]    area_stage_io_output_payload_destination;
  wire                area_stage_io_output_payload_gprWrite;
  wire                area_stage_io_output_payload_hasException;
  wire                area_stage_io_output_payload_isErtn;
  wire       [31:0]   area_stage_io_output_payload_csrResult;
  wire       [13:0]   area_stage_io_output_payload_csrAddress;
  wire                area_stage_io_output_payload_csrWrite;
  wire       [15:0]   area_stage_io_output_payload_exceptionCode;
  wire                area_stage_io_output_payload_isLl;
  wire                area_stage_io_output_payload_isSc;
  wire       [31:0]   area_stage_io_output_payload_errorVirtualAddress;
  wire                area_stage_io_output_payload_tlbSearch;
  wire                area_stage_io_output_payload_tlbFound;
  wire       [4:0]    area_stage_io_output_payload_tlbIndex;
  wire                area_stage_io_output_payload_tlbWrite;
  wire                area_stage_io_output_payload_tlbFill;
  wire                area_stage_io_output_payload_refetch;
  wire                area_stage_io_output_payload_tlbRead;
  wire                area_stage_io_output_payload_invalidateTlb;
  wire       [9:0]    area_stage_io_output_payload_invalidateTlbAsid;
  wire       [18:0]   area_stage_io_output_payload_invalidateTlbVpn;
  wire                area_stage_io_output_payload_instructionCacheOperation;
  wire                area_stage_io_output_payload_isBranch;
  wire                area_stage_io_output_payload_instructionCacheMiss;
  wire                area_stage_io_output_payload_accessesMemory;
  wire                area_stage_io_output_payload_dataCacheMiss;
  wire                area_stage_io_output_payload_isPredictableBranch;
  wire                area_stage_io_output_payload_predictionError;
  wire                area_stage_io_output_payload_idle;
  wire       [31:0]   area_stage_io_output_payload_physicalAddress;
  wire                area_stage_io_output_payload_dataUncached;
  wire       [31:0]   area_stage_io_output_payload_instruction;
  wire       [63:0]   area_stage_io_output_payload_timer;
  wire                area_stage_io_output_payload_isCounterInstruction;
  wire       [7:0]    area_stage_io_output_payload_loadEvent;
  wire       [31:0]   area_stage_io_output_payload_memoryPhysicalAddress;
  wire       [31:0]   area_stage_io_output_payload_memoryVirtualAddress;
  wire       [7:0]    area_stage_io_output_payload_storeEvent;
  wire       [31:0]   area_stage_io_output_payload_storeData;
  wire                area_stage_io_output_payload_csrRstatEvent;
  wire       [31:0]   area_stage_io_output_payload_csrData;
  wire                area_stage_io_dataUncached;
  wire                area_stage_io_tlbExceptionCancel;
  wire                area_stage_io_scCancel;
  wire                area_stage_io_dataAddressTranslationEnable;
  wire                area_stage_io_dmw0Enable;
  wire                area_stage_io_dmw1Enable;
  wire                area_stage_io_cacopModeDi;
  wire                area_stage_io_tlbInstructionStall;
  wire                area_stage_io_writeTlbEntryHigh;
  wire                area_stage_io_stageFlush;
  wire                area_stage_io_forward_valid;
  wire                area_stage_io_forward_dependencyNeedsStall;
  wire                area_stage_io_forward_writeEnabled;
  wire       [4:0]    area_stage_io_forward_destination;
  wire       [31:0]   area_stage_io_forward_result;
  wire       [355:0]  _zz_ms_to_ws_bus;
  wire       [282:0]  _zz_ms_to_ws_bus_1;
  wire       [209:0]  _zz_ms_to_ws_bus_2;
  wire       [0:0]    _zz_ms_to_ws_bus_3;

  assign _zz_ms_to_ws_bus = {{{{{{{{{{{_zz_ms_to_ws_bus_1,area_stage_io_output_payload_invalidateTlbVpn},area_stage_io_output_payload_invalidateTlbAsid},area_stage_io_output_payload_invalidateTlb},area_stage_io_output_payload_tlbRead},area_stage_io_output_payload_refetch},area_stage_io_output_payload_tlbFill},area_stage_io_output_payload_tlbWrite},area_stage_io_output_payload_tlbIndex},area_stage_io_output_payload_tlbFound},area_stage_io_output_payload_tlbSearch},area_stage_io_output_payload_errorVirtualAddress};
  assign _zz_ms_to_ws_bus_3 = area_stage_io_output_payload_isSc;
  assign _zz_ms_to_ws_bus_1 = {{{{{{{{{{{_zz_ms_to_ws_bus_2,area_stage_io_output_payload_instruction},area_stage_io_output_payload_dataUncached},area_stage_io_output_payload_physicalAddress},area_stage_io_output_payload_idle},area_stage_io_output_payload_predictionError},area_stage_io_output_payload_isPredictableBranch},area_stage_io_output_payload_dataCacheMiss},area_stage_io_output_payload_accessesMemory},area_stage_io_output_payload_instructionCacheMiss},area_stage_io_output_payload_isBranch},area_stage_io_output_payload_instructionCacheOperation};
  assign _zz_ms_to_ws_bus_2 = {{{{{{{{area_stage_io_output_payload_csrData,area_stage_io_output_payload_csrRstatEvent},area_stage_io_output_payload_storeData},area_stage_io_output_payload_storeEvent},area_stage_io_output_payload_memoryVirtualAddress},area_stage_io_output_payload_memoryPhysicalAddress},area_stage_io_output_payload_loadEvent},area_stage_io_output_payload_isCounterInstruction},area_stage_io_output_payload_timer};
  MemoryStage area_stage (
    .io_input_valid                              (es_to_ms_valid                                          ), //i
    .io_input_ready                              (area_stage_io_input_ready                               ), //o
    .io_input_payload_pc                         (area_stage_io_input_payload_pc[31:0]                    ), //i
    .io_input_payload_executeResult              (area_stage_io_input_payload_executeResult[31:0]         ), //i
    .io_input_payload_destination                (area_stage_io_input_payload_destination[4:0]            ), //i
    .io_input_payload_gprWrite                   (area_stage_io_input_payload_gprWrite                    ), //i
    .io_input_payload_isLoad                     (area_stage_io_input_payload_isLoad                      ), //i
    .io_input_payload_mulDivOperation            (area_stage_io_input_payload_mulDivOperation[3:0]        ), //i
    .io_input_payload_memorySize                 (area_stage_io_input_payload_memorySize[1:0]             ), //i
    .io_input_payload_hasException               (area_stage_io_input_payload_hasException                ), //i
    .io_input_payload_isErtn                     (area_stage_io_input_payload_isErtn                      ), //i
    .io_input_payload_csrResult                  (area_stage_io_input_payload_csrResult[31:0]             ), //i
    .io_input_payload_csrAddress                 (area_stage_io_input_payload_csrAddress[13:0]            ), //i
    .io_input_payload_csrWrite                   (area_stage_io_input_payload_csrWrite                    ), //i
    .io_input_payload_exceptionCode              (area_stage_io_input_payload_exceptionCode[9:0]          ), //i
    .io_input_payload_isLl                       (area_stage_io_input_payload_isLl                        ), //i
    .io_input_payload_isSc                       (area_stage_io_input_payload_isSc                        ), //i
    .io_input_payload_isStore                    (area_stage_io_input_payload_isStore                     ), //i
    .io_input_payload_tlbSearch                  (area_stage_io_input_payload_tlbSearch                   ), //i
    .io_input_payload_tlbWrite                   (area_stage_io_input_payload_tlbWrite                    ), //i
    .io_input_payload_tlbFill                    (area_stage_io_input_payload_tlbFill                     ), //i
    .io_input_payload_refetch                    (area_stage_io_input_payload_refetch                     ), //i
    .io_input_payload_tlbRead                    (area_stage_io_input_payload_tlbRead                     ), //i
    .io_input_payload_invalidateTlb              (area_stage_io_input_payload_invalidateTlb               ), //i
    .io_input_payload_invalidateTlbAsid          (area_stage_io_input_payload_invalidateTlbAsid[9:0]      ), //i
    .io_input_payload_invalidateTlbVpn           (area_stage_io_input_payload_invalidateTlbVpn[18:0]      ), //i
    .io_input_payload_memorySignExtend           (area_stage_io_input_payload_memorySignExtend            ), //i
    .io_input_payload_instructionCacheOperation  (area_stage_io_input_payload_instructionCacheOperation   ), //i
    .io_input_payload_isBranch                   (area_stage_io_input_payload_isBranch                    ), //i
    .io_input_payload_instructionCacheMiss       (area_stage_io_input_payload_instructionCacheMiss        ), //i
    .io_input_payload_isPredictableBranch        (area_stage_io_input_payload_isPredictableBranch         ), //i
    .io_input_payload_predictionError            (area_stage_io_input_payload_predictionError             ), //i
    .io_input_payload_preload                    (area_stage_io_input_payload_preload                     ), //i
    .io_input_payload_cacheOperation             (area_stage_io_input_payload_cacheOperation              ), //i
    .io_input_payload_idle                       (area_stage_io_input_payload_idle                        ), //i
    .io_input_payload_errorVirtualAddress        (area_stage_io_input_payload_errorVirtualAddress[31:0]   ), //i
    .io_input_payload_instruction                (area_stage_io_input_payload_instruction[31:0]           ), //i
    .io_input_payload_timer                      (area_stage_io_input_payload_timer[63:0]                 ), //i
    .io_input_payload_isCounterInstruction       (area_stage_io_input_payload_isCounterInstruction        ), //i
    .io_input_payload_loadEvent                  (area_stage_io_input_payload_loadEvent[7:0]              ), //i
    .io_input_payload_memoryVirtualAddress       (area_stage_io_input_payload_memoryVirtualAddress[31:0]  ), //i
    .io_input_payload_storeEvent                 (area_stage_io_input_payload_storeEvent[7:0]             ), //i
    .io_input_payload_storeData                  (area_stage_io_input_payload_storeData[31:0]             ), //i
    .io_input_payload_csrRstatEvent              (area_stage_io_input_payload_csrRstatEvent               ), //i
    .io_input_payload_csrData                    (area_stage_io_input_payload_csrData[31:0]               ), //i
    .io_output_valid                             (area_stage_io_output_valid                              ), //o
    .io_output_ready                             (ws_allowin                                              ), //i
    .io_output_payload_pc                        (area_stage_io_output_payload_pc[31:0]                   ), //o
    .io_output_payload_finalResult               (area_stage_io_output_payload_finalResult[31:0]          ), //o
    .io_output_payload_destination               (area_stage_io_output_payload_destination[4:0]           ), //o
    .io_output_payload_gprWrite                  (area_stage_io_output_payload_gprWrite                   ), //o
    .io_output_payload_hasException              (area_stage_io_output_payload_hasException               ), //o
    .io_output_payload_isErtn                    (area_stage_io_output_payload_isErtn                     ), //o
    .io_output_payload_csrResult                 (area_stage_io_output_payload_csrResult[31:0]            ), //o
    .io_output_payload_csrAddress                (area_stage_io_output_payload_csrAddress[13:0]           ), //o
    .io_output_payload_csrWrite                  (area_stage_io_output_payload_csrWrite                   ), //o
    .io_output_payload_exceptionCode             (area_stage_io_output_payload_exceptionCode[15:0]        ), //o
    .io_output_payload_isLl                      (area_stage_io_output_payload_isLl                       ), //o
    .io_output_payload_isSc                      (area_stage_io_output_payload_isSc                       ), //o
    .io_output_payload_errorVirtualAddress       (area_stage_io_output_payload_errorVirtualAddress[31:0]  ), //o
    .io_output_payload_tlbSearch                 (area_stage_io_output_payload_tlbSearch                  ), //o
    .io_output_payload_tlbFound                  (area_stage_io_output_payload_tlbFound                   ), //o
    .io_output_payload_tlbIndex                  (area_stage_io_output_payload_tlbIndex[4:0]              ), //o
    .io_output_payload_tlbWrite                  (area_stage_io_output_payload_tlbWrite                   ), //o
    .io_output_payload_tlbFill                   (area_stage_io_output_payload_tlbFill                    ), //o
    .io_output_payload_refetch                   (area_stage_io_output_payload_refetch                    ), //o
    .io_output_payload_tlbRead                   (area_stage_io_output_payload_tlbRead                    ), //o
    .io_output_payload_invalidateTlb             (area_stage_io_output_payload_invalidateTlb              ), //o
    .io_output_payload_invalidateTlbAsid         (area_stage_io_output_payload_invalidateTlbAsid[9:0]     ), //o
    .io_output_payload_invalidateTlbVpn          (area_stage_io_output_payload_invalidateTlbVpn[18:0]     ), //o
    .io_output_payload_instructionCacheOperation (area_stage_io_output_payload_instructionCacheOperation  ), //o
    .io_output_payload_isBranch                  (area_stage_io_output_payload_isBranch                   ), //o
    .io_output_payload_instructionCacheMiss      (area_stage_io_output_payload_instructionCacheMiss       ), //o
    .io_output_payload_accessesMemory            (area_stage_io_output_payload_accessesMemory             ), //o
    .io_output_payload_dataCacheMiss             (area_stage_io_output_payload_dataCacheMiss              ), //o
    .io_output_payload_isPredictableBranch       (area_stage_io_output_payload_isPredictableBranch        ), //o
    .io_output_payload_predictionError           (area_stage_io_output_payload_predictionError            ), //o
    .io_output_payload_idle                      (area_stage_io_output_payload_idle                       ), //o
    .io_output_payload_physicalAddress           (area_stage_io_output_payload_physicalAddress[31:0]      ), //o
    .io_output_payload_dataUncached              (area_stage_io_output_payload_dataUncached               ), //o
    .io_output_payload_instruction               (area_stage_io_output_payload_instruction[31:0]          ), //o
    .io_output_payload_timer                     (area_stage_io_output_payload_timer[63:0]                ), //o
    .io_output_payload_isCounterInstruction      (area_stage_io_output_payload_isCounterInstruction       ), //o
    .io_output_payload_loadEvent                 (area_stage_io_output_payload_loadEvent[7:0]             ), //o
    .io_output_payload_memoryPhysicalAddress     (area_stage_io_output_payload_memoryPhysicalAddress[31:0]), //o
    .io_output_payload_memoryVirtualAddress      (area_stage_io_output_payload_memoryVirtualAddress[31:0] ), //o
    .io_output_payload_storeEvent                (area_stage_io_output_payload_storeEvent[7:0]            ), //o
    .io_output_payload_storeData                 (area_stage_io_output_payload_storeData[31:0]            ), //o
    .io_output_payload_csrRstatEvent             (area_stage_io_output_payload_csrRstatEvent              ), //o
    .io_output_payload_csrData                   (area_stage_io_output_payload_csrData[31:0]              ), //o
    .io_divResult                                (div_result[31:0]                                        ), //i
    .io_modResult                                (mod_result[31:0]                                        ), //i
    .io_mulResult                                (mul_result[63:0]                                        ), //i
    .io_flush_exception                          (excp_flush                                              ), //i
    .io_flush_ertn                               (ertn_flush                                              ), //i
    .io_flush_refetch                            (refetch_flush                                           ), //i
    .io_flush_instructionCacheOperation          (icacop_flush                                            ), //i
    .io_flush_idle                               (idle_flush                                              ), //i
    .io_dataDataOk                               (data_data_ok                                            ), //i
    .io_dcacheMiss                               (dcache_miss                                             ), //i
    .io_dataReadData                             (data_rdata[31:0]                                        ), //i
    .io_dataUncached                             (area_stage_io_dataUncached                              ), //o
    .io_tlbExceptionCancel                       (area_stage_io_tlbExceptionCancel                        ), //o
    .io_scCancel                                 (area_stage_io_scCancel                                  ), //o
    .io_csrPage                                  (csr_pg                                                  ), //i
    .io_csrDirectAddress                         (csr_da                                                  ), //i
    .io_csrDmw0Plv0                              (area_stage_io_csrDmw0Plv0                               ), //i
    .io_csrDmw0Plv3                              (area_stage_io_csrDmw0Plv3                               ), //i
    .io_csrDmw0VirtualSegment                    (area_stage_io_csrDmw0VirtualSegment[2:0]                ), //i
    .io_csrDmw0MemoryAttribute                   (area_stage_io_csrDmw0MemoryAttribute[1:0]               ), //i
    .io_csrDmw1Plv0                              (area_stage_io_csrDmw1Plv0                               ), //i
    .io_csrDmw1Plv3                              (area_stage_io_csrDmw1Plv3                               ), //i
    .io_csrDmw1VirtualSegment                    (area_stage_io_csrDmw1VirtualSegment[2:0]                ), //i
    .io_csrDmw1MemoryAttribute                   (area_stage_io_csrDmw1MemoryAttribute[1:0]               ), //i
    .io_csrPlv                                   (csr_plv[1:0]                                            ), //i
    .io_csrDatm                                  (csr_datm[1:0]                                           ), //i
    .io_disableCache                             (disable_cache                                           ), //i
    .io_llAddress                                (lladdr[27:0]                                            ), //i
    .io_dataIndexDiff                            (data_index_diff[7:0]                                    ), //i
    .io_dataTagDiff                              (data_tag_diff[19:0]                                     ), //i
    .io_dataOffsetDiff                           (data_offset_diff[3:0]                                   ), //i
    .io_dataAddressTranslationEnable             (area_stage_io_dataAddressTranslationEnable              ), //o
    .io_dmw0Enable                               (area_stage_io_dmw0Enable                                ), //o
    .io_dmw1Enable                               (area_stage_io_dmw1Enable                                ), //o
    .io_cacopModeDi                              (area_stage_io_cacopModeDi                               ), //o
    .io_dataTlbFound                             (data_tlb_found                                          ), //i
    .io_dataTlbIndex                             (area_stage_io_dataTlbIndex[4:0]                         ), //i
    .io_dataTlbValid                             (data_tlb_v                                              ), //i
    .io_dataTlbDirty                             (data_tlb_d                                              ), //i
    .io_dataTlbMat                               (data_tlb_mat[1:0]                                       ), //i
    .io_dataTlbPlv                               (data_tlb_plv[1:0]                                       ), //i
    .io_dataTlbPpn                               (data_tlb_ppn[19:0]                                      ), //i
    .io_tlbInstructionStall                      (area_stage_io_tlbInstructionStall                       ), //o
    .io_writeTlbEntryHigh                        (area_stage_io_writeTlbEntryHigh                         ), //o
    .io_stageFlush                               (area_stage_io_stageFlush                                ), //o
    .io_forward_valid                            (area_stage_io_forward_valid                             ), //o
    .io_forward_dependencyNeedsStall             (area_stage_io_forward_dependencyNeedsStall              ), //o
    .io_forward_writeEnabled                     (area_stage_io_forward_writeEnabled                      ), //o
    .io_forward_destination                      (area_stage_io_forward_destination[4:0]                  ), //o
    .io_forward_result                           (area_stage_io_forward_result[31:0]                      ), //o
    .clk                                         (clk                                                     ), //i
    .reset                                       (reset                                                   )  //i
  );
  assign area_stage_io_input_payload_pc = es_to_ms_bus[31 : 0];
  assign area_stage_io_input_payload_executeResult = es_to_ms_bus[63 : 32];
  assign area_stage_io_input_payload_destination = es_to_ms_bus[68 : 64];
  assign area_stage_io_input_payload_gprWrite = es_to_ms_bus[69];
  assign area_stage_io_input_payload_isLoad = es_to_ms_bus[70];
  assign area_stage_io_input_payload_mulDivOperation = es_to_ms_bus[74 : 71];
  assign area_stage_io_input_payload_memorySize = es_to_ms_bus[76 : 75];
  assign area_stage_io_input_payload_hasException = es_to_ms_bus[77];
  assign area_stage_io_input_payload_isErtn = es_to_ms_bus[78];
  assign area_stage_io_input_payload_csrResult = es_to_ms_bus[110 : 79];
  assign area_stage_io_input_payload_csrAddress = es_to_ms_bus[124 : 111];
  assign area_stage_io_input_payload_csrWrite = es_to_ms_bus[125];
  assign area_stage_io_input_payload_exceptionCode = es_to_ms_bus[135 : 126];
  assign area_stage_io_input_payload_isLl = es_to_ms_bus[136];
  assign area_stage_io_input_payload_isSc = es_to_ms_bus[137];
  assign area_stage_io_input_payload_isStore = es_to_ms_bus[138];
  assign area_stage_io_input_payload_tlbSearch = es_to_ms_bus[139];
  assign area_stage_io_input_payload_tlbWrite = es_to_ms_bus[140];
  assign area_stage_io_input_payload_tlbFill = es_to_ms_bus[141];
  assign area_stage_io_input_payload_refetch = es_to_ms_bus[142];
  assign area_stage_io_input_payload_tlbRead = es_to_ms_bus[143];
  assign area_stage_io_input_payload_invalidateTlb = es_to_ms_bus[144];
  assign area_stage_io_input_payload_invalidateTlbAsid = es_to_ms_bus[154 : 145];
  assign area_stage_io_input_payload_invalidateTlbVpn = es_to_ms_bus[173 : 155];
  assign area_stage_io_input_payload_memorySignExtend = es_to_ms_bus[174];
  assign area_stage_io_input_payload_instructionCacheOperation = es_to_ms_bus[175];
  assign area_stage_io_input_payload_isBranch = es_to_ms_bus[176];
  assign area_stage_io_input_payload_instructionCacheMiss = es_to_ms_bus[177];
  assign area_stage_io_input_payload_isPredictableBranch = es_to_ms_bus[178];
  assign area_stage_io_input_payload_predictionError = es_to_ms_bus[179];
  assign area_stage_io_input_payload_preload = es_to_ms_bus[180];
  assign area_stage_io_input_payload_cacheOperation = es_to_ms_bus[181];
  assign area_stage_io_input_payload_idle = es_to_ms_bus[182];
  assign area_stage_io_input_payload_errorVirtualAddress = es_to_ms_bus[214 : 183];
  assign area_stage_io_input_payload_instruction = es_to_ms_bus[246 : 215];
  assign area_stage_io_input_payload_timer = es_to_ms_bus[310 : 247];
  assign area_stage_io_input_payload_isCounterInstruction = es_to_ms_bus[311];
  assign area_stage_io_input_payload_loadEvent = es_to_ms_bus[319 : 312];
  assign area_stage_io_input_payload_memoryVirtualAddress = es_to_ms_bus[351 : 320];
  assign area_stage_io_input_payload_storeEvent = es_to_ms_bus[359 : 352];
  assign area_stage_io_input_payload_storeData = es_to_ms_bus[391 : 360];
  assign area_stage_io_input_payload_csrRstatEvent = es_to_ms_bus[392];
  assign area_stage_io_input_payload_csrData = es_to_ms_bus[424 : 393];
  assign ms_allowin = area_stage_io_input_ready;
  assign ms_to_ws_valid = area_stage_io_output_valid;
  assign ms_to_ws_bus = {{{{{{{{{{{{_zz_ms_to_ws_bus,_zz_ms_to_ws_bus_3},area_stage_io_output_payload_isLl},area_stage_io_output_payload_exceptionCode},area_stage_io_output_payload_csrWrite},area_stage_io_output_payload_csrAddress},area_stage_io_output_payload_csrResult},area_stage_io_output_payload_isErtn},area_stage_io_output_payload_hasException},area_stage_io_output_payload_gprWrite},area_stage_io_output_payload_destination},area_stage_io_output_payload_finalResult},area_stage_io_output_payload_pc};
  assign ms_to_ds_valid = area_stage_io_forward_valid;
  assign ms_to_ds_forward_bus = {{{area_stage_io_forward_dependencyNeedsStall,area_stage_io_forward_writeEnabled},area_stage_io_forward_destination},area_stage_io_forward_result};
  assign area_stage_io_csrDmw0Plv0 = csr_dmw0[0];
  assign area_stage_io_csrDmw0Plv3 = csr_dmw0[3];
  assign area_stage_io_csrDmw0VirtualSegment = csr_dmw0[31 : 29];
  assign area_stage_io_csrDmw0MemoryAttribute = csr_dmw0[5 : 4];
  assign area_stage_io_csrDmw1Plv0 = csr_dmw1[0];
  assign area_stage_io_csrDmw1Plv3 = csr_dmw1[3];
  assign area_stage_io_csrDmw1VirtualSegment = csr_dmw1[31 : 29];
  assign area_stage_io_csrDmw1MemoryAttribute = csr_dmw1[5 : 4];
  assign area_stage_io_dataTlbIndex = data_tlb_index;
  assign tlb_inst_stall = area_stage_io_tlbInstructionStall;
  assign ms_wr_tlbehi = area_stage_io_writeTlbEntryHigh;
  assign ms_flush = area_stage_io_stageFlush;
  assign data_uncache_en = area_stage_io_dataUncached;
  assign tlb_excp_cancel_req = area_stage_io_tlbExceptionCancel;
  assign sc_cancel_req = area_stage_io_scCancel;
  assign data_addr_trans_en = area_stage_io_dataAddressTranslationEnable;
  assign dmw0_en = area_stage_io_dmw0Enable;
  assign dmw1_en = area_stage_io_dmw1Enable;
  assign cacop_op_mode_di = area_stage_io_cacopModeDi;

endmodule

module MemoryStage (
  input  wire          io_input_valid,
  output wire          io_input_ready,
  input  wire [31:0]   io_input_payload_pc,
  input  wire [31:0]   io_input_payload_executeResult,
  input  wire [4:0]    io_input_payload_destination,
  input  wire          io_input_payload_gprWrite,
  input  wire          io_input_payload_isLoad,
  input  wire [3:0]    io_input_payload_mulDivOperation,
  input  wire [1:0]    io_input_payload_memorySize,
  input  wire          io_input_payload_hasException,
  input  wire          io_input_payload_isErtn,
  input  wire [31:0]   io_input_payload_csrResult,
  input  wire [13:0]   io_input_payload_csrAddress,
  input  wire          io_input_payload_csrWrite,
  input  wire [9:0]    io_input_payload_exceptionCode,
  input  wire          io_input_payload_isLl,
  input  wire          io_input_payload_isSc,
  input  wire          io_input_payload_isStore,
  input  wire          io_input_payload_tlbSearch,
  input  wire          io_input_payload_tlbWrite,
  input  wire          io_input_payload_tlbFill,
  input  wire          io_input_payload_refetch,
  input  wire          io_input_payload_tlbRead,
  input  wire          io_input_payload_invalidateTlb,
  input  wire [9:0]    io_input_payload_invalidateTlbAsid,
  input  wire [18:0]   io_input_payload_invalidateTlbVpn,
  input  wire          io_input_payload_memorySignExtend,
  input  wire          io_input_payload_instructionCacheOperation,
  input  wire          io_input_payload_isBranch,
  input  wire          io_input_payload_instructionCacheMiss,
  input  wire          io_input_payload_isPredictableBranch,
  input  wire          io_input_payload_predictionError,
  input  wire          io_input_payload_preload,
  input  wire          io_input_payload_cacheOperation,
  input  wire          io_input_payload_idle,
  input  wire [31:0]   io_input_payload_errorVirtualAddress,
  input  wire [31:0]   io_input_payload_instruction,
  input  wire [63:0]   io_input_payload_timer,
  input  wire          io_input_payload_isCounterInstruction,
  input  wire [7:0]    io_input_payload_loadEvent,
  input  wire [31:0]   io_input_payload_memoryVirtualAddress,
  input  wire [7:0]    io_input_payload_storeEvent,
  input  wire [31:0]   io_input_payload_storeData,
  input  wire          io_input_payload_csrRstatEvent,
  input  wire [31:0]   io_input_payload_csrData,
  output wire          io_output_valid,
  input  wire          io_output_ready,
  output wire [31:0]   io_output_payload_pc,
  output wire [31:0]   io_output_payload_finalResult,
  output wire [4:0]    io_output_payload_destination,
  output wire          io_output_payload_gprWrite,
  output wire          io_output_payload_hasException,
  output wire          io_output_payload_isErtn,
  output wire [31:0]   io_output_payload_csrResult,
  output wire [13:0]   io_output_payload_csrAddress,
  output wire          io_output_payload_csrWrite,
  output wire [15:0]   io_output_payload_exceptionCode,
  output wire          io_output_payload_isLl,
  output wire          io_output_payload_isSc,
  output wire [31:0]   io_output_payload_errorVirtualAddress,
  output wire          io_output_payload_tlbSearch,
  output wire          io_output_payload_tlbFound,
  output wire [4:0]    io_output_payload_tlbIndex,
  output wire          io_output_payload_tlbWrite,
  output wire          io_output_payload_tlbFill,
  output wire          io_output_payload_refetch,
  output wire          io_output_payload_tlbRead,
  output wire          io_output_payload_invalidateTlb,
  output wire [9:0]    io_output_payload_invalidateTlbAsid,
  output wire [18:0]   io_output_payload_invalidateTlbVpn,
  output wire          io_output_payload_instructionCacheOperation,
  output wire          io_output_payload_isBranch,
  output wire          io_output_payload_instructionCacheMiss,
  output wire          io_output_payload_accessesMemory,
  output wire          io_output_payload_dataCacheMiss,
  output wire          io_output_payload_isPredictableBranch,
  output wire          io_output_payload_predictionError,
  output wire          io_output_payload_idle,
  output wire [31:0]   io_output_payload_physicalAddress,
  output wire          io_output_payload_dataUncached,
  output wire [31:0]   io_output_payload_instruction,
  output wire [63:0]   io_output_payload_timer,
  output wire          io_output_payload_isCounterInstruction,
  output wire [7:0]    io_output_payload_loadEvent,
  output wire [31:0]   io_output_payload_memoryPhysicalAddress,
  output wire [31:0]   io_output_payload_memoryVirtualAddress,
  output wire [7:0]    io_output_payload_storeEvent,
  output wire [31:0]   io_output_payload_storeData,
  output wire          io_output_payload_csrRstatEvent,
  output wire [31:0]   io_output_payload_csrData,
  input  wire [31:0]   io_divResult,
  input  wire [31:0]   io_modResult,
  input  wire [63:0]   io_mulResult,
  input  wire          io_flush_exception,
  input  wire          io_flush_ertn,
  input  wire          io_flush_refetch,
  input  wire          io_flush_instructionCacheOperation,
  input  wire          io_flush_idle,
  input  wire          io_dataDataOk,
  input  wire          io_dcacheMiss,
  input  wire [31:0]   io_dataReadData,
  output wire          io_dataUncached,
  output wire          io_tlbExceptionCancel,
  output wire          io_scCancel,
  input  wire          io_csrPage,
  input  wire          io_csrDirectAddress,
  input  wire          io_csrDmw0Plv0,
  input  wire          io_csrDmw0Plv3,
  input  wire [2:0]    io_csrDmw0VirtualSegment,
  input  wire [1:0]    io_csrDmw0MemoryAttribute,
  input  wire          io_csrDmw1Plv0,
  input  wire          io_csrDmw1Plv3,
  input  wire [2:0]    io_csrDmw1VirtualSegment,
  input  wire [1:0]    io_csrDmw1MemoryAttribute,
  input  wire [1:0]    io_csrPlv,
  input  wire [1:0]    io_csrDatm,
  input  wire          io_disableCache,
  input  wire [27:0]   io_llAddress,
  input  wire [7:0]    io_dataIndexDiff,
  input  wire [19:0]   io_dataTagDiff,
  input  wire [3:0]    io_dataOffsetDiff,
  output wire          io_dataAddressTranslationEnable,
  output wire          io_dmw0Enable,
  output wire          io_dmw1Enable,
  output wire          io_cacopModeDi,
  input  wire          io_dataTlbFound,
  input  wire [4:0]    io_dataTlbIndex,
  input  wire          io_dataTlbValid,
  input  wire          io_dataTlbDirty,
  input  wire [1:0]    io_dataTlbMat,
  input  wire [1:0]    io_dataTlbPlv,
  input  wire [19:0]   io_dataTlbPpn,
  output wire          io_tlbInstructionStall,
  output wire          io_writeTlbEntryHigh,
  output wire          io_stageFlush,
  output wire          io_forward_valid,
  output wire          io_forward_dependencyNeedsStall,
  output wire          io_forward_writeEnabled,
  output wire [4:0]    io_forward_destination,
  output wire [31:0]   io_forward_result,
  input  wire          clk,
  input  wire          reset
);

  wire       [31:0]   _zz_extendedByte;
  wire       [7:0]    _zz_extendedByte_1;
  wire       [31:0]   _zz_extendedByte_2;
  wire       [31:0]   _zz_extendedHalf;
  wire       [15:0]   _zz_extendedHalf_1;
  wire       [31:0]   _zz_extendedHalf_2;
  wire       [31:0]   _zz_finalResult;
  wire       [31:0]   _zz_finalResult_1;
  wire                _zz_finalResult_2;
  wire       [31:0]   _zz_finalResult_3;
  wire       [31:0]   _zz_finalResult_4;
  wire                _zz_finalResult_5;
  reg                 valid;
  reg        [31:0]   payload_pc;
  reg        [31:0]   payload_executeResult;
  reg        [4:0]    payload_destination;
  reg                 payload_gprWrite;
  reg                 payload_isLoad;
  reg        [3:0]    payload_mulDivOperation;
  reg        [1:0]    payload_memorySize;
  reg                 payload_hasException;
  reg                 payload_isErtn;
  reg        [31:0]   payload_csrResult;
  reg        [13:0]   payload_csrAddress;
  reg                 payload_csrWrite;
  reg        [9:0]    payload_exceptionCode;
  reg                 payload_isLl;
  reg                 payload_isSc;
  reg                 payload_isStore;
  reg                 payload_tlbSearch;
  reg                 payload_tlbWrite;
  reg                 payload_tlbFill;
  reg                 payload_refetch;
  reg                 payload_tlbRead;
  reg                 payload_invalidateTlb;
  reg        [9:0]    payload_invalidateTlbAsid;
  reg        [18:0]   payload_invalidateTlbVpn;
  reg                 payload_memorySignExtend;
  reg                 payload_instructionCacheOperation;
  reg                 payload_isBranch;
  reg                 payload_instructionCacheMiss;
  reg                 payload_isPredictableBranch;
  reg                 payload_predictionError;
  reg                 payload_preload;
  reg                 payload_cacheOperation;
  reg                 payload_idle;
  reg        [31:0]   payload_errorVirtualAddress;
  reg        [31:0]   payload_instruction;
  reg        [63:0]   payload_timer;
  reg                 payload_isCounterInstruction;
  reg        [7:0]    payload_loadEvent;
  reg        [31:0]   payload_memoryVirtualAddress;
  reg        [7:0]    payload_storeEvent;
  reg        [31:0]   payload_storeData;
  reg                 payload_csrRstatEvent;
  reg        [31:0]   payload_csrData;
  reg        [31:0]   dataBuffer;
  reg                 dataBufferEnable;
  reg        [7:0]    dataIndex;
  reg        [3:0]    dataOffset;
  wire                accessMemory;
  wire                pgMode;
  wire                daMode;
  wire       [1:0]    cacopMode;
  wire       [31:0]   physicalAddress;
  wire                uncache;
  wire                tlbr;
  wire                pil;
  wire                pis;
  wire                ppi;
  wire                pme;
  wire                exception;
  wire       [15:0]   exceptionCode;
  wire       [31:0]   readData;
  reg        [7:0]    byteData;
  wire       [1:0]    switch_MemoryStage_l117;
  reg        [15:0]   halfData;
  wire                when_MemoryStage_l124;
  wire                when_MemoryStage_l125;
  wire       [31:0]   loadResult;
  wire       [31:0]   extendedByte;
  wire       [31:0]   extendedHalf;
  wire                scAddressEqual;
  wire                scCancel;
  wire       [31:0]   finalResult;
  wire                readyGo;
  wire                when_MemoryStage_l214;
  wire                when_MemoryStage_l218;
  wire                io_input_fire;
  wire                when_MemoryStage_l226;

  assign _zz_extendedByte_1 = byteData;
  assign _zz_extendedByte = {{24{_zz_extendedByte_1[7]}}, _zz_extendedByte_1};
  assign _zz_extendedByte_2 = {24'd0, byteData};
  assign _zz_extendedHalf_1 = halfData;
  assign _zz_extendedHalf = {{16{_zz_extendedHalf_1[15]}}, _zz_extendedHalf_1};
  assign _zz_extendedHalf_2 = {16'd0, halfData};
  assign _zz_finalResult = (payload_isLoad ? loadResult : 32'h0);
  assign _zz_finalResult_1 = (payload_mulDivOperation[0] ? io_mulResult[31 : 0] : 32'h0);
  assign _zz_finalResult_2 = payload_mulDivOperation[1];
  assign _zz_finalResult_3 = io_mulResult[63 : 32];
  assign _zz_finalResult_4 = 32'h0;
  assign _zz_finalResult_5 = (|payload_mulDivOperation);
  assign accessMemory = (payload_isLoad || payload_isStore);
  assign pgMode = ((! io_csrDirectAddress) && io_csrPage);
  assign daMode = (io_csrDirectAddress && (! io_csrPage));
  assign cacopMode = payload_destination[4 : 3];
  assign io_dmw0Enable = ((((io_csrDmw0Plv0 && (io_csrPlv == 2'b00)) || (io_csrDmw0Plv3 && (io_csrPlv == 2'b11))) && (payload_errorVirtualAddress[31 : 29] == io_csrDmw0VirtualSegment)) && pgMode);
  assign io_dmw1Enable = ((((io_csrDmw1Plv0 && (io_csrPlv == 2'b00)) || (io_csrDmw1Plv3 && (io_csrPlv == 2'b11))) && (payload_errorVirtualAddress[31 : 29] == io_csrDmw1VirtualSegment)) && pgMode);
  assign io_cacopModeDi = (payload_cacheOperation && ((cacopMode == 2'b00) || (cacopMode == 2'b01)));
  assign io_dataAddressTranslationEnable = (((pgMode && (! io_dmw0Enable)) && (! io_dmw1Enable)) && (! io_cacopModeDi));
  assign physicalAddress = {io_dataTlbPpn,payload_errorVirtualAddress[11 : 0]};
  assign uncache = (((((daMode && (io_csrDatm == 2'b00)) || (io_dmw0Enable && (io_csrDmw0MemoryAttribute == 2'b00))) || (io_dmw1Enable && (io_csrDmw1MemoryAttribute == 2'b00))) || (io_dataAddressTranslationEnable && (io_dataTlbMat == 2'b00))) || io_disableCache);
  assign io_dataUncached = uncache;
  assign tlbr = (((accessMemory || payload_cacheOperation) && (! io_dataTlbFound)) && io_dataAddressTranslationEnable);
  assign pil = (((payload_isLoad || payload_cacheOperation) && (! io_dataTlbValid)) && io_dataAddressTranslationEnable);
  assign pis = ((payload_isStore && (! io_dataTlbValid)) && io_dataAddressTranslationEnable);
  assign ppi = (((accessMemory && io_dataTlbValid) && (io_dataTlbPlv < io_csrPlv)) && io_dataAddressTranslationEnable);
  assign pme = ((((payload_isStore && io_dataTlbValid) && (io_csrPlv <= io_dataTlbPlv)) && (! io_dataTlbDirty)) && io_dataAddressTranslationEnable);
  assign exception = (((((tlbr || pil) || pis) || ppi) || pme) || payload_hasException);
  assign exceptionCode = {{{{{{pil,pis},ppi},pme},tlbr},1'b0},payload_exceptionCode};
  assign readData = (dataBufferEnable ? dataBuffer : io_dataReadData);
  always @(*) begin
    byteData = readData[7 : 0];
    case(switch_MemoryStage_l117)
      2'b01 : begin
        byteData = readData[15 : 8];
      end
      2'b10 : begin
        byteData = readData[23 : 16];
      end
      2'b11 : begin
        byteData = readData[31 : 24];
      end
      default : begin
      end
    endcase
  end

  assign switch_MemoryStage_l117 = payload_executeResult[1 : 0];
  always @(*) begin
    halfData = 16'h0;
    if(when_MemoryStage_l124) begin
      halfData = readData[15 : 0];
    end
    if(when_MemoryStage_l125) begin
      halfData = readData[31 : 16];
    end
  end

  assign when_MemoryStage_l124 = (payload_executeResult[1 : 0] == 2'b00);
  assign when_MemoryStage_l125 = (payload_executeResult[1 : 0] == 2'b10);
  assign extendedByte = (payload_memorySignExtend ? _zz_extendedByte : _zz_extendedByte_2);
  assign extendedHalf = (payload_memorySignExtend ? _zz_extendedHalf : _zz_extendedHalf_2);
  assign loadResult = (((payload_memorySize[0] ? extendedByte : 32'h0) | (payload_memorySize[1] ? extendedHalf : 32'h0)) | ((! (|payload_memorySize)) ? readData : 32'h0));
  assign scAddressEqual = (io_llAddress == physicalAddress[31 : 4]);
  assign scCancel = ((((! scAddressEqual) || uncache) && payload_isSc) && accessMemory);
  assign io_scCancel = scCancel;
  assign io_tlbExceptionCancel = ((((tlbr || pil) || pis) || ppi) || pme);
  assign finalResult = (((((_zz_finalResult | _zz_finalResult_1) | (_zz_finalResult_2 ? _zz_finalResult_3 : _zz_finalResult_4)) | (payload_mulDivOperation[2] ? io_divResult : 32'h0)) | (payload_mulDivOperation[3] ? io_modResult : 32'h0)) | ((((! _zz_finalResult_5) && (! payload_isLoad)) && (! scCancel)) ? payload_executeResult : 32'h0));
  assign readyGo = ((((io_dataDataOk || dataBufferEnable) || (! accessMemory)) || exception) || scCancel);
  assign io_input_ready = ((! valid) || (readyGo && io_output_ready));
  assign io_output_valid = (valid && readyGo);
  assign io_output_payload_pc = payload_pc;
  assign io_output_payload_finalResult = finalResult;
  assign io_output_payload_destination = payload_destination;
  assign io_output_payload_gprWrite = payload_gprWrite;
  assign io_output_payload_hasException = exception;
  assign io_output_payload_isErtn = payload_isErtn;
  assign io_output_payload_csrResult = payload_csrResult;
  assign io_output_payload_csrAddress = payload_csrAddress;
  assign io_output_payload_csrWrite = payload_csrWrite;
  assign io_output_payload_exceptionCode = exceptionCode;
  assign io_output_payload_isLl = payload_isLl;
  assign io_output_payload_isSc = payload_isSc;
  assign io_output_payload_errorVirtualAddress = payload_errorVirtualAddress;
  assign io_output_payload_tlbSearch = payload_tlbSearch;
  assign io_output_payload_tlbFound = io_dataTlbFound;
  assign io_output_payload_tlbIndex = io_dataTlbIndex;
  assign io_output_payload_tlbWrite = payload_tlbWrite;
  assign io_output_payload_tlbFill = payload_tlbFill;
  assign io_output_payload_refetch = payload_refetch;
  assign io_output_payload_tlbRead = payload_tlbRead;
  assign io_output_payload_invalidateTlb = payload_invalidateTlb;
  assign io_output_payload_invalidateTlbAsid = payload_invalidateTlbAsid;
  assign io_output_payload_invalidateTlbVpn = payload_invalidateTlbVpn;
  assign io_output_payload_instructionCacheOperation = payload_instructionCacheOperation;
  assign io_output_payload_isBranch = payload_isBranch;
  assign io_output_payload_instructionCacheMiss = payload_instructionCacheMiss;
  assign io_output_payload_accessesMemory = accessMemory;
  assign io_output_payload_dataCacheMiss = io_dcacheMiss;
  assign io_output_payload_isPredictableBranch = payload_isPredictableBranch;
  assign io_output_payload_predictionError = payload_predictionError;
  assign io_output_payload_idle = payload_idle;
  assign io_output_payload_physicalAddress = physicalAddress;
  assign io_output_payload_dataUncached = uncache;
  assign io_output_payload_instruction = payload_instruction;
  assign io_output_payload_timer = payload_timer;
  assign io_output_payload_isCounterInstruction = payload_isCounterInstruction;
  assign io_output_payload_loadEvent = payload_loadEvent;
  assign io_output_payload_memoryPhysicalAddress = {{io_dataTagDiff,dataIndex},dataOffset};
  assign io_output_payload_memoryVirtualAddress = payload_memoryVirtualAddress;
  assign io_output_payload_storeEvent = payload_storeEvent;
  assign io_output_payload_storeData = payload_storeData;
  assign io_output_payload_csrRstatEvent = payload_csrRstatEvent;
  assign io_output_payload_csrData = payload_csrData;
  assign io_forward_valid = valid;
  assign io_forward_dependencyNeedsStall = (payload_isLoad && (! io_output_valid));
  assign io_forward_writeEnabled = ((payload_gprWrite && (payload_destination != 5'h0)) && valid);
  assign io_forward_destination = payload_destination;
  assign io_forward_result = finalResult;
  assign io_tlbInstructionStall = ((payload_tlbSearch || payload_tlbRead) && valid);
  assign io_writeTlbEntryHigh = ((payload_csrWrite && (payload_csrAddress == 14'h0011)) && valid);
  assign io_stageFlush = ((((((exception || payload_isErtn) || payload_csrWrite) || ((payload_isLl || payload_isSc) && (! exception))) || payload_refetch) || payload_idle) && valid);
  assign when_MemoryStage_l214 = (((((io_flush_exception || io_flush_ertn) || io_flush_refetch) || io_flush_instructionCacheOperation) || io_flush_idle) || (readyGo && io_output_ready));
  assign when_MemoryStage_l218 = (io_dataDataOk && (! io_output_ready));
  assign io_input_fire = (io_input_valid && io_input_ready);
  assign when_MemoryStage_l226 = ((((io_flush_exception || io_flush_ertn) || io_flush_refetch) || io_flush_instructionCacheOperation) || io_flush_idle);
  always @(posedge clk) begin
    if(reset) begin
      valid <= 1'b0;
      dataBuffer <= 32'h0;
      dataBufferEnable <= 1'b0;
    end else begin
      if(when_MemoryStage_l214) begin
        valid <= 1'b0;
        dataBufferEnable <= 1'b0;
        dataBuffer <= 32'h0;
      end else begin
        if(when_MemoryStage_l218) begin
          dataBuffer <= io_dataReadData;
          dataBufferEnable <= 1'b1;
        end
      end
      if(io_input_fire) begin
        valid <= 1'b1;
      end
      if(when_MemoryStage_l226) begin
        valid <= 1'b0;
      end
    end
  end

  always @(posedge clk) begin
    if(io_input_fire) begin
      payload_pc <= io_input_payload_pc;
      payload_executeResult <= io_input_payload_executeResult;
      payload_destination <= io_input_payload_destination;
      payload_gprWrite <= io_input_payload_gprWrite;
      payload_isLoad <= io_input_payload_isLoad;
      payload_mulDivOperation <= io_input_payload_mulDivOperation;
      payload_memorySize <= io_input_payload_memorySize;
      payload_hasException <= io_input_payload_hasException;
      payload_isErtn <= io_input_payload_isErtn;
      payload_csrResult <= io_input_payload_csrResult;
      payload_csrAddress <= io_input_payload_csrAddress;
      payload_csrWrite <= io_input_payload_csrWrite;
      payload_exceptionCode <= io_input_payload_exceptionCode;
      payload_isLl <= io_input_payload_isLl;
      payload_isSc <= io_input_payload_isSc;
      payload_isStore <= io_input_payload_isStore;
      payload_tlbSearch <= io_input_payload_tlbSearch;
      payload_tlbWrite <= io_input_payload_tlbWrite;
      payload_tlbFill <= io_input_payload_tlbFill;
      payload_refetch <= io_input_payload_refetch;
      payload_tlbRead <= io_input_payload_tlbRead;
      payload_invalidateTlb <= io_input_payload_invalidateTlb;
      payload_invalidateTlbAsid <= io_input_payload_invalidateTlbAsid;
      payload_invalidateTlbVpn <= io_input_payload_invalidateTlbVpn;
      payload_memorySignExtend <= io_input_payload_memorySignExtend;
      payload_instructionCacheOperation <= io_input_payload_instructionCacheOperation;
      payload_isBranch <= io_input_payload_isBranch;
      payload_instructionCacheMiss <= io_input_payload_instructionCacheMiss;
      payload_isPredictableBranch <= io_input_payload_isPredictableBranch;
      payload_predictionError <= io_input_payload_predictionError;
      payload_preload <= io_input_payload_preload;
      payload_cacheOperation <= io_input_payload_cacheOperation;
      payload_idle <= io_input_payload_idle;
      payload_errorVirtualAddress <= io_input_payload_errorVirtualAddress;
      payload_instruction <= io_input_payload_instruction;
      payload_timer <= io_input_payload_timer;
      payload_isCounterInstruction <= io_input_payload_isCounterInstruction;
      payload_loadEvent <= io_input_payload_loadEvent;
      payload_memoryVirtualAddress <= io_input_payload_memoryVirtualAddress;
      payload_storeEvent <= io_input_payload_storeEvent;
      payload_storeData <= io_input_payload_storeData;
      payload_csrRstatEvent <= io_input_payload_csrRstatEvent;
      payload_csrData <= io_input_payload_csrData;
    end
    dataIndex <= io_dataIndexDiff;
    dataOffset <= io_dataOffsetDiff;
  end


endmodule
