# PR draft: SpinalHDL ID stage replacement

- Branch: `refactor/20260713-2120-id-stage-spinal`
- Base: `b2946f8ac93fc9ccfa9c8748bb53f444976c36cb`
- Scope: typed SpinalHDL decode stage plus exact legacy adapter and local differential gate.
- Evidence: `logs/refactor/20260713-2120-id-stage-spinal/`.
- Supported claim: four locked LACC/DiffTest configurations pass 8259-cycle local golden lockstep and negative control; generated RTL is reproducible.
- Explicit non-claims: no active core_top integration, official func/random/perf/Linux/Vivado result, or complete Spinal refactor claim.
- Review: awaiting Claude review result and maintainer review.
- Rollback: revert this PR; remove `id_stage` replacement from dependent overlay.
