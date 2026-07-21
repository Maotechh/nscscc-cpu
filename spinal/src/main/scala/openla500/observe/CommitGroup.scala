package openla500.observe

import spinal.core._
import spinal.lib._

/** A same-cycle retirement bundle. Lane zero is the oldest instruction. */
final case class CommitGroup(width: Int = CommitGroup.Width) extends Bundle {
  require(width >= 1, "a commit group must contain at least one lane")

  val valid = Bits(width bits)
  val events = Vec(CommitEvent(), width)

  /** A legal group has no hole between the oldest and youngest valid lanes. */
  def isPrefix: Bool =
    if (width == 1) True
    else (1 until width).map(lane => !valid(lane) || valid(lane - 1)).reduce(_ && _)

  def terminal(lane: Int): Bool = events(lane).exception.valid || events(lane).ertn
}

object CommitGroup {
  val Width = 3
  val EventWidth = 505
}

/** Enforces the architectural ordering contract before a multi-issue group reaches observation.
  *
  * A malformed producer is fail-closed: holes and instructions younger than an exception/ERTN are
  * removed from the output and reported on `contractViolation`. The active scalar core naturally
  * drives only lane zero, while a future rename/ROB owner can fill all three lanes.
  */
final class OrderedCommitGroup(
    width: Int = CommitGroup.Width,
    reportViolation: Boolean = true
) extends Component {
  val io = new Bundle {
    val input = slave(Flow(CommitGroup(width)))
    val output = master(Flow(CommitGroup(width)))
    val contractViolation = if (reportViolation) out(Bool()) else null
  }

  io.output.valid := io.input.valid
  io.output.payload.events := io.input.payload.events

  var seenInvalid: Bool = False
  var seenTerminal: Bool = False
  for (lane <- 0 until width) {
    val inputValid = io.input.payload.valid(lane)
    val admitted = inputValid && !seenInvalid && !seenTerminal

    io.output.payload.valid(lane) := admitted
    seenInvalid = seenInvalid || !inputValid
    seenTerminal = seenTerminal || (admitted && io.input.payload.terminal(lane))
  }

  if (reportViolation) {
    io.contractViolation := io.input.valid && (io.input.payload.valid =/= io.output.payload.valid)
  }
}
