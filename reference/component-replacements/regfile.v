`timescale 1ns/1ps
module regfile(
    input         clk,
    input  [ 4:0] raddr1,
    output [31:0] rdata1,
    input  [ 4:0] raddr2,
    output [31:0] rdata2,
    input         we,
    input  [ 4:0] waddr,
    input  [31:0] wdata
    `ifdef DIFFTEST_EN
    ,
    output [31:0] rf_o [31:0]
    `endif
);


  reg        [31:0]   tmp_rdata1;
  reg        [31:0]   tmp_rdata2;
  reg        [31:0]   storage_registers_0;
  reg        [31:0]   storage_registers_1;
  reg        [31:0]   storage_registers_2;
  reg        [31:0]   storage_registers_3;
  reg        [31:0]   storage_registers_4;
  reg        [31:0]   storage_registers_5;
  reg        [31:0]   storage_registers_6;
  reg        [31:0]   storage_registers_7;
  reg        [31:0]   storage_registers_8;
  reg        [31:0]   storage_registers_9;
  reg        [31:0]   storage_registers_10;
  reg        [31:0]   storage_registers_11;
  reg        [31:0]   storage_registers_12;
  reg        [31:0]   storage_registers_13;
  reg        [31:0]   storage_registers_14;
  reg        [31:0]   storage_registers_15;
  reg        [31:0]   storage_registers_16;
  reg        [31:0]   storage_registers_17;
  reg        [31:0]   storage_registers_18;
  reg        [31:0]   storage_registers_19;
  reg        [31:0]   storage_registers_20;
  reg        [31:0]   storage_registers_21;
  reg        [31:0]   storage_registers_22;
  reg        [31:0]   storage_registers_23;
  reg        [31:0]   storage_registers_24;
  reg        [31:0]   storage_registers_25;
  reg        [31:0]   storage_registers_26;
  reg        [31:0]   storage_registers_27;
  reg        [31:0]   storage_registers_28;
  reg        [31:0]   storage_registers_29;
  reg        [31:0]   storage_registers_30;
  reg        [31:0]   storage_registers_31;
  wire       [31:0]   tmp_1;

  always @(*) begin
    case(raddr1)
      5'b00000 : tmp_rdata1 = storage_registers_0;
      5'b00001 : tmp_rdata1 = storage_registers_1;
      5'b00010 : tmp_rdata1 = storage_registers_2;
      5'b00011 : tmp_rdata1 = storage_registers_3;
      5'b00100 : tmp_rdata1 = storage_registers_4;
      5'b00101 : tmp_rdata1 = storage_registers_5;
      5'b00110 : tmp_rdata1 = storage_registers_6;
      5'b00111 : tmp_rdata1 = storage_registers_7;
      5'b01000 : tmp_rdata1 = storage_registers_8;
      5'b01001 : tmp_rdata1 = storage_registers_9;
      5'b01010 : tmp_rdata1 = storage_registers_10;
      5'b01011 : tmp_rdata1 = storage_registers_11;
      5'b01100 : tmp_rdata1 = storage_registers_12;
      5'b01101 : tmp_rdata1 = storage_registers_13;
      5'b01110 : tmp_rdata1 = storage_registers_14;
      5'b01111 : tmp_rdata1 = storage_registers_15;
      5'b10000 : tmp_rdata1 = storage_registers_16;
      5'b10001 : tmp_rdata1 = storage_registers_17;
      5'b10010 : tmp_rdata1 = storage_registers_18;
      5'b10011 : tmp_rdata1 = storage_registers_19;
      5'b10100 : tmp_rdata1 = storage_registers_20;
      5'b10101 : tmp_rdata1 = storage_registers_21;
      5'b10110 : tmp_rdata1 = storage_registers_22;
      5'b10111 : tmp_rdata1 = storage_registers_23;
      5'b11000 : tmp_rdata1 = storage_registers_24;
      5'b11001 : tmp_rdata1 = storage_registers_25;
      5'b11010 : tmp_rdata1 = storage_registers_26;
      5'b11011 : tmp_rdata1 = storage_registers_27;
      5'b11100 : tmp_rdata1 = storage_registers_28;
      5'b11101 : tmp_rdata1 = storage_registers_29;
      5'b11110 : tmp_rdata1 = storage_registers_30;
      default : tmp_rdata1 = storage_registers_31;
    endcase
  end

  always @(*) begin
    case(raddr2)
      5'b00000 : tmp_rdata2 = storage_registers_0;
      5'b00001 : tmp_rdata2 = storage_registers_1;
      5'b00010 : tmp_rdata2 = storage_registers_2;
      5'b00011 : tmp_rdata2 = storage_registers_3;
      5'b00100 : tmp_rdata2 = storage_registers_4;
      5'b00101 : tmp_rdata2 = storage_registers_5;
      5'b00110 : tmp_rdata2 = storage_registers_6;
      5'b00111 : tmp_rdata2 = storage_registers_7;
      5'b01000 : tmp_rdata2 = storage_registers_8;
      5'b01001 : tmp_rdata2 = storage_registers_9;
      5'b01010 : tmp_rdata2 = storage_registers_10;
      5'b01011 : tmp_rdata2 = storage_registers_11;
      5'b01100 : tmp_rdata2 = storage_registers_12;
      5'b01101 : tmp_rdata2 = storage_registers_13;
      5'b01110 : tmp_rdata2 = storage_registers_14;
      5'b01111 : tmp_rdata2 = storage_registers_15;
      5'b10000 : tmp_rdata2 = storage_registers_16;
      5'b10001 : tmp_rdata2 = storage_registers_17;
      5'b10010 : tmp_rdata2 = storage_registers_18;
      5'b10011 : tmp_rdata2 = storage_registers_19;
      5'b10100 : tmp_rdata2 = storage_registers_20;
      5'b10101 : tmp_rdata2 = storage_registers_21;
      5'b10110 : tmp_rdata2 = storage_registers_22;
      5'b10111 : tmp_rdata2 = storage_registers_23;
      5'b11000 : tmp_rdata2 = storage_registers_24;
      5'b11001 : tmp_rdata2 = storage_registers_25;
      5'b11010 : tmp_rdata2 = storage_registers_26;
      5'b11011 : tmp_rdata2 = storage_registers_27;
      5'b11100 : tmp_rdata2 = storage_registers_28;
      5'b11101 : tmp_rdata2 = storage_registers_29;
      5'b11110 : tmp_rdata2 = storage_registers_30;
      default : tmp_rdata2 = storage_registers_31;
    endcase
  end

  assign tmp_1 = ({31'd0,1'b1} <<< waddr);
  assign rdata1 = ((raddr1 == 5'h0) ? 32'h0 : ((we && (raddr1 == waddr)) ? wdata : tmp_rdata1));
  assign rdata2 = ((raddr2 == 5'h0) ? 32'h0 : ((we && (raddr2 == waddr)) ? wdata : tmp_rdata2));
`ifdef DIFFTEST_EN
  assign rf_o[0] = storage_registers_0;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[1] = storage_registers_1;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[2] = storage_registers_2;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[3] = storage_registers_3;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[4] = storage_registers_4;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[5] = storage_registers_5;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[6] = storage_registers_6;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[7] = storage_registers_7;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[8] = storage_registers_8;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[9] = storage_registers_9;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[10] = storage_registers_10;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[11] = storage_registers_11;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[12] = storage_registers_12;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[13] = storage_registers_13;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[14] = storage_registers_14;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[15] = storage_registers_15;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[16] = storage_registers_16;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[17] = storage_registers_17;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[18] = storage_registers_18;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[19] = storage_registers_19;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[20] = storage_registers_20;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[21] = storage_registers_21;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[22] = storage_registers_22;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[23] = storage_registers_23;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[24] = storage_registers_24;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[25] = storage_registers_25;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[26] = storage_registers_26;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[27] = storage_registers_27;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[28] = storage_registers_28;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[29] = storage_registers_29;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[30] = storage_registers_30;
`endif
`ifdef DIFFTEST_EN
  assign rf_o[31] = storage_registers_31;
`endif
  always @(posedge clk) begin
    if(we) begin
      if(tmp_1[0]) begin
        storage_registers_0 <= wdata;
      end
      if(tmp_1[1]) begin
        storage_registers_1 <= wdata;
      end
      if(tmp_1[2]) begin
        storage_registers_2 <= wdata;
      end
      if(tmp_1[3]) begin
        storage_registers_3 <= wdata;
      end
      if(tmp_1[4]) begin
        storage_registers_4 <= wdata;
      end
      if(tmp_1[5]) begin
        storage_registers_5 <= wdata;
      end
      if(tmp_1[6]) begin
        storage_registers_6 <= wdata;
      end
      if(tmp_1[7]) begin
        storage_registers_7 <= wdata;
      end
      if(tmp_1[8]) begin
        storage_registers_8 <= wdata;
      end
      if(tmp_1[9]) begin
        storage_registers_9 <= wdata;
      end
      if(tmp_1[10]) begin
        storage_registers_10 <= wdata;
      end
      if(tmp_1[11]) begin
        storage_registers_11 <= wdata;
      end
      if(tmp_1[12]) begin
        storage_registers_12 <= wdata;
      end
      if(tmp_1[13]) begin
        storage_registers_13 <= wdata;
      end
      if(tmp_1[14]) begin
        storage_registers_14 <= wdata;
      end
      if(tmp_1[15]) begin
        storage_registers_15 <= wdata;
      end
      if(tmp_1[16]) begin
        storage_registers_16 <= wdata;
      end
      if(tmp_1[17]) begin
        storage_registers_17 <= wdata;
      end
      if(tmp_1[18]) begin
        storage_registers_18 <= wdata;
      end
      if(tmp_1[19]) begin
        storage_registers_19 <= wdata;
      end
      if(tmp_1[20]) begin
        storage_registers_20 <= wdata;
      end
      if(tmp_1[21]) begin
        storage_registers_21 <= wdata;
      end
      if(tmp_1[22]) begin
        storage_registers_22 <= wdata;
      end
      if(tmp_1[23]) begin
        storage_registers_23 <= wdata;
      end
      if(tmp_1[24]) begin
        storage_registers_24 <= wdata;
      end
      if(tmp_1[25]) begin
        storage_registers_25 <= wdata;
      end
      if(tmp_1[26]) begin
        storage_registers_26 <= wdata;
      end
      if(tmp_1[27]) begin
        storage_registers_27 <= wdata;
      end
      if(tmp_1[28]) begin
        storage_registers_28 <= wdata;
      end
      if(tmp_1[29]) begin
        storage_registers_29 <= wdata;
      end
      if(tmp_1[30]) begin
        storage_registers_30 <= wdata;
      end
      if(tmp_1[31]) begin
        storage_registers_31 <= wdata;
      end
    end
  end



endmodule
