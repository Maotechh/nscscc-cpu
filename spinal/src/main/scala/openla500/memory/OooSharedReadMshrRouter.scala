package openla500.memory

import openla500.core._
import spinal.core._
import spinal.lib._

/** Four-entry identity router between private L1 line readers and the shared L2.
  *
  * Each accepted request receives a hierarchy-global MSHR id. Return beats may be interleaved by
  * global id; the router restores the requesting L1's local id and applies only that client's
  * backpressure. Entries are released on an accepted final beat.
  */
final class OooSharedReadMshrRouter(
    config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit
) extends Component {
  private val idWidth = log2Up(config.mshrEntries)
  private val countWidth = log2Up(config.mshrEntries + 1)

  private def selectLowest(mask: Bits): UInt = {
    val selected = UInt(idWidth bits)
    selected := 0
    for (entry <- (0 until config.mshrEntries).reverse) {
      when(mask(entry)) { selected := U(entry, idWidth bits) }
    }
    selected
  }

  val io = new Bundle {
    val instructionReadValid = in Bool ()
    val instructionRead = in(OooLineReadRequest(config))
    val instructionReadReady = out Bool ()
    val instructionReadBeatValid = out Bool ()
    val instructionReadBeat = out(OooLineReadBeat(config))
    val instructionReadBeatReady = in Bool ()

    val dataReadValid = in Bool ()
    val dataRead = in(OooLineReadRequest(config))
    val dataReadReady = out Bool ()
    val dataReadBeatValid = out Bool ()
    val dataReadBeat = out(OooLineReadBeat(config))
    val dataReadBeatReady = in Bool ()

    val lowerReadValid = out Bool ()
    val lowerRead = out(OooLineReadRequest(config))
    val lowerReadReady = in Bool ()
    val lowerReadBeatValid = in Bool ()
    val lowerReadBeat = in(OooLineReadBeat(config))
    val lowerReadBeatReady = out Bool ()

    val activeCount = out UInt (countWidth bits)
  }

  val valid = Vec.fill(config.mshrEntries)(Reg(Bool()) init (False))
  val ownerData = Vec.fill(config.mshrEntries)(Reg(Bool()))
  val localId = Vec.fill(config.mshrEntries)(Reg(UInt(idWidth bits)))
  val preferData = RegInit(True)

  val freeMask = Bits(config.mshrEntries bits)
  for (entry <- 0 until config.mshrEntries) { freeMask(entry) := !valid(entry) }
  val hasFree = freeMask.orR
  val allocateId = selectLowest(freeMask)

  val bothPending = io.instructionReadValid && io.dataReadValid
  val selectData = io.dataReadValid && (!io.instructionReadValid || preferData)
  val selectInstruction = io.instructionReadValid && (!io.dataReadValid || !preferData)
  io.lowerReadValid := hasFree && (selectData || selectInstruction)
  io.lowerRead.lineAddress := Mux(
    selectData,
    io.dataRead.lineAddress,
    io.instructionRead.lineAddress
  )
  io.lowerRead.mshrId := allocateId
  io.dataReadReady := hasFree && selectData && io.lowerReadReady
  io.instructionReadReady := hasFree && selectInstruction && io.lowerReadReady

  val allocateFire = io.lowerReadValid && io.lowerReadReady
  when(allocateFire) {
    valid(allocateId) := True
    ownerData(allocateId) := selectData
    localId(allocateId) := Mux(selectData, io.dataRead.mshrId, io.instructionRead.mshrId)
    when(bothPending) { preferData := !selectData }
  }

  val responseId = io.lowerReadBeat.mshrId
  val responseKnown = valid(responseId)
  val responseOwnerData = ownerData(responseId)
  io.dataReadBeatValid := io.lowerReadBeatValid && responseKnown && responseOwnerData
  io.instructionReadBeatValid := io.lowerReadBeatValid && responseKnown && !responseOwnerData
  for (beat <- Seq(io.dataReadBeat, io.instructionReadBeat)) {
    beat.mshrId := localId(responseId)
    beat.beat := io.lowerReadBeat.beat
    beat.data := io.lowerReadBeat.data
    beat.last := io.lowerReadBeat.last
    beat.error := io.lowerReadBeat.error
  }
  io.lowerReadBeatReady := responseKnown && Mux(
    responseOwnerData,
    io.dataReadBeatReady,
    io.instructionReadBeatReady
  )

  val responseFire = io.lowerReadBeatValid && io.lowerReadBeatReady
  when(responseFire && io.lowerReadBeat.last) { valid(responseId) := False }

  io.activeCount := CountOne(valid.asBits)
}
