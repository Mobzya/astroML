---
name: research-integrity
description: Design leak-free, statistically defensible machine-learning experiments and audit results, metrics and plots for a scientific competition project.
---

Use whenever choosing data, splits, baselines, uncertainty, thresholds, comparisons, conclusions or publication figures.

1. List the scientific hypothesis and null comparator before a new experiment; freeze primary metrics and evaluation scenarios before seeing final test.
2. Split by underlying event/source first. Augmented, perturbed or differently sampled realizations of one source stay together. Test the split mechanically.
3. Define both positive PSPL-like events and realistic negatives (noise-only, variable stars, flares, eclipse, systematics); RMDC26's microlensing subtype labels are not negative examples.
4. For rare events report recall at predeclared fixed FPR, PR-AUC and calibrated uncertainty; choose all thresholds only on validation data.
5. Bootstrap at independent event level; report multiple seeds, sample sizes, CI and failure cases. Never bootstrap individual observations within one curve as if independent events.
6. Control experimental fairness: same sources, observation budget, training budget where meaningful and locked hardware/time cost.
7. Ablate each proposed component and compare to a simple fixed ensemble / calibrated logistic stacker, not only weak baselines.
8. Save exact run manifest: commit, config, seed, package versions, data hashes, model hash, outputs, runtime.
9. Do not invent performance figures. Explicitly distinguish simulations, external synthetic test and true telescope data.
10. If all novel candidates fail, faithfully conclude limitations and consider changing research question; never cherry-pick seeds or leak test data.
