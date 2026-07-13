// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : icache



module icache (
  input  wire          clk,
  input  wire          reset,
  input  wire          valid,
  input  wire          op,
  input  wire [7:0]    index,
  input  wire [19:0]   tag,
  input  wire [3:0]    offset,
  input  wire [3:0]    wstrb,
  input  wire [31:0]   wdata,
  output wire          addr_ok,
  output wire          data_ok,
  output wire [31:0]   rdata,
  input  wire          uncache_en,
  input  wire          icacop_op_en,
  input  wire [1:0]    cacop_op_mode,
  input  wire [7:0]    cacop_op_addr_index,
  input  wire [19:0]   cacop_op_addr_tag,
  input  wire [3:0]    cacop_op_addr_offset,
  output wire          icache_unbusy,
  input  wire          tlb_excp_cancel_req,
  output wire          rd_req,
  output wire [2:0]    rd_type,
  output wire [31:0]   rd_addr,
  input  wire          rd_rdy,
  input  wire          ret_valid,
  input  wire          ret_last,
  input  wire [31:0]   ret_data,
  output wire          wr_req,
  output wire [2:0]    wr_type,
  output wire [31:0]   wr_addr,
  output wire [3:0]    wr_wstrb,
  output wire [127:0]  wr_data,
  input  wire          wr_rdy,
  output wire          cache_miss
);

  reg        [31:0]   logic_dataMem_0_0_spinal_port1;
  reg        [31:0]   logic_dataMem_0_1_spinal_port1;
  reg        [31:0]   logic_dataMem_0_2_spinal_port1;
  reg        [31:0]   logic_dataMem_0_3_spinal_port1;
  reg        [31:0]   logic_dataMem_1_0_spinal_port1;
  reg        [31:0]   logic_dataMem_1_1_spinal_port1;
  reg        [31:0]   logic_dataMem_1_2_spinal_port1;
  reg        [31:0]   logic_dataMem_1_3_spinal_port1;
  reg        [20:0]   logic_tagMem_0_spinal_port1;
  reg        [20:0]   logic_tagMem_1_spinal_port1;
  reg        [31:0]   _zz_logic_wayWords_0;
  wire       [1:0]    _zz_logic_wayWords_0_1;
  reg        [31:0]   _zz_logic_wayWords_1;
  wire       [1:0]    _zz_logic_wayWords_1_1;
  wire       [7:0]    _zz_logic_dataMem_0_0_port;
  wire                _zz_logic_dataMem_0_0_port_1;
  wire       [7:0]    _zz_logic_dataMem_0_1_port;
  wire                _zz_logic_dataMem_0_1_port_1;
  wire       [7:0]    _zz_logic_dataMem_0_2_port;
  wire                _zz_logic_dataMem_0_2_port_1;
  wire       [7:0]    _zz_logic_dataMem_0_3_port;
  wire                _zz_logic_dataMem_0_3_port_1;
  wire       [7:0]    _zz_logic_dataMem_1_0_port;
  wire                _zz_logic_dataMem_1_0_port_1;
  wire       [7:0]    _zz_logic_dataMem_1_1_port;
  wire                _zz_logic_dataMem_1_1_port_1;
  wire       [7:0]    _zz_logic_dataMem_1_2_port;
  wire                _zz_logic_dataMem_1_2_port_1;
  wire       [7:0]    _zz_logic_dataMem_1_3_port;
  wire                _zz_logic_dataMem_1_3_port_1;
  wire       [7:0]    _zz_logic_tagMem_0_port;
  wire       [20:0]   _zz_logic_tagMem_0_port_1;
  wire       [7:0]    _zz_logic_tagMem_1_port;
  wire       [20:0]   _zz_logic_tagMem_1_port_1;
  wire       [4:0]    logic_MainIdle;
  wire       [4:0]    logic_MainLookup;
  wire       [4:0]    logic_MainReplace;
  wire       [4:0]    logic_MainRefill;
  reg        [4:0]    logic_mainState;
  reg        [7:0]    logic_requestIndex;
  reg        [19:0]   logic_requestTag;
  reg        [3:0]    logic_requestOffset;
  reg                 logic_requestUncache;
  reg                 logic_requestCacop;
  reg        [1:0]    logic_requestCacopMode;
  reg        [1:0]    logic_missReplaceWay;
  reg        [1:0]    logic_missRetNum;
  reg        [1:0]    logic_lookupWayHitBuffer;
  reg                 logic_rdReqBuffer;
  reg        [7:0]    logic_lfsr;
  reg                 logic_legacyWrReq;
  wire                logic_isIdle;
  wire                logic_isLookup;
  wire                logic_isReplace;
  wire                logic_isRefill;
  wire       [3:0]    logic_realOffset;
  wire       [7:0]    logic_realIndex;
  wire       [19:0]   logic_realTag;
  wire                logic_requestValid;
  wire                logic_mode0;
  wire                logic_mode1;
  wire                logic_mode2;
  wire                logic_mode2HitWrite;
  wire       [20:0]   logic_tagOutputs_0;
  wire       [20:0]   logic_tagOutputs_1;
  wire       [31:0]   logic_dataOutputs_0_0;
  wire       [31:0]   logic_dataOutputs_0_1;
  wire       [31:0]   logic_dataOutputs_0_2;
  wire       [31:0]   logic_dataOutputs_0_3;
  wire       [31:0]   logic_dataOutputs_1_0;
  wire       [31:0]   logic_dataOutputs_1_1;
  wire       [31:0]   logic_dataOutputs_1_2;
  wire       [31:0]   logic_dataOutputs_1_3;
  reg        [1:0]    logic_wayHit;
  wire                logic_cacheHit;
  wire                logic_addrOk;
  wire       [31:0]   logic_wayWords_0;
  wire       [31:0]   logic_wayWords_1;
  wire       [31:0]   logic_loadResult;
  reg        [1:0]    logic_invalidWay;
  wire                when_OpenLa500ICache_l123;
  wire                when_OpenLa500ICache_l125;
  wire                logic_hasInvalidWay;
  wire       [1:0]    logic_randomWay;
  wire       [1:0]    logic_randomReplacement;
  wire       [1:0]    logic_cacopChosenWay;
  reg        [1:0]    logic_replaceWay;
  wire                when_OpenLa500ICache_l134;
  wire                when_OpenLa500ICache_l138;
  wire                logic_rdReq;
  wire                logic_refillMatch;
  wire                logic_dataOk;
  wire       [1:0]    logic_nextRetNum;
  wire       [7:0]    _zz_logic_dataOutputs_0_0;
  reg        [3:0]    _zz_logic_dataOutputs_0_0_1;
  wire                when_OpenLa500ICache_l155;
  wire                _zz_logic_dataOutputs_0_0_2;
  wire                _zz_logic_dataOutputs_0_0_3;
  wire       [7:0]    _zz_logic_dataOutputs_0_0_4;
  wire       [7:0]    _zz_logic_dataOutputs_0_1;
  reg        [3:0]    _zz_logic_dataOutputs_0_1_1;
  wire                when_OpenLa500ICache_l155_1;
  wire                _zz_logic_dataOutputs_0_1_2;
  wire                _zz_logic_dataOutputs_0_1_3;
  wire       [7:0]    _zz_logic_dataOutputs_0_1_4;
  wire       [7:0]    _zz_logic_dataOutputs_0_2;
  reg        [3:0]    _zz_logic_dataOutputs_0_2_1;
  wire                when_OpenLa500ICache_l155_2;
  wire                _zz_logic_dataOutputs_0_2_2;
  wire                _zz_logic_dataOutputs_0_2_3;
  wire       [7:0]    _zz_logic_dataOutputs_0_2_4;
  wire       [7:0]    _zz_logic_dataOutputs_0_3;
  reg        [3:0]    _zz_logic_dataOutputs_0_3_1;
  wire                when_OpenLa500ICache_l155_3;
  wire                _zz_logic_dataOutputs_0_3_2;
  wire                _zz_logic_dataOutputs_0_3_3;
  wire       [7:0]    _zz_logic_dataOutputs_0_3_4;
  wire       [7:0]    _zz_logic_dataOutputs_1_0;
  reg        [3:0]    _zz_logic_dataOutputs_1_0_1;
  wire                when_OpenLa500ICache_l155_4;
  wire                _zz_logic_dataOutputs_1_0_2;
  wire                _zz_logic_dataOutputs_1_0_3;
  wire       [7:0]    _zz_logic_dataOutputs_1_0_4;
  wire       [7:0]    _zz_logic_dataOutputs_1_1;
  reg        [3:0]    _zz_logic_dataOutputs_1_1_1;
  wire                when_OpenLa500ICache_l155_5;
  wire                _zz_logic_dataOutputs_1_1_2;
  wire                _zz_logic_dataOutputs_1_1_3;
  wire       [7:0]    _zz_logic_dataOutputs_1_1_4;
  wire       [7:0]    _zz_logic_dataOutputs_1_2;
  reg        [3:0]    _zz_logic_dataOutputs_1_2_1;
  wire                when_OpenLa500ICache_l155_6;
  wire                _zz_logic_dataOutputs_1_2_2;
  wire                _zz_logic_dataOutputs_1_2_3;
  wire       [7:0]    _zz_logic_dataOutputs_1_2_4;
  wire       [7:0]    _zz_logic_dataOutputs_1_3;
  reg        [3:0]    _zz_logic_dataOutputs_1_3_1;
  wire                when_OpenLa500ICache_l155_7;
  wire                _zz_logic_dataOutputs_1_3_2;
  wire                _zz_logic_dataOutputs_1_3_3;
  wire       [7:0]    _zz_logic_dataOutputs_1_3_4;
  reg        [7:0]    _zz_logic_tagOutputs_0;
  wire                when_OpenLa500ICache_l176;
  wire                when_OpenLa500ICache_l178;
  wire                _zz_logic_tagOutputs_0_1;
  wire                _zz_logic_tagOutputs_0_2;
  wire       [7:0]    _zz_logic_tagOutputs_0_3;
  wire                _zz_logic_tagOutputs_0_4;
  reg        [7:0]    _zz_logic_tagOutputs_1;
  wire                when_OpenLa500ICache_l176_1;
  wire                when_OpenLa500ICache_l178_1;
  wire                _zz_logic_tagOutputs_1_1;
  wire                _zz_logic_tagOutputs_1_2;
  wire       [7:0]    _zz_logic_tagOutputs_1_3;
  wire                _zz_logic_tagOutputs_1_4;
  wire                when_OpenLa500ICache_l212;
  wire                when_OpenLa500ICache_l219;
  wire                when_OpenLa500ICache_l235;
  wire                when_OpenLa500ICache_l246;
  wire                when_OpenLa500ICache_l252;
  reg [7:0] logic_dataMem_0_0_symbol0 [0:255];
  reg [7:0] logic_dataMem_0_0_symbol1 [0:255];
  reg [7:0] logic_dataMem_0_0_symbol2 [0:255];
  reg [7:0] logic_dataMem_0_0_symbol3 [0:255];
  reg [7:0] _zz_logic_dataMem_0_0symbol_read;
  reg [7:0] _zz_logic_dataMem_0_0symbol_read_1;
  reg [7:0] _zz_logic_dataMem_0_0symbol_read_2;
  reg [7:0] _zz_logic_dataMem_0_0symbol_read_3;
  reg [7:0] logic_dataMem_0_1_symbol0 [0:255];
  reg [7:0] logic_dataMem_0_1_symbol1 [0:255];
  reg [7:0] logic_dataMem_0_1_symbol2 [0:255];
  reg [7:0] logic_dataMem_0_1_symbol3 [0:255];
  reg [7:0] _zz_logic_dataMem_0_1symbol_read;
  reg [7:0] _zz_logic_dataMem_0_1symbol_read_1;
  reg [7:0] _zz_logic_dataMem_0_1symbol_read_2;
  reg [7:0] _zz_logic_dataMem_0_1symbol_read_3;
  reg [7:0] logic_dataMem_0_2_symbol0 [0:255];
  reg [7:0] logic_dataMem_0_2_symbol1 [0:255];
  reg [7:0] logic_dataMem_0_2_symbol2 [0:255];
  reg [7:0] logic_dataMem_0_2_symbol3 [0:255];
  reg [7:0] _zz_logic_dataMem_0_2symbol_read;
  reg [7:0] _zz_logic_dataMem_0_2symbol_read_1;
  reg [7:0] _zz_logic_dataMem_0_2symbol_read_2;
  reg [7:0] _zz_logic_dataMem_0_2symbol_read_3;
  reg [7:0] logic_dataMem_0_3_symbol0 [0:255];
  reg [7:0] logic_dataMem_0_3_symbol1 [0:255];
  reg [7:0] logic_dataMem_0_3_symbol2 [0:255];
  reg [7:0] logic_dataMem_0_3_symbol3 [0:255];
  reg [7:0] _zz_logic_dataMem_0_3symbol_read;
  reg [7:0] _zz_logic_dataMem_0_3symbol_read_1;
  reg [7:0] _zz_logic_dataMem_0_3symbol_read_2;
  reg [7:0] _zz_logic_dataMem_0_3symbol_read_3;
  reg [7:0] logic_dataMem_1_0_symbol0 [0:255];
  reg [7:0] logic_dataMem_1_0_symbol1 [0:255];
  reg [7:0] logic_dataMem_1_0_symbol2 [0:255];
  reg [7:0] logic_dataMem_1_0_symbol3 [0:255];
  reg [7:0] _zz_logic_dataMem_1_0symbol_read;
  reg [7:0] _zz_logic_dataMem_1_0symbol_read_1;
  reg [7:0] _zz_logic_dataMem_1_0symbol_read_2;
  reg [7:0] _zz_logic_dataMem_1_0symbol_read_3;
  reg [7:0] logic_dataMem_1_1_symbol0 [0:255];
  reg [7:0] logic_dataMem_1_1_symbol1 [0:255];
  reg [7:0] logic_dataMem_1_1_symbol2 [0:255];
  reg [7:0] logic_dataMem_1_1_symbol3 [0:255];
  reg [7:0] _zz_logic_dataMem_1_1symbol_read;
  reg [7:0] _zz_logic_dataMem_1_1symbol_read_1;
  reg [7:0] _zz_logic_dataMem_1_1symbol_read_2;
  reg [7:0] _zz_logic_dataMem_1_1symbol_read_3;
  reg [7:0] logic_dataMem_1_2_symbol0 [0:255];
  reg [7:0] logic_dataMem_1_2_symbol1 [0:255];
  reg [7:0] logic_dataMem_1_2_symbol2 [0:255];
  reg [7:0] logic_dataMem_1_2_symbol3 [0:255];
  reg [7:0] _zz_logic_dataMem_1_2symbol_read;
  reg [7:0] _zz_logic_dataMem_1_2symbol_read_1;
  reg [7:0] _zz_logic_dataMem_1_2symbol_read_2;
  reg [7:0] _zz_logic_dataMem_1_2symbol_read_3;
  reg [7:0] logic_dataMem_1_3_symbol0 [0:255];
  reg [7:0] logic_dataMem_1_3_symbol1 [0:255];
  reg [7:0] logic_dataMem_1_3_symbol2 [0:255];
  reg [7:0] logic_dataMem_1_3_symbol3 [0:255];
  reg [7:0] _zz_logic_dataMem_1_3symbol_read;
  reg [7:0] _zz_logic_dataMem_1_3symbol_read_1;
  reg [7:0] _zz_logic_dataMem_1_3symbol_read_2;
  reg [7:0] _zz_logic_dataMem_1_3symbol_read_3;
  reg [20:0] logic_tagMem_0 [0:255];
  reg [20:0] logic_tagMem_1 [0:255];

  assign _zz_logic_dataMem_0_0_port = _zz_logic_dataOutputs_0_0;
  assign _zz_logic_dataMem_0_0_port_1 = (_zz_logic_dataOutputs_0_0_2 && (|_zz_logic_dataOutputs_0_0_1));
  assign _zz_logic_dataMem_0_1_port = _zz_logic_dataOutputs_0_1;
  assign _zz_logic_dataMem_0_1_port_1 = (_zz_logic_dataOutputs_0_1_2 && (|_zz_logic_dataOutputs_0_1_1));
  assign _zz_logic_dataMem_0_2_port = _zz_logic_dataOutputs_0_2;
  assign _zz_logic_dataMem_0_2_port_1 = (_zz_logic_dataOutputs_0_2_2 && (|_zz_logic_dataOutputs_0_2_1));
  assign _zz_logic_dataMem_0_3_port = _zz_logic_dataOutputs_0_3;
  assign _zz_logic_dataMem_0_3_port_1 = (_zz_logic_dataOutputs_0_3_2 && (|_zz_logic_dataOutputs_0_3_1));
  assign _zz_logic_dataMem_1_0_port = _zz_logic_dataOutputs_1_0;
  assign _zz_logic_dataMem_1_0_port_1 = (_zz_logic_dataOutputs_1_0_2 && (|_zz_logic_dataOutputs_1_0_1));
  assign _zz_logic_dataMem_1_1_port = _zz_logic_dataOutputs_1_1;
  assign _zz_logic_dataMem_1_1_port_1 = (_zz_logic_dataOutputs_1_1_2 && (|_zz_logic_dataOutputs_1_1_1));
  assign _zz_logic_dataMem_1_2_port = _zz_logic_dataOutputs_1_2;
  assign _zz_logic_dataMem_1_2_port_1 = (_zz_logic_dataOutputs_1_2_2 && (|_zz_logic_dataOutputs_1_2_1));
  assign _zz_logic_dataMem_1_3_port = _zz_logic_dataOutputs_1_3;
  assign _zz_logic_dataMem_1_3_port_1 = (_zz_logic_dataOutputs_1_3_2 && (|_zz_logic_dataOutputs_1_3_1));
  assign _zz_logic_tagMem_0_port = _zz_logic_tagOutputs_0;
  assign _zz_logic_tagMem_0_port_1 = (((logic_mode0 || logic_mode1) || logic_mode2HitWrite) ? 21'h0 : {logic_requestTag,1'b1});
  assign _zz_logic_tagMem_1_port = _zz_logic_tagOutputs_1;
  assign _zz_logic_tagMem_1_port_1 = (((logic_mode0 || logic_mode1) || logic_mode2HitWrite) ? 21'h0 : {logic_requestTag,1'b1});
  assign _zz_logic_wayWords_0_1 = logic_requestOffset[3 : 2];
  assign _zz_logic_wayWords_1_1 = logic_requestOffset[3 : 2];
  always @(*) begin
    logic_dataMem_0_0_spinal_port1 = {_zz_logic_dataMem_0_0symbol_read_3, _zz_logic_dataMem_0_0symbol_read_2, _zz_logic_dataMem_0_0symbol_read_1, _zz_logic_dataMem_0_0symbol_read};
  end
  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_0_0_1[0] && _zz_logic_dataMem_0_0_port_1) begin
      logic_dataMem_0_0_symbol0[_zz_logic_dataMem_0_0_port] <= ret_data[7 : 0];
    end
    if(_zz_logic_dataOutputs_0_0_1[1] && _zz_logic_dataMem_0_0_port_1) begin
      logic_dataMem_0_0_symbol1[_zz_logic_dataMem_0_0_port] <= ret_data[15 : 8];
    end
    if(_zz_logic_dataOutputs_0_0_1[2] && _zz_logic_dataMem_0_0_port_1) begin
      logic_dataMem_0_0_symbol2[_zz_logic_dataMem_0_0_port] <= ret_data[23 : 16];
    end
    if(_zz_logic_dataOutputs_0_0_1[3] && _zz_logic_dataMem_0_0_port_1) begin
      logic_dataMem_0_0_symbol3[_zz_logic_dataMem_0_0_port] <= ret_data[31 : 24];
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_0_0_3) begin
      _zz_logic_dataMem_0_0symbol_read <= logic_dataMem_0_0_symbol0[_zz_logic_dataOutputs_0_0_4];
      _zz_logic_dataMem_0_0symbol_read_1 <= logic_dataMem_0_0_symbol1[_zz_logic_dataOutputs_0_0_4];
      _zz_logic_dataMem_0_0symbol_read_2 <= logic_dataMem_0_0_symbol2[_zz_logic_dataOutputs_0_0_4];
      _zz_logic_dataMem_0_0symbol_read_3 <= logic_dataMem_0_0_symbol3[_zz_logic_dataOutputs_0_0_4];
    end
  end

  always @(*) begin
    logic_dataMem_0_1_spinal_port1 = {_zz_logic_dataMem_0_1symbol_read_3, _zz_logic_dataMem_0_1symbol_read_2, _zz_logic_dataMem_0_1symbol_read_1, _zz_logic_dataMem_0_1symbol_read};
  end
  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_0_1_1[0] && _zz_logic_dataMem_0_1_port_1) begin
      logic_dataMem_0_1_symbol0[_zz_logic_dataMem_0_1_port] <= ret_data[7 : 0];
    end
    if(_zz_logic_dataOutputs_0_1_1[1] && _zz_logic_dataMem_0_1_port_1) begin
      logic_dataMem_0_1_symbol1[_zz_logic_dataMem_0_1_port] <= ret_data[15 : 8];
    end
    if(_zz_logic_dataOutputs_0_1_1[2] && _zz_logic_dataMem_0_1_port_1) begin
      logic_dataMem_0_1_symbol2[_zz_logic_dataMem_0_1_port] <= ret_data[23 : 16];
    end
    if(_zz_logic_dataOutputs_0_1_1[3] && _zz_logic_dataMem_0_1_port_1) begin
      logic_dataMem_0_1_symbol3[_zz_logic_dataMem_0_1_port] <= ret_data[31 : 24];
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_0_1_3) begin
      _zz_logic_dataMem_0_1symbol_read <= logic_dataMem_0_1_symbol0[_zz_logic_dataOutputs_0_1_4];
      _zz_logic_dataMem_0_1symbol_read_1 <= logic_dataMem_0_1_symbol1[_zz_logic_dataOutputs_0_1_4];
      _zz_logic_dataMem_0_1symbol_read_2 <= logic_dataMem_0_1_symbol2[_zz_logic_dataOutputs_0_1_4];
      _zz_logic_dataMem_0_1symbol_read_3 <= logic_dataMem_0_1_symbol3[_zz_logic_dataOutputs_0_1_4];
    end
  end

  always @(*) begin
    logic_dataMem_0_2_spinal_port1 = {_zz_logic_dataMem_0_2symbol_read_3, _zz_logic_dataMem_0_2symbol_read_2, _zz_logic_dataMem_0_2symbol_read_1, _zz_logic_dataMem_0_2symbol_read};
  end
  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_0_2_1[0] && _zz_logic_dataMem_0_2_port_1) begin
      logic_dataMem_0_2_symbol0[_zz_logic_dataMem_0_2_port] <= ret_data[7 : 0];
    end
    if(_zz_logic_dataOutputs_0_2_1[1] && _zz_logic_dataMem_0_2_port_1) begin
      logic_dataMem_0_2_symbol1[_zz_logic_dataMem_0_2_port] <= ret_data[15 : 8];
    end
    if(_zz_logic_dataOutputs_0_2_1[2] && _zz_logic_dataMem_0_2_port_1) begin
      logic_dataMem_0_2_symbol2[_zz_logic_dataMem_0_2_port] <= ret_data[23 : 16];
    end
    if(_zz_logic_dataOutputs_0_2_1[3] && _zz_logic_dataMem_0_2_port_1) begin
      logic_dataMem_0_2_symbol3[_zz_logic_dataMem_0_2_port] <= ret_data[31 : 24];
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_0_2_3) begin
      _zz_logic_dataMem_0_2symbol_read <= logic_dataMem_0_2_symbol0[_zz_logic_dataOutputs_0_2_4];
      _zz_logic_dataMem_0_2symbol_read_1 <= logic_dataMem_0_2_symbol1[_zz_logic_dataOutputs_0_2_4];
      _zz_logic_dataMem_0_2symbol_read_2 <= logic_dataMem_0_2_symbol2[_zz_logic_dataOutputs_0_2_4];
      _zz_logic_dataMem_0_2symbol_read_3 <= logic_dataMem_0_2_symbol3[_zz_logic_dataOutputs_0_2_4];
    end
  end

  always @(*) begin
    logic_dataMem_0_3_spinal_port1 = {_zz_logic_dataMem_0_3symbol_read_3, _zz_logic_dataMem_0_3symbol_read_2, _zz_logic_dataMem_0_3symbol_read_1, _zz_logic_dataMem_0_3symbol_read};
  end
  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_0_3_1[0] && _zz_logic_dataMem_0_3_port_1) begin
      logic_dataMem_0_3_symbol0[_zz_logic_dataMem_0_3_port] <= ret_data[7 : 0];
    end
    if(_zz_logic_dataOutputs_0_3_1[1] && _zz_logic_dataMem_0_3_port_1) begin
      logic_dataMem_0_3_symbol1[_zz_logic_dataMem_0_3_port] <= ret_data[15 : 8];
    end
    if(_zz_logic_dataOutputs_0_3_1[2] && _zz_logic_dataMem_0_3_port_1) begin
      logic_dataMem_0_3_symbol2[_zz_logic_dataMem_0_3_port] <= ret_data[23 : 16];
    end
    if(_zz_logic_dataOutputs_0_3_1[3] && _zz_logic_dataMem_0_3_port_1) begin
      logic_dataMem_0_3_symbol3[_zz_logic_dataMem_0_3_port] <= ret_data[31 : 24];
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_0_3_3) begin
      _zz_logic_dataMem_0_3symbol_read <= logic_dataMem_0_3_symbol0[_zz_logic_dataOutputs_0_3_4];
      _zz_logic_dataMem_0_3symbol_read_1 <= logic_dataMem_0_3_symbol1[_zz_logic_dataOutputs_0_3_4];
      _zz_logic_dataMem_0_3symbol_read_2 <= logic_dataMem_0_3_symbol2[_zz_logic_dataOutputs_0_3_4];
      _zz_logic_dataMem_0_3symbol_read_3 <= logic_dataMem_0_3_symbol3[_zz_logic_dataOutputs_0_3_4];
    end
  end

  always @(*) begin
    logic_dataMem_1_0_spinal_port1 = {_zz_logic_dataMem_1_0symbol_read_3, _zz_logic_dataMem_1_0symbol_read_2, _zz_logic_dataMem_1_0symbol_read_1, _zz_logic_dataMem_1_0symbol_read};
  end
  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_1_0_1[0] && _zz_logic_dataMem_1_0_port_1) begin
      logic_dataMem_1_0_symbol0[_zz_logic_dataMem_1_0_port] <= ret_data[7 : 0];
    end
    if(_zz_logic_dataOutputs_1_0_1[1] && _zz_logic_dataMem_1_0_port_1) begin
      logic_dataMem_1_0_symbol1[_zz_logic_dataMem_1_0_port] <= ret_data[15 : 8];
    end
    if(_zz_logic_dataOutputs_1_0_1[2] && _zz_logic_dataMem_1_0_port_1) begin
      logic_dataMem_1_0_symbol2[_zz_logic_dataMem_1_0_port] <= ret_data[23 : 16];
    end
    if(_zz_logic_dataOutputs_1_0_1[3] && _zz_logic_dataMem_1_0_port_1) begin
      logic_dataMem_1_0_symbol3[_zz_logic_dataMem_1_0_port] <= ret_data[31 : 24];
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_1_0_3) begin
      _zz_logic_dataMem_1_0symbol_read <= logic_dataMem_1_0_symbol0[_zz_logic_dataOutputs_1_0_4];
      _zz_logic_dataMem_1_0symbol_read_1 <= logic_dataMem_1_0_symbol1[_zz_logic_dataOutputs_1_0_4];
      _zz_logic_dataMem_1_0symbol_read_2 <= logic_dataMem_1_0_symbol2[_zz_logic_dataOutputs_1_0_4];
      _zz_logic_dataMem_1_0symbol_read_3 <= logic_dataMem_1_0_symbol3[_zz_logic_dataOutputs_1_0_4];
    end
  end

  always @(*) begin
    logic_dataMem_1_1_spinal_port1 = {_zz_logic_dataMem_1_1symbol_read_3, _zz_logic_dataMem_1_1symbol_read_2, _zz_logic_dataMem_1_1symbol_read_1, _zz_logic_dataMem_1_1symbol_read};
  end
  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_1_1_1[0] && _zz_logic_dataMem_1_1_port_1) begin
      logic_dataMem_1_1_symbol0[_zz_logic_dataMem_1_1_port] <= ret_data[7 : 0];
    end
    if(_zz_logic_dataOutputs_1_1_1[1] && _zz_logic_dataMem_1_1_port_1) begin
      logic_dataMem_1_1_symbol1[_zz_logic_dataMem_1_1_port] <= ret_data[15 : 8];
    end
    if(_zz_logic_dataOutputs_1_1_1[2] && _zz_logic_dataMem_1_1_port_1) begin
      logic_dataMem_1_1_symbol2[_zz_logic_dataMem_1_1_port] <= ret_data[23 : 16];
    end
    if(_zz_logic_dataOutputs_1_1_1[3] && _zz_logic_dataMem_1_1_port_1) begin
      logic_dataMem_1_1_symbol3[_zz_logic_dataMem_1_1_port] <= ret_data[31 : 24];
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_1_1_3) begin
      _zz_logic_dataMem_1_1symbol_read <= logic_dataMem_1_1_symbol0[_zz_logic_dataOutputs_1_1_4];
      _zz_logic_dataMem_1_1symbol_read_1 <= logic_dataMem_1_1_symbol1[_zz_logic_dataOutputs_1_1_4];
      _zz_logic_dataMem_1_1symbol_read_2 <= logic_dataMem_1_1_symbol2[_zz_logic_dataOutputs_1_1_4];
      _zz_logic_dataMem_1_1symbol_read_3 <= logic_dataMem_1_1_symbol3[_zz_logic_dataOutputs_1_1_4];
    end
  end

  always @(*) begin
    logic_dataMem_1_2_spinal_port1 = {_zz_logic_dataMem_1_2symbol_read_3, _zz_logic_dataMem_1_2symbol_read_2, _zz_logic_dataMem_1_2symbol_read_1, _zz_logic_dataMem_1_2symbol_read};
  end
  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_1_2_1[0] && _zz_logic_dataMem_1_2_port_1) begin
      logic_dataMem_1_2_symbol0[_zz_logic_dataMem_1_2_port] <= ret_data[7 : 0];
    end
    if(_zz_logic_dataOutputs_1_2_1[1] && _zz_logic_dataMem_1_2_port_1) begin
      logic_dataMem_1_2_symbol1[_zz_logic_dataMem_1_2_port] <= ret_data[15 : 8];
    end
    if(_zz_logic_dataOutputs_1_2_1[2] && _zz_logic_dataMem_1_2_port_1) begin
      logic_dataMem_1_2_symbol2[_zz_logic_dataMem_1_2_port] <= ret_data[23 : 16];
    end
    if(_zz_logic_dataOutputs_1_2_1[3] && _zz_logic_dataMem_1_2_port_1) begin
      logic_dataMem_1_2_symbol3[_zz_logic_dataMem_1_2_port] <= ret_data[31 : 24];
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_1_2_3) begin
      _zz_logic_dataMem_1_2symbol_read <= logic_dataMem_1_2_symbol0[_zz_logic_dataOutputs_1_2_4];
      _zz_logic_dataMem_1_2symbol_read_1 <= logic_dataMem_1_2_symbol1[_zz_logic_dataOutputs_1_2_4];
      _zz_logic_dataMem_1_2symbol_read_2 <= logic_dataMem_1_2_symbol2[_zz_logic_dataOutputs_1_2_4];
      _zz_logic_dataMem_1_2symbol_read_3 <= logic_dataMem_1_2_symbol3[_zz_logic_dataOutputs_1_2_4];
    end
  end

  always @(*) begin
    logic_dataMem_1_3_spinal_port1 = {_zz_logic_dataMem_1_3symbol_read_3, _zz_logic_dataMem_1_3symbol_read_2, _zz_logic_dataMem_1_3symbol_read_1, _zz_logic_dataMem_1_3symbol_read};
  end
  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_1_3_1[0] && _zz_logic_dataMem_1_3_port_1) begin
      logic_dataMem_1_3_symbol0[_zz_logic_dataMem_1_3_port] <= ret_data[7 : 0];
    end
    if(_zz_logic_dataOutputs_1_3_1[1] && _zz_logic_dataMem_1_3_port_1) begin
      logic_dataMem_1_3_symbol1[_zz_logic_dataMem_1_3_port] <= ret_data[15 : 8];
    end
    if(_zz_logic_dataOutputs_1_3_1[2] && _zz_logic_dataMem_1_3_port_1) begin
      logic_dataMem_1_3_symbol2[_zz_logic_dataMem_1_3_port] <= ret_data[23 : 16];
    end
    if(_zz_logic_dataOutputs_1_3_1[3] && _zz_logic_dataMem_1_3_port_1) begin
      logic_dataMem_1_3_symbol3[_zz_logic_dataMem_1_3_port] <= ret_data[31 : 24];
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_dataOutputs_1_3_3) begin
      _zz_logic_dataMem_1_3symbol_read <= logic_dataMem_1_3_symbol0[_zz_logic_dataOutputs_1_3_4];
      _zz_logic_dataMem_1_3symbol_read_1 <= logic_dataMem_1_3_symbol1[_zz_logic_dataOutputs_1_3_4];
      _zz_logic_dataMem_1_3symbol_read_2 <= logic_dataMem_1_3_symbol2[_zz_logic_dataOutputs_1_3_4];
      _zz_logic_dataMem_1_3symbol_read_3 <= logic_dataMem_1_3_symbol3[_zz_logic_dataOutputs_1_3_4];
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_tagOutputs_0_2) begin
      logic_tagMem_0[_zz_logic_tagMem_0_port] <= _zz_logic_tagMem_0_port_1;
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_tagOutputs_0_4) begin
      logic_tagMem_0_spinal_port1 <= logic_tagMem_0[_zz_logic_tagOutputs_0_3];
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_tagOutputs_1_2) begin
      logic_tagMem_1[_zz_logic_tagMem_1_port] <= _zz_logic_tagMem_1_port_1;
    end
  end

  always @(posedge clk) begin
    if(_zz_logic_tagOutputs_1_4) begin
      logic_tagMem_1_spinal_port1 <= logic_tagMem_1[_zz_logic_tagOutputs_1_3];
    end
  end

  always @(*) begin
    case(_zz_logic_wayWords_0_1)
      2'b00 : _zz_logic_wayWords_0 = logic_dataOutputs_0_0;
      2'b01 : _zz_logic_wayWords_0 = logic_dataOutputs_0_1;
      2'b10 : _zz_logic_wayWords_0 = logic_dataOutputs_0_2;
      default : _zz_logic_wayWords_0 = logic_dataOutputs_0_3;
    endcase
  end

  always @(*) begin
    case(_zz_logic_wayWords_1_1)
      2'b00 : _zz_logic_wayWords_1 = logic_dataOutputs_1_0;
      2'b01 : _zz_logic_wayWords_1 = logic_dataOutputs_1_1;
      2'b10 : _zz_logic_wayWords_1 = logic_dataOutputs_1_2;
      default : _zz_logic_wayWords_1 = logic_dataOutputs_1_3;
    endcase
  end

  assign logic_MainIdle = 5'h01;
  assign logic_MainLookup = 5'h02;
  assign logic_MainReplace = 5'h08;
  assign logic_MainRefill = 5'h10;
  assign logic_isIdle = (logic_mainState == logic_MainIdle);
  assign logic_isLookup = (logic_mainState == logic_MainLookup);
  assign logic_isReplace = (logic_mainState == logic_MainReplace);
  assign logic_isRefill = (logic_mainState == logic_MainRefill);
  assign logic_realOffset = (icacop_op_en ? cacop_op_addr_offset : offset);
  assign logic_realIndex = (icacop_op_en ? cacop_op_addr_index : index);
  assign logic_realTag = (logic_requestCacop ? cacop_op_addr_tag : tag);
  assign logic_requestValid = (valid || icacop_op_en);
  assign logic_mode0 = (logic_requestCacop && (logic_requestCacopMode == 2'b00));
  assign logic_mode1 = (logic_requestCacop && ((logic_requestCacopMode == 2'b01) || (logic_requestCacopMode == 2'b11)));
  assign logic_mode2 = (logic_requestCacop && (logic_requestCacopMode == 2'b10));
  assign logic_mode2HitWrite = (logic_mode2 && (|logic_lookupWayHitBuffer));
  always @(*) begin
    logic_wayHit[0] = (logic_tagOutputs_0[0] && (logic_tagOutputs_0[20 : 1] == logic_realTag));
    logic_wayHit[1] = (logic_tagOutputs_1[0] && (logic_tagOutputs_1[20 : 1] == logic_realTag));
  end

  assign logic_cacheHit = ((|logic_wayHit) && (! uncache_en));
  assign logic_addrOk = ((logic_isIdle || (logic_isLookup && logic_cacheHit)) && (! icacop_op_en));
  assign logic_wayWords_0 = _zz_logic_wayWords_0;
  assign logic_wayWords_1 = _zz_logic_wayWords_1;
  assign logic_loadResult = ((logic_wayHit[0] ? logic_wayWords_0 : 32'h0) | (logic_wayHit[1] ? logic_wayWords_1 : 32'h0));
  always @(*) begin
    logic_invalidWay = 2'b00;
    if(when_OpenLa500ICache_l123) begin
      logic_invalidWay = 2'b01;
    end else begin
      if(when_OpenLa500ICache_l125) begin
        logic_invalidWay = 2'b10;
      end
    end
  end

  assign when_OpenLa500ICache_l123 = (! logic_tagOutputs_0[0]);
  assign when_OpenLa500ICache_l125 = (! logic_tagOutputs_1[0]);
  assign logic_hasInvalidWay = (|logic_invalidWay);
  assign logic_randomWay = (logic_lfsr[6] ? 2'b10 : 2'b01);
  assign logic_randomReplacement = (logic_hasInvalidWay ? logic_invalidWay : logic_randomWay);
  assign logic_cacopChosenWay = (logic_requestOffset[0] ? 2'b10 : 2'b01);
  always @(*) begin
    logic_replaceWay = 2'b00;
    if(when_OpenLa500ICache_l134) begin
      logic_replaceWay = logic_cacopChosenWay;
    end else begin
      if(logic_mode2) begin
        logic_replaceWay = logic_wayHit;
      end else begin
        if(when_OpenLa500ICache_l138) begin
          logic_replaceWay = logic_randomReplacement;
        end
      end
    end
  end

  assign when_OpenLa500ICache_l134 = (logic_mode0 || logic_mode1);
  assign when_OpenLa500ICache_l138 = (! logic_requestCacop);
  assign logic_rdReq = (logic_isReplace && (! ((logic_mode0 || logic_mode1) || logic_mode2)));
  assign logic_refillMatch = (logic_missRetNum == logic_requestOffset[3 : 2]);
  assign logic_dataOk = ((logic_isLookup && ((logic_cacheHit || tlb_excp_cancel_req) || logic_requestCacop)) || (((logic_isRefill && ret_valid) && (logic_refillMatch || logic_requestUncache)) && (! logic_requestCacop)));
  assign logic_nextRetNum = (logic_missRetNum + 2'b01);
  assign _zz_logic_dataOutputs_0_0 = (logic_addrOk ? logic_realIndex : logic_requestIndex);
  always @(*) begin
    _zz_logic_dataOutputs_0_0_1 = 4'b0000;
    if(when_OpenLa500ICache_l155) begin
      _zz_logic_dataOutputs_0_0_1 = 4'b1111;
    end
  end

  assign when_OpenLa500ICache_l155 = (((logic_isRefill && logic_missReplaceWay[0]) && ret_valid) && (logic_missRetNum == 2'b00));
  assign _zz_logic_dataOutputs_0_0_2 = (((! (logic_requestUncache || logic_mode0)) || logic_isIdle) || logic_isLookup);
  assign _zz_logic_dataOutputs_0_0_3 = (_zz_logic_dataOutputs_0_0_2 && (! (|_zz_logic_dataOutputs_0_0_1)));
  assign _zz_logic_dataOutputs_0_0_4 = _zz_logic_dataOutputs_0_0;
  assign logic_dataOutputs_0_0 = logic_dataMem_0_0_spinal_port1;
  assign _zz_logic_dataOutputs_0_1 = (logic_addrOk ? logic_realIndex : logic_requestIndex);
  always @(*) begin
    _zz_logic_dataOutputs_0_1_1 = 4'b0000;
    if(when_OpenLa500ICache_l155_1) begin
      _zz_logic_dataOutputs_0_1_1 = 4'b1111;
    end
  end

  assign when_OpenLa500ICache_l155_1 = (((logic_isRefill && logic_missReplaceWay[0]) && ret_valid) && (logic_missRetNum == 2'b01));
  assign _zz_logic_dataOutputs_0_1_2 = (((! (logic_requestUncache || logic_mode0)) || logic_isIdle) || logic_isLookup);
  assign _zz_logic_dataOutputs_0_1_3 = (_zz_logic_dataOutputs_0_1_2 && (! (|_zz_logic_dataOutputs_0_1_1)));
  assign _zz_logic_dataOutputs_0_1_4 = _zz_logic_dataOutputs_0_1;
  assign logic_dataOutputs_0_1 = logic_dataMem_0_1_spinal_port1;
  assign _zz_logic_dataOutputs_0_2 = (logic_addrOk ? logic_realIndex : logic_requestIndex);
  always @(*) begin
    _zz_logic_dataOutputs_0_2_1 = 4'b0000;
    if(when_OpenLa500ICache_l155_2) begin
      _zz_logic_dataOutputs_0_2_1 = 4'b1111;
    end
  end

  assign when_OpenLa500ICache_l155_2 = (((logic_isRefill && logic_missReplaceWay[0]) && ret_valid) && (logic_missRetNum == 2'b10));
  assign _zz_logic_dataOutputs_0_2_2 = (((! (logic_requestUncache || logic_mode0)) || logic_isIdle) || logic_isLookup);
  assign _zz_logic_dataOutputs_0_2_3 = (_zz_logic_dataOutputs_0_2_2 && (! (|_zz_logic_dataOutputs_0_2_1)));
  assign _zz_logic_dataOutputs_0_2_4 = _zz_logic_dataOutputs_0_2;
  assign logic_dataOutputs_0_2 = logic_dataMem_0_2_spinal_port1;
  assign _zz_logic_dataOutputs_0_3 = (logic_addrOk ? logic_realIndex : logic_requestIndex);
  always @(*) begin
    _zz_logic_dataOutputs_0_3_1 = 4'b0000;
    if(when_OpenLa500ICache_l155_3) begin
      _zz_logic_dataOutputs_0_3_1 = 4'b1111;
    end
  end

  assign when_OpenLa500ICache_l155_3 = (((logic_isRefill && logic_missReplaceWay[0]) && ret_valid) && (logic_missRetNum == 2'b11));
  assign _zz_logic_dataOutputs_0_3_2 = (((! (logic_requestUncache || logic_mode0)) || logic_isIdle) || logic_isLookup);
  assign _zz_logic_dataOutputs_0_3_3 = (_zz_logic_dataOutputs_0_3_2 && (! (|_zz_logic_dataOutputs_0_3_1)));
  assign _zz_logic_dataOutputs_0_3_4 = _zz_logic_dataOutputs_0_3;
  assign logic_dataOutputs_0_3 = logic_dataMem_0_3_spinal_port1;
  assign _zz_logic_dataOutputs_1_0 = (logic_addrOk ? logic_realIndex : logic_requestIndex);
  always @(*) begin
    _zz_logic_dataOutputs_1_0_1 = 4'b0000;
    if(when_OpenLa500ICache_l155_4) begin
      _zz_logic_dataOutputs_1_0_1 = 4'b1111;
    end
  end

  assign when_OpenLa500ICache_l155_4 = (((logic_isRefill && logic_missReplaceWay[1]) && ret_valid) && (logic_missRetNum == 2'b00));
  assign _zz_logic_dataOutputs_1_0_2 = (((! (logic_requestUncache || logic_mode0)) || logic_isIdle) || logic_isLookup);
  assign _zz_logic_dataOutputs_1_0_3 = (_zz_logic_dataOutputs_1_0_2 && (! (|_zz_logic_dataOutputs_1_0_1)));
  assign _zz_logic_dataOutputs_1_0_4 = _zz_logic_dataOutputs_1_0;
  assign logic_dataOutputs_1_0 = logic_dataMem_1_0_spinal_port1;
  assign _zz_logic_dataOutputs_1_1 = (logic_addrOk ? logic_realIndex : logic_requestIndex);
  always @(*) begin
    _zz_logic_dataOutputs_1_1_1 = 4'b0000;
    if(when_OpenLa500ICache_l155_5) begin
      _zz_logic_dataOutputs_1_1_1 = 4'b1111;
    end
  end

  assign when_OpenLa500ICache_l155_5 = (((logic_isRefill && logic_missReplaceWay[1]) && ret_valid) && (logic_missRetNum == 2'b01));
  assign _zz_logic_dataOutputs_1_1_2 = (((! (logic_requestUncache || logic_mode0)) || logic_isIdle) || logic_isLookup);
  assign _zz_logic_dataOutputs_1_1_3 = (_zz_logic_dataOutputs_1_1_2 && (! (|_zz_logic_dataOutputs_1_1_1)));
  assign _zz_logic_dataOutputs_1_1_4 = _zz_logic_dataOutputs_1_1;
  assign logic_dataOutputs_1_1 = logic_dataMem_1_1_spinal_port1;
  assign _zz_logic_dataOutputs_1_2 = (logic_addrOk ? logic_realIndex : logic_requestIndex);
  always @(*) begin
    _zz_logic_dataOutputs_1_2_1 = 4'b0000;
    if(when_OpenLa500ICache_l155_6) begin
      _zz_logic_dataOutputs_1_2_1 = 4'b1111;
    end
  end

  assign when_OpenLa500ICache_l155_6 = (((logic_isRefill && logic_missReplaceWay[1]) && ret_valid) && (logic_missRetNum == 2'b10));
  assign _zz_logic_dataOutputs_1_2_2 = (((! (logic_requestUncache || logic_mode0)) || logic_isIdle) || logic_isLookup);
  assign _zz_logic_dataOutputs_1_2_3 = (_zz_logic_dataOutputs_1_2_2 && (! (|_zz_logic_dataOutputs_1_2_1)));
  assign _zz_logic_dataOutputs_1_2_4 = _zz_logic_dataOutputs_1_2;
  assign logic_dataOutputs_1_2 = logic_dataMem_1_2_spinal_port1;
  assign _zz_logic_dataOutputs_1_3 = (logic_addrOk ? logic_realIndex : logic_requestIndex);
  always @(*) begin
    _zz_logic_dataOutputs_1_3_1 = 4'b0000;
    if(when_OpenLa500ICache_l155_7) begin
      _zz_logic_dataOutputs_1_3_1 = 4'b1111;
    end
  end

  assign when_OpenLa500ICache_l155_7 = (((logic_isRefill && logic_missReplaceWay[1]) && ret_valid) && (logic_missRetNum == 2'b11));
  assign _zz_logic_dataOutputs_1_3_2 = (((! (logic_requestUncache || logic_mode0)) || logic_isIdle) || logic_isLookup);
  assign _zz_logic_dataOutputs_1_3_3 = (_zz_logic_dataOutputs_1_3_2 && (! (|_zz_logic_dataOutputs_1_3_1)));
  assign _zz_logic_dataOutputs_1_3_4 = _zz_logic_dataOutputs_1_3;
  assign logic_dataOutputs_1_3 = logic_dataMem_1_3_spinal_port1;
  always @(*) begin
    _zz_logic_tagOutputs_0 = 8'h0;
    if(when_OpenLa500ICache_l176) begin
      _zz_logic_tagOutputs_0 = logic_realIndex;
    end else begin
      if(when_OpenLa500ICache_l178) begin
        _zz_logic_tagOutputs_0 = logic_requestIndex;
      end
    end
  end

  assign when_OpenLa500ICache_l176 = (logic_addrOk || (icacop_op_en && (logic_isIdle || logic_isLookup)));
  assign when_OpenLa500ICache_l178 = (logic_isReplace || logic_isRefill);
  assign _zz_logic_tagOutputs_0_1 = (((! logic_requestUncache) || logic_isIdle) || logic_isLookup);
  assign _zz_logic_tagOutputs_0_2 = (((_zz_logic_tagOutputs_0_1 && logic_missReplaceWay[0]) && logic_isRefill) && ((((ret_valid && ret_last) || logic_mode0) || logic_mode1) || logic_mode2HitWrite));
  assign _zz_logic_tagOutputs_0_3 = _zz_logic_tagOutputs_0;
  assign _zz_logic_tagOutputs_0_4 = (_zz_logic_tagOutputs_0_1 && (! _zz_logic_tagOutputs_0_2));
  assign logic_tagOutputs_0 = logic_tagMem_0_spinal_port1;
  always @(*) begin
    _zz_logic_tagOutputs_1 = 8'h0;
    if(when_OpenLa500ICache_l176_1) begin
      _zz_logic_tagOutputs_1 = logic_realIndex;
    end else begin
      if(when_OpenLa500ICache_l178_1) begin
        _zz_logic_tagOutputs_1 = logic_requestIndex;
      end
    end
  end

  assign when_OpenLa500ICache_l176_1 = (logic_addrOk || (icacop_op_en && (logic_isIdle || logic_isLookup)));
  assign when_OpenLa500ICache_l178_1 = (logic_isReplace || logic_isRefill);
  assign _zz_logic_tagOutputs_1_1 = (((! logic_requestUncache) || logic_isIdle) || logic_isLookup);
  assign _zz_logic_tagOutputs_1_2 = (((_zz_logic_tagOutputs_1_1 && logic_missReplaceWay[1]) && logic_isRefill) && ((((ret_valid && ret_last) || logic_mode0) || logic_mode1) || logic_mode2HitWrite));
  assign _zz_logic_tagOutputs_1_3 = _zz_logic_tagOutputs_1;
  assign _zz_logic_tagOutputs_1_4 = (_zz_logic_tagOutputs_1_1 && (! _zz_logic_tagOutputs_1_2));
  assign logic_tagOutputs_1 = logic_tagMem_1_spinal_port1;
  assign when_OpenLa500ICache_l212 = (logic_requestValid && logic_cacheHit);
  assign when_OpenLa500ICache_l219 = (! logic_cacheHit);
  assign when_OpenLa500ICache_l235 = ((ret_valid && ret_last) || (! logic_rdReqBuffer));
  assign when_OpenLa500ICache_l246 = (logic_mode2 && logic_isLookup);
  assign when_OpenLa500ICache_l252 = ((logic_isRefill && ret_valid) && ret_last);
  assign addr_ok = logic_addrOk;
  assign data_ok = logic_dataOk;
  assign rdata = (logic_isLookup ? logic_loadResult : (logic_isRefill ? ret_data : 32'h0));
  assign icache_unbusy = logic_isIdle;
  assign rd_req = logic_rdReq;
  assign rd_type = (logic_requestUncache ? 3'b010 : 3'b100);
  assign rd_addr = (logic_requestUncache ? {{logic_requestTag,logic_requestIndex},logic_requestOffset} : {{logic_requestTag,logic_requestIndex},4'b0000});
  assign wr_req = logic_legacyWrReq;
  assign wr_type = 3'b000;
  assign wr_addr = 32'h0;
  assign wr_wstrb = 4'b0000;
  assign wr_data = 128'h0;
  assign cache_miss = ((logic_isRefill && ret_last) && (! (logic_requestUncache || logic_requestCacop)));
  always @(posedge clk) begin
    if(reset) begin
      logic_mainState <= logic_MainIdle;
      logic_requestIndex <= 8'h0;
      logic_requestTag <= 20'h0;
      logic_requestOffset <= 4'b0000;
      logic_requestUncache <= 1'b0;
      logic_requestCacop <= 1'b0;
      logic_requestCacopMode <= 2'b00;
      logic_missReplaceWay <= 2'b00;
      logic_lookupWayHitBuffer <= 2'b00;
      logic_rdReqBuffer <= 1'b0;
      logic_lfsr <= 8'h01;
      logic_legacyWrReq <= 1'b0;
    end else begin
      if((logic_mainState == logic_MainIdle)) begin
          if(logic_requestValid) begin
            logic_mainState <= logic_MainLookup;
            logic_requestIndex <= logic_realIndex;
            logic_requestOffset <= logic_realOffset;
            logic_requestCacopMode <= cacop_op_mode;
            logic_requestCacop <= icacop_op_en;
          end
      end else if((logic_mainState == logic_MainLookup)) begin
          if(when_OpenLa500ICache_l212) begin
            logic_mainState <= logic_MainLookup;
            logic_requestIndex <= logic_realIndex;
            logic_requestOffset <= logic_realOffset;
            logic_requestCacopMode <= cacop_op_mode;
            logic_requestCacop <= icacop_op_en;
          end else begin
            if(tlb_excp_cancel_req) begin
              logic_mainState <= logic_MainIdle;
            end else begin
              if(logic_requestCacop) begin
                logic_mainState <= logic_MainIdle;
              end else begin
                if(when_OpenLa500ICache_l219) begin
                  logic_mainState <= logic_MainReplace;
                  logic_requestTag <= logic_realTag;
                  logic_requestUncache <= (uncache_en && (! logic_requestCacop));
                  logic_missReplaceWay <= logic_replaceWay;
                end else begin
                  logic_mainState <= logic_MainIdle;
                end
              end
            end
          end
      end else if((logic_mainState == logic_MainReplace)) begin
          if(rd_rdy) begin
            logic_mainState <= logic_MainRefill;
          end
      end else if((logic_mainState == logic_MainRefill)) begin
          if(when_OpenLa500ICache_l235) begin
            logic_mainState <= logic_MainIdle;
          end
      end else begin
          logic_mainState <= logic_MainIdle;
      end
      if(when_OpenLa500ICache_l246) begin
        logic_lookupWayHitBuffer <= logic_wayHit;
      end
      if(logic_rdReq) begin
        logic_rdReqBuffer <= 1'b1;
      end else begin
        if(when_OpenLa500ICache_l252) begin
          logic_rdReqBuffer <= 1'b0;
        end
      end
      logic_lfsr[0] <= logic_lfsr[7];
      logic_lfsr[1] <= logic_lfsr[0];
      logic_lfsr[2] <= logic_lfsr[1];
      logic_lfsr[3] <= logic_lfsr[2];
      logic_lfsr[4] <= (logic_lfsr[3] ^ logic_lfsr[7]);
      logic_lfsr[5] <= (logic_lfsr[4] ^ logic_lfsr[7]);
      logic_lfsr[6] <= (logic_lfsr[5] ^ logic_lfsr[7]);
      logic_lfsr[7] <= logic_lfsr[6];
      logic_legacyWrReq <= logic_legacyWrReq;
    end
  end

  always @(posedge clk) begin
    if((logic_mainState == logic_MainIdle)) begin
    end else if((logic_mainState == logic_MainLookup)) begin
    end else if((logic_mainState == logic_MainReplace)) begin
        if(rd_rdy) begin
          logic_missRetNum <= 2'b00;
        end
    end else if((logic_mainState == logic_MainRefill)) begin
        if(!when_OpenLa500ICache_l235) begin
          if(ret_valid) begin
            logic_missRetNum <= logic_nextRetNum;
          end
        end
    end else begin
    end
  end


endmodule
