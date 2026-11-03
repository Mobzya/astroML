# COV06 calibration freeze — 03.11.2026

**Calibration completed and independently verified; evaluation has not been generated at this checkpoint.** New main namespace`astroml-cov06-main-20261103-v1`,seeds620301/620302/620303,80calibration units perseed=240independent sources. White/Matérn-biased × PSPL/Gaussian × complete=960observed curves;5arms/14400selected mean fits. Main source split assigned jointly before views; no old evaluation records used.

[Protocol](../../research/experiment_06_protocol.md), [config](../../configs/experiment_06.json), [frozen policy](frozen_policy.json), [raw archive](calibration/artifacts.json), [numerical verifier](../checks/cov06_calibration_verifier.json), [independent policy verifier](../checks/cov06_policy_verifier.json), [restore480files](../checks/cov06_calibration_restore.json).

Fitting clean main start`b6af9117ae16506326c9ed880221a1e6d56c0680`; numerical engine unchanged from[007b9d3](https://github.com/Mobzya/astroML/blob/007b9d3c2e7613f2f5f207eb55c15dff923e7bbc/src/microlens/covariance06.py), [runner85f59bc](https://github.com/Mobzya/astroML/blob/85f59bc2db97c744ab2ef74411feaf80a534eafa/scripts/run_covariance06.py). Scientific fingerprint`0052cec5531f3920346e4624b283cad6752b7e57fb5c783f9f65850ef5e5369c`. [Statistics implementation and independent verifier frozen269da73 before evaluation](https://github.com/Mobzya/astroML/tree/269da73/scripts); exact analysis-producer hash is embedded in policy and checked before analysis.

Two fitting invocations:232sources788.100s,remaining8sources27.732s; cumulative815.832s<1800s phase cap,2CPUworkers/1BLASthread. First invocation stops conservatively before900s call limit, not a failure or discarded source. Resume read-only preflight PASS; no completed source refit. NumPy2.5.4/SciPy1.18.1/Python3.12.14,CPUquota2cores,RSS max perworker73664KiB (not aggregate RAM). Ancillary same-task statistical fixture tests ran during calibration; actual wall cost includes quota contention.

Independent reference checks all14400selected densities/KKT/primal/bounds/BIC/score plus15313first/best witnesses and84480initial/end profiled states. Max selected NLL difference2.27e−12; all960method sets valid perarm in this calibration. This is not a global-optimum guarantee. Source priors/analytic PSPL–Gaussian matching/SNR errors, noise pairing, input hashes, source split and numerical nesting verified. Full intermediate main parameter vectors are not archived; full scalar improvement history and bounded witnesses/starts are saved as predeclared.

One empirical global threshold perarm from480dependent complete Gaussian calibration views/240sources. Invalid=−infinity, ascending index455,next float above selected value. Everyarm has24/480calibration negatives selected (5%); this is **not** a population or subgroup FPR guarantee and does not choose a candidate.

| Arm | Frozen threshold |
|---|---:|
| diagonal |2.5787273940060236|
| scale-only |−1.6526096153630474|
| new estimated |−2.6478470345959972|
| original3-start estimated |70.91541487583147|
| privileged oracle |−3.264474012608502|

Policy SHA256`4028b7244b45b96ec3b350bcc9309ae830c66da1cbd3f0b21b0ff196a13c86a0`. Independent weighted-order-statistic implementation recomputed all5limits and counts. Policy must be successfully pushed before any evaluation observation; runner enforces remote policy bytes/source-disjointness/fingerprint/clean new-run checks.

Original calibration archive7,834,835bytes,60immutable LZMA source shards;480raw JSONfiles restored. Calibration all-complete-view extrapolation gives52.89MB for main, slightly above50MiB. Before evaluation, tested lossless solid ZIP(LZMA over an inner ZIP_STORED) on the same calibration bytes:7,068,456bytes,all480files restored byte-identically; conservative complete-view extrapolation47,712,078bytes≈45.5MiB<50MiB. [Storage gate](../checks/cov06_solid_storage_gate.json). Evaluation uses this lossless container only; no observation/model/config/fingerprint/decision change. Existing calibration archive kept. Future checkpoints reuse verified immutable source shards. Actual phase/shard caps remain enforced; projections are not guarantees. Solid restore corruption/path fixtures pass.

39unit tests after storage-helper addition (38full-suite checks plus new specific restore test at freeze); remote CI for earlier b6af911 PASS. Evaluate only after freeze push. Primary remains OU-biased/complete newestimated−scale-only with joint calibration/evaluation source bootstrap,500replicates, recall margin5pp,coverage≥80%; no main result yet.
