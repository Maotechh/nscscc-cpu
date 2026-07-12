package openla500.pipeline

import spinal.core._

/** A redirect request owns a target but does not declare an IO direction.
  *
  * The producer must hold active/target stable while its pipeline decision is stalled.
  */
final case class RedirectRequest() extends Bundle {
  val active = Bool()
  val target = UInt(32 bits)
}

/** Occupancy of stages older than decode.
  *
  * These bits report whether a stage register holds an instruction. They remain asserted during
  * backpressure and therefore must not be derived from `Stream.fire` or a ready-qualified valid.
  */
final case class OlderStageOccupancy() extends Bundle {
  val execute = Bool()
  val memory = Bool()
  val writeback = Bool()

  def any: Bool = execute || memory || writeback
}

/** Cross-stage control reasons kept separate to preserve precise flush semantics.
  *
  * Global redirects kill every younger instruction. Branch repair only kills younger fetch/decode
  * work. debugBreakPoint applies backpressure at writeback and must not manufacture a commit.
  */
final case class PipelineCtrl() extends Bundle {
  val exception = RedirectRequest()
  val ertn = RedirectRequest()
  val refetch = RedirectRequest()
  val instructionCacheOp = RedirectRequest()
  val idle = RedirectRequest()
  val branchRepair = RedirectRequest()
  val debugBreakPoint = Bool()

  def globalFlush: Bool =
    exception.active || ertn.active || refetch.active || instructionCacheOp.active || idle.active

  def globalTarget: UInt =
    Mux(
      exception.active,
      exception.target,
      Mux(
        ertn.active,
        ertn.target,
        Mux(
          refetch.active,
          refetch.target,
          Mux(instructionCacheOp.active, instructionCacheOp.target, idle.target)
        )
      )
    )
}

sealed trait GlobalRedirectCause

object GlobalRedirectCause {
  case object Exception extends GlobalRedirectCause
  case object Ertn extends GlobalRedirectCause
  case object Refetch extends GlobalRedirectCause
  case object InstructionCacheOp extends GlobalRedirectCause
  case object Idle extends GlobalRedirectCause
}

object PipelineCtrlPriority {
  import GlobalRedirectCause._

  val HighestFirst: Vector[GlobalRedirectCause] =
    Vector(Exception, Ertn, Refetch, InstructionCacheOp, Idle)

  def selectGlobal(
      exception: Boolean,
      ertn: Boolean,
      refetch: Boolean,
      instructionCacheOp: Boolean,
      idle: Boolean
  ): Option[GlobalRedirectCause] =
    if (exception) Some(Exception)
    else if (ertn) Some(Ertn)
    else if (refetch) Some(Refetch)
    else if (instructionCacheOp) Some(InstructionCacheOp)
    else if (idle) Some(Idle)
    else None
}
