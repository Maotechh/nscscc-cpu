// Generator : SpinalHDL v1.10.2    git head : 279867b771fb50fc0aec21d8a20d8fdad0f87e3f
// Component : AddrTrans
// Git hash  : 2a036cbe6f1375c725b52f589992d464a607d0cd

`timescale 1ns/1ps

module AddrTrans (
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
