package openla500

import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._
import scala.language.reflectiveCalls

case class ALUSimTop() extends Component {
  val io = new Bundle {
    val aluOp = in UInt (4 bits)
    val src1 = in UInt (32 bits)
    val src2 = in UInt (32 bits)
    val result = out UInt (32 bits)
    val overflow = out Bool ()
    val cmpSub = out Bool ()
    val heartbeat = out Bool ()
  }

  val alu = ALU()
  alu.io.alu_op := io.aluOp
  alu.io.src1 := io.src1
  alu.io.src2 := io.src2
  io.result := alu.io.result
  io.overflow := alu.io.overflow
  io.cmpSub := alu.io.cmp_sub

  val heartbeat = Reg(Bool()) init (False)
  heartbeat := !heartbeat
  io.heartbeat := heartbeat
}

class ALUSpec extends AnyFunSuite {
  private val mask32 = (BigInt(1) << 32) - 1

  private def unsigned32(value: BigInt): BigInt = value & mask32

  test("the current 4-bit ALU passes a local smoke contract, not golden equivalence") {
    val workspace = sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-local")
    SimConfig
      .withConfig(SpinalConfig(oneFilePerComponent = true))
      .withVerilator
      .addSimulatorFlag("-Wall")
      .addSimulatorFlag("-Wwarn-WIDTH")
      .addSimulatorFlag("-Wwarn-UNOPTFLAT")
      .addSimulatorFlag("-Wwarn-CMPCONST")
      .addSimulatorFlag("-Wwarn-UNSIGNED")
      .disableCache
      .workspacePath(workspace)
      .compile(ALUSimTop())
      .doSim("alu-directed", 0x5a17) { dut =>
        dut.clockDomain.forkStimulus(period = 10)

        def drive(op: Int, src1: BigInt, src2: BigInt): Unit = {
          dut.io.aluOp #= op
          dut.io.src1 #= unsigned32(src1)
          dut.io.src2 #= unsigned32(src2)
          sleep(1)
        }

        def check(op: Int, src1: BigInt, src2: BigInt, expected: BigInt): Unit = {
          drive(op, src1, src2)
          assert(dut.io.result.toBigInt == unsigned32(expected))
        }

        check(AluOp.ADD, 0x7fffffff, 1, 0x80000000L)
        assert(dut.io.overflow.toBoolean)

        check(AluOp.SUB, BigInt("80000000", 16), 1, BigInt("7fffffff", 16))
        assert(dut.io.overflow.toBoolean)

        check(AluOp.SLT, -1, 1, 1)
        check(AluOp.SLTU, -1, 1, 0)
        check(AluOp.AND, 0xf0f00f0fL, 0x55aa55aaL, 0x50a0050aL)
        check(AluOp.NOR, 0xf000000fL, 0x0ff00000L, 0x000ffff0L)
        check(AluOp.OR, 0xf000000fL, 0x0ff00000L, 0xfff0000fL)
        check(AluOp.XOR, 0xaaaa5555L, 0xffff0000L, 0x55555555L)
        check(AluOp.SLL, 1, 31, BigInt("80000000", 16))
        check(AluOp.SRL, BigInt("80000000", 16), 31, 1)
        check(AluOp.SRA, BigInt("80000000", 16), 31, mask32)
        check(AluOp.LUI, 0x12345678L, 0x89abcdefL, 0x89abcdefL)

        drive(AluOp.ADD, -2, 1)
        assert(dut.io.cmpSub.toBoolean)
        assert(!dut.io.overflow.toBoolean)
      }
  }
}
