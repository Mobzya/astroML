# COV development: постановка до вычислительного pilot, 02.11.2026

Это проектирование и development-only проверка вычислительной осуществимости; **не frozen main protocol** и не завершённый Stage5. Никакие новые covariance calibration/evaluation пока не генерируются. R2 evaluation не используется для настройки.

## Проверяемый кандидат

Observation-only совместная подгонка mean + Matérn3/2 covariance. Линейные неотрицательные потоки профилируются через whitened NNLS; остальные mean/noise параметры оцениваются bounded L-BFGS-B. Для каждого competing mean одно noise family:

C = diag((s sigma_report)²) + a² K_Matern32(ell).

D0: C=diag(sigma_report²). D1: известная C_true, только oracle. D2: s/a/ell оцениваются из Observations, без class/noise labels, true t0/SNR или clean means. Все три режима используют одни mean families и начальные mean-приближения. Oracle не практический победитель.

Предварительные bounds: s∈[.5,3]; a/median(sigma_report)∈[1e-4,4]; ell∈[1,120] суток. Mean bounds как R2, в масштабированных координатах. Три deterministic starts, maxiter120 и maxfun2000 на старт; для известных noise constant model решается точно. В D2 нелинейных параметров больше, поэтому отдельно измерить evaluations/runtime; одинаковый cap не означает одинаковую сложность.

Классически marginalize latent GP values, но не интегрировать гиперпараметры. NLL включает logdet; BIC dimensions=signal1/5/4 плюс3 noise в D2, без добавления n latent GP values. Это heuristic score с оговорками о boundary/non-identifiability; калибровка и independent evaluation обязательны.

## Development данные

Новый namespace astroml-cov-development-20261102-v1, seed20261112,4 matched latent pairs, n96,SNR15. White и Matérn3/2 (ell12d, GP amplitude .8 median sigma_true) с sigma_report=.65 sigma_true. В каждой паре классы используют одинаковые времена, sigma и noise draw. Complete/peak40 views; true peak только для генерации маски. Source-level independent count4, остальные views зависимы. Эти же источники не попадут в будущую calibration/evaluation.

## Численные safeguards и критерии pilot

- Gaussian density crosscheck, Matérn symmetry/diagonal/SPD, duplicate times и diagonal limit.
- Для fixed C профилированная NLL не хуже произвольных допустимых linear parameters.
- D2 API отвергает переданную извне privileged covariance; unit fixtures не являются исследовательской evaluation.
- Сохранять все starts/failures, optimizer budget, jitter policy (пока без скрытого jitter), hyperparameter boundaries, actual NLL и timings.
- Pilot CPU≤50 независимых источников,≤900s. Увеличение main sample counts решать по измеренной стоимости и необходимой точности FPR, до новой evaluation. Если текущий алгоритм слишком дорог/неустойчив, сохранить отрицательный feasibility outcome и пересмотреть design на development.

Следующий этап после pilot: окончательные families/noise shifts, source counts, primary operating criteria, calibration uncertainty, mean/optimizer budget и независимый verifier в experiment_05_protocol.md. Не переносить автоматически исторические5%/7.5%/80% требования и не называть один pilot доказательством эффективности.
