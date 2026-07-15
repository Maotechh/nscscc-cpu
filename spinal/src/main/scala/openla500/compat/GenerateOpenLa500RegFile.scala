package openla500.compat

import openla500.config.CoreConfig
import openla500.pipeline.OpenLa500RegFile
import spinal.core._

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Paths}

object GenerateOpenLa500RegFile {
  private val implementationName = "openla500_regfile_impl"

  def emit(targetDirectory: String): Unit = {
    val target = Paths.get(targetDirectory)
    Files.createDirectories(target)
    SpinalConfig(
      mode = Verilog,
      targetDirectory = target.toString,
      oneFilePerComponent = true,
      headerWithDate = false,
      anonymSignalPrefix = "tmp"
    ).generate(new OpenLa500RegFile(CoreConfig.LockedWithDiffTest, implementationName))

    val implementationPath = target.resolve(s"$implementationName.v")
    val implementation = Files.readString(implementationPath, StandardCharsets.US_ASCII)
    val headerEnd = implementation.indexOf(");")
    val moduleEnd = implementation.lastIndexOf("endmodule")
    require(headerEnd >= 0 && moduleEnd > headerEnd, "generated regfile module is malformed")
    var body = implementation.substring(headerEnd + 2, moduleEnd)
    for (index <- (0 until 32).reverse) body = body.replace(s"rf_o_$index", s"rf_o[$index]")
    body = "(?m)^(\\s*assign\\s+rf_o\\[\\d+\\]\\s*=.*;\\s*)$".r.replaceAllIn(
      body,
      matched => s"`ifdef DIFFTEST_EN\n${matched.group(1)}\n`endif"
    )

    val generated =
      s"""`timescale 1ns/1ps
         |module regfile(
         |    input         clk,
         |    input  [ 4:0] raddr1,
         |    output [31:0] rdata1,
         |    input  [ 4:0] raddr2,
         |    output [31:0] rdata2,
         |    input         we,
         |    input  [ 4:0] waddr,
         |    input  [31:0] wdata
         |    `ifdef DIFFTEST_EN
         |    ,
         |    output [31:0] rf_o [31:0]
         |    `endif
         |);
         |$body
         |endmodule
         |""".stripMargin
    Files.writeString(target.resolve("regfile.v"), generated, StandardCharsets.US_ASCII)
    Files.delete(implementationPath)
  }

  def main(args: Array[String]): Unit =
    emit(sys.env.getOrElse("OPENLA500_RTL_OUT", "build/generated-regfile"))
}
