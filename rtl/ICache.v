// Generator : SpinalHDL v1.10.2    git head : 279867b771fb50fc0aec21d8a20d8fdad0f87e3f
// Component : ICache
// Git hash  : 2a036cbe6f1375c725b52f589992d464a607d0cd

`timescale 1ns/1ps

module ICache (
  input  wire          _zz_when_Cache_l49,
  input  wire          _zz_5,
  input  wire [31:0]   _zz_when_Cache_l55,
  input  wire [31:0]   _zz_6,
  input  wire [3:0]    _zz_7,
  output reg           _zz_8,
  output wire [31:0]   _zz_9,
  output reg           _zz_10,
  input  wire          _zz_when_Cache_l53,
  input  wire [1:0]    _zz_when_Cache_l46,
  input  wire [31:0]   _zz_11,
  output reg           _zz_12,
  output wire          _zz_13,
  output wire [31:0]   _zz_14,
  input  wire          when_Cache_l60,
  input  wire [31:0]   _zz_15,
  input  wire          when_Cache_l62,
  output wire          _zz_16,
  input  wire          clk,
  input  wire          reset
);

  wire       [0:0]    _zz_18_spinal_port0;
  wire       [0:0]    _zz_18_spinal_port1;
  wire       [19:0]   _zz_19_spinal_port0;
  wire       [19:0]   _zz_19_spinal_port1;
  wire       [31:0]   _zz_20_spinal_port0;
  wire       [4:0]    _zz__zz_30;
  wire       [8:0]    _zz__zz_18_port;
  wire       [0:0]    _zz__zz_18_port_1;
  wire       [8:0]    _zz__zz_18_port_2;
  wire       [0:0]    _zz__zz_18_port_3;
  wire       [8:0]    _zz__zz_18_port_4;
  wire       [0:0]    _zz__zz_18_port_5;
  wire       [8:0]    _zz__zz_19_port;
  wire       [19:0]   _zz__zz_19_port_1;
  reg                 _zz_1;
  reg                 _zz_2;
  reg                 _zz_3;
  reg                 _zz_4;
  wire       [7:0]    _zz_when_Cache_l55_1;
  wire       [19:0]   _zz_when_Cache_l55_2;
  wire       [7:0]    _zz_17;
  reg        [31:0]   _zz_21;
  reg                 when_Cache_l53;
  reg        [1:0]    _zz_when_Cache_l46_1;
  reg        [2:0]    switch_Cache_l48;
  reg        [31:0]   _zz_22;
  reg        [0:0]    _zz_23;
  reg        [1:0]    _zz_24;
  reg        [7:0]    _zz_25;
  wire       [8:0]    _zz_when_Cache_l55_3;
  wire       [8:0]    _zz_when_Cache_l55_4;
  wire       [8:0]    _zz_when_Cache_l55_5;
  wire       [8:0]    _zz_when_Cache_l55_6;
  wire                when_Cache_l55;
  wire       [10:0]   _zz_30;
  wire                when_Cache_l46;
  wire                when_Cache_l49;
  (* ram_style = "distributed" *) reg [0:0] _zz_18 [0:511];
  (* ram_style = "distributed" *) reg [19:0] _zz_19 [0:511];
  reg [31:0] _zz_20 [0:2047];

  assign _zz__zz_30 = {{_zz_23,_zz_24},_zz_21[3 : 2]};
  assign _zz__zz_18_port = {_zz_17,1'b0};
  assign _zz__zz_18_port_1 = 1'b0;
  assign _zz__zz_18_port_2 = {_zz_17,1'b1};
  assign _zz__zz_18_port_3 = 1'b0;
  assign _zz__zz_18_port_4 = {_zz_25,_zz_23};
  assign _zz__zz_18_port_5 = 1'b1;
  assign _zz__zz_19_port = {_zz_25,_zz_23};
  assign _zz__zz_19_port_1 = _zz_21[31 : 12];
  assign _zz_18_spinal_port0 = _zz_18[_zz_when_Cache_l55_3];
  assign _zz_18_spinal_port1 = _zz_18[_zz_when_Cache_l55_5];
  always @(posedge clk) begin
    if(_zz_4) begin
      _zz_18[_zz__zz_18_port] <= _zz__zz_18_port_1;
    end
  end

  always @(posedge clk) begin
    if(_zz_3) begin
      _zz_18[_zz__zz_18_port_2] <= _zz__zz_18_port_3;
    end
  end

  always @(posedge clk) begin
    if(_zz_2) begin
      _zz_18[_zz__zz_18_port_4] <= _zz__zz_18_port_5;
    end
  end

  assign _zz_19_spinal_port0 = _zz_19[_zz_when_Cache_l55_4];
  assign _zz_19_spinal_port1 = _zz_19[_zz_when_Cache_l55_6];
  always @(posedge clk) begin
    if(_zz_1) begin
      _zz_19[_zz__zz_19_port] <= _zz__zz_19_port_1;
    end
  end

  assign _zz_20_spinal_port0 = _zz_20[_zz_30];
  always @(*) begin
    _zz_1 = 1'b0;
    case(switch_Cache_l48)
      3'b011 : begin
        if(when_Cache_l60) begin
          if(when_Cache_l62) begin
            _zz_1 = 1'b1;
          end
        end
      end
      default : begin
      end
    endcase
  end

  always @(*) begin
    _zz_2 = 1'b0;
    case(switch_Cache_l48)
      3'b011 : begin
        if(when_Cache_l60) begin
          if(when_Cache_l62) begin
            _zz_2 = 1'b1;
          end
        end
      end
      default : begin
      end
    endcase
  end

  always @(*) begin
    _zz_3 = 1'b0;
    if(when_Cache_l46) begin
      _zz_3 = 1'b1;
    end
  end

  always @(*) begin
    _zz_4 = 1'b0;
    if(when_Cache_l46) begin
      _zz_4 = 1'b1;
    end
  end

  assign _zz_when_Cache_l55_1 = _zz_when_Cache_l55[11 : 4];
  assign _zz_when_Cache_l55_2 = _zz_when_Cache_l55[31 : 12];
  assign _zz_17 = _zz_11[11 : 4];
  assign _zz_when_Cache_l55_3 = {_zz_when_Cache_l55_1,1'b0};
  assign _zz_when_Cache_l55_4 = {_zz_when_Cache_l55_1,1'b0};
  assign _zz_when_Cache_l55_5 = {_zz_when_Cache_l55_1,1'b1};
  assign _zz_when_Cache_l55_6 = {_zz_when_Cache_l55_1,1'b1};
  assign when_Cache_l55 = ((((_zz_18_spinal_port0[0] && (_zz_19_spinal_port0 == _zz_when_Cache_l55_2)) || (_zz_18_spinal_port1[0] && (_zz_19_spinal_port1 == _zz_when_Cache_l55_2))) && (! when_Cache_l53)) || when_Cache_l53);
  always @(*) begin
    _zz_10 = 1'b0;
    case(switch_Cache_l48)
      3'b001 : begin
        if(!when_Cache_l53) begin
          if(!when_Cache_l55) begin
            _zz_10 = 1'b1;
          end
        end
      end
      default : begin
      end
    endcase
  end

  always @(*) begin
    _zz_8 = 1'b0;
    case(switch_Cache_l48)
      3'b001 : begin
        if(when_Cache_l53) begin
          _zz_8 = 1'b1;
        end else begin
          if(when_Cache_l55) begin
            _zz_8 = 1'b1;
          end
        end
      end
      3'b011 : begin
        if(when_Cache_l60) begin
          if(when_Cache_l62) begin
            _zz_8 = 1'b1;
          end
        end
      end
      default : begin
      end
    endcase
  end

  assign _zz_13 = 1'b0;
  assign _zz_14 = _zz_22;
  assign _zz_16 = 1'b1;
  always @(*) begin
    _zz_12 = 1'b0;
    case(switch_Cache_l48)
      3'b001 : begin
        if(when_Cache_l53) begin
          _zz_12 = 1'b1;
        end
      end
      default : begin
      end
    endcase
  end

  assign _zz_30 = {6'd0, _zz__zz_30};
  assign _zz_9 = _zz_20_spinal_port0;
  assign when_Cache_l46 = (when_Cache_l53 && (when_Cache_l53 && (_zz_when_Cache_l46_1 == 2'b00)));
  assign when_Cache_l49 = (_zz_when_Cache_l49 || _zz_when_Cache_l53);
  always @(posedge clk or posedge reset) begin
    if(reset) begin
      switch_Cache_l48 <= 3'b000;
    end else begin
      case(switch_Cache_l48)
        3'b000 : begin
          if(when_Cache_l49) begin
            switch_Cache_l48 <= 3'b001;
          end
        end
        3'b001 : begin
          if(when_Cache_l53) begin
            switch_Cache_l48 <= 3'b000;
          end else begin
            if(when_Cache_l55) begin
              switch_Cache_l48 <= 3'b000;
            end else begin
              switch_Cache_l48 <= 3'b011;
            end
          end
        end
        3'b011 : begin
          if(when_Cache_l60) begin
            if(when_Cache_l62) begin
              switch_Cache_l48 <= 3'b000;
            end
          end
        end
        default : begin
        end
      endcase
    end
  end

  always @(posedge clk) begin
    case(switch_Cache_l48)
      3'b000 : begin
        if(when_Cache_l49) begin
          _zz_21 <= (_zz_when_Cache_l53 ? _zz_11 : _zz_when_Cache_l55);
          when_Cache_l53 <= _zz_when_Cache_l53;
          _zz_when_Cache_l46_1 <= _zz_when_Cache_l46;
        end
      end
      3'b001 : begin
        if(when_Cache_l53) begin
          when_Cache_l53 <= 1'b0;
        end else begin
          if(!when_Cache_l55) begin
            _zz_22 <= _zz_21;
            _zz_23 <= (_zz_23 + 1'b1);
            _zz_24 <= 2'b00;
            _zz_25 <= _zz_when_Cache_l55_1;
          end
        end
      end
      3'b011 : begin
        if(when_Cache_l60) begin
          _zz_24 <= (_zz_24 + 2'b01);
        end
      end
      default : begin
      end
    endcase
  end


endmodule
