// Generator : SpinalHDL v1.10.2    git head : 279867b771fb50fc0aec21d8a20d8fdad0f87e3f
// Component : Divider
// Git hash  : 2a036cbe6f1375c725b52f589992d464a607d0cd

`timescale 1ns/1ps

module Divider (
  input  wire [0:0]    switch_Misc_l241,
  input  wire          _zz_when_Divider_l33,
  input  wire [31:0]   _zz_when_Divider_l33_1,
  input  wire [31:0]   _zz_when_Divider_l33_2,
  input  wire          _zz_when_Divider_l15,
  output wire [31:0]   _zz_1,
  output wire          _zz_2,
  output wire          _zz_3,
  input  wire          clk,
  input  wire          reset
);

  wire       [31:0]   _zz__zz_when_Divider_l30_1;
  wire       [31:0]   _zz__zz_when_Divider_l30_2;
  wire       [31:0]   _zz__zz_when_Divider_l30_3;
  wire       [31:0]   _zz__zz_when_Divider_l30_3_1;
  wire       [31:0]   _zz__zz_when_Divider_l30;
  wire       [31:0]   _zz__zz_when_Divider_l30_4;
  wire       [31:0]   _zz__zz_when_Divider_l30_1_1;
  wire       [31:0]   _zz__zz_when_Divider_l30_1_2;
  reg        [5:0]    _zz_when_Divider_l31;
  reg                 when_Divider_l25;
  reg        [31:0]   _zz_when_Divider_l30;
  reg        [31:0]   _zz_when_Divider_l30_1;
  reg        [31:0]   _zz_when_Divider_l30_2;
  reg                 when_Divider_l33;
  reg                 when_Divider_l34;
  wire                when_Divider_l15;
  wire                when_Divider_l21;
  wire       [31:0]   _zz_when_Divider_l30_3;
  wire                when_Divider_l30;
  wire                when_Divider_l31;
  reg        [31:0]   _zz_4;

  assign _zz__zz_when_Divider_l30_1 = (32'h0 - _zz_when_Divider_l33_1);
  assign _zz__zz_when_Divider_l30_2 = (32'h0 - _zz_when_Divider_l33_2);
  assign _zz__zz_when_Divider_l30_3 = _zz_when_Divider_l30_1;
  assign _zz__zz_when_Divider_l30_3_1 = _zz_when_Divider_l30_2;
  assign _zz__zz_when_Divider_l30 = ($signed(32'h0) - $signed(_zz__zz_when_Divider_l30_4));
  assign _zz__zz_when_Divider_l30_4 = _zz_when_Divider_l30;
  assign _zz__zz_when_Divider_l30_1_1 = ($signed(32'h0) - $signed(_zz__zz_when_Divider_l30_1_2));
  assign _zz__zz_when_Divider_l30_1_2 = _zz_when_Divider_l30_1;
  assign when_Divider_l15 = (_zz_when_Divider_l15 && (! when_Divider_l25));
  assign when_Divider_l21 = (_zz_when_Divider_l33_2 == 32'h0);
  assign _zz_when_Divider_l30_3 = ($signed(_zz__zz_when_Divider_l30_3) - $signed(_zz__zz_when_Divider_l30_3_1));
  assign when_Divider_l30 = (! _zz_when_Divider_l30_3[31]);
  assign when_Divider_l31 = (_zz_when_Divider_l31 == 6'h1f);
  always @(*) begin
    case(switch_Misc_l241)
      1'b0 : begin
        _zz_4 = _zz_when_Divider_l30;
      end
      default : begin
        _zz_4 = _zz_when_Divider_l30_1;
      end
    endcase
  end

  assign _zz_1 = _zz_4;
  assign _zz_2 = (! when_Divider_l25);
  assign _zz_3 = (_zz_when_Divider_l33_2 == 32'h0);
  always @(posedge clk or posedge reset) begin
    if(reset) begin
      _zz_when_Divider_l31 <= 6'h0;
      when_Divider_l25 <= 1'b0;
    end else begin
      if(when_Divider_l15) begin
        when_Divider_l25 <= 1'b1;
        _zz_when_Divider_l31 <= 6'h0;
        if(when_Divider_l21) begin
          when_Divider_l25 <= 1'b0;
        end
      end
      if(when_Divider_l25) begin
        _zz_when_Divider_l31 <= (_zz_when_Divider_l31 + 6'h01);
        if(when_Divider_l31) begin
          when_Divider_l25 <= 1'b0;
        end
      end
    end
  end

  always @(posedge clk) begin
    if(when_Divider_l15) begin
      when_Divider_l33 <= (_zz_when_Divider_l33 && (_zz_when_Divider_l33_1[31] ^ _zz_when_Divider_l33_2[31]));
      when_Divider_l34 <= (_zz_when_Divider_l33 && _zz_when_Divider_l33_1[31]);
      if(when_Divider_l21) begin
        _zz_when_Divider_l30 <= 32'h0;
        _zz_when_Divider_l30_1 <= _zz_when_Divider_l33_1;
      end else begin
        _zz_when_Divider_l30 <= 32'h0;
        _zz_when_Divider_l30_1 <= ((_zz_when_Divider_l33 && _zz_when_Divider_l33_1[31]) ? _zz__zz_when_Divider_l30_1 : _zz_when_Divider_l33_1);
        _zz_when_Divider_l30_2 <= ((_zz_when_Divider_l33 && _zz_when_Divider_l33_2[31]) ? _zz__zz_when_Divider_l30_2 : _zz_when_Divider_l33_2);
      end
    end
    if(when_Divider_l25) begin
      _zz_when_Divider_l30_1 <= {_zz_when_Divider_l30_1[30 : 0],_zz_when_Divider_l30[31]};
      _zz_when_Divider_l30[0] <= (! _zz_when_Divider_l30_3[31]);
      if(when_Divider_l30) begin
        _zz_when_Divider_l30_1 <= _zz_when_Divider_l30_3;
      end
      if(when_Divider_l31) begin
        if(when_Divider_l33) begin
          _zz_when_Divider_l30 <= _zz__zz_when_Divider_l30;
        end
        if(when_Divider_l34) begin
          _zz_when_Divider_l30_1 <= _zz__zz_when_Divider_l30_1_1;
        end
      end
    end
  end


endmodule
