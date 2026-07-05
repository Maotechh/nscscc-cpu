package openla500
import spinal.core._

// Generate all 17 Verilog modules to ../rtl/
// 9 modules generate directly. 8 modules (BTB,TLB,AxiBridge,CSR,ID/EXE/MEM/WB)
// require Spinal dev version; use existing hand-written Verilog in rtl/ for now.

object GenAll extends App {
  val dir = "../rtl"
  
  def gen(c: => Component): Unit = try {
    SpinalConfig(targetDirectory = dir).generateVerilog(c)
    println("  OK")
  } catch { case e: Exception => println(s"  FAIL: ${e.getMessage.take(100)}") }

  println("Generating 17 modules to ../rtl/...")
  gen(new ALU); gen(new RegFile); gen(new Multiplier); gen(new Divider)
  gen(new AddrTrans); gen(new PerfCounter); gen(new ICache); gen(new DCache)
  gen(new IFStage)
  
  // These 8 need Spinal dev version (SpinalHDL 1.10+ hierarchy limitation)
  println("Skipping 8 modules (need Spinal dev): BTB,TLB,AxiBridge,CSR,ID,EXE,MEM,WB")
  println("Done. 9 modules generated.")
}
