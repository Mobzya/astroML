# Проверка и восстановление COV05

Источником состояния служит GitHub, а не оставшийся `/workspace`. Сначала прочитайте [STATUS](../../research/STATUS.md) и [очередь](../../research/task_queue.json). DONE-задачи автоматический агент повторно не запускает. Команды ниже — для явной проверки или восстановления checkpoint, а не новый план подбора метода.

## Окружение с нуля

Linux/macOS, Python3.12:

```bash
git clone https://github.com/Mobzya/astroML.git
cd astroML
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
```

Пакеты и версии исходного запуска перечислены в manifest; [hardware](execution_environment.json) и4 workers/1BLASthread — контекст времени, не обещание одинаковой скорости. Проверка данных ниже не выполняет fit и не открывает дополнительные тестовые выборки.

## Восстановить архивы и независимо проверить

Все компактные ZIP находятся в `reports/examples/`. GitHub Releases **asset upload** вернул401; ничего с того endpoint скачивать не требуется. [Индекс](artifacts.json) содержит SHA256 архивов, списки batch files и контрольную сумму общего manifest. Один source со всеми views хранится в одном batch; shards не перекрываются.

```bash
python scripts/restore_covariance05.py --phase calibration --output artifacts/cov05-calibration-restored
python scripts/restore_covariance05.py --phase evaluation --output artifacts/cov05-evaluation-restored
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/verify_covariance05.py artifacts/cov05-calibration-restored --policy reports/covariance05/frozen_policy.json
```

Restore запрещает перезапись существующей папки, проверяет checksum каждого ZIP/файла, не извлекает произвольные paths и не превращает partial в COMPLETE. В текущем Git snapshot смотрите `evaluation_snapshot.status` в индексе. После COMPLETE:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/verify_covariance05.py artifacts/cov05-evaluation-restored --policy reports/covariance05/frozen_policy.json --summary reports/covariance05/evaluation_summary.json
```

Verifier независимо пересчитывает SciPy density/full NLL/BIC, linear KKT, общий noise draw, observed subsets/masks, reported sigma, white oracle control, source split, counts/point metrics/CI и все primary joint-bootstrap draws. Он не доказывает global nonlinear optimum или real-survey validity. [Negative controls](../checks/cov05_verifier_negative_controls.json) проверяют обнаружение намеренной научной порчи при обновлённых SHA256.

## Если checkpoint ещё partial

Убедитесь, что предыдущий fitting process не работает. Сначала восстановите **тот же** сохранённый output, затем при неизменном scientific fingerprint выполните:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_covariance05.py --phase evaluation --output artifacts/cov05-evaluation-restored --policy reports/covariance05/frozen_policy.json
```

900s cap может дать exit75/PARTIAL: повтор команды после фактического окончания процесса продолжает недостающие batches. Completed batches заново не считаются. Если fingerprint отличается, не обходите guard: scientific snapshot зафиксирован commit4a94d440186a34c1a8de4cdc0b76d0f4cd715871 и protocol/config. Установите соответствующий код/окружение; не меняйте fingerprint или policy ради продолжения другого метода. Новая гипотеза требует отдельного namespace/протокола и evaluation.

## Полный повтор вычислений

Fit-код и policy: [freeze commit4a94d44](https://github.com/Mobzya/astroML/tree/4a94d440186a34c1a8de4cdc0b76d0f4cd715871). Calibration code SHA5add9ea; scientific fingerprint совпадает с freeze. На этом историческом snapshot уже есть frozen policy, и run/evaluation запускается в новой output-папке. Не используйте current-main модификации fitter вместо зафиксированного scientific кода. Analysis/verifier/report scripts появились позже и могут проверять сохранённый output отдельно.

При повторе data/parameters/metrics сравниваются с численной точностью зафиксированных библиотек. Runtime/RSS и timestamps меняются, поэтому checksum целого нового run не обязан совпадать с историческим. Нельзя редактировать старые архивы, скрывать failures или менять thresholds по результатам повторной evaluation. Платные ресурсы не нужны и не авторизованы.

## Сборка итогового отчёта из COMPLETE output

Эти команды обрабатывают сохранённые fits, не запускают новый научный опыт. Analyzer сохраняет новый summary и отказывается перезаписывать существующий: при возобновлении уже выполненный шаг пропускается.

```bash
python scripts/analyze_covariance05.py artifacts/cov05-evaluation-restored --policy reports/covariance05/frozen_policy.json --output reports/covariance05/evaluation_summary.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/verify_covariance05.py artifacts/cov05-evaluation-restored --policy reports/covariance05/frozen_policy.json --summary reports/covariance05/evaluation_summary.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/diagnose_covariance05_local_minima.py artifacts/cov05-evaluation-restored --output reports/covariance05/evaluation_local_minima.json
python scripts/report_covariance05.py artifacts/cov05-evaluation-restored
python scripts/plot_covariance05_cases.py artifacts/cov05-evaluation-restored
```

Последние графики — описательная иллюстрация lexicographically first source error каждой категории; правило выбора записано в JSON. Oracle feasible-point diagnostic добавлен после freeze как exploratory контроль, не новый primary endpoint и не truth-based исправление детектора.
