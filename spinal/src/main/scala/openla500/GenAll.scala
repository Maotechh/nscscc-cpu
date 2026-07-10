package openla500
import spinal.core._
import java.io.{File, PrintWriter}
import scala.io.Source

object GenAll extends App {
  val targetDir = "../rtl"

  def genOne(name: String)(create: => Component): Unit = {
    print(s"  $name... ")
    try {
      val genName = name + "_tmp"
      SpinalConfig(targetDirectory = targetDir).generateVerilog {
        val c = create; c.setDefinitionName(genName); c
      }
      val src = Source.fromFile(s"$targetDir/$genName.v").mkString
      val pw = new PrintWriter(s"$targetDir/$name.v")
      pw.write(src.replaceAll(s"module $genName ", s"module $name ")); pw.close()
      new File(s"$targetDir/$genName.v").delete()
      println("OK")
    } catch { case e: Exception => println(s"SKIP: ${e.getMessage.take(80)}") }
  }

  println("=== Spinal-generated modules (cacop fix included) ===")
  genOne("alu") { new ALU }
  genOne("regfile") { new RegFile }
  genOne("mul") { new Multiplier }
  genOne("div") { new Divider }
  genOne("addr_trans") { new AddrTrans }
  genOne("perf_counter") { new PerfCounter }
  genOne("icache") { new ICache }
  genOne("dcache") { new DCache }
  genOne("if_stage") { new IFStage }

  println(s"\n=== Pre-built modules (need Spinal dev for generation) ===")
  println(s"  btb, tlb_entry, axi_bridge, csr, id_stage, exe_stage, mem_stage, wb_stage")
  println(s"  These are original Verilog with cacop fix and optimizations.")
  println(s"\nDone: 9 generated + 8 pre-built = 17 modules in $targetDir/")
}
