package openla500.pipeline

import openla500.predict.PredictorDirectionMetadata
import spinal.core._
import spinal.lib._

/** One instruction plus the predictor metadata that must remain aligned with it. */
final case class BufferedFetchInstruction() extends Bundle {
  val fetch = FetchPayload()
  val direction = PredictorDirectionMetadata()
}

/** Prefix-valid fetch packet used by the fetch4 frontend boundary.
  *
  * Slots are ordered oldest to youngest. A producer may provide one through four instructions, but
  * valid slots must form a prefix starting at lane zero.
  */
final case class FetchPacket(width: Int = FetchPacket.Width) extends Bundle {
  require(width >= 1, "a fetch packet must contain at least one slot")

  val slotValid = Bits(width bits)
  val slots = Vec(BufferedFetchInstruction(), width)

  def count: UInt = CountOne(slotValid)
  def isPrefix: Bool =
    if (width == 1) True
    else (1 until width).map(lane => !slotValid(lane) || slotValid(lane - 1)).reduce(_ && _)
}

object FetchPacket {
  val Width = 4
}

/** Redirectable instruction buffer between fetch and decode.
  *
  * The storage already accepts a four-slot packet and exposes a four-entry ordered window, while
  * the active scalar backend consumes one head entry per cycle. This keeps the current decode path
  * functional and establishes the concrete boundary needed by a future decode3/rename3 backend.
  * Redirect recovery is owned here: queued instructions are flushed atomically and, when an older
  * Fetch response is still in flight, exactly its next returned packet is consumed before any
  * target-path packet can enter the buffer.
  */
final class FetchInstructionBuffer(
    depth: Int = 8,
    packetWidth: Int = FetchPacket.Width,
    windowWidth: Int = FetchPacket.Width,
    exposePreview: Boolean = true
) extends Component {
  private def isPowerOfTwo(value: Int): Boolean = value > 0 && (value & (value - 1)) == 0

  require(isPowerOfTwo(depth), "instruction-buffer depth must be a power of two")
  require(packetWidth >= 1 && packetWidth <= depth, "invalid fetch packet width")
  require(windowWidth >= 1 && windowWidth <= depth, "invalid instruction window width")

  private val pointerWidth = log2Up(depth)
  private val occupancyWidth = log2Up(depth + 1)

  val io = new Bundle {
    val flush = in Bool ()
    val redirect = in Bool ()
    val redirectTargetAccepted = in Bool ()
    val push = slave(Stream(FetchPacket(packetWidth)))
    val pop = master(Stream(BufferedFetchInstruction()))
    val windowValid = if (exposePreview) out(Bits(windowWidth bits)) else null
    val window = if (exposePreview) out(Vec(BufferedFetchInstruction(), windowWidth)) else null
    val occupancy = if (exposePreview) out(UInt(occupancyWidth bits)) else null
  }

  val storage = Vec.fill(depth)(Reg(BufferedFetchInstruction()))
  val readPointer = Reg(UInt(pointerWidth bits)) init (0)
  val writePointer = Reg(UInt(pointerWidth bits)) init (0)
  val occupancy = Reg(UInt(occupancyWidth bits)) init (0)
  val discardNextPush = RegInit(False)

  val empty = occupancy === 0
  val popFire = io.pop.valid && io.pop.ready
  val packetCount = io.push.payload.count.resize(occupancyWidth)
  val freeAfterPop = UInt(occupancyWidth bits)
  freeAfterPop := U(depth, occupancyWidth bits) - occupancy + popFire.asUInt.resize(occupancyWidth)

  io.pop.valid := !io.flush && !empty
  io.pop.payload := storage(readPointer)
  // flush 拍和延迟丢弃拍始终向上游声明 ready，使 Fetch 能原子清空旧路径。
  // 否则 Fetch 可能保留旧 PC，却已经让 I-cache 接受了 redirect 目标。
  io.push.ready := io.flush || discardNextPush || freeAfterPop >= packetCount

  if (exposePreview) {
    io.occupancy := occupancy
    for (lane <- 0 until windowWidth) {
      val windowAddress = (readPointer + U(lane, pointerWidth bits)).resized
      io.windowValid(lane) := !io.flush && occupancy > U(lane, occupancyWidth bits)
      io.window(lane) := storage(windowAddress)
    }
  }

  val discardFire = discardNextPush && io.push.valid && io.push.ready && !io.flush
  val pushFire = io.push.valid && io.push.ready && !io.flush && !discardNextPush
  for (lane <- 0 until packetWidth) {
    val writeAddress = (writePointer + U(lane, pointerWidth bits)).resized
    when(pushFire && io.push.payload.slotValid(lane)) {
      storage(writeAddress) := io.push.payload.slots(lane)
    }
  }

  when(io.flush) {
    readPointer := 0
    writePointer := 0
    occupancy := 0
    // A response visible in the redirect cycle is discarded by this flush. If the target request
    // was accepted in the same cycle, the next response is already target-path. Only the remaining
    // case has one old-path packet still in flight and therefore needs a delayed discard.
    discardNextPush := io.redirect && !io.redirectTargetAccepted && !io.push.valid
  } otherwise {
    when(discardFire) {
      discardNextPush := False
    }
    when(popFire) {
      readPointer := (readPointer + 1).resized
    }
    when(pushFire) {
      writePointer := (writePointer + packetCount.resize(pointerWidth)).resized
    }

    when(pushFire && popFire) {
      occupancy := (occupancy + packetCount - 1).resized
    }.elsewhen(pushFire) {
      occupancy := (occupancy + packetCount).resized
    }.elsewhen(popFire) {
      occupancy := occupancy - 1
    }
  }
}
