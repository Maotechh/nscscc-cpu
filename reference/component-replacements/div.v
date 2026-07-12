// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : div



module div (
  input  wire          div_clk,
  input  wire          reset,
  input  wire          div,
  input  wire          div_signed,
  input  wire [31:0]   x,
  input  wire [31:0]   y,
  output wire [31:0]   s,
  output wire [31:0]   r,
  output wire          complete
);

  wire       [32:0]   _zz_logic_trialDifference;
  reg        [31:0]   logic_quotient;
  reg        [31:0]   logic_partialRemainder;
  reg        [31:0]   logic_capturedRemainder;
  reg        [7:0]    logic_count;
  reg                 logic_signedBuffer;
  reg                 logic_xNegativeBuffer;
  reg                 logic_yNegativeBuffer;
  wire                logic_complete;
  wire                logic_cleanup;
  wire                logic_useBufferedSigns;
  wire                logic_effectiveSigned;
  wire                logic_effectiveXNegative;
  wire                logic_effectiveYNegative;
  reg        [31:0]   logic_xMagnitude;
  reg        [31:0]   logic_yMagnitude;
  wire                when_OpenLa500Div_l59;
  wire                when_OpenLa500Div_l62;
  wire       [32:0]   logic_unsignedX;
  wire                logic_dividendBit;
  wire       [32:0]   logic_shiftedRemainder;
  wire       [32:0]   logic_trialDifference;
  wire                logic_trialNegative;
  wire                when_OpenLa500Div_l78;
  wire                when_OpenLa500Div_l81;
  reg        [31:0]   logic_signedQuotient;
  reg        [31:0]   logic_signedRemainder;
  wire                when_OpenLa500Div_l98;
  wire                when_OpenLa500Div_l101;

  assign _zz_logic_trialDifference = {1'd0, logic_yMagnitude};
  assign logic_complete = (logic_count == 8'hff);
  assign logic_cleanup = (logic_count == 8'hf0);
  assign logic_useBufferedSigns = (logic_complete || logic_cleanup);
  assign logic_effectiveSigned = (logic_useBufferedSigns ? logic_signedBuffer : div_signed);
  assign logic_effectiveXNegative = (logic_useBufferedSigns ? logic_xNegativeBuffer : x[31]);
  assign logic_effectiveYNegative = (logic_useBufferedSigns ? logic_yNegativeBuffer : y[31]);
  always @(*) begin
    logic_xMagnitude = x;
    if(when_OpenLa500Div_l59) begin
      logic_xMagnitude = (32'h0 - x);
    end
  end

  always @(*) begin
    logic_yMagnitude = y;
    if(when_OpenLa500Div_l62) begin
      logic_yMagnitude = (32'h0 - y);
    end
  end

  assign when_OpenLa500Div_l59 = (logic_effectiveSigned && x[31]);
  assign when_OpenLa500Div_l62 = (logic_effectiveSigned && y[31]);
  assign logic_unsignedX = {1'b0,logic_xMagnitude};
  assign logic_dividendBit = logic_unsignedX[logic_count[5 : 0]];
  assign logic_shiftedRemainder = {logic_partialRemainder,logic_dividendBit};
  assign logic_trialDifference = (logic_shiftedRemainder - _zz_logic_trialDifference);
  assign logic_trialNegative = logic_trialDifference[32];
  assign when_OpenLa500Div_l78 = ((! div) || logic_cleanup);
  assign when_OpenLa500Div_l81 = (! logic_count[7]);
  always @(*) begin
    logic_signedQuotient = logic_quotient;
    if(when_OpenLa500Div_l98) begin
      logic_signedQuotient = (32'h0 - logic_quotient);
    end
  end

  always @(*) begin
    logic_signedRemainder = logic_capturedRemainder;
    if(when_OpenLa500Div_l101) begin
      logic_signedRemainder = (32'h0 - logic_capturedRemainder);
    end
  end

  assign when_OpenLa500Div_l98 = (logic_effectiveSigned && (logic_effectiveXNegative != logic_effectiveYNegative));
  assign when_OpenLa500Div_l101 = (logic_effectiveSigned && logic_effectiveXNegative);
  assign s = logic_signedQuotient;
  assign r = logic_signedRemainder;
  assign complete = logic_complete;
  always @(posedge div_clk) begin
    if(reset) begin
      logic_quotient <= 32'h0;
      logic_partialRemainder <= 32'h0;
      logic_capturedRemainder <= 32'h0;
      logic_count <= 8'h20;
      logic_signedBuffer <= 1'b0;
      logic_xNegativeBuffer <= 1'b0;
      logic_yNegativeBuffer <= 1'b0;
    end else begin
      if(div) begin
        logic_signedBuffer <= div_signed;
        logic_xNegativeBuffer <= x[31];
        logic_yNegativeBuffer <= y[31];
      end
      if(when_OpenLa500Div_l78) begin
        logic_count <= 8'h20;
        logic_partialRemainder <= 32'h0;
      end else begin
        if(when_OpenLa500Div_l81) begin
          logic_quotient <= {logic_quotient[30 : 0],(! logic_trialNegative)};
          logic_partialRemainder <= (logic_trialNegative ? logic_shiftedRemainder[31 : 0] : logic_trialDifference[31 : 0]);
          logic_count <= (logic_count - 8'h01);
        end else begin
          logic_capturedRemainder <= logic_partialRemainder;
          logic_count <= 8'hf0;
        end
      end
    end
  end


endmodule
