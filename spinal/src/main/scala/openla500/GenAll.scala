package openla500
import spinal.core._

object GenAll extends App {
  val targetDir = "../rtl"
  def gen(c: => Component): Unit = {
    try { SpinalConfig(targetDirectory = targetDir).generateVerilog(c) } 
    catch { case e: Exception => println(s"FAIL: ${e.getMessage.take(80)}") }
  }
  gen(new ALU); gen(new RegFile); gen(new Multiplier); gen(new Divider)
  gen(new BTB); gen(new TLBEntry); gen(new AddrTrans); gen(new PerfCounter)
  gen(new AxiBridge); gen(new CSRFile)
  gen(new ICache); gen(new DCache)  // cacop FIX included
  gen(new IFStage); gen(new IDStage); gen(new EXEStage)
  gen(new MEMStage); gen(new WBStage)
  println("Generation complete. Check ../rtl/ for .v files.")
}
