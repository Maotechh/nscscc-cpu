// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : mul_tmp
// Git hash  : 44b96c9d95df20c771a4c037f38a50b58c18805d

`timescale 1ns/1ps

module mul (
  input  wire [1:0]    switch_Misc_l245,
  input  wire          _zz_1,
  input  wire [31:0]   _zz_when_Multiplier_l25,
  input  wire [31:0]   _zz_when_Multiplier_l25_1,
  input  wire          _zz_when_Multiplier_l14,
  output wire [31:0]   _zz_2,
  output wire          _zz_3,
  input  wire          clk,
  input  wire          reset
);

  wire       [31:0]   _zz__zz_when_Multiplier_l25_2;
  wire       [31:0]   _zz__zz_when_Multiplier_l25_2_1;
  wire       [32:0]   _zz__zz_when_Multiplier_l25_2_2;
  wire       [32:0]   _zz__zz_when_Multiplier_l25_2_3;
  wire       [31:0]   _zz__zz_when_Multiplier_l25_2_4;
  wire       [32:0]   _zz__zz_when_Multiplier_l25_2_5;
  reg        [5:0]    _zz_when_Multiplier_l24;
  reg                 when_Multiplier_l22;
  reg        [64:0]   _zz_when_Multiplier_l25_2;
  reg                 _zz_when_Multiplier_l33;
  reg                 _zz_when_Multiplier_l33_1;
  wire                _zz_when_Multiplier_l25_3;
  wire                when_Multiplier_l14;
  wire                when_Multiplier_l24;
  wire                when_Multiplier_l25;
  wire                when_Multiplier_l31;
  wire                when_Multiplier_l33;
  reg        [31:0]   _zz_4;

  assign _zz__zz_when_Multiplier_l25_2 = ((_zz_when_Multiplier_l25_3 && _zz_when_Multiplier_l25[31]) ? _zz__zz_when_Multiplier_l25_2_1 : _zz_when_Multiplier_l25);
  assign _zz__zz_when_Multiplier_l25_2_1 = (32'h0 - _zz_when_Multiplier_l25);
  assign _zz__zz_when_Multiplier_l25_2_2 = (_zz__zz_when_Multiplier_l25_2_3 + _zz__zz_when_Multiplier_l25_2_5);
  assign _zz__zz_when_Multiplier_l25_2_4 = _zz_when_Multiplier_l25_2[64 : 33];
  assign _zz__zz_when_Multiplier_l25_2_3 = {1'd0, _zz__zz_when_Multiplier_l25_2_4};
  assign _zz__zz_when_Multiplier_l25_2_5 = {1'd0, _zz_when_Multiplier_l25_1};
  assign _zz_when_Multiplier_l25_3 = ((switch_Misc_l245 == 2'b00) || (switch_Misc_l245 == 2'b01));
  assign when_Multiplier_l14 = (_zz_when_Multiplier_l14 && (! when_Multiplier_l22));
  assign when_Multiplier_l24 = (_zz_when_Multiplier_l24 < 6'h20);
  assign when_Multiplier_l25 = _zz_when_Multiplier_l25_2[0];
  assign when_Multiplier_l31 = (_zz_when_Multiplier_l24 == 6'h20);
  assign when_Multiplier_l33 = (_zz_when_Multiplier_l33 ^ _zz_when_Multiplier_l33_1);
  always @(*) begin
    case(switch_Misc_l245)
      2'b00 : begin
        _zz_4 = _zz_when_Multiplier_l25_2[31 : 0];
      end
      default : begin
        _zz_4 = _zz_when_Multiplier_l25_2[63 : 32];
      end
    endcase
  end

  assign _zz_2 = _zz_4;
  assign _zz_3 = (! when_Multiplier_l22);
  always @(posedge clk or posedge reset) begin
    if(reset) begin
      _zz_when_Multiplier_l24 <= 6'h0;
      when_Multiplier_l22 <= 1'b0;
    end else begin
      if(when_Multiplier_l14) begin
        when_Multiplier_l22 <= 1'b1;
        _zz_when_Multiplier_l24 <= 6'h0;
      end
      if(when_Multiplier_l22) begin
        _zz_when_Multiplier_l24 <= (_zz_when_Multiplier_l24 + 6'h01);
        if(when_Multiplier_l31) begin
          when_Multiplier_l22 <= 1'b0;
        end
      end
    end
  end

  always @(posedge clk) begin
    if(when_Multiplier_l14) begin
      _zz_when_Multiplier_l33 <= (_zz_when_Multiplier_l25_3 && _zz_when_Multiplier_l25[31]);
      _zz_when_Multiplier_l33_1 <= (_zz_when_Multiplier_l25_3 && _zz_when_Multiplier_l25_1[31]);
      _zz_when_Multiplier_l25_2 <= {33'd0, _zz__zz_when_Multiplier_l25_2};
      _zz_when_Multiplier_l25_2[0] <= 1'b0;
    end
    if(when_Multiplier_l22) begin
      if(when_Multiplier_l24) begin
        if(when_Multiplier_l25) begin
          _zz_when_Multiplier_l25_2 <= {_zz__zz_when_Multiplier_l25_2_2,_zz_when_Multiplier_l25_2[32 : 1]};
        end else begin
          _zz_when_Multiplier_l25_2 <= (_zz_when_Multiplier_l25_2 >>> 1);
        end
      end
      if(when_Multiplier_l31) begin
        if(when_Multiplier_l33) begin
          _zz_when_Multiplier_l25_2[63 : 31] <= (33'h0 - _zz_when_Multiplier_l25_2[63 : 31]);
        end
      end
    end
  end


endmodule
