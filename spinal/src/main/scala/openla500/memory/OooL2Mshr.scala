package openla500.memory

import openla500.core._
import spinal.core._

object OooL2MshrState extends SpinalEnum {
  val writeback, readRequest, refill, install, respond = newElement()
}

object OooL2WriteState extends SpinalEnum {
  val idle, lookup, victimWriteback, writeThrough, install = newElement()
}

final case class OooL2Mshr(config: OooCoreConfig) extends Bundle {
  val valid = Bool()
  val state = OooL2MshrState()
  val lineAddress = UInt(config.xlen bits)
  val victimWay = UInt(log2Up(config.level2Cache.ways) bits)
  val victimAddress = UInt(config.xlen bits)
  val victimData = Bits(OooCacheContract.LineBits bits)
  val lineData = Vec(Bits(OooCacheContract.BeatBits bits), OooCacheContract.BeatsPerLine)
  val refillMask = Bits(OooCacheContract.BeatsPerLine bits)
  val error = Bool()
  val returnBeat = UInt(OooCacheContract.BeatIndexWidth bits)
}
