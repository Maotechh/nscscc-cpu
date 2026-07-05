package openla500
import spinal.core._

// Batch generate all modules to ../rtl/
object GenAll extends App {
  val targetDir = "../rtl"
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new ALU)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new RegFile)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new Multiplier)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new Divider)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new BTB)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new TLBEntry)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new AddrTrans)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new PerfCounter)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new AxiBridge)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new CSRFile)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new ICache)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new DCache)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new IFStage)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new IDStage)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new EXEStage)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new MEMStage)
  SpinalConfig(targetDirectory = targetDir).generateVerilog(new WBStage)
  println("All 17 modules generated to ../rtl/")
}
