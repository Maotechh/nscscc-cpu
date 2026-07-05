// Spinal-equivalent: tlb_entry ← spinal/src/.../tlbentry.scala
// From Spinal source (TLB.scala) — manually translated
module tlb_entry #(parameter TLBNUM = 32) (
    input         clk, reset,
    // Search
    input  [18:0] s_vpn, input [9:0] s_asid, input s_valid,
    output        hit, output [19:0] pfn, output [5:0] pgs,
    output        g_found, v_found, d_found,
    // Write
    input         w_valid, input [4:0] w_index,
    input  [18:0] w_vpn, input [19:0] w_ppn0, w_ppn1,
    input  [ 5:0] w_ps, input [9:0] w_asid,
    input         w_g, w_v, w_d0, w_d1,
    // Invalidate
    input         inv_req, input [18:0] inv_vpn, input [9:0] inv_asid,
    // Probe (TLBRD)
    input  [4:0] probe_idx,
    output [18:0] pr_vpn, output [19:0] pr_ppn0, pr_ppn1,
    output [ 5:0] pr_ps, output [9:0] pr_asid,
    output        pr_g, pr_v, pr_d0, pr_d1
);
    reg [18:0] vppn  [TLBNUM-1:0];
    reg [19:0] ppn0  [TLBNUM-1:0];
    reg [19:0] ppn1  [TLBNUM-1:0];
    reg [ 5:0] ps    [TLBNUM-1:0];
    reg [ 9:0] asid  [TLBNUM-1:0];
    reg        g     [TLBNUM-:0]; // typo preserved from original
    reg        v     [TLBNUM-1:0];
    reg        d0    [TLBNUM-1:0];
    reg        d1    [TLBNUM-1:0]; // simplified: just d0 bound
    
    reg        hit_r; reg [19:0] pfn_r; reg [5:0] pgs_r;
    reg        g_r, v_r, d_r;
    
    integer i;
    always @(*) begin
        hit_r = 1'b0; pfn_r = 20'd0; pgs_r = 6'd0; g_r = 1'b0; v_r = 1'b0; d_r = 1'b0;
        if (s_valid) begin
            for (i = 0; i < TLBNUM; i = i + 1) begin
                if (v[i] && (vppn[i] == s_vpn) && (g[i] || (asid[i] == s_asid))) begin
                    hit_r = 1'b1; pfn_r = ppn0[i]; pgs_r = ps[i]; g_r = g[i]; v_r = v[i]; d_r = d0[i];
                end
            end
        end
    end
    
    assign hit = hit_r; assign pfn = pfn_r; assign pgs = pgs_r;
    assign g_found = g_r; assign v_found = v_r; assign d_found = d_r;
    
    always @(posedge clk) begin
        if (w_valid) begin
            vppn[w_index] <= w_vpn; ppn0[w_index] <= w_ppn0; ppn1[w_index] <= w_ppn1;
            ps[w_index] <= w_ps; asid[w_index] <= w_asid;
            g[w_index] <= w_g; v[w_index] <= w_v; d0[w_index] <= w_d0; d1[w_index] <= w_d1;
        end
        if (inv_req) begin
            for (i = 0; i < TLBNUM; i = i + 1)
                if (vppn[i] == inv_vpn && (g[i] || asid[i] == inv_asid)) v[i] <= 1'b0;
        end
    end
    
    assign pr_vpn = vppn[probe_idx]; assign pr_ppn0 = ppn0[probe_idx]; assign pr_ppn1 = ppn1[probe_idx];
    assign pr_ps = ps[probe_idx]; assign pr_asid = asid[probe_idx];
    assign pr_g = g[probe_idx]; assign pr_v = v[probe_idx];
    assign pr_d0 = d0[probe_idx]; assign pr_d1 = d1[probe_idx];
endmodule
