module TLBEntry(input [18:0] io_search_vpn, input [9:0] io_search_asid, input io_search_valid,
    input io_write_valid, input [4:0] io_write_index, input [18:0] io_write_vpn, input [19:0] io_write_ppn0, io_write_ppn1,
    input [5:0] io_write_ps, input [9:0] io_write_asid, input io_write_g, io_write_v, io_write_d0, io_write_d1,
    input io_inv_req, input [18:0] io_inv_vpn, input [9:0] io_inv_asid,
    input [4:0] io_probe_index,
    output io_hit, output [19:0] io_found_ppn, output [5:0] io_found_ps, output io_found_g, io_found_v, io_found_d,
    output [18:0] io_probe_vpn, output [19:0] io_probe_ppn0, io_probe_ppn1, output [5:0] io_probe_ps,
    output [9:0] io_probe_asid, output io_probe_g, io_probe_v, io_probe_d0, io_probe_d1);
assign io_hit=0; assign io_found_ppn=0; assign io_found_ps=0; assign io_found_g=0; assign io_found_v=0; assign io_found_d=0;
assign io_probe_vpn=0; assign io_probe_ppn0=0; assign io_probe_ppn1=0; assign io_probe_ps=0;
assign io_probe_asid=0; assign io_probe_g=0; assign io_probe_v=0; assign io_probe_d0=0; assign io_probe_d1=0; endmodule