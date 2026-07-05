// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : CPUCoreFlat
// Git hash  : eb47745889230a47fa0819408570d501b4e90a80

`timescale 1ns/1ps

module CPUCoreFlat (
  input  wire          _zz_8,
  input  wire          _zz_9,
  input  wire [7:0]    _zz_10,
  output wire [3:0]    _zz_11,
  output wire [31:0]   _zz_12,
  output wire [7:0]    _zz_13,
  output wire [2:0]    _zz_14,
  output wire [1:0]    _zz_15,
  output wire [1:0]    _zz_16,
  output wire [3:0]    _zz_17,
  output wire [2:0]    _zz_18,
  output wire          _zz_19,
  input  wire          _zz_20,
  input  wire [3:0]    _zz_21,
  input  wire [31:0]   _zz_22,
  input  wire [1:0]    _zz_23,
  input  wire          _zz_24,
  input  wire          _zz_25,
  output wire          _zz_26,
  output wire [3:0]    _zz_27,
  output wire [31:0]   _zz_28,
  output wire [7:0]    _zz_29,
  output wire [2:0]    _zz_30,
  output wire [1:0]    _zz_31,
  output wire [1:0]    _zz_32,
  output wire [3:0]    _zz_33,
  output wire [2:0]    _zz_34,
  output wire          _zz_35,
  input  wire          _zz_36,
  output wire [3:0]    _zz_37,
  output wire [31:0]   _zz_38,
  output wire [3:0]    _zz_39,
  output wire          _zz_40,
  output wire          _zz_41,
  input  wire          _zz_42,
  input  wire [3:0]    _zz_43,
  input  wire [1:0]    _zz_44,
  input  wire          _zz_45,
  output wire          _zz_46,
  output wire [31:0]   _zz_47,
  output wire          _zz_48,
  output wire [4:0]    _zz_49,
  output wire [31:0]   _zz_50,
  output wire [31:0]   _zz_51,
  input  wire          clk,
  input  wire          resetn
);

  wire       [31:0]   _zz_52_spinal_port1;
  wire       [31:0]   _zz_52_spinal_port2;
  wire       [0:0]    _zz_61_spinal_port0;
  wire       [0:0]    _zz_61_spinal_port1;
  wire       [19:0]   _zz_62_spinal_port0;
  wire       [19:0]   _zz_62_spinal_port1;
  wire       [31:0]   _zz_63_spinal_port0;
  wire       [0:0]    _zz_71_spinal_port0;
  wire       [0:0]    _zz_71_spinal_port1;
  wire       [19:0]   _zz_72_spinal_port0;
  wire       [19:0]   _zz_72_spinal_port1;
  wire       [31:0]   _zz_73_spinal_port0;
  wire       [31:0]   _zz__zz_52_port;
  wire       [31:0]   _zz__zz_when_Core_l148_5;
  wire       [11:0]   _zz__zz_when_Core_l148_5_1;
  wire       [17:0]   _zz__zz_when_Core_l148_5_2;
  wire       [27:0]   _zz__zz_when_Core_l148_5_3;
  wire       [31:0]   _zz__zz_switch_Misc_l245_2;
  wire       [31:0]   _zz__zz_switch_Misc_l245_2_1;
  wire       [31:0]   _zz__zz_switch_Misc_l245_2_2;
  wire       [4:0]    _zz__zz_switch_Misc_l245_2_3;
  wire       [31:0]   _zz__zz_switch_Misc_l245_2_4;
  wire       [31:0]   _zz__zz_switch_Misc_l245_2_5;
  wire       [31:0]   _zz_when_Core_l148_9;
  wire       [31:0]   _zz_when_Core_l148_10;
  wire       [31:0]   _zz__zz_84;
  wire       [15:0]   _zz__zz_84_1;
  wire       [31:0]   _zz__zz_84_2;
  wire       [31:0]   _zz__zz_84_3;
  wire       [7:0]    _zz__zz_84_4;
  wire       [31:0]   _zz__zz_84_5;
  wire       [10:0]   _zz__zz_73_port;
  wire       [31:0]   _zz__zz_73_port_1;
  wire       [8:0]    _zz__zz_71_port;
  wire       [0:0]    _zz__zz_71_port_1;
  wire       [8:0]    _zz__zz_72_port;
  wire       [19:0]   _zz__zz_72_port_1;
  wire       [10:0]   _zz__zz_73_port_2;
  wire       [31:0]   _zz__zz_73_port_3;
  wire       [8:0]    _zz__zz_71_port_2;
  wire       [0:0]    _zz__zz_71_port_3;
  wire       [8:0]    _zz__zz_72_port_2;
  wire       [19:0]   _zz__zz_72_port_3;
  reg                 _zz_1;
  reg                 _zz_2;
  reg                 _zz_3;
  reg                 _zz_4;
  reg                 _zz_5;
  reg                 _zz_6;
  reg                 _zz_7;
  wire                _zz_when_Core_l28;
  wire       [4:0]    _zz_when_Core_l28_1;
  wire       [31:0]   _zz_53;
  wire                when_Core_l28;
  reg        [31:0]   _zz_when_Core_l69;
  reg        [31:0]   _zz_when_Core_l95;
  reg                 _zz_when_Core_l73;
  reg        [31:0]   _zz_55;
  reg        [31:0]   _zz_when_Core_l95_1;
  reg                 _zz_when_Core_l108;
  reg        [4:0]    _zz_when_Core_l28_2;
  reg        [31:0]   _zz_when_Core_l148;
  reg        [3:0]    switch_Core_l118;
  reg                 _zz_when_Core_l147;
  reg                 _zz_when_Core_l185;
  reg        [1:0]    _zz_switch_Misc_l245;
  reg                 _zz_56;
  reg                 _zz_when_Core_l28_3;
  reg                 _zz_when_Core_l148_1;
  reg        [1:0]    _zz_when_Core_l148_2;
  reg        [31:0]   _zz_57;
  reg        [31:0]   _zz_switch_Misc_l245_1;
  reg        [31:0]   _zz_58;
  reg                 _zz_when_Core_l147_1;
  reg                 _zz_when_Core_l185_1;
  reg        [1:0]    switch_Misc_l245;
  reg                 _zz_59;
  reg                 _zz_when_Core_l28_4;
  reg                 when_Core_l180;
  reg        [31:0]   _zz_60;
  reg                 _zz_when_Core_l28_5;
  reg                 _zz_when_Core_l28_6;
  reg        [4:0]    _zz_when_Core_l28_7;
  reg                 when_Core_l52;
  reg                 _zz_when_Core_l73_1;
  reg                 when_Core_l51;
  reg        [31:0]   _zz_when_Core_l69_1;
  wire       [7:0]    _zz_when_Core_l69_2;
  wire       [19:0]   _zz_when_Core_l69_3;
  wire       [8:0]    _zz_when_Core_l69_4;
  wire       [8:0]    _zz_when_Core_l69_5;
  wire                _zz_when_Core_l69_6;
  wire       [8:0]    _zz_when_Core_l69_7;
  wire       [8:0]    _zz_when_Core_l69_8;
  wire                when_Core_l69;
  wire       [10:0]   _zz_when_Core_l95_2;
  wire                when_Core_l73;
  wire       [5:0]    _zz_when_Core_l95_3;
  wire       [4:0]    _zz_when_Core_l148_3;
  wire       [4:0]    _zz_when_Core_l148_4;
  wire                _zz_when_Core_l100;
  wire                _zz_when_Core_l92;
  wire                _zz_when_Core_l92_1;
  wire                _zz_when_Core_l92_2;
  wire                _zz_when_Core_l94;
  wire                when_Core_l95;
  wire                _zz_when_Core_l94_1;
  wire                _zz_when_Core_l93;
  wire                _zz_when_Core_l93_1;
  wire                _zz_when_Core_l92_3;
  reg        [31:0]   _zz_when_Core_l148_5;
  wire                when_Core_l92;
  wire                when_Core_l93;
  wire                when_Core_l94;
  reg        [3:0]    _zz_switch_Core_l118;
  wire                when_Core_l100;
  wire                when_Core_l101;
  wire       [31:0]   _zz_when_Core_l148_6;
  wire       [31:0]   _zz_when_Core_l148_7;
  wire                when_Core_l108;
  wire       [31:0]   _zz_when_Core_l148_8;
  reg        [31:0]   _zz_switch_Misc_l245_2;
  wire                when_Core_l148;
  wire                when_Core_l147;
  wire                when_Core_l142;
  wire       [7:0]    _zz_when_Core_l147_2;
  wire       [19:0]   _zz_when_Core_l147_3;
  wire       [1:0]    _zz_74;
  wire       [8:0]    _zz_when_Core_l147_4;
  wire       [8:0]    _zz_when_Core_l147_5;
  wire                _zz_when_Core_l147_6;
  wire       [8:0]    _zz_when_Core_l147_7;
  wire       [8:0]    _zz_when_Core_l147_8;
  wire                _zz_when_Core_l147_9;
  wire       [10:0]   _zz_79;
  wire       [31:0]   _zz_80;
  wire       [1:0]    switch_Misc_l245_1;
  reg        [7:0]    _zz_82;
  wire       [15:0]   _zz_83;
  reg        [31:0]   _zz_84;
  wire                when_Core_l185;
  wire       [0:0]    _zz_85;
  wire                when_Core_l192;
  wire       [0:0]    _zz_89;
  (* ram_style = "distributed" *) reg [31:0] _zz_52 [0:31];
  reg [0:0] _zz_61 [0:511];
  reg [19:0] _zz_62 [0:511];
  reg [31:0] _zz_63 [0:2047];
  (* ram_style = "distributed" *) reg [0:0] _zz_71 [0:511];
  (* ram_style = "distributed" *) reg [19:0] _zz_72 [0:511];
  (* ram_style = "distributed" *) reg [31:0] _zz_73 [0:2047];

  assign _zz__zz_when_Core_l148_5_1 = _zz_when_Core_l95_1[21 : 10];
  assign _zz__zz_when_Core_l148_5 = {{20{_zz__zz_when_Core_l148_5_1[11]}}, _zz__zz_when_Core_l148_5_1};
  assign _zz__zz_when_Core_l148_5_2 = {_zz_when_Core_l95_1[25 : 10],2'b00};
  assign _zz__zz_when_Core_l148_5_3 = {{_zz_when_Core_l95_1[9 : 0],_zz_when_Core_l95_1[25 : 10]},2'b00};
  assign _zz__zz_switch_Misc_l245_2 = _zz_when_Core_l148_6;
  assign _zz__zz_switch_Misc_l245_2_1 = _zz_when_Core_l148_8;
  assign _zz__zz_switch_Misc_l245_2_3 = _zz_when_Core_l148_8[4 : 0];
  assign _zz__zz_switch_Misc_l245_2_2 = {27'd0, _zz__zz_switch_Misc_l245_2_3};
  assign _zz__zz_switch_Misc_l245_2_4 = ($signed(_zz__zz_switch_Misc_l245_2_5) >>> _zz_when_Core_l148_8[4 : 0]);
  assign _zz__zz_switch_Misc_l245_2_5 = _zz_when_Core_l148_6;
  assign _zz_when_Core_l148_9 = _zz_when_Core_l148_6;
  assign _zz_when_Core_l148_10 = _zz_when_Core_l148_8;
  assign _zz__zz_84_1 = _zz_83;
  assign _zz__zz_84 = {{16{_zz__zz_84_1[15]}}, _zz__zz_84_1};
  assign _zz__zz_84_2 = {16'd0, _zz_83};
  assign _zz__zz_84_4 = _zz_82;
  assign _zz__zz_84_3 = {{24{_zz__zz_84_4[7]}}, _zz__zz_84_4};
  assign _zz__zz_84_5 = {24'd0, _zz_82};
  assign _zz__zz_52_port = _zz_53;
  assign _zz__zz_71_port = {_zz_when_Core_l147_2,_zz_85};
  assign _zz__zz_71_port_1 = 1'b1;
  assign _zz__zz_71_port_2 = {_zz_when_Core_l147_2,_zz_89};
  assign _zz__zz_71_port_3 = 1'b1;
  assign _zz__zz_72_port = {_zz_when_Core_l147_2,_zz_85};
  assign _zz__zz_72_port_1 = _zz_when_Core_l147_3;
  assign _zz__zz_72_port_2 = {_zz_when_Core_l147_2,_zz_89};
  assign _zz__zz_72_port_3 = _zz_when_Core_l147_3;
  assign _zz__zz_73_port = {{_zz_85,_zz_when_Core_l147_2},_zz_74};
  assign _zz__zz_73_port_1 = _zz_58;
  assign _zz__zz_73_port_2 = {{_zz_89,_zz_when_Core_l147_2},2'b00};
  assign _zz__zz_73_port_3 = _zz_80;
  always @(posedge clk) begin
    if(_zz_7) begin
      _zz_52[_zz_when_Core_l28_1] <= _zz__zz_52_port;
    end
  end

  assign _zz_52_spinal_port1 = _zz_52[_zz_when_Core_l148_3];
  assign _zz_52_spinal_port2 = _zz_52[_zz_when_Core_l148_4];
  assign _zz_61_spinal_port0 = _zz_61[_zz_when_Core_l69_4];
  assign _zz_61_spinal_port1 = _zz_61[_zz_when_Core_l69_7];
  assign _zz_62_spinal_port0 = _zz_62[_zz_when_Core_l69_5];
  assign _zz_62_spinal_port1 = _zz_62[_zz_when_Core_l69_8];
  assign _zz_63_spinal_port0 = _zz_63[_zz_when_Core_l95_2];
  assign _zz_71_spinal_port0 = _zz_71[_zz_when_Core_l147_4];
  assign _zz_71_spinal_port1 = _zz_71[_zz_when_Core_l147_7];
  always @(posedge clk) begin
    if(_zz_5) begin
      _zz_71[_zz__zz_71_port] <= _zz__zz_71_port_1;
    end
  end

  always @(posedge clk) begin
    if(_zz_2) begin
      _zz_71[_zz__zz_71_port_2] <= _zz__zz_71_port_3;
    end
  end

  assign _zz_72_spinal_port0 = _zz_72[_zz_when_Core_l147_5];
  assign _zz_72_spinal_port1 = _zz_72[_zz_when_Core_l147_8];
  always @(posedge clk) begin
    if(_zz_4) begin
      _zz_72[_zz__zz_72_port] <= _zz__zz_72_port_1;
    end
  end

  always @(posedge clk) begin
    if(_zz_1) begin
      _zz_72[_zz__zz_72_port_2] <= _zz__zz_72_port_3;
    end
  end

  assign _zz_73_spinal_port0 = _zz_73[_zz_79];
  always @(posedge clk) begin
    if(_zz_6) begin
      _zz_73[_zz__zz_73_port] <= _zz__zz_73_port_1;
    end
  end

  always @(posedge clk) begin
    if(_zz_3) begin
      _zz_73[_zz__zz_73_port_2] <= _zz__zz_73_port_3;
    end
  end

  always @(*) begin
    _zz_1 = 1'b0;
    if(when_Core_l192) begin
      _zz_1 = 1'b1;
    end
  end

  always @(*) begin
    _zz_2 = 1'b0;
    if(when_Core_l192) begin
      _zz_2 = 1'b1;
    end
  end

  always @(*) begin
    _zz_3 = 1'b0;
    if(when_Core_l192) begin
      _zz_3 = 1'b1;
    end
  end

  always @(*) begin
    _zz_4 = 1'b0;
    if(when_Core_l185) begin
      _zz_4 = 1'b1;
    end
  end

  always @(*) begin
    _zz_5 = 1'b0;
    if(when_Core_l185) begin
      _zz_5 = 1'b1;
    end
  end

  always @(*) begin
    _zz_6 = 1'b0;
    if(when_Core_l185) begin
      _zz_6 = 1'b1;
    end
  end

  always @(*) begin
    _zz_7 = 1'b0;
    if(when_Core_l28) begin
      _zz_7 = 1'b1;
    end
  end

  assign when_Core_l28 = (_zz_when_Core_l28 && (_zz_when_Core_l28_1 != 5'h0));
  always @(*) begin
    if(when_Core_l51) begin
      _zz_when_Core_l69_1 = 32'h1bfc0000;
    end else begin
      if(when_Core_l52) begin
        _zz_when_Core_l69_1 = _zz_when_Core_l69;
      end else begin
        _zz_when_Core_l69_1 = (_zz_when_Core_l69 + 32'h00000004);
      end
    end
  end

  assign _zz_when_Core_l69_2 = _zz_when_Core_l69[11 : 4];
  assign _zz_when_Core_l69_3 = _zz_when_Core_l69[31 : 12];
  assign _zz_when_Core_l69_4 = {_zz_when_Core_l69_2,1'b0};
  assign _zz_when_Core_l69_5 = {_zz_when_Core_l69_2,1'b0};
  assign _zz_when_Core_l69_6 = (_zz_61_spinal_port0[0] && (_zz_62_spinal_port0 == _zz_when_Core_l69_3));
  assign _zz_when_Core_l69_7 = {_zz_when_Core_l69_2,1'b1};
  assign _zz_when_Core_l69_8 = {_zz_when_Core_l69_2,1'b1};
  assign when_Core_l69 = ((_zz_when_Core_l69_6 || (_zz_61_spinal_port1[0] && (_zz_62_spinal_port1 == _zz_when_Core_l69_3))) && (! when_Core_l52));
  assign _zz_when_Core_l95_2 = {{(_zz_when_Core_l69_6 ? 1'b0 : 1'b1),_zz_when_Core_l69_2},_zz_when_Core_l69[3 : 2]};
  assign when_Core_l73 = ((! _zz_when_Core_l73_1) && _zz_when_Core_l73);
  assign _zz_when_Core_l95_3 = _zz_when_Core_l95_1[31 : 26];
  assign _zz_when_Core_l148_3 = _zz_when_Core_l95_1[9 : 5];
  assign _zz_when_Core_l148_4 = _zz_when_Core_l95_1[14 : 10];
  assign _zz_when_Core_l100 = ((_zz_when_Core_l95_3[5 : 2] <= 4'b1110) && (! _zz_when_Core_l95_1[25]));
  assign _zz_when_Core_l92 = _zz_when_Core_l95_1[25];
  assign _zz_when_Core_l92_1 = ((4'b1000 <= _zz_when_Core_l95_3[5 : 2]) && (_zz_when_Core_l95_3[5 : 2] <= 4'b1011));
  assign _zz_when_Core_l92_2 = ((4'b0100 <= _zz_when_Core_l95_3[5 : 2]) && (_zz_when_Core_l95_3[5 : 2] <= 4'b0111));
  assign _zz_when_Core_l94 = (_zz_when_Core_l95_3[5 : 1] == 5'h0c);
  assign when_Core_l95 = (_zz_when_Core_l95_3 == 6'h13);
  assign _zz_when_Core_l94_1 = (_zz_when_Core_l95_3 == 6'h12);
  assign _zz_when_Core_l93 = (_zz_when_Core_l95_3 == 6'h05);
  assign _zz_when_Core_l93_1 = (_zz_when_Core_l95_3 == 6'h06);
  assign _zz_when_Core_l92_3 = (_zz_when_Core_l92_1 || _zz_when_Core_l92_2);
  assign when_Core_l92 = (_zz_when_Core_l92 || _zz_when_Core_l92_3);
  always @(*) begin
    if(when_Core_l92) begin
      _zz_when_Core_l148_5 = _zz__zz_when_Core_l148_5;
    end else begin
      if(when_Core_l93) begin
        _zz_when_Core_l148_5 = {_zz_when_Core_l95_1[24 : 5],12'h0};
      end else begin
        if(when_Core_l94) begin
          _zz_when_Core_l148_5 = {14'd0, _zz__zz_when_Core_l148_5_2};
        end else begin
          if(when_Core_l95) begin
            _zz_when_Core_l148_5 = {4'd0, _zz__zz_when_Core_l148_5_3};
          end else begin
            _zz_when_Core_l148_5 = 32'h0;
          end
        end
      end
    end
  end

  assign when_Core_l93 = (_zz_when_Core_l93_1 || _zz_when_Core_l93);
  assign when_Core_l94 = (_zz_when_Core_l94 || _zz_when_Core_l94_1);
  assign when_Core_l100 = (_zz_when_Core_l100 || _zz_when_Core_l92);
  always @(*) begin
    if(when_Core_l100) begin
      _zz_switch_Core_l118 = _zz_when_Core_l95_3[3 : 0];
    end else begin
      if(when_Core_l101) begin
        _zz_switch_Core_l118 = 4'b0000;
      end else begin
        _zz_switch_Core_l118 = 4'b1111;
      end
    end
  end

  assign when_Core_l101 = (((((_zz_when_Core_l92_3 || _zz_when_Core_l93) || _zz_when_Core_l93_1) || _zz_when_Core_l94_1) || when_Core_l95) || _zz_when_Core_l94);
  assign _zz_when_Core_l148_6 = ((_zz_when_Core_l148_3 == 5'h0) ? 32'h0 : _zz_52_spinal_port1);
  assign _zz_when_Core_l148_7 = ((_zz_when_Core_l148_4 == 5'h0) ? 32'h0 : _zz_52_spinal_port2);
  assign when_Core_l108 = (_zz_when_Core_l108 && (! _zz_when_Core_l73_1));
  assign _zz_when_Core_l148_8 = (_zz_when_Core_l148_1 ? _zz_when_Core_l148 : _zz_when_Core_l148_7);
  always @(*) begin
    case(switch_Core_l118)
      4'b0000 : begin
        _zz_switch_Misc_l245_2 = (_zz_when_Core_l148_6 + _zz_when_Core_l148_8);
      end
      4'b0001 : begin
        _zz_switch_Misc_l245_2 = (_zz_when_Core_l148_6 - _zz_when_Core_l148_8);
      end
      4'b0010 : begin
        _zz_switch_Misc_l245_2 = (($signed(_zz__zz_switch_Misc_l245_2) < $signed(_zz__zz_switch_Misc_l245_2_1)) ? 32'h00000001 : 32'h0);
      end
      4'b0011 : begin
        _zz_switch_Misc_l245_2 = ((_zz_when_Core_l148_6 < _zz_when_Core_l148_8) ? 32'h00000001 : 32'h0);
      end
      4'b0100 : begin
        _zz_switch_Misc_l245_2 = (_zz_when_Core_l148_6 & _zz_when_Core_l148_8);
      end
      4'b0101 : begin
        _zz_switch_Misc_l245_2 = (~ (_zz_when_Core_l148_6 | _zz_when_Core_l148_8));
      end
      4'b0110 : begin
        _zz_switch_Misc_l245_2 = (_zz_when_Core_l148_6 | _zz_when_Core_l148_8);
      end
      4'b0111 : begin
        _zz_switch_Misc_l245_2 = (_zz_when_Core_l148_6 ^ _zz_when_Core_l148_8);
      end
      4'b1000 : begin
        _zz_switch_Misc_l245_2 = (_zz_when_Core_l148_6 <<< _zz__zz_switch_Misc_l245_2_2);
      end
      4'b1001 : begin
        _zz_switch_Misc_l245_2 = (_zz_when_Core_l148_6 >>> _zz_when_Core_l148_8[4 : 0]);
      end
      4'b1010 : begin
        _zz_switch_Misc_l245_2 = _zz__zz_switch_Misc_l245_2_4;
      end
      4'b1011 : begin
        _zz_switch_Misc_l245_2 = _zz_when_Core_l148_8;
      end
      default : begin
        _zz_switch_Misc_l245_2 = _zz_when_Core_l148_6;
      end
    endcase
  end

  assign when_Core_l148 = (_zz_when_Core_l148_1 && (((((_zz_when_Core_l148_2 == 2'b00) && (_zz_when_Core_l148_6 != _zz_when_Core_l148_8)) || ((_zz_when_Core_l148_2 == 2'b01) && (_zz_when_Core_l148_6 == _zz_when_Core_l148_8))) || ((_zz_when_Core_l148_2 == 2'b10) && ($signed(_zz_when_Core_l148_9) < $signed(_zz_when_Core_l148_10)))) || ((_zz_when_Core_l148_2 == 2'b11) && (_zz_when_Core_l148_6 < _zz_when_Core_l148_8))));
  assign when_Core_l142 = (_zz_when_Core_l108 && (! when_Core_l147));
  assign _zz_when_Core_l147_2 = _zz_switch_Misc_l245_1[11 : 4];
  assign _zz_when_Core_l147_3 = _zz_switch_Misc_l245_1[31 : 12];
  assign _zz_74 = _zz_switch_Misc_l245_1[3 : 2];
  assign _zz_when_Core_l147_4 = {_zz_when_Core_l147_2,1'b0};
  assign _zz_when_Core_l147_5 = {_zz_when_Core_l147_2,1'b0};
  assign _zz_when_Core_l147_6 = (_zz_71_spinal_port0[0] && (_zz_72_spinal_port0 == _zz_when_Core_l147_3));
  assign _zz_when_Core_l147_7 = {_zz_when_Core_l147_2,1'b1};
  assign _zz_when_Core_l147_8 = {_zz_when_Core_l147_2,1'b1};
  assign _zz_when_Core_l147_9 = (_zz_when_Core_l147_6 || (_zz_71_spinal_port1[0] && (_zz_72_spinal_port1 == _zz_when_Core_l147_3)));
  assign _zz_79 = {{(_zz_when_Core_l147_6 ? 1'b0 : 1'b1),_zz_when_Core_l147_2},_zz_74};
  assign _zz_80 = _zz_73_spinal_port0;
  assign when_Core_l147 = (_zz_when_Core_l147_1 && (! _zz_when_Core_l147_9));
  assign switch_Misc_l245_1 = _zz_switch_Misc_l245_1[1 : 0];
  always @(*) begin
    case(switch_Misc_l245_1)
      2'b00 : begin
        _zz_82 = _zz_80[7 : 0];
      end
      2'b01 : begin
        _zz_82 = _zz_80[15 : 8];
      end
      2'b10 : begin
        _zz_82 = _zz_80[23 : 16];
      end
      default : begin
        _zz_82 = _zz_80[31 : 24];
      end
    endcase
  end

  assign _zz_83 = (_zz_switch_Misc_l245_1[1] ? _zz_80[31 : 16] : _zz_80[15 : 0]);
  always @(*) begin
    case(switch_Misc_l245)
      2'b10 : begin
        _zz_84 = _zz_80;
      end
      2'b01 : begin
        _zz_84 = (_zz_59 ? _zz__zz_84 : _zz__zz_84_2);
      end
      2'b00 : begin
        _zz_84 = (_zz_59 ? _zz__zz_84_3 : _zz__zz_84_5);
      end
      default : begin
        _zz_84 = 32'h0;
      end
    endcase
  end

  assign when_Core_l185 = ((_zz_when_Core_l185_1 && (! when_Core_l147)) && _zz_when_Core_l147_9);
  assign _zz_85 = (_zz_when_Core_l147_6 ? 1'b0 : 1'b1);
  assign when_Core_l192 = (_zz_when_Core_l147_1 && (! _zz_when_Core_l147_9));
  assign _zz_89 = 1'b0;
  assign _zz_when_Core_l28 = (_zz_when_Core_l28_5 && _zz_when_Core_l28_6);
  assign _zz_when_Core_l28_1 = _zz_when_Core_l28_7;
  assign _zz_53 = _zz_60;
  assign _zz_11 = 4'b0000;
  assign _zz_19 = 1'b1;
  assign _zz_12 = _zz_when_Core_l69;
  assign _zz_13 = 8'h0;
  assign _zz_14 = 3'b010;
  assign _zz_15 = 2'b01;
  assign _zz_16 = 2'b00;
  assign _zz_17 = 4'b0000;
  assign _zz_18 = 3'b000;
  assign _zz_26 = 1'b1;
  assign _zz_27 = 4'b0000;
  assign _zz_35 = 1'b0;
  assign _zz_28 = 32'h0;
  assign _zz_29 = 8'h0;
  assign _zz_30 = 3'b010;
  assign _zz_31 = 2'b01;
  assign _zz_32 = 2'b00;
  assign _zz_33 = 4'b0000;
  assign _zz_34 = 3'b000;
  assign _zz_37 = 4'b0000;
  assign _zz_38 = 32'h0;
  assign _zz_39 = 4'b0000;
  assign _zz_40 = 1'b1;
  assign _zz_41 = 1'b0;
  assign _zz_46 = 1'b0;
  assign _zz_47 = _zz_55;
  assign _zz_48 = _zz_when_Core_l28;
  assign _zz_49 = _zz_when_Core_l28_1;
  assign _zz_50 = _zz_53;
  assign _zz_51 = _zz_when_Core_l95_1;
  always @(posedge clk) begin
    if(!resetn) begin
      _zz_when_Core_l69 <= 32'h1bfffffc;
      _zz_when_Core_l95 <= 32'h0;
      _zz_when_Core_l73 <= 1'b0;
      _zz_when_Core_l108 <= 1'b0;
      when_Core_l180 <= 1'b0;
      _zz_when_Core_l28_6 <= 1'b0;
      when_Core_l52 <= 1'b0;
      _zz_when_Core_l73_1 <= 1'b0;
      when_Core_l51 <= 1'b0;
    end else begin
      _zz_when_Core_l69 <= _zz_when_Core_l69_1;
      if(when_Core_l69) begin
        _zz_when_Core_l95 <= _zz_63_spinal_port0;
        _zz_when_Core_l73 <= 1'b1;
      end else begin
        _zz_when_Core_l73 <= 1'b0;
      end
      if(when_Core_l73) begin
        _zz_when_Core_l108 <= 1'b1;
      end else begin
        if(when_Core_l51) begin
          _zz_when_Core_l108 <= 1'b0;
        end
      end
      if(when_Core_l142) begin
        when_Core_l180 <= 1'b1;
      end
      if(when_Core_l148) begin
        when_Core_l51 <= 1'b1;
        _zz_when_Core_l108 <= 1'b0;
      end
      when_Core_l52 <= when_Core_l147;
      _zz_when_Core_l73_1 <= when_Core_l147;
      if(when_Core_l180) begin
        _zz_when_Core_l28_6 <= 1'b1;
      end
    end
  end

  always @(posedge clk) begin
    if(when_Core_l73) begin
      _zz_55 <= _zz_when_Core_l69;
      _zz_when_Core_l95_1 <= _zz_when_Core_l95;
    end
    if(when_Core_l108) begin
      _zz_when_Core_l28_2 <= _zz_when_Core_l95_1[4 : 0];
      _zz_when_Core_l148 <= _zz_when_Core_l148_5;
      switch_Core_l118 <= _zz_switch_Core_l118;
      _zz_when_Core_l147 <= _zz_when_Core_l92_1;
      _zz_when_Core_l185 <= _zz_when_Core_l92_2;
      _zz_switch_Misc_l245 <= (_zz_when_Core_l92_3 ? _zz_when_Core_l95_3[1 : 0] : 2'b10);
      _zz_56 <= (! _zz_when_Core_l95_3[2]);
      _zz_when_Core_l28_3 <= ((((((_zz_when_Core_l100 || _zz_when_Core_l92) || _zz_when_Core_l92_1) || _zz_when_Core_l94_1) || when_Core_l95) || _zz_when_Core_l93) || _zz_when_Core_l93_1);
      _zz_when_Core_l148_1 <= _zz_when_Core_l94;
      _zz_when_Core_l148_2 <= (_zz_when_Core_l94 ? _zz_when_Core_l95_3[1 : 0] : 2'b00);
    end
    if(when_Core_l142) begin
      _zz_57 <= _zz_switch_Misc_l245_2;
      _zz_switch_Misc_l245_1 <= _zz_switch_Misc_l245_2;
      _zz_58 <= _zz_when_Core_l148_7;
      _zz_when_Core_l147_1 <= _zz_when_Core_l147;
      _zz_when_Core_l185_1 <= _zz_when_Core_l185;
      switch_Misc_l245 <= _zz_switch_Misc_l245;
      _zz_59 <= _zz_56;
      _zz_when_Core_l28_4 <= _zz_when_Core_l28_3;
    end
    if(when_Core_l180) begin
      _zz_60 <= (_zz_when_Core_l147_1 ? _zz_84 : _zz_57);
      _zz_when_Core_l28_5 <= _zz_when_Core_l28_4;
      _zz_when_Core_l28_7 <= _zz_when_Core_l28_2;
    end
  end


endmodule
