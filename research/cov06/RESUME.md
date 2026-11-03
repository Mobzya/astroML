# COV06: restore/resume without relying on workspace or venv

This is an operational guide, not evidence that another run completed. Active task and exact completed count come from `task_queue.json` and `reports/covariance06/evaluation_manifest.json`; baseline DONE never reopened. Same chat, no second runner/subagents.

1. Find checkout by `https://github.com/Mobzya/astroML`,fetch main and preserve user changes. Read AGENTS/autonomous/week/status/queue/session/log. Check previous processes and foreign lease. Unresolved liveness→BLOCKED_SESSION_LIVENESS; expiry/null history is insufficient. Acquire a **new unique** owner/lease for the existing W1-COV06-EVAL and commit+push before work; don't reuse a former session owner. Push rejection→fetch/recheck ownership.
2. Restore Python3.12.14 and locked NumPy2.5.4/SciPy1.18.1. A missing `.venv` is expected; create/install using `requirements-lock.txt`,then editable project with `--no-deps`. Do not silently resume under other versions. No paid compute/auth changes.
3. Read `reports/covariance06/artifacts.json`: calibration index + latest evaluation checkpoint index, with hashes. If raw run folder is absent, restore only the **latest** evaluation checkpoint (not every index):

```bash
.venv/bin/python scripts/restore_research_shards.py \
  --index <latest_evaluation_index_from_artifacts.json> \
  --output artifacts/cov06-evaluation-v1 --allow-partial
```

The index references immutable checked source shards. `solid-zip-v1` is a lossless outer LZMA ZIP containing an uncompressed inner ZIP; loader supports old per-file ZIPs too and rejects checksum/path/duplicate errors. Every restored JSON byte matches manifest. Receipt files are ephemeral: runner reconstructs receipts for manifest-authorized **completed** sources and skips them. Never delete/archive an unreceipted partial local source to hide unfinished work; investigate and retain its cumulative budget.

4. After owner checkpoint push, read-only preflight:

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
.venv/bin/python scripts/preflight_covariance06_resume.py \
  artifacts/cov06-evaluation-v1 --owner <new_unique_owner>
```

Verify scientific fingerprint`0052cec5531f3920346e4624b283cad6752b7e57fb5c783f9f65850ef5e5369c`,policy SHA256`4028b7244b45b96ec3b350bcc9309ae830c66da1cbd3f0b21b0ff196a13c86a0`. Policy was pushed in[44ec73e](https://github.com/Mobzya/astroML/commit/44ec73ee8aa2804eb5a7628fd99fd67a2e0326aa) before first evaluation. Keep candidate/config/policy/statistical producer unchanged. All main source IDs were assigned before views; calibration/evaluation disjoint.

5. Resume bounded call; do not request calibration or a new output folder:

```bash
.venv/bin/python scripts/run_covariance06.py --phase evaluation \
  --output artifacts/cov06-evaluation-v1 --owner <new_unique_owner>
```

2CPUworkers/1BLASthread,4source batches.900s call admission checked conservatively;7200s cumulative fit-wall across calls. Completed batches never refit. Use `--max-batches N` to finish before end of session, with measured preceding batch cost. Persistent `research/cov06/runner_evaluation_ledger.json` is not reset. Unclosed invocation/runtime/liveness→investigate/BLOCKED, not a new namespace. Record actual overshoot/interruption rather than shrinking sample. Primary scientific sample remains360units/6480curves, not partialN or dependent views.

6. After call closes, save numerical/source checks, immutable shards/index and restore proof. Partial checker needs`--allow-partial`; no interim classifier-based method/subgroup selection. Reuse shard root`reports/covariance06/evaluation-shards` and label`cov06-evaluation-v1`; new index destination must not exist. Maintain artifact pointers/STATUS/queue/log/dated report,commit+push and check remote SHA. At session end release only own lease, leave unfinished task IN_PROGRESS and week automation enabled.

7. Only after all360units exist: mark output task DONE after raw restore/hash/source/code continuity, then W1-COV06-VERIFY. Run frozen `covariance06_statistics.py` and independent `verify_covariance06_statistics.py`; all180tables/500calibration-aware joint source-bootstrap draws must be verified. Producer SHA is locked in policy; BIC is not probability,oracle not practical,negative result acceptable. No detector repair/retest on the same evaluation. Keep old R2/COV05 event-level/reserved final test closed.

Then next ready tasks: frozen stress, external audit, new synthesis; W1-HANDOFF only on week trigger, not because this small checkpoint ended. Other automations unchanged.

## Liveness note from second session03.11

On resume, raw manifest `status` can retain the preceding `PARTIAL_CHECKPOINT` while the next invocation is actually running. Do not infer liveness from that field. The fitting PID/process start, fresh owner lease, `runner_evaluation_ledger.json` invocation_in_progress flag and actual process-pool completion must agree. Preflight and checkpoint helper require a closed invocation and null fitting PID; no second runner is authorized by a stale manifest status. Frozen scientific runner is unchanged.
