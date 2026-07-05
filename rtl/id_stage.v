// Spinal-equivalent: id_stage ← spinal/src/.../idstage.scala
// Generated from Spinal source (IDStage in Pipeline.scala) — manually translated
module id_stage(
    input               clk, reset,
    input  [31:0]       if2id_pc, if2id_inst,
    input               if2id_valid, if2id_predict, if2id_pred_pc,
    input  [31:0]       rf_rdata1, rf_rdata2,
    input               stall_exe,
    // Outputs to EXE stage
    output [ 3:0]       id2exe_alu_op,
    output [ 1:0]       id2exe_mul_op, id2exe_branch_op, id2exe_mem_size, id2exe_csr_op,
    output              id2exe_valid, id2exe_branch, id2exe_mem_read, id2exe_mem_write,
    output              id2exe_mem_sext, id2exe_wb_en,
    output              id2exe_excp_ine, id2exe_excp_sys, id2exe_excp_brk, id2exe_excp_ertn,
    output [31:0]       id2exe_pc, id2exe_rdata1, id2exe_rdata2, id2exe_imm,
    output [ 4:0]       id2exe_rd_addr, id2exe_rj_addr, id2exe_rk_addr, id2exe_csr_num,
    output [ 4:0]       rf_rnum1, rf_rnum2,
    output              br_inst,
    output [31:0]       br_pc, br_target,
    // Cache op
    output              icacop_op_en, dcacop_op_en,
    output [ 1:0]       cacop_op_mode
);
    wire [5:0] opcode = if2id_inst[31:26];
    wire [4:0] rj = if2id_inst[9:5], rk = if2id_inst[14:10], rd = if2id_inst[4:0];
    wire [11:0] imm12 = if2id_inst[21:10];
    wire [15:0] imm16 = if2id_inst[25:10];
    wire [19:0] imm20 = if2id_inst[24:5];
    wire [25:0] imm26 = {if2id_inst[9:0], if2id_inst[25:10]};
    
    // Instruction decode (simplified — full decode table is in the Spinal source / openLA500 original)
    wire is_alu_reg = (opcode[5:2] <= 4'd14) && !if2id_inst[25];
    wire is_alu_imm = if2id_inst[25];
    wire is_load    = (opcode[5:2] >= 4'd8 && opcode[5:2] <= 4'd11);
    wire is_store   = (opcode[5:2] >= 4'd4 && opcode[5:2] <= 4'd7);
    wire is_branch  = (opcode[5:1] == 5'd12);
    wire is_jump    = (opcode == 6'h13);
    wire is_jirl    = (opcode == 6'h12);
    wire is_lu12iw  = (opcode == 6'h05);
    wire is_pcaddu12i = (opcode == 6'h06);
    wire is_syscall = (opcode == 6'h00 && rd == 5'd11);
    wire is_break   = (opcode == 6'h00 && rd == 5'd10);
    wire is_ertn    = (opcode == 6'h01 && rd == 5'd14);
    wire is_csr     = (opcode == 6'h01 && rj != 5'd0);
    wire is_cacop   = (opcode == 6'h01 && rj == 5'd11);
    wire is_mul     = (opcode == 6'h00 && rd == 5'd2);
    wire is_div     = (opcode == 6'h00 && rd == 5'd3 && rk == 5'd0);
    wire is_nop     = (if2id_inst == 32'h03400000);
    wire is_mem     = is_load || is_store;
    
    // Immediate generation
    reg [31:0] imm;
    always @(*) begin
        if (is_alu_imm || is_mem)          imm = {{20{imm12[11]}}, imm12};
        else if (is_pcaddu12i || is_lu12iw) imm = {imm20, 12'd0};
        else if (is_branch || is_jirl)      imm = {{14{imm16[15]}}, imm16, 2'd0};
        else if (is_jump)                  imm = {{4{imm26[25]}}, imm26, 2'd0};
        else                               imm = 32'd0;
    end
    
    // ALU operation
    reg [3:0] alu_op;
    always @(*) begin
        if (is_alu_reg || is_alu_imm)      alu_op = opcode[3:0];
        else if (is_mem || is_lu12iw || is_pcaddu12i) alu_op = 4'h0; // ADD
        else if (is_jirl || is_jump || is_branch)    alu_op = 4'h0;
        else                               alu_op = 4'hF; // NONE
    end
    
    wire valid_inst = is_alu_reg || is_alu_imm || is_mul || is_div || is_mem ||
                      is_branch || is_jump || is_jirl || is_csr || is_cacop ||
                      is_syscall || is_break || is_ertn || is_lu12iw || is_pcaddu12i || is_nop;
    
    assign rf_rnum1 = rj;
    assign rf_rnum2 = rk;
    assign id2exe_alu_op = alu_op;
    assign id2exe_mul_op = is_mul ? if2id_inst[17:16] : 2'd0;
    assign id2exe_div_op = is_div ? if2id_inst[16] : 1'd0;
    assign id2exe_branch = is_branch;
    assign id2exe_branch_op = is_branch ? opcode[1:0] : 2'd0;
    assign id2exe_mem_read = is_load;
    assign id2exe_mem_write = is_store;
    assign id2exe_mem_size = is_mem ? opcode[1:0] : 2'd2;
    assign id2exe_mem_sext = ~opcode[2];
    assign id2exe_wb_en = (is_alu_reg || is_alu_imm || is_load || is_mul || is_div ||
                           is_jirl || is_jump || is_csr || is_lu12iw || is_pcaddu12i) && (rd != 5'd0);
    assign id2exe_csr_op = is_csr ? 2'd1 : 2'd0;
    assign id2exe_pc = if2id_pc;
    assign id2exe_rdata1 = rf_rdata1;
    assign id2exe_rdata2 = rf_rdata2;
    assign id2exe_imm = imm;
    assign id2exe_rd_addr = rd;
    assign id2exe_rj_addr = rj;
    assign id2exe_rk_addr = rk;
    assign id2exe_csr_num = 14'd0;
    assign id2exe_valid = if2id_valid && ~stall_exe;
    assign id2exe_excp_ine = ~valid_inst;
    assign id2exe_excp_sys = is_syscall;
    assign id2exe_excp_brk = is_break;
    assign id2exe_excp_ertn = is_ertn;
    assign br_inst = is_branch || is_jump;
    assign br_pc = if2id_pc;
    assign br_target = if2id_pc + imm;
    assign icacop_op_en = is_cacop && (rd[4:3] != 2'd2);
    assign dcacop_op_en = is_cacop && (rd[4:3] == 2'd2);
    assign cacop_op_mode = rd[1:0];
endmodule
