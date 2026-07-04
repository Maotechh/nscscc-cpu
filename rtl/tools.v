module decoder_2_4(
    input  [ 1:0] in,
    output [ 3:0] out
);

genvar i;
generate for (i=0; i<4; i=i+1) begin : gen_for_dec_2_4
    assign out[i] = (in == i);
end endgenerate

endmodule


module encoder_4_2(
    input  [3:0] in,
    output [1:0] out
);

assign out = {2{in[0]}} & 2'd0 |
	     {2{in[1]}} & 2'd1 |
	     {2{in[2]}} & 2'd2 |
	     {2{in[3]}} & 2'd3 ;

endmodule

module decoder_4_16(
    input  [ 3:0] in,
    output [15:0] out
);

genvar i;
generate for (i=0; i<16; i=i+1) begin : gen_for_dec_4_16
    assign out[i] = (in == i);
end endgenerate

endmodule

module encoder_16_4(
    input  [15:0] in,
    output [ 3:0] out
);

wire [1:0] out_0, out_1, out_2, out_3;

encoder_4_2 one (.in(in[ 3: 0]), .out(out_0));
encoder_4_2 two (.in(in[ 7: 4]), .out(out_1));
encoder_4_2 thr (.in(in[11: 8]), .out(out_2));
encoder_4_2 fou (.in(in[15:12]), .out(out_3));

assign out = {4{|in[ 3: 0]}} & {2'd0, out_0} |
	     {4{|in[ 7: 4]}} & {2'd1, out_1} |		
	     {4{|in[11: 8]}} & {2'd2, out_2} |		
	     {4{|in[15:12]}} & {2'd3, out_3} ;		

endmodule

module decoder_5_32(
    input  [ 4:0] in,
    output [31:0] out
);

genvar i;
generate for (i=0; i<32; i=i+1) begin : gen_for_dec_5_32
    assign out[i] = (in == i);
end endgenerate

endmodule

module encoder_32_5(
    input  [31:0] in,
    output [ 4:0] out
);

wire [3:0] out_0, out_1;

encoder_16_4 one (.in(in[15: 0]), .out(out_0));
encoder_16_4 two (.in(in[31:16]), .out(out_1));

assign out = {5{|in[15: 0]}} & {1'd0, out_0} |
	     {5{|in[31:16]}} & {1'd1, out_1} ;

endmodule


module decoder_6_64(
    input  [ 5:0] in,
    output [63:0] out
);

genvar i;
generate 
	for (i=0; i<64; i=i+1) 
	begin : gen_for_dec_6_64  //bug7
    	assign out[i] = (in == i);
	end
endgenerate

endmodule

module one_valid_n #(
	parameter n = 16
)(
	input  [n-1:0] in,
	output [n-1:0] out,
	output         nozero
);

wire [n-1:0] one_in;

assign one_in[0] = in[0];

genvar i;
generate 
	for (i=1; i<n; i=i+1)
	begin: sel_one
		assign one_in[i] = in[i] && ~|in[i-1:0];
	end
endgenerate

assign out = one_in;
assign nozero = |out;

endmodule


module one_valid_16 (
    input  [15:0] in,
    output [ 3:0] out_en
);

wire [15:0] one_in;

assign one_in[0] = in[0];

genvar i;
generate 
	for (i=1; i<16; i=i+1)
	begin: sel_one
		assign one_in[i] = in[i] && ~|in[i-1:0];
	end
endgenerate

encoder_16_4 coder (.in(one_in), .out(out_en));

endmodule

module one_valid_32 (
    input  [31:0] in,
    output [ 4:0] out_en
);

wire [31:0] one_in;

assign one_in[0] = in[0];

genvar i;
generate 
	for (i=1; i<32; i=i+1)
	begin: sel_one
		assign one_in[i] = in[i] && ~|in[i-1:0];
	end
endgenerate

encoder_32_5 coder (.in(one_in), .out(out_en));

endmodule


module encoder_64_6 (
    input  [63:0] in,
    output [ 5:0] out
);
    assign out = in[ 0] ? 6'd0  : in[ 1] ? 6'd1  :
                 in[ 2] ? 6'd2  : in[ 3] ? 6'd3  :
                 in[ 4] ? 6'd4  : in[ 5] ? 6'd5  :
                 in[ 6] ? 6'd6  : in[ 7] ? 6'd7  :
                 in[ 8] ? 6'd8  : in[ 9] ? 6'd9  :
                 in[10] ? 6'd10 : in[11] ? 6'd11 :
                 in[12] ? 6'd12 : in[13] ? 6'd13 :
                 in[14] ? 6'd14 : in[15] ? 6'd15 :
                 in[16] ? 6'd16 : in[17] ? 6'd17 :
                 in[18] ? 6'd18 : in[19] ? 6'd19 :
                 in[20] ? 6'd20 : in[21] ? 6'd21 :
                 in[22] ? 6'd22 : in[23] ? 6'd23 :
                 in[24] ? 6'd24 : in[25] ? 6'd25 :
                 in[26] ? 6'd26 : in[27] ? 6'd27 :
                 in[28] ? 6'd28 : in[29] ? 6'd29 :
                 in[30] ? 6'd30 : in[31] ? 6'd31 :
                 in[32] ? 6'd32 : in[33] ? 6'd33 :
                 in[34] ? 6'd34 : in[35] ? 6'd35 :
                 in[36] ? 6'd36 : in[37] ? 6'd37 :
                 in[38] ? 6'd38 : in[39] ? 6'd39 :
                 in[40] ? 6'd40 : in[41] ? 6'd41 :
                 in[42] ? 6'd42 : in[43] ? 6'd43 :
                 in[44] ? 6'd44 : in[45] ? 6'd45 :
                 in[46] ? 6'd46 : in[47] ? 6'd47 :
                 in[48] ? 6'd48 : in[49] ? 6'd49 :
                 in[50] ? 6'd50 : in[51] ? 6'd51 :
                 in[52] ? 6'd52 : in[53] ? 6'd53 :
                 in[54] ? 6'd54 : in[55] ? 6'd55 :
                 in[56] ? 6'd56 : in[57] ? 6'd57 :
                 in[58] ? 6'd58 : in[59] ? 6'd59 :
                 in[60] ? 6'd60 : in[61] ? 6'd61 :
                 in[62] ? 6'd62 : in[63] ? 6'd63 : 6'd0;
endmodule

module one_valid_64 (
    input  [63:0] in,
    output [ 5:0] out_en
);
    wire [63:0] one_in;
    assign one_in[0] = in[0];
    genvar i;
    generate 
        for (i=1; i<64; i=i+1) begin: sel_one
            assign one_in[i] = in[i] && ~|in[i-1:0];
        end
    endgenerate
    encoder_64_6 coder (.in(one_in), .out(out_en));
endmodule
