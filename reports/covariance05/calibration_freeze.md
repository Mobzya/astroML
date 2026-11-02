# COV05 calibration freeze — 02.11.2026

Clean scientific code:5add9ea5ea16b59fc33706def4afcf3bfef784c5. 240 independent sources,480 dependent negative views per method; runtime285.8227s,4 workers/1 BLAS thread. No COV evaluation generated at freeze.

Thresholds: diagonal6.916426455022731; oracle−3.593344890888772; estimated73.69523337163282. Each24/480 calibration false positives. No method or threshold chosen using evaluation. Oracle remains privileged. Independent density/linear KKT/counterfactual/mask/quantile verifier PASS:8640 fit rows, max NLL difference3.64e−12.

Full policy/source IDs/fingerprint: [frozen_policy.json](frozen_policy.json); raw archive SHA256: [artifacts](artifacts.json). Failed first48-source calibration archived separately, before this clean restart.

Commands:
```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_covariance05.py --phase calibration --output artifacts/cov05-calibration-v1a
python scripts/analyze_covariance05.py artifacts/cov05-calibration-v1a --output reports/covariance05/frozen_policy.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/verify_covariance05.py artifacts/cov05-calibration-v1a --policy reports/covariance05/frozen_policy.json
# Only after this file/policy are committed and pushed:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_covariance05.py --phase evaluation --output artifacts/cov05-evaluation-v1 --policy reports/covariance05/frozen_policy.json
```

Run manifest records exact policy commit/hash. Repeating the final command resumes intact batches with the same scientific fingerprint; it does not regenerate completed batches.

Independent feasible-point diagnostics were added after freeze without changing this policy/fitter. The exact scope and numerical optimizer limitations are reported separately; a converged start is not a certified global optimum.
