module lacc_core_lockstep;
  reg clk = 1'b0;
  always #1 clk = ~clk;

  reg reset;
  reg lacc_flush;
  reg lacc_req_valid;
  reg [1:0] lacc_req_command;
  reg [6:0] lacc_req_imm;
  reg [31:0] lacc_req_rj;
  reg [31:0] lacc_req_rk;
  reg lacc_data_ready;
  reg lacc_drsp_valid;
  reg [31:0] lacc_drsp_rdata;

  wire g_lacc_rsp_valid;
  wire [31:0] g_lacc_rsp_rdat;
  wire g_lacc_data_valid;
  wire [31:0] g_lacc_data_addr;
  wire g_lacc_data_read;
  wire [31:0] g_lacc_data_wdata;
  wire [1:0] g_lacc_data_size;
  wire c_lacc_rsp_valid;
  wire [31:0] c_lacc_rsp_rdat;
  wire c_lacc_data_valid;
  wire [31:0] c_lacc_data_addr;
  wire c_lacc_data_read;
  wire [31:0] c_lacc_data_wdata;
  wire [1:0] c_lacc_data_size;

`define LACC_INPUTS \
    .clk(clk), .reset(reset), .lacc_flush(lacc_flush), \
    .lacc_req_valid(lacc_req_valid), .lacc_req_command(lacc_req_command), \
    .lacc_req_imm(lacc_req_imm), .lacc_req_rj(lacc_req_rj), \
    .lacc_req_rk(lacc_req_rk), .lacc_data_ready(lacc_data_ready), \
    .lacc_drsp_valid(lacc_drsp_valid), .lacc_drsp_rdata(lacc_drsp_rdata)

  golden_lacc_core golden (
    `LACC_INPUTS,
    .lacc_rsp_valid(g_lacc_rsp_valid), .lacc_rsp_rdat(g_lacc_rsp_rdat),
    .lacc_data_valid(g_lacc_data_valid), .lacc_data_addr(g_lacc_data_addr),
    .lacc_data_read(g_lacc_data_read), .lacc_data_wdata(g_lacc_data_wdata),
    .lacc_data_size(g_lacc_data_size)
  );

  lacc_core candidate (
    `LACC_INPUTS,
    .lacc_rsp_valid(c_lacc_rsp_valid), .lacc_rsp_rdat(c_lacc_rsp_rdat),
    .lacc_data_valid(c_lacc_data_valid), .lacc_data_addr(c_lacc_data_addr),
    .lacc_data_read(c_lacc_data_read), .lacc_data_wdata(c_lacc_data_wdata),
    .lacc_data_size(c_lacc_data_size)
  );

  integer cycle;
  integer cycle_limit;
  integer seed_value;
  integer queue_head;
  integer queue_tail;
  integer queue_count;
  reg [31:0] request_count;
  reg [31:0] response_count;
  reg [31:0] data_count;
  reg [31:0] read_count;
  reg [31:0] write_count;
  reg [31:0] stall_count;
  reg [31:0] drsp_count;
  reg [31:0] reset_count;
  reg [31:0] flush_count;
  reg [31:0] lfsr;
  reg [31:0] response_queue [0:255];
  reg negative_control;
  reg request_active;
  reg scheduled_read;
  reg scheduled_response;
  reg scheduled_arch_response;
  reg scheduled_cancel;
  reg [31:0] scheduled_read_data;
  reg previous_valid;
  reg previous_ready;
  reg previous_read;
  reg previous_cancel;
  reg [31:0] previous_g_addr;
  reg [31:0] previous_g_wdata;
  reg [1:0] previous_g_size;
  reg [31:0] previous_c_addr;
  reg [31:0] previous_c_wdata;
  reg [1:0] previous_c_size;

  wire observed_c_rsp_valid = c_lacc_rsp_valid ^ negative_control;

  function automatic [31:0] next_lfsr(input [31:0] value);
    begin
      next_lfsr = {value[30:0], value[31] ^ value[21] ^ value[1] ^ value[0]};
    end
  endfunction

  task automatic fail_mismatch(input [511:0] reason);
    begin
      $display("LACC_MISMATCH cycle=%0d reason=%0s negative_control=%0d", cycle,
               reason, negative_control);
      $display("rsp valid=%b/%b data=%h/%h", g_lacc_rsp_valid,
               observed_c_rsp_valid, g_lacc_rsp_rdat, c_lacc_rsp_rdat);
      $display("mem valid=%b/%b addr=%h/%h read=%b/%b wdata=%h/%h size=%h/%h ready=%b",
               g_lacc_data_valid, c_lacc_data_valid, g_lacc_data_addr,
               c_lacc_data_addr, g_lacc_data_read, c_lacc_data_read,
               g_lacc_data_wdata, c_lacc_data_wdata, g_lacc_data_size,
               c_lacc_data_size, lacc_data_ready);
      $fatal(1);
    end
  endtask

  task automatic compare_outputs;
    begin
      if (g_lacc_rsp_valid !== observed_c_rsp_valid)
        fail_mismatch("response_valid");
      if (g_lacc_rsp_valid && (g_lacc_rsp_rdat !== c_lacc_rsp_rdat))
        fail_mismatch("response_payload");
      if (g_lacc_data_valid !== c_lacc_data_valid)
        fail_mismatch("memory_valid");
      if (g_lacc_data_valid) begin
        if (g_lacc_data_addr !== c_lacc_data_addr)
          fail_mismatch("memory_address");
        if (g_lacc_data_read !== c_lacc_data_read)
          fail_mismatch("memory_direction");
        if (g_lacc_data_size !== c_lacc_data_size)
          fail_mismatch("memory_size");
        if (!g_lacc_data_read && (g_lacc_data_wdata !== c_lacc_data_wdata))
          fail_mismatch("memory_write_data");
      end
    end
  endtask

  task automatic check_stability;
    begin
      if (previous_valid && !previous_ready && !previous_cancel) begin
        if (!g_lacc_data_valid || !c_lacc_data_valid)
          fail_mismatch("backpressure_valid_stability");
        if ((g_lacc_data_addr !== previous_g_addr) ||
            (c_lacc_data_addr !== previous_c_addr) ||
            (g_lacc_data_read !== previous_read) ||
            (c_lacc_data_read !== previous_read) ||
            (g_lacc_data_size !== previous_g_size) ||
            (c_lacc_data_size !== previous_c_size))
          fail_mismatch("backpressure_payload_stability");
        if (!previous_read &&
            ((g_lacc_data_wdata !== previous_g_wdata) ||
             (c_lacc_data_wdata !== previous_c_wdata)))
          fail_mismatch("backpressure_write_data_stability");
      end
    end
  endtask

  task automatic process_scheduled_events;
    begin
      if (scheduled_cancel) begin
        queue_head = 0;
        queue_tail = 0;
        queue_count = 0;
        request_active = 1'b0;
      end else begin
        if (scheduled_response) begin
          if (queue_count <= 0)
            fail_mismatch("response_queue_underflow");
          queue_head = (queue_head + 1) & 255;
          queue_count = queue_count - 1;
        end
        if (scheduled_read) begin
          if (queue_count >= 255)
            fail_mismatch("response_queue_overflow");
          response_queue[queue_tail] = scheduled_read_data;
          queue_tail = (queue_tail + 1) & 255;
          queue_count = queue_count + 1;
        end
        if (scheduled_arch_response) begin
          request_active = 1'b0;
        end
      end
    end
  endtask

  task automatic drive_cycle;
    reg [31:0] random_value;
    begin
      lfsr = next_lfsr(lfsr);
      random_value = lfsr;
      reset = (cycle < 3) || (cycle == 256) ||
              ((cycle > 300) && (random_value[10:0] == 11'h000));
      lacc_flush = !reset && ((cycle == 128) || (random_value[7:0] == 8'h00));
      lacc_data_ready = random_value[1] | random_value[4];

      lacc_drsp_valid = 1'b0;
      lacc_drsp_rdata = 32'b0;
      if (!reset && !lacc_flush && (queue_count > 0) && random_value[2]) begin
        lacc_drsp_valid = 1'b1;
        lacc_drsp_rdata = response_queue[queue_head];
      end

      if (reset || lacc_flush) begin
        lacc_req_valid = 1'b0;
      end else if (request_active) begin
        lacc_req_valid = 1'b1;
      end else begin
        lacc_req_valid = 1'b0;
        if (cycle == 3) begin
          request_active = 1'b1;
          lacc_req_valid = 1'b1;
          lacc_req_command = 2'd1;
          lacc_req_imm = 7'h35;
          lacc_req_rj = 32'd2;
          lacc_req_rk = 32'h00003000;
        end else if (cycle == 5) begin
          request_active = 1'b1;
          lacc_req_valid = 1'b1;
          lacc_req_command = 2'd0;
          lacc_req_imm = 7'h2a;
          lacc_req_rj = 32'h00001000;
          lacc_req_rk = 32'h00002000;
        end else if (random_value[6:0] == 7'h00) begin
          request_active = 1'b1;
          lacc_req_valid = 1'b1;
          lacc_req_command = random_value[8] ? 2'd1 : 2'd0;
          lacc_req_imm = random_value[15:9];
          if (random_value[8]) begin
            lacc_req_rj = {29'b0, random_value[18:16]} + 32'd1;
            lacc_req_rk = {random_value[31:12], 12'b0};
          end else begin
            lacc_req_rj = {random_value[31:2], 2'b0};
            lfsr = next_lfsr(lfsr);
            lacc_req_rk = {lfsr[31:2], 2'b0};
          end
        end else if (random_value[9:0] == 10'h001) begin
          // Unsupported commands are one-cycle pulses because the golden has no response.
          lacc_req_valid = 1'b1;
          lacc_req_command = random_value[10] ? 2'd2 : 2'd3;
          lacc_req_imm = random_value[17:11];
          lacc_req_rj = random_value;
          lacc_req_rk = ~random_value;
        end
      end
    end
  endtask

  initial begin
    cycle_limit = 8192;
    seed_value = 32'h00158aa8;
    if (!$value$plusargs("cycles=%d", cycle_limit)) cycle_limit = 8192;
    if (!$value$plusargs("seed=%h", seed_value)) seed_value = 32'h00158aa8;
    negative_control = $test$plusargs("negative-control");
    lfsr = seed_value;
    reset = 1'b1;
    lacc_flush = 1'b0;
    lacc_req_valid = 1'b0;
    lacc_req_command = 2'b0;
    lacc_req_imm = 7'b0;
    lacc_req_rj = 32'b0;
    lacc_req_rk = 32'b0;
    lacc_data_ready = 1'b0;
    lacc_drsp_valid = 1'b0;
    lacc_drsp_rdata = 32'b0;
    queue_head = 0;
    queue_tail = 0;
    queue_count = 0;
    request_count = 0;
    response_count = 0;
    data_count = 0;
    read_count = 0;
    write_count = 0;
    stall_count = 0;
    drsp_count = 0;
    reset_count = 0;
    flush_count = 0;
    request_active = 1'b0;
    scheduled_read = 1'b0;
    scheduled_response = 1'b0;
    scheduled_arch_response = 1'b0;
    scheduled_cancel = 1'b0;
    previous_valid = 1'b0;
    previous_ready = 1'b0;
    previous_read = 1'b0;
    previous_cancel = 1'b1;
    previous_g_addr = 32'b0;
    previous_g_wdata = 32'b0;
    previous_g_size = 2'b0;
    previous_c_addr = 32'b0;
    previous_c_wdata = 32'b0;
    previous_c_size = 2'b0;

    for (cycle = 0; cycle < cycle_limit; cycle = cycle + 1) begin
      @(negedge clk);
      process_scheduled_events();
      drive_cycle();
      #1;
      compare_outputs();
      check_stability();

      if (reset) reset_count = reset_count + 1;
      if (lacc_flush) flush_count = flush_count + 1;
      if (lacc_req_valid) request_count = request_count + 1;
      if (g_lacc_rsp_valid) response_count = response_count + 1;
      if (lacc_drsp_valid) drsp_count = drsp_count + 1;
      if (g_lacc_data_valid) begin
        data_count = data_count + 1;
        if (!lacc_data_ready) stall_count = stall_count + 1;
        if (lacc_data_ready && g_lacc_data_read)
          read_count = read_count + 1;
        if (lacc_data_ready && !g_lacc_data_read)
          write_count = write_count + 1;
      end

      lfsr = next_lfsr(lfsr);
      scheduled_read_data = lfsr ^ cycle;
      scheduled_read = g_lacc_data_valid && lacc_data_ready && g_lacc_data_read;
      scheduled_response = lacc_drsp_valid;
      scheduled_arch_response = g_lacc_rsp_valid;
      scheduled_cancel = reset || lacc_flush;

      previous_valid = g_lacc_data_valid;
      previous_ready = lacc_data_ready;
      previous_read = g_lacc_data_read;
      previous_cancel = reset || lacc_flush;
      previous_g_addr = g_lacc_data_addr;
      previous_g_wdata = g_lacc_data_wdata;
      previous_g_size = g_lacc_data_size;
      previous_c_addr = c_lacc_data_addr;
      previous_c_wdata = c_lacc_data_wdata;
      previous_c_size = c_lacc_data_size;
    end

    if (negative_control) begin
      $display("NEGATIVE_CONTROL_DID_NOT_FAIL");
      $fatal(1);
    end
    if ((request_count == 0) || (response_count == 0) || (data_count == 0) ||
        (read_count == 0) || (write_count == 0) || (stall_count == 0) ||
        (drsp_count == 0) || (reset_count == 0) || (flush_count == 0)) begin
      $display("LACC_COVERAGE_MISSING requests=%0d responses=%0d data=%0d reads=%0d writes=%0d stalls=%0d drsp=%0d resets=%0d flushes=%0d",
               request_count, response_count, data_count, read_count, write_count,
               stall_count, drsp_count, reset_count, flush_count);
      $fatal(1);
    end
    $display("LACC_DIFF_PASS cycles=%0d seed=0x%08x requests=%0d responses=%0d data=%0d reads=%0d writes=%0d stalls=%0d drsp=%0d resets=%0d flushes=%0d",
             cycle_limit, seed_value, request_count, response_count, data_count,
             read_count, write_count, stall_count, drsp_count, reset_count,
             flush_count);
    $finish;
  end
endmodule
