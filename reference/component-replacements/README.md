# Active Spinal CPU Overlay

The only committed CPU RTL is the reproducible SpinalHDL output `rtl/mycpu_top.v`.
`core-top.json` and `active-reachable.json` bind that exact blob to the locked
`a158aa8` target. Historical leaf replacement RTL and mixed-overlay manifests
were removed after the self-contained top became the only synthesis input.
