module perf_counter_lockstep;
  reg clk;
  reg reset;
  reg dcache_miss;
  reg icache_miss;
  reg commit_inst;
  reg br_inst;
  reg mem_inst;
  reg br_pre;
  reg br_pre_error;

  integer cycle_limit;
  integer cycle_count;
  integer reset_count;
  integer idle_count;
  integer concurrent_count;
  integer wrap_count;
  integer event_count [0:6];
  integer index;
  reg [31:0] seed_value;
  reg [31:0] lfsr;
  reg negative_control;

  golden_perf_counter golden (
      .clk(clk),
      .reset(reset),
      .dcache_miss(dcache_miss),
      .icache_miss(icache_miss),
      .commit_inst(commit_inst),
      .br_inst(br_inst),
      .mem_inst(mem_inst),
      .br_pre(br_pre),
      .br_pre_error(br_pre_error)
  );

  perf_counter candidate (
      .clk(clk),
      .reset(reset),
      .dcache_miss(dcache_miss),
      .icache_miss(icache_miss),
      .commit_inst(commit_inst),
      .br_inst(br_inst),
      .mem_inst(mem_inst),
      .br_pre(br_pre),
      .br_pre_error(br_pre_error)
  );

  function automatic [31:0] next_lfsr(input [31:0] value);
    next_lfsr = {value[30:0], value[31] ^ value[21] ^ value[1] ^ value[0]};
  endfunction

  task automatic compare_counters;
    reg [31:0] candidate_dcache;
    begin
      candidate_dcache = candidate.dcache_miss_counter ^ {31'b0, negative_control};
      if (golden.dcache_miss_counter !== candidate_dcache ||
          golden.icache_miss_counter !== candidate.icache_miss_counter ||
          golden.commit_inst_counter !== candidate.commit_inst_counter ||
          golden.br_inst_counter !== candidate.br_inst_counter ||
          golden.mem_inst_counter !== candidate.mem_inst_counter ||
          golden.br_pre_counter !== candidate.br_pre_counter ||
          golden.br_pre_error_counter !== candidate.br_pre_error_counter) begin
        $display("PERF_COUNTER_MISMATCH cycle=%0d negative_control=%0d", cycle_count, negative_control);
        $display("golden=%08x,%08x,%08x,%08x,%08x,%08x,%08x",
          golden.dcache_miss_counter, golden.icache_miss_counter,
          golden.commit_inst_counter, golden.br_inst_counter, golden.mem_inst_counter,
          golden.br_pre_counter, golden.br_pre_error_counter);
        $display("candidate=%08x,%08x,%08x,%08x,%08x,%08x,%08x",
          candidate_dcache, candidate.icache_miss_counter,
          candidate.commit_inst_counter, candidate.br_inst_counter, candidate.mem_inst_counter,
          candidate.br_pre_counter, candidate.br_pre_error_counter);
        $fatal(1);
      end
    end
  endtask

  task automatic step_and_compare;
    begin
      @(negedge clk);
      cycle_count = cycle_count + 1;
      compare_counters();
    end
  endtask

  task automatic drive_all(input value);
    begin
      dcache_miss = value;
      icache_miss = value;
      commit_inst = value;
      br_inst = value;
      mem_inst = value;
      br_pre = value;
      br_pre_error = value;
    end
  endtask

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    cycle_limit = 8192;
    seed_value = 32'h0158aa8e;
    if (!$value$plusargs("cycles=%d", cycle_limit)) cycle_limit = 8192;
    if (!$value$plusargs("seed=%h", seed_value)) seed_value = 32'h0158aa8e;
    negative_control = $test$plusargs("negative-control");
    cycle_count = 0;
    reset_count = 0;
    idle_count = 0;
    concurrent_count = 0;
    wrap_count = 0;
    for (index = 0; index < 7; index = index + 1) event_count[index] = 0;
    lfsr = seed_value;
    reset = 1'b1;
    drive_all(1'b1);

    step_and_compare();
    step_and_compare();
    reset_count = reset_count + 2;

    reset = 1'b0;
    drive_all(1'b0);
    dcache_miss = 1'b1;
    event_count[0] = event_count[0] + 1;
    step_and_compare();

    drive_all(1'b1);
    for (index = 0; index < 7; index = index + 1)
      event_count[index] = event_count[index] + 1;
    concurrent_count = concurrent_count + 1;
    step_and_compare();

    drive_all(1'b0);
    idle_count = idle_count + 1;
    step_and_compare();

    reset = 1'b1;
    drive_all(1'b1);
    reset_count = reset_count + 1;
    step_and_compare();

    reset = 1'b0;
    drive_all(1'b0);
    golden.dcache_miss_counter = 32'hffffffff;
    golden.icache_miss_counter = 32'hffffffff;
    golden.commit_inst_counter = 32'hffffffff;
    golden.br_inst_counter = 32'hffffffff;
    golden.mem_inst_counter = 32'hffffffff;
    golden.br_pre_counter = 32'hffffffff;
    golden.br_pre_error_counter = 32'hffffffff;
    candidate.dcache_miss_counter = 32'hffffffff;
    candidate.icache_miss_counter = 32'hffffffff;
    candidate.commit_inst_counter = 32'hffffffff;
    candidate.br_inst_counter = 32'hffffffff;
    candidate.mem_inst_counter = 32'hffffffff;
    candidate.br_pre_counter = 32'hffffffff;
    candidate.br_pre_error_counter = 32'hffffffff;
    drive_all(1'b1);
    for (index = 0; index < 7; index = index + 1)
      event_count[index] = event_count[index] + 1;
    concurrent_count = concurrent_count + 1;
    wrap_count = wrap_count + 1;
    step_and_compare();

    for (index = 0; index < cycle_limit; index = index + 1) begin
      lfsr = next_lfsr(lfsr);
      reset = (lfsr[9:0] == 10'h000);
      dcache_miss = lfsr[0];
      icache_miss = lfsr[2];
      commit_inst = lfsr[4];
      br_inst = lfsr[6];
      mem_inst = lfsr[8];
      br_pre = lfsr[10];
      br_pre_error = lfsr[12];
      if (reset) begin
        reset_count = reset_count + 1;
      end else begin
        if (!(dcache_miss || icache_miss || commit_inst || br_inst || mem_inst || br_pre || br_pre_error))
          idle_count = idle_count + 1;
        if ((dcache_miss && (icache_miss || commit_inst || br_inst || mem_inst || br_pre || br_pre_error)) ||
            (icache_miss && (commit_inst || br_inst || mem_inst || br_pre || br_pre_error)) ||
            (commit_inst && (br_inst || mem_inst || br_pre || br_pre_error)) ||
            (br_inst && (mem_inst || br_pre || br_pre_error)) ||
            (mem_inst && (br_pre || br_pre_error)) || (br_pre && br_pre_error))
          concurrent_count = concurrent_count + 1;
        event_count[0] = event_count[0] + (dcache_miss ? 1 : 0);
        event_count[1] = event_count[1] + (icache_miss ? 1 : 0);
        event_count[2] = event_count[2] + (commit_inst ? 1 : 0);
        event_count[3] = event_count[3] + (br_inst ? 1 : 0);
        event_count[4] = event_count[4] + (mem_inst ? 1 : 0);
        event_count[5] = event_count[5] + (br_pre ? 1 : 0);
        event_count[6] = event_count[6] + (br_pre_error ? 1 : 0);
      end
      step_and_compare();
    end

    for (index = 0; index < 7; index = index + 1)
      if (event_count[index] == 0) $fatal(1, "missing event coverage index=%0d", index);
    if (reset_count == 0 || idle_count == 0 || concurrent_count == 0 || wrap_count != 1)
      $fatal(1, "coverage incomplete reset=%0d idle=%0d concurrent=%0d wrap=%0d",
        reset_count, idle_count, concurrent_count, wrap_count);

    $display("PERF_COUNTER_DIFF_PASS cycles=%0d seed=0x%08x resets=%0d idle=%0d concurrent=%0d wrap=%0d events=%0d,%0d,%0d,%0d,%0d,%0d,%0d",
      cycle_limit, seed_value, reset_count, idle_count, concurrent_count, wrap_count,
      event_count[0], event_count[1], event_count[2], event_count[3],
      event_count[4], event_count[5], event_count[6]);
    $finish;
  end
endmodule
