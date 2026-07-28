if {$argc != 2} {
  puts stderr "usage: vivado -mode batch -source tools/ooo_core_synth.tcl -tclargs <rtl> <out-dir>"
  exit 2
}

set rtl [file normalize [lindex $argv 0]]
set out_dir [file normalize [lindex $argv 1]]
file mkdir $out_dir

read_verilog -sv $rtl
synth_design -top ooo_core -part xc7a200tfbg676-2 -flatten_hierarchy rebuilt
create_clock -name ooo_clk -period 10.000 [get_ports clk]

report_utilization -hierarchical -file [file join $out_dir utilization.rpt]
report_timing_summary -delay_type max -max_paths 20 -file [file join $out_dir timing.rpt]
write_checkpoint -force [file join $out_dir ooo_core_synth.dcp]

set worst_slack [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
puts "OOO_CORE_SYNTH_WNS=$worst_slack"
puts "OOO_CORE_SYNTH_OUT=$out_dir"
exit 0
