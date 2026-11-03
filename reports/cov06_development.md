# COV06-A development pilot — 03.11.2026

Это новый development-only numerical feasibility run, не calibration/evaluation. Old event-level evaluation закрыта; candidate selection по AUC/FPR не выполнялась.

Scientific code `007b9d3c2e7613f2f5f207eb55c15dff923e7bbc`, clean at start=True. 24 независимых source units,3seeds,192 dependent views,2304 selected mean fit rows. Runtime 219.16s на1worker/1BLASthread, RSS86032KiB. Logical pilot cap900s preserved in tracked ledger.

| Method | Sets | Valid sets | Unavailable means | Nonconverged selected means | Incremental elapsed sum (s) |
|---|---:|---:|---:|---:|---:|
| diagonal | 192 | 189 | 0 | 3 | 48.34 |
| scale | 192 | 189 | 0 | 3 | 0.01 |
| estimated | 192 | 191 | 0 | 1 | 93.35 |
| legacy_estimated | 192 | 192 | 0 | 0 | 68.23 |

Scale/estimated share the observed diagonal initializer; their timers are incremental, not isolated end-to-end cost. Views/classes/masks are not independent repetitions. Convergence/availability here are implementation diagnostics, not classification performance.

**Independent numerical verification still PENDING**: next task W1-OPT-VERIFY must recompute density/KKT/bounds/incumbents/analytic scale/input isolation/corruption controls before numerical correctness or main readiness is claimed.

[Raw shards/checksums](covariance06/development/artifacts.json), [manifest](covariance06/development/run_manifest.json), [summary](covariance06/development/development_summary.json), [design](../research/cov06/optimizer_design.md), [logical budget ledger](../research/cov06/development_manifest.json).
