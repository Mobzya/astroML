# COV06-A numerical verification — 03.11.2026

**W1-OPT-VERIFY PASS только для перечисленных численных проверок.** Это не performance evaluation, не гарантия global optimum и не воспроизведение старого COV05. Closed event-level R2/COV05 data не использовались.

Новый24-source development pilot:3seeds,192 dependent views,2304selected competing mean fits. Independent verifier не импортирует fitters: SciPy Gaussian density/eigendecomposition, собственные mean/covariance formulas, Cholesky KKT/primal bounds, analytic-scale scalar search, source matching/masks/noise/input hashes и incumbent logic.

- Проверены2304selected fits и**57304** saved improvement points. Max|NLL_ref−NLL_saved|=6.65068e−12.
- Selected NLL не хуже лучших saved feasible points с заранее заданнойδ=1e−8max(1,|NLL_best|); maximum observed gap1.1578e−7 остаётся вδ. Raw success/fallback flags не переписывались. Diagonal/scale имеют по3 nonconverged selected fits; estimated1, legacy0. Независимых источников24; views и models зависимы.
- Scale-only совпадает с independent bounded scalar minimizer; GP q0 даёт exact nested scale covariance. Unit suite29tests, включая forced worse converged endpoint, hard evaluation cap, nearzero/zero columns и explicit oracle density/input guard.
-6negative controls: неверный BIC, неверный incumbent certificate, negative coefficient с пересчитанной density, counterfactual flux, oracle flag и SHA архива обнаружены. Для первых5 обновлены байтовые checksums: проверяется научное содержание, не только целостность ZIP.
-48datafiles/24sources восстановлены из6опубликованных Git shards, hashes совпали. Повторный fit для восстановления не нужен.

В отдельно помеченном oracle feasible-point control new estimated missed0/192views, legacy18/192. Это контроль lower bound на численные провалы, а не доказательство отсутствия других minima, не classification metric и не новый practical truth-based алгоритм. Семейства/число starts/q0 и стоимость отличаются от legacy; causal attribution отдельным компонентам не выполнена. Main сравнение с scale-only будет отдельным frozen опытом.

Fit runtime219.16s on1worker/1BLASthread. Два verifier passes48.42s и50.33s, negative controls6.70s и reported unit durations учтены; суммарные измеренные core timers331.36s, conservative logical charge360s с резервом на неохваченные локальные startup/archive/restore затраты. Это не точный end-to-end runtime. Все значения ниже logical900s cap; новых fit attempts не было.

Выбран один заранее описанный candidate COV06-A **по numerical invariants/feasibility/cost**, без AUC/FPR/recall selection. Main/stress datasets и policies ещё не созданы. Следующий gate — протокол COV06, затем stress protocol и отдельный pre-main CPU pilot.

[Полный verifier JSON](checks/cov06_numerical_verifier.json), [negative controls](checks/cov06_negative_controls.json), [29-test log](checks/cov06_verified_unit_tests.txt), [restore](checks/cov06_development_restore.json), [helper provenance](checks/cov06_verification_provenance.json), [raw/checksums](covariance06/development/artifacts.json), [design](../research/cov06/optimizer_design.md), [logical ledger](../research/cov06/development_manifest.json).

Reproduce saved numeric checks (no new fitting): restore index using `scripts/restore_research_shards.py`, then run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/verify_covariance06_development.py <restored-path> --output <new-json>`. Source data must remain development-only. Existing artifacts are not replaced or retuned.
