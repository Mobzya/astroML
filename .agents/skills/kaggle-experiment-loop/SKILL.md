---
name: kaggle-experiment-loop
description: Package CPU-tested AstroML experiments into Kaggle scripts or notebooks, safely submit allowed GPU runs with Kaggle CLI, retrieve logs and model artifacts, and maintain reproducible experiment manifests.
---

Use for Kaggle kernel/CLI/cloud compute orchestration and Colab fallback planning.

1. Read official Kaggle CLI docs (https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md) and local `kaggle kernels --help`, since CLI flags evolve.
2. Check authentication availability without exposing tokens. If not authenticated or network disabled, provide manual owner-only commands and mark blocked. Never paste credentials into files/Git/logs.
3. Preflight: `pytest`, small CPU sample train and eval, serialization, dataset paths, dependency versions, GPU CUDA check, estimated runtime, quota (`kaggle quota`).
4. Generate correct `kernel-metadata.json` from `kaggle kernels init -p kaggle/experiment` before editing, specify script or notebook, and required public/private inputs with permission. Use an approved, available accelerator; do not assume every listed accelerator is in user's quota.
5. Owner-approved submit: `kaggle kernels push -p kaggle/experiment --accelerator NvidiaTeslaT4` (if available). Poll boundedly with `kaggle kernels status OWNER/SLUG`, inspect `kaggle kernels logs OWNER/SLUG`, retrieve `kaggle kernels output OWNER/SLUG -p artifacts/...`.
6. Save results and checkpoints into `/kaggle/working/`; include a manifest with commit, config hash, data checksum, seed, timing, framework versions and the Kaggle kernel version identifier.
7. Jobs can fail/queue/timeout; do not report success before logs and expected artifact validation. Protect GPU quota with approved budgets.
8. Provide a single source-code training command shared by Kaggle and Colab. Colab is interactive fallback; do not automate anti-idle, bypass restrictions, or promise always-on headless GPU.
9. Stop after predeclared budget or documented blocker. Report exact commands, returned status and artifacts.
