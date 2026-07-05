// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : addr_trans_tmp
// Git hash  : 44b96c9d95df20c771a4c037f38a50b58c18805d

`timescale 1ns/1ps

module addr_trans (
  input  wire [31:0]   _zz_when_AddrTrans_l11,
  input  wire          _zz_1,
  output reg  [31:0]   _zz_2,
  output wire          _zz_3,
  output wire [5:0]    _zz_4,
  output reg           _zz_5,
  output reg  [1:0]    _zz_6
);

  wire       [27:0]   _zz__zz_2;
  wire       [27:0]   _zz__zz_2_1;
  wire                when_AddrTrans_l11;
  wire                when_AddrTrans_l14;

  assign _zz__zz_2 = _zz_when_AddrTrans_l11[27 : 0];
  assign _zz__zz_2_1 = _zz_when_AddrTrans_l11[27 : 0];
  always @(*) begin
    _zz_2 = _zz_when_AddrTrans_l11;
    if(when_AddrTrans_l11) begin
      _zz_2 = {4'd0, _zz__zz_2};
    end else begin
      if(when_AddrTrans_l14) begin
        _zz_2 = {4'd0, _zz__zz_2_1};
      end
    end
  end

  always @(*) begin
    _zz_6 = 2'b01;
    if(when_AddrTrans_l11) begin
      _zz_6 = 2'b00;
    end else begin
      if(when_AddrTrans_l14) begin
        _zz_6 = 2'b01;
      end
    end
  end

  always @(*) begin
    _zz_5 = 1'b0;
    if(when_AddrTrans_l11) begin
      _zz_5 = 1'b1;
    end else begin
      if(when_AddrTrans_l14) begin
        _zz_5 = 1'b0;
      end
    end
  end

  assign _zz_3 = 1'b0;
  assign _zz_4 = 6'h0;
  assign when_AddrTrans_l11 = (_zz_when_AddrTrans_l11[31 : 28] == 4'b1000);
  assign when_AddrTrans_l14 = (_zz_when_AddrTrans_l11[31 : 28] == 4'b1010);

endmodule
