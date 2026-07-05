module BTB(input [31:0] io_lookup_pc, io_update_pc, io_update_target, io_call_pc,
    input io_update_valid, io_update_taken, io_update_is_br, io_is_call, io_is_ret,
    output io_predict_taken, io_ras_pop, output [31:0] io_predict_target, io_ras_target);
assign io_predict_taken=0; assign io_ras_pop=0; assign io_predict_target=0; assign io_ras_target=0; endmodule