package openla500.ooo

import spinal.core._
import spinal.lib._

/** Circular queue separating rename allocation from execution-port routing. */
final class OooDispatchQueue(
    config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit
) extends Component {
  private val pointerWidth = log2Up(config.dispatchQueueEntries)
  private val countWidth = log2Up(config.dispatchQueueEntries + 1)
  private val prefixWidth = log2Up(config.renameWidth + 1)

  val io = new Bundle {
    val enqueueValid = in Bits (config.renameWidth bits)
    val enqueue = in Vec (OooRenamedUop(config), config.renameWidth)
    val enqueueReady = out Bool ()
    val enqueueAccept = in Bool ()

    val dequeueValid = out Bits (config.dispatchWidth bits)
    val dequeue = out Vec (OooRenamedUop(config), config.dispatchWidth)
    val dequeueReady = in Bits (config.dispatchWidth bits)

    val flush = in Bool ()
    val occupancy = out UInt (countWidth bits)
  }

  val entries = Vec.fill(config.dispatchQueueEntries)(Reg(OooRenamedUop(config)))
  val head = Reg(UInt(pointerWidth bits)) init (0)
  val tail = Reg(UInt(pointerWidth bits)) init (0)
  val count = Reg(UInt(countWidth bits)) init (0)

  val enqueuePrefix = Vec(UInt(prefixWidth bits), config.renameWidth + 1)
  enqueuePrefix(0) := U(0, prefixWidth bits)
  for (lane <- 0 until config.renameWidth) {
    enqueuePrefix(lane + 1) := enqueuePrefix(lane) + io.enqueueValid(lane).asUInt
  }
  val enqueueCount = enqueuePrefix(config.renameWidth)
  val freeSlots = U(config.dispatchQueueEntries, countWidth bits) - count
  io.enqueueReady := !io.flush && freeSlots >= enqueueCount

  for (lane <- 0 until config.dispatchWidth) {
    io.dequeueValid(lane) := !io.flush && count > U(lane, countWidth bits)
    val source = (head + U(lane, pointerWidth bits)).resized
    io.dequeue(lane) := entries(source)
  }
  val dequeueFire = io.dequeueValid & io.dequeueReady
  val dequeueCount = CountOne(dequeueFire)

  when(io.flush) {
    head := tail
    count := U(0, countWidth bits)
  }.otherwise {
    when(io.enqueueAccept) {
      for (lane <- 0 until config.renameWidth) {
        when(io.enqueueValid(lane)) {
          val destination = (tail + enqueuePrefix(lane)).resized
          entries(destination) := io.enqueue(lane)
        }
      }
      tail := tail + enqueueCount
    }
    head := head + dequeueCount
    count := count + Mux(io.enqueueAccept, enqueueCount, U(0, prefixWidth bits)) -
      dequeueCount
  }

  io.occupancy := count
}
