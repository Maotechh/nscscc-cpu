# PR draft: WB active overlay integration

- Branch: `refactor/20260713-2059-wb-active-overlay`
- Base: `288c4c834244b4b3e6ee03198124a82774d52002`
- Scope: add `wb_stage` to the 10-module active replacement set, update reachability contract and regression test.
- Verified: 11/11 reachability, Scala 4/4, 318 tests pass with 10 known skips, locked chiplab doctor, Vivado 2023.2 doctor.
- Diagnostic only: official hierarchy build/simulation exit 0 but strict warnings fail (254 DUT + 373 official) and func_lab19 mismatch remains at `0x1c07c79c`.
- Not claimed: 58/81 functional sets, random NEMU, perf20, U-Boot/Linux, FPGA implementation/timing, or complete SpinalHDL rewrite.
- Claude review: unavailable because `GEEKPIE_CLAUDE_API_KEY` is not set; local audit is retained.
- Merge policy: awaiting review; no automatic PR creation or merge.
