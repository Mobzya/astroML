# COV06 fixed robustness design v1 — before main data

03.11.2026. This is a protocol, **not an experiment result**. Inherits [COV06](experiment_06_protocol.md) and its single numerical-development-selected COV06-A. No main observations or policy exist at this freeze. [Configuration](../configs/cov06_stress.json).

## Units, matrix and transfer

Namespace `astroml-cov06-stress-20261103-v1`, seeds630301/630302/630303,80source units each =240independent units. Assign before any views. All six cells and their PSPL/negative partners stay within one source cluster. No source is from COV06 development/main; same underlying physical prior,96times/240days and shared source-level standard-noise draw. Each cell has one PSPL and the specified alternative. Changing SNR changes nominal white error, not the source physical signal. These are controlled **toy** alternatives, not reliable telescope object labels.

| ID | SNR | true kernel / ell days | mask | alternative |
|---|---:|---|---|---|
| S01 |5| OU biased /12 |complete|matched Gaussian bump|
| S02 |5| OU biased /12 |peak40|matched Gaussian bump|
| S03 |15| Matérn3/2 biased /3 |complete|asymmetric positive flare|
| S04 |15| OU biased /40 |random40|double bump|
| S05 |15| white /not applicable |complete|noise-only constant mean|
| S06 |15| Matérn3/2 biased /12 |random40|negative eclipse-like dip|

Correlated a=.8median(full true sigma), reported sigma=.65true sigma; white a0, reported=true. Masks random40/peak40 retain58/96. Kernel covariance is constructed on full cadence before subsetting. True t0 is used only by generator peak mask. S01/S02 provide a paired missingness comparison. Other cells change multiple factors and **do not identify separate causal effects**; no subgroup selected after COV06.

Only diagonal/scale/estimated practical methods, exactly COV06-A parameters/starts/budgets/validity/score. Apply their **same global COV06 calibration thresholds**, immutable policy hash required before stress data. No stress recalibration, per-cell threshold or method choice. No oracle input or stress-driven repair. Old3-start/oracle comparisons remain the main study, reducing stress cost. The matrix is not extended after seeing results.

## Alternative mean definitions and exceptions

PSPL and Gaussian matching use analytic peak excess H and excess FWHM w. Source baseline=1 and center=t0. Existing double bump uses two Gaussian lobes and its analytic outer half-maximum matching rule; it is not a physical binary-lensing simulator.

Flare excess is H exp((t−t0)/tau_r) before t0 and H exp(−(t−t0)/tau_d) after it, with tau_d=4tau_r and tau_r=w/(5log2). Thus analytic peak H,center t0,and total excess FWHM w match, with asymmetric half-widths1:4. It is an idealized discontinuity in derivative at peak, not a radiative flare model.

Eclipse-like mean=1−min(H,.8)exp(−.5((t−t0)/s_g)^2), s_g=w/(2sqrt(2log2)). The cap keeps the noiseless mean positive. It matches center/FWHM but **not sign and, when capped, not absolute peak amplitude**. No EB completeness or label claim.

Noise-only mean=1. It cannot match peak/FWHM by definition. Keep nominal errors/times/noise matched to its PSPL partner. It is a negative control for variable-versus-constant decisions, not evidence for realistic contaminant prevalence.

## Predeclared reporting and reliability flags

Report all6cells×3methods, each with240negative and240positive source-level outcomes: unconditional FPR/recall with exact CP95, coverage/reject fractions, FPR among accepted, selected-fit failures and runtime. AP/raw AUC are descriptive at synthetic prevalence1/2; no probability/Brier claim. Within each cell, sources are independent; across cells/methods they are paired. No pooling17280dependent class/method decisions as independent trials.

Primary stress reliability question: does the unchanged policy exhibit clear gross transfer failure? For every cell/method, flag `high_false_positive_evidence` if **lower CP95 bound for FPR>.10**, `low_recall_evidence` if **upper CP95 bound for recall<.50**, and `low_coverage` if coverage<.80. Flags and thresholds are exploratory fixed diagnostics, not familywise tests or a success theorem. Lack of a flag is not proof of FPR≤10% or adequate power. Report zero detections honestly; rejection cannot convert loss of all positives into a reliable detector. Report all flags, not just best cells. S01/S02 paired ΔFPR/Δrecall use500source-bootstrap replicates stratified by seed, fixed inherited threshold, bootstrap seed630607; descriptive pointwise95% intervals, no selection. At5%/240negatives nominal SE≈1.41pp; zero FP upper CP≈1.53%.

## Mechanical gate BEFORE observations and resource cap

Implement deterministic analytic fixtures before any random stress observations: baseline/center/analytic peak/FWHM and flare1:4half-widths; exact eclipse sign/cap; constant mean; covariance SPD/variance/ell; identical full noise between class partners; correct subset indices/length; deterministic source IDs and disjoint namespaces. Use dense noiseless functions for shape checks, not noisy data-driven estimates. Tests must demonstrate that deliberate wrong flare width/sign/namespace fixtures fail. The pre-main development smoke may instantiate a separate pilot namespace only; this is not the stress240sample.

Full stress=240sources×6cells×2classes=2880curves; three practical methods/three competing means=25920selected fits. Freeze maxiter120/maxfun2000,2CPUworkers/1BLASthread,batches4sources,900s invocation limit between batches,cumulative fit-wall cap3600s across resumes. Estimate from actual pre-main smoke before launching; resource exhaustion preserves PARTIAL_RESOURCE_LIMIT/BLOCKED, not a smaller claimed completed test. Archive cap50MiB/shard8MiB; retain complete observations/selected fits/all starts/failures plus bounded witness/history trace policy from main. Truth remains a separate generator artifact inaccessible to practical inference.

## Acceptance after running

Full240source manifest, all cells, frozen code/policy/config hashes, versions/SHA/clean status, cost, raw Git shards and restore proofs. Independent density/KKT/bounds/scale/selection/input/matching/source checks and independent metric/CP/bootstrap recomputation. No repair from stress evaluation. Main and stress numerical failures/negative findings are publishable outcomes. This task freezes design only; W1-STRESS-RUN remains TODO until actual execution and verifier.
