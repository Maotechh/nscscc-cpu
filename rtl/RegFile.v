// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : regfile_tmp
// Git hash  : 44b96c9d95df20c771a4c037f38a50b58c18805d

`timescale 1ns/1ps

module regfile (
  input  wire          _zz_when_RegFile_l52,
  input  wire [4:0]    _zz_when_RegFile_l52_1,
  input  wire [31:0]   _zz_1,
  input  wire [4:0]    _zz_2,
  output wire [31:0]   _zz_3,
  input  wire [4:0]    _zz_4,
  output wire [31:0]   _zz_5,
  input  wire          clk,
  input  wire          reset
);

  reg        [31:0]   _zz__zz_3;
  reg        [31:0]   _zz__zz_5;
  reg        [31:0]   _zz_6;
  reg        [31:0]   _zz_7;
  reg        [31:0]   _zz_8;
  reg        [31:0]   _zz_9;
  reg        [31:0]   _zz_10;
  reg        [31:0]   _zz_11;
  reg        [31:0]   _zz_12;
  reg        [31:0]   _zz_13;
  reg        [31:0]   _zz_14;
  reg        [31:0]   _zz_15;
  reg        [31:0]   _zz_16;
  reg        [31:0]   _zz_17;
  reg        [31:0]   _zz_18;
  reg        [31:0]   _zz_19;
  reg        [31:0]   _zz_20;
  reg        [31:0]   _zz_21;
  reg        [31:0]   _zz_22;
  reg        [31:0]   _zz_23;
  reg        [31:0]   _zz_24;
  reg        [31:0]   _zz_25;
  reg        [31:0]   _zz_26;
  reg        [31:0]   _zz_27;
  reg        [31:0]   _zz_28;
  reg        [31:0]   _zz_29;
  reg        [31:0]   _zz_30;
  reg        [31:0]   _zz_31;
  reg        [31:0]   _zz_32;
  reg        [31:0]   _zz_33;
  reg        [31:0]   _zz_34;
  reg        [31:0]   _zz_35;
  reg        [31:0]   _zz_36;
  reg        [31:0]   _zz_37;
  wire                when_RegFile_l52;
  wire       [31:0]   _zz_38;
  wire                _zz_39;

  always @(*) begin
    case(_zz_2)
      5'b00000 : _zz__zz_3 = _zz_6;
      5'b00001 : _zz__zz_3 = _zz_7;
      5'b00010 : _zz__zz_3 = _zz_8;
      5'b00011 : _zz__zz_3 = _zz_9;
      5'b00100 : _zz__zz_3 = _zz_10;
      5'b00101 : _zz__zz_3 = _zz_11;
      5'b00110 : _zz__zz_3 = _zz_12;
      5'b00111 : _zz__zz_3 = _zz_13;
      5'b01000 : _zz__zz_3 = _zz_14;
      5'b01001 : _zz__zz_3 = _zz_15;
      5'b01010 : _zz__zz_3 = _zz_16;
      5'b01011 : _zz__zz_3 = _zz_17;
      5'b01100 : _zz__zz_3 = _zz_18;
      5'b01101 : _zz__zz_3 = _zz_19;
      5'b01110 : _zz__zz_3 = _zz_20;
      5'b01111 : _zz__zz_3 = _zz_21;
      5'b10000 : _zz__zz_3 = _zz_22;
      5'b10001 : _zz__zz_3 = _zz_23;
      5'b10010 : _zz__zz_3 = _zz_24;
      5'b10011 : _zz__zz_3 = _zz_25;
      5'b10100 : _zz__zz_3 = _zz_26;
      5'b10101 : _zz__zz_3 = _zz_27;
      5'b10110 : _zz__zz_3 = _zz_28;
      5'b10111 : _zz__zz_3 = _zz_29;
      5'b11000 : _zz__zz_3 = _zz_30;
      5'b11001 : _zz__zz_3 = _zz_31;
      5'b11010 : _zz__zz_3 = _zz_32;
      5'b11011 : _zz__zz_3 = _zz_33;
      5'b11100 : _zz__zz_3 = _zz_34;
      5'b11101 : _zz__zz_3 = _zz_35;
      5'b11110 : _zz__zz_3 = _zz_36;
      default : _zz__zz_3 = _zz_37;
    endcase
  end

  always @(*) begin
    case(_zz_4)
      5'b00000 : _zz__zz_5 = _zz_6;
      5'b00001 : _zz__zz_5 = _zz_7;
      5'b00010 : _zz__zz_5 = _zz_8;
      5'b00011 : _zz__zz_5 = _zz_9;
      5'b00100 : _zz__zz_5 = _zz_10;
      5'b00101 : _zz__zz_5 = _zz_11;
      5'b00110 : _zz__zz_5 = _zz_12;
      5'b00111 : _zz__zz_5 = _zz_13;
      5'b01000 : _zz__zz_5 = _zz_14;
      5'b01001 : _zz__zz_5 = _zz_15;
      5'b01010 : _zz__zz_5 = _zz_16;
      5'b01011 : _zz__zz_5 = _zz_17;
      5'b01100 : _zz__zz_5 = _zz_18;
      5'b01101 : _zz__zz_5 = _zz_19;
      5'b01110 : _zz__zz_5 = _zz_20;
      5'b01111 : _zz__zz_5 = _zz_21;
      5'b10000 : _zz__zz_5 = _zz_22;
      5'b10001 : _zz__zz_5 = _zz_23;
      5'b10010 : _zz__zz_5 = _zz_24;
      5'b10011 : _zz__zz_5 = _zz_25;
      5'b10100 : _zz__zz_5 = _zz_26;
      5'b10101 : _zz__zz_5 = _zz_27;
      5'b10110 : _zz__zz_5 = _zz_28;
      5'b10111 : _zz__zz_5 = _zz_29;
      5'b11000 : _zz__zz_5 = _zz_30;
      5'b11001 : _zz__zz_5 = _zz_31;
      5'b11010 : _zz__zz_5 = _zz_32;
      5'b11011 : _zz__zz_5 = _zz_33;
      5'b11100 : _zz__zz_5 = _zz_34;
      5'b11101 : _zz__zz_5 = _zz_35;
      5'b11110 : _zz__zz_5 = _zz_36;
      default : _zz__zz_5 = _zz_37;
    endcase
  end

  assign when_RegFile_l52 = (_zz_when_RegFile_l52 && (_zz_when_RegFile_l52_1 != 5'h0));
  assign _zz_38 = ({31'd0,1'b1} <<< _zz_when_RegFile_l52_1);
  assign _zz_39 = (_zz_when_RegFile_l52 && (_zz_when_RegFile_l52_1 != 5'h0));
  assign _zz_3 = ((_zz_39 && (_zz_2 == _zz_when_RegFile_l52_1)) ? _zz_1 : ((_zz_2 == 5'h0) ? 32'h0 : _zz__zz_3));
  assign _zz_5 = ((_zz_39 && (_zz_4 == _zz_when_RegFile_l52_1)) ? _zz_1 : ((_zz_4 == 5'h0) ? 32'h0 : _zz__zz_5));
  always @(posedge clk or posedge reset) begin
    if(reset) begin
      _zz_6 <= 32'h0;
      _zz_7 <= 32'h0;
      _zz_8 <= 32'h0;
      _zz_9 <= 32'h0;
      _zz_10 <= 32'h0;
      _zz_11 <= 32'h0;
      _zz_12 <= 32'h0;
      _zz_13 <= 32'h0;
      _zz_14 <= 32'h0;
      _zz_15 <= 32'h0;
      _zz_16 <= 32'h0;
      _zz_17 <= 32'h0;
      _zz_18 <= 32'h0;
      _zz_19 <= 32'h0;
      _zz_20 <= 32'h0;
      _zz_21 <= 32'h0;
      _zz_22 <= 32'h0;
      _zz_23 <= 32'h0;
      _zz_24 <= 32'h0;
      _zz_25 <= 32'h0;
      _zz_26 <= 32'h0;
      _zz_27 <= 32'h0;
      _zz_28 <= 32'h0;
      _zz_29 <= 32'h0;
      _zz_30 <= 32'h0;
      _zz_31 <= 32'h0;
      _zz_32 <= 32'h0;
      _zz_33 <= 32'h0;
      _zz_34 <= 32'h0;
      _zz_35 <= 32'h0;
      _zz_36 <= 32'h0;
      _zz_37 <= 32'h0;
    end else begin
      if(when_RegFile_l52) begin
        if(_zz_38[0]) begin
          _zz_6 <= _zz_1;
        end
        if(_zz_38[1]) begin
          _zz_7 <= _zz_1;
        end
        if(_zz_38[2]) begin
          _zz_8 <= _zz_1;
        end
        if(_zz_38[3]) begin
          _zz_9 <= _zz_1;
        end
        if(_zz_38[4]) begin
          _zz_10 <= _zz_1;
        end
        if(_zz_38[5]) begin
          _zz_11 <= _zz_1;
        end
        if(_zz_38[6]) begin
          _zz_12 <= _zz_1;
        end
        if(_zz_38[7]) begin
          _zz_13 <= _zz_1;
        end
        if(_zz_38[8]) begin
          _zz_14 <= _zz_1;
        end
        if(_zz_38[9]) begin
          _zz_15 <= _zz_1;
        end
        if(_zz_38[10]) begin
          _zz_16 <= _zz_1;
        end
        if(_zz_38[11]) begin
          _zz_17 <= _zz_1;
        end
        if(_zz_38[12]) begin
          _zz_18 <= _zz_1;
        end
        if(_zz_38[13]) begin
          _zz_19 <= _zz_1;
        end
        if(_zz_38[14]) begin
          _zz_20 <= _zz_1;
        end
        if(_zz_38[15]) begin
          _zz_21 <= _zz_1;
        end
        if(_zz_38[16]) begin
          _zz_22 <= _zz_1;
        end
        if(_zz_38[17]) begin
          _zz_23 <= _zz_1;
        end
        if(_zz_38[18]) begin
          _zz_24 <= _zz_1;
        end
        if(_zz_38[19]) begin
          _zz_25 <= _zz_1;
        end
        if(_zz_38[20]) begin
          _zz_26 <= _zz_1;
        end
        if(_zz_38[21]) begin
          _zz_27 <= _zz_1;
        end
        if(_zz_38[22]) begin
          _zz_28 <= _zz_1;
        end
        if(_zz_38[23]) begin
          _zz_29 <= _zz_1;
        end
        if(_zz_38[24]) begin
          _zz_30 <= _zz_1;
        end
        if(_zz_38[25]) begin
          _zz_31 <= _zz_1;
        end
        if(_zz_38[26]) begin
          _zz_32 <= _zz_1;
        end
        if(_zz_38[27]) begin
          _zz_33 <= _zz_1;
        end
        if(_zz_38[28]) begin
          _zz_34 <= _zz_1;
        end
        if(_zz_38[29]) begin
          _zz_35 <= _zz_1;
        end
        if(_zz_38[30]) begin
          _zz_36 <= _zz_1;
        end
        if(_zz_38[31]) begin
          _zz_37 <= _zz_1;
        end
      end
    end
  end


endmodule
