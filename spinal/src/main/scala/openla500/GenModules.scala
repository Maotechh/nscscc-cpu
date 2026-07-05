package openla500
import spinal.core._
// Generate individual Verilog modules — avoids Spinal's anti-submodule limitation

object GenALU extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new ALU) }
object GenRegFile extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new RegFile) }
object GenMultiplier extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new Multiplier) }
object GenDivider extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new Divider) }
object GenBTB extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new BTB) }
object GenTLB extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new TLBEntry) }
object GenAddrTrans extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new AddrTrans) }
object GenPerfCounter extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new PerfCounter) }
object GenAxiBridge extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new AxiBridge) }
object GenCSR extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new CSRFile) }
object GenICache extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new ICache) }
object GenDCache extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new DCache) }
object GenIFStage extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new IFStage) }
object GenIDStage extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new IDStage) }
object GenEXEStage extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new EXEStage) }
object GenMEMStage extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new MEMStage) }
object GenWBStage extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new WBStage) }
object GenMyCPUTop extends App { SpinalConfig(targetDirectory = "gen").generateVerilog(new MyCPUTop) }
