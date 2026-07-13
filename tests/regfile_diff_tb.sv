`timescale 1ns/1ps
module regfile_diff_tb;
  logic        clk;
  logic [4:0]  raddr1;
  logic [4:0]  raddr2;
  logic        we;
  logic [4:0]  waddr;
  logic [31:0] wdata;
  wire [31:0]  golden_rdata1;
  wire [31:0]  golden_rdata2;
  wire [31:0]  candidate_rdata1;
  wire [31:0]  candidate_rdata2;
  wire [31:0]  golden_rf [31:0];
  wire [31:0]  candidate_rf [31:0];

  regfile_golden golden(
    .clk(clk), .raddr1(raddr1), .rdata1(golden_rdata1),
    .raddr2(raddr2), .rdata2(golden_rdata2),
    .we(we), .waddr(waddr), .wdata(wdata), .rf_o(golden_rf)
  );

  regfile candidate(
    .clk(clk), .raddr1(raddr1), .rdata1(candidate_rdata1),
    .raddr2(raddr2), .rdata2(candidate_rdata2),
    .we(we), .waddr(waddr), .wdata(wdata), .rf_o(candidate_rf)
  );

  task automatic compare_reads(input integer vector_index);
    begin
      if (golden_rdata1 !== candidate_rdata1)
        $fatal(1, "rdata1 mismatch vector=%0d golden=%08x candidate=%08x", vector_index, golden_rdata1, candidate_rdata1);
      if (golden_rdata2 !== candidate_rdata2)
        $fatal(1, "rdata2 mismatch vector=%0d golden=%08x candidate=%08x", vector_index, golden_rdata2, candidate_rdata2);
    end
  endtask

  task automatic compare_state(input integer vector_index);
    integer index;
    begin
      for (index = 0; index < 32; index = index + 1)
        if (golden_rf[index] !== candidate_rf[index])
          $fatal(1, "state mismatch vector=%0d index=%0d golden=%08x candidate=%08x", vector_index, index, golden_rf[index], candidate_rf[index]);
    end
  endtask

  integer index;
  integer vector_index;
  logic [63:0] random_state;
  initial begin
    clk = 0;
    raddr1 = 0;
    raddr2 = 0;
    we = 0;
    waddr = 0;
    wdata = 0;
    random_state = 64'h158aa8_2026_0713;

    for (index = 0; index < 32; index = index + 1) begin
      we = 1;
      waddr = index[4:0];
      wdata = 32'h8100_0000 + index;
      #4 clk = 1;
      #1 clk = 0;
      #5;
    end
    we = 0;
    compare_state(-1);

    for (vector_index = 0; vector_index < 4096; vector_index = vector_index + 1) begin
      random_state = {random_state[62:0], random_state[63] ^ random_state[62] ^ random_state[60] ^ random_state[59]};
      raddr1 = random_state[4:0];
      raddr2 = random_state[9:5];
      waddr = random_state[14:10];
      we = random_state[15];
      wdata = random_state[47:16] ^ {16'h0, vector_index[15:0]};
      #1;
      compare_reads(vector_index);
      #3 clk = 1;
      #1 clk = 0;
      #5;
      compare_state(vector_index);
    end

    $display("REGFILE_DIFF_PASS vectors=4096");
    $finish;
  end
endmodule
