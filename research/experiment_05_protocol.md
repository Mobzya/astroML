# Новый опыт по ковариации — DRAFT, не разрешение основного запуска

Статус: проект протокола. Исторический Stage5 не воспроизведён. Этот файл нельзя считать заранее зафиксированным полным протоколом, пока не заполнены численные параметры и не создан freeze commit.

## Гипотеза

Практическая оценка временной корреляции по наблюдениям уменьшает ложные тревоги относительно diagonal likelihood в части режимов; при коротких рядах или пропуске пика её ошибка может поглотить выгоду.

## Минимальное сравнение

D0: diag(sigma_report²). D1: C_true генератора только как oracle-диагностика. D2: общая для всех конкурирующих средних семейство C = diag((s*sigma_report)²) + a² K_Matern32(ell), с параметрами s, a, ell из наблюдений. Полная likelihood включает logdet, Cholesky и одинаковую политику numerical failure. Это выбранный кандидат нового опыта, не описание утраченного генератора.

Constant, PSPL и Gaussian используют одинаковую модель ошибок и сопоставимый бюджет. При BIC учитываются все оцениваемые параметры шума и сигнала; нерегулярная асимптотика BIC явно обсуждается. Нельзя выбирать ядро по скрытым noise labels.

## Данные и оценивание

Новый namespace; train/validation/calibration/evaluation по latent pair/source, все views вместе. Matched nuisance для классов; complete/random40/peak40; знакомый и новый шум, новые отрицательные семейства. True t0 разрешён только генератору маски. Calibration выбирает thresholds; evaluation открывается после freeze.

Основной контраст D2−D0: FPR_all с CI, recall_all и coverage; дополнительно FPR_accepted, selective risk, runtime, ошибки оптимизации и диагностика GP absorption. Oracle отдельно. Brier только при наличии честного probability calibrator.

Bootstrap по source/pair, биномиальные верхние границы для независимых отрицательных событий в отдельном условии; не применять обычный binomial к зависимым pooled views. Нулевые FP не означают нулевой истинный FPR.

## Обязательные решения перед freeze

1. Полная литературная проверка likelihood и ближайших аналогов.
2. Генераторы, kernel mismatch, численные bounds и starts, правила failures.
3. Pilot на development: runtime/conditioning; evaluation недоступна.
4. Source counts из расчёта точности FPR/мощности; обоснование целевых FPR/coverage и допустимого recall loss. Исторические 5%/7.5%/80% не переносить автоматически.
5. Точные seeds, manifests, primary/subgroup comparisons, CI, threshold rule и stop budget.
6. Unit tests, negative controls, commit протокола и замороженная calibration.

Выход: predictions, failure table, calibration/threshold hashes, source manifest, per-group CI, рисунки, verifier и отчёт. Отрицательный или неопределённый исход считается завершённым опытом при соблюдении протокола.
