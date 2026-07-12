package openla500.pipeline

import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import openla500.config.CoreConfig
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

import scala.util.Random

private final class PipelinePayloadRoundTripTop extends Component {
  val io = new Bundle {
    val fetchIn = in Bits (FetchPayload.LegacyWidth bits)
    val fetchOut = out Bits (FetchPayload.LegacyWidth bits)
    val decodeIn = in Bits (DecodePayload.BaseLegacyWidth bits)
    val decodeOut = out Bits (DecodePayload.BaseLegacyWidth bits)
    val decodeLaccIn = in Bits (DecodePayload.LaccLegacyWidth bits)
    val decodeLaccOut = out Bits (DecodePayload.LaccLegacyWidth bits)
    val executeIn = in Bits (ExecutePayload.LegacyWidth bits)
    val executeOut = out Bits (ExecutePayload.LegacyWidth bits)
    val memoryIn = in Bits (MemoryPayload.LegacyWidth bits)
    val memoryOut = out Bits (MemoryPayload.LegacyWidth bits)
    val writebackOut = out Bits (WritebackPayload.LegacyWidth bits)
    val fetchContractMatches = out Bool ()
    val decodeContractMatches = out Bool ()
    val decodeLaccContractMatches = out Bool ()
    val executeContractMatches = out Bool ()
    val memoryContractMatches = out Bool ()
    val heartbeat = out Bool ()
  }

  private def assertPayloadContract(payload: Bundle): Unit = {
    assert(
      payload.flatten.forall(_.isDirectionLess),
      s"${payload.getClass.getSimpleName} has IO direction"
    )
    assert(!payload.elements.contains("valid"), s"${payload.getClass.getSimpleName} owns valid")
  }

  val fetch = FetchPayload.unpackLegacy(io.fetchIn)
  val decode = DecodePayload.unpackLegacy(io.decodeIn)
  val decodeLacc = DecodePayload.unpackLegacy(io.decodeLaccIn, CoreConfig.LockedWithLacc)
  val execute = ExecutePayload.unpackLegacy(io.executeIn)
  val memory = MemoryPayload.unpackLegacy(io.memoryIn)
  val writeback = WritebackPayload.unpackLegacy(io.memoryIn)

  Seq(fetch, decode, decodeLacc, execute, memory, writeback).foreach(assertPayloadContract)

  private def namedField(payload: Bundle, field: LegacyBitField): Data = {
    val data = payload.elements
      .find(_._1 == field.name)
      .map(_._2)
      .getOrElse(
        throw new IllegalArgumentException(s"${payload.getClass.getSimpleName} lacks ${field.name}")
      )
    assert(data.getBitsWidth == field.width, s"${field.name} has the wrong width")
    data
  }

  private def oraclePack(payload: Bundle, layout: Seq[LegacyBitField], width: Int): Bits = {
    val result = Bits(width bits)
    result := 0
    layout.foreach { field =>
      result(field.high downto field.low) := namedField(payload, field).asBits
    }
    result
  }

  private def unpackMatches(
      payload: Bundle,
      input: Bits,
      layout: Seq[LegacyBitField]
  ): Bool =
    layout
      .map(field => namedField(payload, field).asBits === input(field.high downto field.low))
      .reduce(_ && _)

  io.fetchOut := fetch.toLegacyBits
  io.decodeOut := decode.toLegacyBits
  io.decodeLaccOut := decodeLacc.toLegacyBits
  io.executeOut := execute.toLegacyBits
  io.memoryOut := memory.toLegacyBits
  io.writebackOut := WritebackPayload.packLegacy(writeback)
  io.fetchContractMatches := unpackMatches(fetch, io.fetchIn, FetchPayload.LegacyLayout) &&
    (fetch.toLegacyBits === oraclePack(fetch, FetchPayload.LegacyLayout, FetchPayload.LegacyWidth))
  io.decodeContractMatches := unpackMatches(
    decode,
    io.decodeIn,
    DecodePayload.BaseLegacyLayout
  ) && (decode.toLegacyBits === oraclePack(
    decode,
    DecodePayload.BaseLegacyLayout,
    DecodePayload.BaseLegacyWidth
  ))
  io.decodeLaccContractMatches := unpackMatches(
    decodeLacc,
    io.decodeLaccIn,
    DecodePayload.LaccLegacyLayout
  ) && (decodeLacc.toLegacyBits === oraclePack(
    decodeLacc,
    DecodePayload.LaccLegacyLayout,
    DecodePayload.LaccLegacyWidth
  ))
  io.executeContractMatches := unpackMatches(
    execute,
    io.executeIn,
    ExecutePayload.LegacyLayout
  ) && (execute.toLegacyBits === oraclePack(
    execute,
    ExecutePayload.LegacyLayout,
    ExecutePayload.LegacyWidth
  ))
  io.memoryContractMatches := unpackMatches(
    memory,
    io.memoryIn,
    MemoryPayload.LegacyLayout
  ) && (memory.toLegacyBits === oraclePack(
    memory,
    MemoryPayload.LegacyLayout,
    MemoryPayload.LegacyWidth
  ))
  val heartbeat = Reg(Bool()) init (False)
  heartbeat := !heartbeat
  io.heartbeat := heartbeat
}

class PipelinePayloadsSpec extends AnyFunSuite {
  // tests/test_core_contract_manifest.py recomputes these from a158aa8 concat expressions.
  private val GoldenLayoutSha256 = Map(
    "fetch" -> "c5e3c16b881eb58ecf2eff38c691626b910862280fbe05415aecc75b6d5aab41",
    "decode_base" -> "fd56358e4d20c3489aba8dba91cf19b3d5013ab56ef1832fb6c08965b39ab7d2",
    "decode_lacc" -> "06af0fe025df63a5e490f95473c024d18a755a65f14c8b1ecdd3c10861b371a8",
    "execute" -> "18db2eeef7b20a78b8ed130b461720c991d4af395b3a58bd9f4e41acb77ca985",
    "memory" -> "89098e7060abc6917b8753a7a155b16489671c17dcbb31fe49eb5d2e75055ad4"
  )

  private def layoutSha256(layout: Seq[LegacyBitField]): String = {
    val canonical =
      layout.map(field => s"${field.name}:${field.high}:${field.low}").mkString("", "\n", "\n")
    MessageDigest
      .getInstance("SHA-256")
      .digest(canonical.getBytes(StandardCharsets.UTF_8))
      .map(byte => f"${byte & 0xff}%02x")
      .mkString
  }

  test("legacy layouts reproduce the independently parsed golden concat oracle") {
    assert(layoutSha256(FetchPayload.LegacyLayout) == GoldenLayoutSha256("fetch"))
    assert(layoutSha256(DecodePayload.BaseLegacyLayout) == GoldenLayoutSha256("decode_base"))
    assert(layoutSha256(DecodePayload.LaccLegacyLayout) == GoldenLayoutSha256("decode_lacc"))
    assert(layoutSha256(ExecutePayload.LegacyLayout) == GoldenLayoutSha256("execute"))
    assert(layoutSha256(MemoryPayload.LegacyLayout) == GoldenLayoutSha256("memory"))

    val layouts = Seq(
      FetchPayload.LegacyWidth -> FetchPayload.LegacyLayout,
      DecodePayload.BaseLegacyWidth -> DecodePayload.BaseLegacyLayout,
      DecodePayload.LaccLegacyWidth -> DecodePayload.LaccLegacyLayout,
      ExecutePayload.LegacyWidth -> ExecutePayload.LegacyLayout,
      MemoryPayload.LegacyWidth -> MemoryPayload.LegacyLayout
    )
    layouts.foreach { case (width, layout) =>
      assert(layout.head.low == 0)
      assert(layout.last.high == width - 1)
      assert(layout.map(_.width).sum == width)
      assert(layout.sliding(2).forall {
        case Seq(lower, upper) => lower.high + 1 == upper.low
        case _                 => true
      })
    }
  }

  test("explicit pack and unpack preserve every bit in all locked layouts") {
    val workspace =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-contracts") +
        "/pipeline-payloads"
    SimConfig.withVerilator
      .addSimulatorFlag("-Wall")
      .addSimulatorFlag("-Wwarn-WIDTH")
      .addSimulatorFlag("-Wwarn-UNOPTFLAT")
      .addSimulatorFlag("-Wwarn-CMPCONST")
      .addSimulatorFlag("-Wwarn-UNSIGNED")
      .disableCache
      .workspacePath(workspace)
      .compile(new PipelinePayloadRoundTripTop)
      .doSim { dut =>
        val random = new Random(0x5eed2026L)
        def next(width: Int): BigInt = BigInt(width, random)

        for (_ <- 0 until 128) {
          val fetch = next(FetchPayload.LegacyWidth)
          val decode = next(DecodePayload.BaseLegacyWidth)
          val decodeLacc = next(DecodePayload.LaccLegacyWidth)
          val execute = next(ExecutePayload.LegacyWidth)
          val memory = next(MemoryPayload.LegacyWidth)

          dut.io.fetchIn #= fetch
          dut.io.decodeIn #= decode
          dut.io.decodeLaccIn #= decodeLacc
          dut.io.executeIn #= execute
          dut.io.memoryIn #= memory
          sleep(1)

          assert(dut.io.fetchOut.toBigInt == fetch)
          assert(dut.io.decodeOut.toBigInt == decode)
          assert(dut.io.decodeLaccOut.toBigInt == decodeLacc)
          assert(dut.io.executeOut.toBigInt == execute)
          assert(dut.io.memoryOut.toBigInt == memory)
          assert(dut.io.writebackOut.toBigInt == memory)
          assert(dut.io.fetchContractMatches.toBoolean)
          assert(dut.io.decodeContractMatches.toBoolean)
          assert(dut.io.decodeLaccContractMatches.toBoolean)
          assert(dut.io.executeContractMatches.toBoolean)
          assert(dut.io.memoryContractMatches.toBoolean)
        }
      }
  }
}
