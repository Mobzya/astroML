# COV06 pre-main runner smoke — 03.11.2026

**VERIFIED numerical/input/resume feasibility; no classification performance claim.** New namespace `astroml-cov06-smoke-20261103-v1`,seeds640301/640302/640303,4sources each:12independent units,216dependent observed curves,5methods/3240selected competing mean fits. Main calibration/evaluation and old event-level evaluation were not opened by this pilot.

Code clean85f59bc before data; resume metadata399f5e1; scientific fingerprint`0052cec5531f3920346e4624b283cad6752b7e57fb5c783f9f65850ef5e5369c` unchanged. Full [provenance/hashes](checks/cov06_pilot_provenance.json), [config](../configs/cov06_pilot.json), [numerical check](checks/cov06_pilot_verifier.json), [controls](checks/cov06_pilot_controls.json).

Two calls on2CPUworkers/1BLASthread: first4sources58.354s,remaining8sources105.677s; total measured fit wall164.031s. Partial data were archived/pushed, moved aside and restored from immutable ZIP. All8previously completed observation/truth file hashes are unchanged after resume; no repeat fitting. Combined fit/validation/archive/unit/restore budget is conservatively charged240s<900 in [persistent ledger](../research/cov06/runner_pilot_ledger.json), not an exact end-to-end stopwatch.

Independent verifier:3240selected full Gaussian NLL/KKT/bounds/BIC/score checks,3427first/best witnesses,19008initial+endpoint states independently profiled with an alternative active-set enumeration. Max selected NLL error2.05e−12. All216method sets perarm valid in this small smoke; this does not establish full-sample convergence. Shared class/noise/mask consistency, independently derived source IDs, disjoint namespaces and observed-input hashes pass. Full main intermediate parameter vectors are intentionally not archived; full scalar improvement history plus first/best witnesses/start states are retained. No global-minimum guarantee.

Eight controls detect wrong BIC/history/start theta/flux/oracle flag/input hash, completed-run restart and foreign owner before fitting.34unit tests pass. Logging-only wrapper on original3-start solver preserves numerical results and exact objective call counts in a deterministic equivalence test; no scientific legacy implementation rewrite.

The first separate start-profiler used unscaled least-squares and dropped a tiny nonzero column. [Failure/correction](checks/cov06_smoke_reference_correction.json) is retained; reference rescaling plus analytic1e−266-column test resolves it. No fitter, data, bounds or policy were changed.

[Complete raw archive](covariance06/pilot/complete/artifacts.json):1,437,632bytes across3lossless LZMA ZIP shards; [restore](checks/cov06_pilot_restore.json)24JSONfiles. Initial4-source DEFLATE extrapolated main storage70.1MB>50MiB. Lossless LZMA leaves identical JSON/float bytes and extrapolates43,128,960bytes≈41.1MiB, within50MiB; actual full-phase caps remain enforced, estimate is not guaranteed. [Resume/storage proof](checks/cov06_pilot_resume_storage.json).

Measured wall extrapolation: evaluation6480/216×164.031≈4921s≈82min on2-core quota; calibration960/216×164.031≈729s≈12min. Both estimates exclude main verifier/archive/policy/checkpoint overhead, depend on finite-start costs and can differ in practice. Keep bounded resumable batches,1800s calibration/7200s evaluation cumulative fit cap and all failures.

Next: generate **calibration only**, independently verify, archive/restore, freeze one empirical global threshold perarm and successfully push code/policy before any evaluation generation. Pilot numerical success is not evidence that correlation estimation beats scale-only.
