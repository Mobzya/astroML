# R2 v1 — controlled peak/random loss: протокол до evaluation

Дата первой фиксации: 02.11.2026. Конфигурация: configs/reconstruction_02.json. Этот новый опыт проверяет известный по историческим отчётам эффект; он не является впервые возникшей confirmatory гипотезой и не восстановлением утраченных массивов.

## Гипотеза и область вывода

На новой controlled population при SNR15 удаление 40% измерений около true peak ухудшает budget-limited различимость PSPL и matched Gaussian сильнее случайного удаления такого же числа точек. **Primary contrast:** AUC_peak40 − AUC_random40; отрицательная разность с парным 95% bootstrap интервалом ниже нуля поддерживает эффект в этой постановке. Все outcomes сохраняются, независимо от знака разности. Вывод о фундаментальной невозможности, новых физических объектах или реальных survey FPR не делается.

Никаких новых ML-моделей в R2: constant/PSPL/Gaussian и один BIC-score. Covariance hypothesis — следующий отдельный опыт после R2.

## Источники, nuisance и независимость

Новый namespace astroml-r2-20261102-v1, три seeds. На seed80 calibration +120 evaluation latent pairs; всего600 пар, из них360 evaluation. В каждой паре PSPL и Gaussian согласованы по baseline, амплитуде, точной excess FWHM, центру, cadence, sigma и одной реализации шума. Времена/параметры/модель sigma как в research/generator_design.md и текущем simulation.py. Для SNR15 sigma_nominal = analytic peak excess /15, с множителями U[.8,1.2]; это не measured telescope SNR.

Complete96 точек; random40 и peak40 по58. Одна пара и все её masked views принадлежат одному split. True t0 используется только для синтетического вмешательства peak40, не для fitting/calibration. Статистическая единица — latent pair; две формы/три маски не являются независимыми источниками. Основная evaluation не генерируется до freeze. Исторический reserved test не используется.

Выбор360 независимых отрицательных evaluation событий на условие даёт ориентировочную standard error около1.15п.п. при FPR5%; это не точная power гарантия. Калибровочных240 негативов достаточно для exploratory target5%, но не для заявлений о строгом1% хвосте или subgroup guarantees. Для primary paired AUC неопределённость измеряется по фактическим данным, не обещается заранее.

## Подгонка и failure policy

Observations(t,flux,sigma), без truth/семейства/маски/SNR в аргументах fit. Текущий diagonal fit:9 deterministic starts, max_nfev600, bounds из inference.py; signal dimensions1/5/4. Это reconstruction defaults, а не якобы исторический optimizer. Протокол и исполняемые source hashes сохраняются.

Счёт `min(BIC_constant,BIC_gaussian) − BIC_pspl`. Primary ranking использует best finite возвращённые fits даже при отсутствии converged start; поэтому это различимость при конечном бюджете, не oracle/global optimum. При исключении или nonfinite result score задаётся −infinity (нижняя tie-группа), status failure сохраняется. Такие источники не удаляются.

Для operational decisions требуем convergence обоих nonlinear fits; иначе reject. Это заранее фиксированное техническое правило, не обученный confidence gate. При валидном fit positive, если score >= frozen threshold, иначе negative. Отказ не считается TP. Если failures превышают20% в условии, эффект нельзя объяснять только потерей информации: отдельно обсуждать ограничения оптимизации, без post-evaluation изменения primary метода.

## Calibration, freeze и evaluation

Один threshold выбирается только по complete calibration Gaussian negatives. Scores невалидных operational fits считаются −infinity. Отсортировать240 score; взять элемент ceil(.95*n)−1 и следующий representable float в сторону +infinity. Так на calibration может быть не более12 FP из240, с учётом ties. Если порог nonfinite, применить явно записанную no-positive policy и не объявлять это полезным детектором.

Threshold применяется без изменения к трём evaluation условиям. Это намеренная проверка переноса; соблюдение5% вне calibration не предполагается. Политику/threshold/source hashes закоммитить в GitHub ДО генерации evaluation. Изменение документации между calibration и evaluation допустимо, научный код/config должны совпадать по fingerprint. После открытия evaluation thresholds/priors/optimizer для primary результата не меняются.

## Метрики и CI

На каждое условие: AUC с ties, n_pairs, FP/negative count (FPR_all), TP/positive count (recall_all), coverage, rejected counts, selective risk, FDR при balanced design и runtime/failure rates. FPR среди принятых negative отдельно от FPR_all. Когда знаменатель0, metric=null, а не0. Brier не вычисляется: BIC-score не probability.

Primary AUC и парная разность:500 bootstrap повторов по pair, стратифицированных по seed; во всех условиях и классах использовать одинаковые sampled IDs. Percentile95% CI, без поправки на secondary comparisons. FPR/recall для одного условия — exact Clopper–Pearson95% по360 исходным negative/positive соответственно, условно на frozen calibration. Pooled dependent views не трактовать биномиально независимыми. Неопределённость самой calibration отдельно оговаривается, OOD гарантия не заявляется.

## Development pilot, ресурсы и остановки

Pilot — отдельный development namespace,12 пар, SNR15,72 views; не более50 независимых sources и15 минут CPU wall-time. Проверить matching/splits, numeric outputs, missing peak optimizer failures, хранение и runtime estimate. Pilot может выявить баг или недоступный бюджет; тогда исправление и новая версия протокола фиксируются ДО evaluation. Нельзя подгонять дизайн к желательному evaluation outcome.

Основной run разбить на batches по10 пар, до4 CPU workers с BLAS/OMP threads=1. Для одного вызова runtime limit900s; при исчерпании сохранять completed batches и возобновлять, не удаляя частичные ошибки. Коммитить компактные raw observations/fit records/manifests/frozen policy и итоговые таблицы в GitHub; если объём превышает разумный Git размер, использовать Release с SHA256. Никаких GPU/платных ресурсов.

## Acceptance и независимая проверка

Проверяющий код должен пересчитать PSPL/Gaussian/constant predictions, χ²/BIC/score из сохранённых observations/parameters; проверить source IDs, counts, masks, split isolation, checksums и metric denominators. Нужны unit fixtures с известным AUC/ties, reject cases, CI при нуле FP и сохранённые failure records. Отчёт включает код/config/threshold SHA, все seeds, runtime и CI. Оригинальные отчёты2–4 остаются REPORTED_ONLY; новый результат маркируется отдельно.
