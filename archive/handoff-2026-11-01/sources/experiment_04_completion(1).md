# Этап 4: итоговая сдача

Этап завершён как исследование. Метод E не выполнил заранее заданное требование
переносимости: это отрицательный научный результат, а не незавершённая разработка.
Нет основания продолжать подбирать порог по уже просмотренной evaluation.

## Что дополнительно доведено до конца

- Независимая сверка итоговых таблиц с сохранёнными решениями, без повторного fit,
  обучения и выбора порогов: `scripts/check_experiment04_completion.py`.
- Проверено 37 072 значения метрик: 320 общих строк, 960 строк по seed, 1296 строк
  по семейству/шуму/условию. Пересчитаны FPR с обоими знаменателями, FDR, coverage,
  recall, selective risk, ROC-AUC, Average Precision, Brier, prevalence-сценарии.
- Пересчитаны все критерии primary E: 3 успешных условия из 9. Расхождений нет.
- Проверены SHA256 всех 14 612 артефактов основного запуска и неизменность исходных
  models/thresholds и reserved source manifest.
- Отрицательный контроль проверяющего кода: намеренно неверный знаменатель FPR
  вызывает ошибку; первичные данные при этом не менялись.
- Подготовлен [автономный PDF](../output/pdf/experiment_04_summary.pdf) с таблицами,
  семью сохранёнными графиками и пояснениями. Редкие FDR показаны с дополнительными
  знаками: округлённое «100,00%» не выдаётся за точную вероятность единица.

Логи и JSON: `reports/checks/experiment04_completion.json`,
`experiment04_completion_negative_control.json`, `stage4_handoff_*.log`.
Полный observation verifier ранее независимо проверил 45 900 рядов и 266 400
предсказаний; новая сверка дополняет его проверкой опубликованных итогов.

## Матрица требований руководителя

| Требование | Фактический результат и расположение |
|---|---|
| Аудит и протокол до основного опыта | `research/audit_04.md`, `experiment_04_protocol.md`; frozen commit 5483c93 |
| Контролируемые negatives и шум | `generator04.py`, main config; новые формы, AR/GP, sigma bias, shared cadence/noise |
| Независимые разделы | 6300 источников, source manifest; train/risk_train/validation/calibration/evaluation |
| Отдельные family/noise/joint shifts | Четыре парные cells, 1200 новых evaluation-источников; final test закрыт |
| A-E и абляции | Восемь методов, frozen models/rules; новый RF, pool, conditional NP и independent risk LR |
| Три показателя ложных тревог | `metrics.csv`; prevalence .5/.01/.001/10⁻⁶ в `prevalence_scenarios.csv` |
| Coverage и отказ | Frozen operational metrics отдельно от диагностического risk80/RC; провалы 80% сохранены |
| Размер и статистика | 3000 calibration sources; 300 cal+eval source bootstrap; seed/family counts и интервалы |
| Primary metrics и критерии | `success_criteria.csv`: E 3/9; ни один метод не выполняет FPR/coverage во всех joint-условиях |
| Механизмы ошибок | Архив 1949 FP-строк / 764 sources, усиленный optimizer check, oracle diagnostics, paired noise controls |
| Воспроизводимость | CPU main 753 с, manifests/versions/seeds/hashes/logs, повторный smoke и resume, полный verifier |
| Итоговые материалы и анализ | Полный отчёт, supervisor report, defense notes с 25 вопросами, 7 графиков, CSV.gz predictions, обновлённая литература |

## Научный итог

На joint-shift B: FPR 2,53%, coverage 88,51%, recall 41,11%.
E: FPR 4,94%, coverage 81,40%, recall 46,31%.
Разность FPR E-B +2,42 п.п., source CI [1,21; 3,17]: E не улучшил надёжность
положительных ответов. При peak40 его coverage 55-59%, при SNR3/random40 FPR 10,40%.

H4.1 не поддержана как operational claim. H4.2 имеет частичную описательную
поддержку, без общего контроля subgroup FPR. H4.3 поддержана узко для ранжирования
candidate errors; лучший средний risk score не гарантирует правильный хвост.
H4.4 не подтверждена в общем виде. Все seeds и отрицательные исходы сохранены.

Локальный diagnostic risk80 gain E на joint не заменяет operational criterion.
Потеря пика действительно уменьшает различающий сигнал; истинная covariance/means
используются только в отдельной диагностике. Невозможность общей задачи не доказана.
Сходимость оптимизатора не означает идентифицируемость физических параметров.

## Что осталось вне этого этапа

Не выполнялись CNN/PINN, GPU-обучение и real-survey validation. Это предусмотренные
границы этапа, не недоделанные обязательные эксперименты. Optional MulensModel
crosscheck пропущен из-за отсутствия библиотеки. Надёжность на настоящих обзорах,
произвольных OOD и FPR 1%/редких хвостах не установлена.

Следующая гипотеза: noise-aware/robust likelihood против diagonal, с новой
независимой evaluation. Руководителю нужно определить стоимость FP/FN/отказа и
доступный лицензированный реальный positive/negative pool. Новые алгоритмы не
объявляются открытием; самостоятельное понимание учеником ещё предстоит проверить.

## Проверка без нового обучения

Из корня репозитория после установки основных зависимостей:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m pytest -q
python -m ruff check src scripts tests
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/check_experiment04_completion.py artifacts/experiment04-main
```

Глубокая проверка наблюдений: `python scripts/verify_experiment04.py artifacts/experiment04-main`.
PDF воспроизводится `python scripts/build_experiment04_pdf.py artifacts/experiment04-main`;
для этого дополнительно нужен ReportLab и DejaVu Sans, не GPU. Основной pipeline
от ReportLab не зависит. Исторические output-директории не использовать для новых
порогов или научного run с другим кодом.
