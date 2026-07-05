// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : alu_tmp
// Git hash  : 44b96c9d95df20c771a4c037f38a50b58c18805d

`timescale 1ns/1ps

module alu (
  input  wire [3:0]    _zz_when_ALU_l49,
  input  wire [31:0]   _zz_1,
  input  wire [31:0]   _zz_2,
  output reg  [31:0]   _zz_3,
  output reg           _zz_4,
  output wire          _zz_5
);

  wire       [31:0]   _zz__zz_3;
  wire       [31:0]   _zz__zz_3_1;
  wire       [31:0]   _zz__zz_3_2;
  wire       [31:0]   _zz__zz_3_3;
  wire       [31:0]   _zz__zz_5;
  wire       [31:0]   _zz__zz_5_1;
  wire       [4:0]    _zz_6;
  wire                when_ALU_l49;
  wire                when_ALU_l50;
  wire                when_ALU_l51;
  wire                when_ALU_l52;
  wire                when_ALU_l53;
  wire                when_ALU_l54;
  wire                when_ALU_l55;
  wire                when_ALU_l56;
  wire                when_ALU_l57;
  wire                when_ALU_l58;
  wire                when_ALU_l59;
  wire                when_ALU_l60;
  wire                when_ALU_l64;
  wire                when_ALU_l66;

  assign _zz__zz_3 = _zz_1;
  assign _zz__zz_3_1 = _zz_2;
  assign _zz__zz_3_2 = ($signed(_zz__zz_3_3) >>> _zz_6);
  assign _zz__zz_3_3 = _zz_1;
  assign _zz__zz_5 = _zz_1;
  assign _zz__zz_5_1 = _zz_2;
  assign _zz_6 = _zz_2[4 : 0];
  always @(*) begin
    _zz_3 = _zz_1;
    if(when_ALU_l49) begin
      _zz_3 = (_zz_1 + _zz_2);
    end else begin
      if(when_ALU_l50) begin
        _zz_3 = (_zz_1 - _zz_2);
      end else begin
        if(when_ALU_l51) begin
          _zz_3 = (($signed(_zz__zz_3) < $signed(_zz__zz_3_1)) ? 32'h00000001 : 32'h0);
        end else begin
          if(when_ALU_l52) begin
            _zz_3 = ((_zz_1 < _zz_2) ? 32'h00000001 : 32'h0);
          end else begin
            if(when_ALU_l53) begin
              _zz_3 = (_zz_1 & _zz_2);
            end else begin
              if(when_ALU_l54) begin
                _zz_3 = (~ (_zz_1 | _zz_2));
              end else begin
                if(when_ALU_l55) begin
                  _zz_3 = (_zz_1 | _zz_2);
                end else begin
                  if(when_ALU_l56) begin
                    _zz_3 = (_zz_1 ^ _zz_2);
                  end else begin
                    if(when_ALU_l57) begin
                      _zz_3 = (_zz_1 <<< _zz_6);
                    end else begin
                      if(when_ALU_l58) begin
                        _zz_3 = (_zz_1 >>> _zz_6);
                      end else begin
                        if(when_ALU_l59) begin
                          _zz_3 = _zz__zz_3_2;
                        end else begin
                          if(when_ALU_l60) begin
                            _zz_3 = _zz_2;
                          end
                        end
                      end
                    end
                  end
                end
              end
            end
          end
        end
      end
    end
  end

  assign when_ALU_l49 = (_zz_when_ALU_l49 == 4'b0000);
  assign when_ALU_l50 = (_zz_when_ALU_l49 == 4'b0001);
  assign when_ALU_l51 = (_zz_when_ALU_l49 == 4'b0010);
  assign when_ALU_l52 = (_zz_when_ALU_l49 == 4'b0011);
  assign when_ALU_l53 = (_zz_when_ALU_l49 == 4'b0100);
  assign when_ALU_l54 = (_zz_when_ALU_l49 == 4'b0101);
  assign when_ALU_l55 = (_zz_when_ALU_l49 == 4'b0110);
  assign when_ALU_l56 = (_zz_when_ALU_l49 == 4'b0111);
  assign when_ALU_l57 = (_zz_when_ALU_l49 == 4'b1000);
  assign when_ALU_l58 = (_zz_when_ALU_l49 == 4'b1001);
  assign when_ALU_l59 = (_zz_when_ALU_l49 == 4'b1010);
  assign when_ALU_l60 = (_zz_when_ALU_l49 == 4'b1011);
  always @(*) begin
    _zz_4 = 1'b0;
    if(when_ALU_l64) begin
      _zz_4 = ((_zz_1[31] == _zz_2[31]) && (_zz_3[31] != _zz_1[31]));
    end else begin
      if(when_ALU_l66) begin
        _zz_4 = ((_zz_1[31] != _zz_2[31]) && (_zz_3[31] != _zz_1[31]));
      end
    end
  end

  assign when_ALU_l64 = (_zz_when_ALU_l49 == 4'b0000);
  assign when_ALU_l66 = (_zz_when_ALU_l49 == 4'b0001);
  assign _zz_5 = ($signed(_zz__zz_5) < $signed(_zz__zz_5_1));

endmodule
