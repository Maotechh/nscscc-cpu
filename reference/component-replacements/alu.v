// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : alu



module alu (
  input  wire [13:0]   alu_op,
  input  wire [31:0]   alu_src1,
  input  wire [31:0]   alu_src2,
  output wire [31:0]   alu_result
);

  wire       [32:0]   _zz_adder;
  wire       [32:0]   _zz_adder_1;
  wire       [31:0]   _zz_adder_2;
  wire       [32:0]   _zz_adder_3;
  wire       [31:0]   _zz_adder_4;
  wire       [32:0]   _zz_adder_5;
  wire       [0:0]    _zz_adder_6;
  wire       [0:0]    _zz_sltResult;
  wire       [0:0]    _zz_sltuResult;
  wire       [31:0]   _zz_sllResult;
  wire       [31:0]   _zz_logicalRightResult;
  wire       [31:0]   _zz_arithmeticRightResult;
  wire       [31:0]   _zz_arithmeticRightResult_1;
  wire                subtract;
  wire       [31:0]   adderB;
  wire       [32:0]   adder;
  wire       [31:0]   addSubResult;
  wire                signedLess;
  wire       [31:0]   sltResult;
  wire       [31:0]   sltuResult;
  wire       [31:0]   andResult;
  wire       [31:0]   andnResult;
  wire       [31:0]   orResult;
  wire       [31:0]   ornResult;
  wire       [31:0]   norResult;
  wire       [31:0]   xorResult;
  wire       [4:0]    shiftAmount;
  wire       [31:0]   sllResult;
  wire       [31:0]   logicalRightResult;
  wire       [31:0]   arithmeticRightResult;
  wire       [31:0]   shiftRightResult;
  wire                when_OpenLa500Alu_l71;
  reg        [31:0]   resultTerms_0;
  wire                when_OpenLa500Alu_l71_1;
  reg        [31:0]   resultTerms_1;
  wire                when_OpenLa500Alu_l71_2;
  reg        [31:0]   resultTerms_2;
  wire                when_OpenLa500Alu_l71_3;
  reg        [31:0]   resultTerms_3;
  wire                when_OpenLa500Alu_l71_4;
  reg        [31:0]   resultTerms_4;
  wire                when_OpenLa500Alu_l71_5;
  reg        [31:0]   resultTerms_5;
  wire                when_OpenLa500Alu_l71_6;
  reg        [31:0]   resultTerms_6;
  wire                when_OpenLa500Alu_l71_7;
  reg        [31:0]   resultTerms_7;
  wire                when_OpenLa500Alu_l71_8;
  reg        [31:0]   resultTerms_8;
  wire                when_OpenLa500Alu_l71_9;
  reg        [31:0]   resultTerms_9;
  wire                when_OpenLa500Alu_l71_10;
  reg        [31:0]   resultTerms_10;
  wire                when_OpenLa500Alu_l71_11;
  reg        [31:0]   resultTerms_11;

  assign _zz_adder = (_zz_adder_1 + _zz_adder_3);
  assign _zz_adder_2 = alu_src1;
  assign _zz_adder_1 = {1'd0, _zz_adder_2};
  assign _zz_adder_4 = adderB;
  assign _zz_adder_3 = {1'd0, _zz_adder_4};
  assign _zz_adder_6 = subtract;
  assign _zz_adder_5 = {32'd0, _zz_adder_6};
  assign _zz_sltResult = signedLess;
  assign _zz_sltuResult = (! adder[32]);
  assign _zz_sllResult = (alu_src1 <<< shiftAmount);
  assign _zz_logicalRightResult = (alu_src1 >>> shiftAmount);
  assign _zz_arithmeticRightResult = ($signed(_zz_arithmeticRightResult_1) >>> shiftAmount);
  assign _zz_arithmeticRightResult_1 = alu_src1;
  assign subtract = ((alu_op[1] || alu_op[2]) || alu_op[3]);
  assign adderB = (subtract ? (~ alu_src2) : alu_src2);
  assign adder = (_zz_adder + _zz_adder_5);
  assign addSubResult = adder[31 : 0];
  assign signedLess = ((alu_src1[31] && (! alu_src2[31])) || ((alu_src1[31] == alu_src2[31]) && addSubResult[31]));
  assign sltResult = {31'd0, _zz_sltResult};
  assign sltuResult = {31'd0, _zz_sltuResult};
  assign andResult = (alu_src1 & alu_src2);
  assign andnResult = (alu_src1 & (~ alu_src2));
  assign orResult = (alu_src1 | alu_src2);
  assign ornResult = (alu_src1 | (~ alu_src2));
  assign norResult = (~ orResult);
  assign xorResult = (alu_src1 ^ alu_src2);
  assign shiftAmount = alu_src2[4 : 0];
  assign sllResult = _zz_sllResult;
  assign logicalRightResult = _zz_logicalRightResult;
  assign arithmeticRightResult = _zz_arithmeticRightResult;
  assign shiftRightResult = (alu_op[10] ? arithmeticRightResult : logicalRightResult);
  assign when_OpenLa500Alu_l71 = (alu_op[0] || alu_op[1]);
  always @(*) begin
    resultTerms_0 = 32'h0;
    if(when_OpenLa500Alu_l71) begin
      resultTerms_0 = addSubResult;
    end
  end

  assign when_OpenLa500Alu_l71_1 = alu_op[2];
  always @(*) begin
    resultTerms_1 = 32'h0;
    if(when_OpenLa500Alu_l71_1) begin
      resultTerms_1 = sltResult;
    end
  end

  assign when_OpenLa500Alu_l71_2 = alu_op[3];
  always @(*) begin
    resultTerms_2 = 32'h0;
    if(when_OpenLa500Alu_l71_2) begin
      resultTerms_2 = sltuResult;
    end
  end

  assign when_OpenLa500Alu_l71_3 = alu_op[4];
  always @(*) begin
    resultTerms_3 = 32'h0;
    if(when_OpenLa500Alu_l71_3) begin
      resultTerms_3 = andResult;
    end
  end

  assign when_OpenLa500Alu_l71_4 = alu_op[12];
  always @(*) begin
    resultTerms_4 = 32'h0;
    if(when_OpenLa500Alu_l71_4) begin
      resultTerms_4 = andnResult;
    end
  end

  assign when_OpenLa500Alu_l71_5 = alu_op[5];
  always @(*) begin
    resultTerms_5 = 32'h0;
    if(when_OpenLa500Alu_l71_5) begin
      resultTerms_5 = norResult;
    end
  end

  assign when_OpenLa500Alu_l71_6 = alu_op[6];
  always @(*) begin
    resultTerms_6 = 32'h0;
    if(when_OpenLa500Alu_l71_6) begin
      resultTerms_6 = orResult;
    end
  end

  assign when_OpenLa500Alu_l71_7 = alu_op[13];
  always @(*) begin
    resultTerms_7 = 32'h0;
    if(when_OpenLa500Alu_l71_7) begin
      resultTerms_7 = ornResult;
    end
  end

  assign when_OpenLa500Alu_l71_8 = alu_op[7];
  always @(*) begin
    resultTerms_8 = 32'h0;
    if(when_OpenLa500Alu_l71_8) begin
      resultTerms_8 = xorResult;
    end
  end

  assign when_OpenLa500Alu_l71_9 = alu_op[11];
  always @(*) begin
    resultTerms_9 = 32'h0;
    if(when_OpenLa500Alu_l71_9) begin
      resultTerms_9 = alu_src2;
    end
  end

  assign when_OpenLa500Alu_l71_10 = alu_op[8];
  always @(*) begin
    resultTerms_10 = 32'h0;
    if(when_OpenLa500Alu_l71_10) begin
      resultTerms_10 = sllResult;
    end
  end

  assign when_OpenLa500Alu_l71_11 = (alu_op[9] || alu_op[10]);
  always @(*) begin
    resultTerms_11 = 32'h0;
    if(when_OpenLa500Alu_l71_11) begin
      resultTerms_11 = shiftRightResult;
    end
  end

  assign alu_result = (((((((((((resultTerms_0 | resultTerms_1) | resultTerms_2) | resultTerms_3) | resultTerms_4) | resultTerms_5) | resultTerms_6) | resultTerms_7) | resultTerms_8) | resultTerms_9) | resultTerms_10) | resultTerms_11);

endmodule
