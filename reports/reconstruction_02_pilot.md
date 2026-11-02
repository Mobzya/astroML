# R2 development pilot — 02.11.2026

Протокол `1d5efb7`, code SHA `fae2d17c8c0c9584b93bc8224da822eb399d0adf`, clean tree, отдельный development namespace. Команда: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_reconstruction02.py --phase pilot --output artifacts/r2-pilot-v1`.

12 независимых latent pairs, 72 views, 216 fit rows. Runtime17.52s на4 workers, peak per-worker RSS51464KiB (не total RSS). Все nonlinear fits имели converged start; это не доказательство глобального минимума. Предварительная экстраполяция600/12×17.52≈876s на весь опыт; фактическая стоимость зависит от новых источников.

Независимый verifier PASS: max absolute difference 2.2737367544323206e-13. Проверены budgets96/58/58, class-matched cadence/sigma, source IDs, scores и сохранённые χ²/BIC. Повторный вызов resume не изменил batch bytes. Negative control изменил BIC и пересчитал checksum файла; verifier всё равно отклонил численную ошибку.

[Архив исходных данных и fits](examples/reconstruction02-pilot-v1.zip), [summary](checks/reconstruction02_pilot_summary.json), [проверка/SHA256](checks/reconstruction02_pilot_verifier.json). Распаковать архив и выполнить `python scripts/verify_reconstruction02.py r2-pilot-v1`.

16 unit tests и Ruff прошли, включая AUC/ties, threshold ties, reject denominators и верхнюю CI при0FP. Статистическая evaluation не генерировалась; quality metrics для выбора метода не использовались. Настройки протокола сохранены без изменений. Следующий шаг:240 calibration pairs, затем commit frozen policy до360 evaluation pairs.
