# Новый COV05 v1 — протокол до calibration/evaluation, 02.11.2026

Исторический Stage5 остаётся UNVERIFIED. Новый опыт имеет собственный namespace и не продолжает старую evaluation. Development design/pilot зафиксированы отдельно;4 development sources не входят в main. Конфигурация: configs/experiment_05.json. Исполняемый код должен пройти численные/unit проверки и быть закоммичен до данных.

## Гипотеза, primary comparison и достаточный результат

Проверяем, уменьшает ли observation-only estimated covariance ложные тревоги относительно diagonal baseline при новом временном kernel без недопустимой потери recall. **Primary:** Gaussian negatives, OU+sigma bias, complete,SNR15; ΔFPR = estimated−diagonal. Поддержка практической гипотезы требует одновременно: upper95% bootstrap ΔFPR<0; lower95% bootstrap Δrecall≥−0.05; coverage estimated≥0.80. Это исследовательский operating point с допустимой потерей5п.п., не оптимальная политика обсерватории и не гарантия произвольного OOD. Target calibration FPR5% выбран как измеримый exploratory хвост; точность1% не заявляется.

Oracle true covariance — отдельно diagnostic reference, не практический алгоритм. Отрицательный, частичный или неопределённый исход считается полноценным результатом при соблюдении протокола. R2 outcomes не используются для настройки данного метода.

## Данные и interventions

Новый namespace astroml-cov-main-20261102-v1,3 seeds;80 calibration +120 evaluation sources на seed:240/360. Source unit — общая latent PSPL shape/nuisance/noise, не каждый класс/маска. PSPL/negative Gaussian matching как R2; sigma_true задаётся H/15 с общими heteroskedastic множителями. Все исходные96 времени и standard noise draw общие для классов/повторных views; masks complete96/random40/peak40 по58. True t0 используется только генератором маски.

Noise: white с C_true=diag(sigma_true²), report=true; Matérn3/2 и OU с ell12d, GP amplitude=.8 median(sigma_true), C_true=diag(sigma_true²)+GP covariance, report=.65 sigma_true. OU kernel exp(−|dt|/12) отсутствует в practical noise family. Одна стандартная Gaussian vector на source преобразуется соответствующим Cholesky; классы в каждом noise case получают одинаковую реализацию.

Calibration содержит только Gaussian negatives/PSPL, white+Matérn, complete. Evaluation: все3 noise,3 masks и PSPL/Gaussian/новый double_bump. Double bump имеет одинаковые baseline/peak excess/outer FWHM и envelope center: сумма равновесных Gaussian с центрами±2 в единицах ширины; peak и outer half-width определяются численно и масштабируются к PSPL. Максимумы double bump не совпадают с центром envelope — это явно иной signal family. Семантика negative: toy non-PSPL, не перечень всех реальных переменных.

## Методы, знания и optimizer

Одинаковые constant/PSPL/Gaussian mean families во всех режимах, без double-bump fit. D0 diagonal report covariance; D1 fixed true covariance с явной oracle пометкой; D2 joint estimate `C=diag((s sigma_report)²)+a² K_Matern32(ell)` по Observations. Нельзя передавать D2 hidden class/noise labels, true SNR/t0/covariance/clean means.

Профилирование linear nonnegative coefficients через whitened NNLS; bounded L-BFGS-B по scaled nonlinear means/noise. Mean bounds и3 starts указаны в covariance_development_design.md и covariance.py. Noise bounds s[.5,3], a/median(report_sigma)[1e-4,4], ell[1,120]d,3 starts. maxiter120/maxfun2000 на старт. Fixed-noise constant решается точно; остальные режимы имеют одинаковый cap на start, но неодинаковое число параметров/стоимость — runtime/nfev публикуются. Никакого скрытого jitter; SPD/numerical failures сохраняются.

Full Gaussian NLL включает quadratic/logdet/normalization через Cholesky. GP latent values интегрированы; гиперпараметры оптимизированы, не маргинализированы. BIC k=signal1/5/4 плюс3 noise в D2. Вблизи amplitude floor/неидентифицируемого ell это heuristic, не calibrated evidence. Выбирается лучший converged start; при отсутствии — лучший finite iterate с fail flag. При полном failure score=−infinity. Operational acceptance требует convergence всех3 means; иначе reject. Raw score AUC диагностическая, с budget-limited failures без удаления источников.

## Calibration и freeze

Для каждого метода один global threshold по Gaussian complete calibration negatives, white/Matérn pooled:480 зависимых views из240 независимых sources. Невалидные scores=−infinity. Порядковая точка ceil(.95*n)−1 и следующий float выше неё; ties conservative. Nonfinite threshold → явная no-positive policy. Это empirical target, не NP distribution-free гарантия.

Policy, source IDs/hashes и scientific code/config/protocol fingerprint отправить в GitHub до генерации новой evaluation. Один threshold на метод применяется ко всем noise/family/mask cases без скрытого label-conditioned выбора. Изменять scientific method после открытия evaluation запрещено. Незначимые documentation/independent verifier corrections не меняют detector, но фиксируются.

## Метрики, неопределённость и множества сравнений

Каждый scenario/method: FPR_all, recall_all, coverage, FPR_accepted_negative, selective risk, AUC, reject/failure counts, balanced FDR, runtime/condition numbers/noise-bound diagnostics. Нулевой знаменатель=null. Brier не вычисляется без probability model.

Primary95% percentile CI:500 source-bootstrap повторов, стратификация по seed, отдельно resample calibration и evaluation; одна и та же выборка source IDs используется для всех методов. Calibration bootstrap сохраняет white/Matérn views вместе и заново считает threshold; evaluation bootstrap сохраняет все counterfactual views/classes вместе. Так учитывается finite calibration variation. Для primary ΔFPR/Δrecall сохраняются все draws и independent recomputation. Дополнительно conditional Clopper–Pearson95% в каждом отдельном negative/positive scenario по360 sources. Не применять binomial к pooled dependent views.

Sample size: при FPR5% nominal standard error для360 independent negatives около1.15п.п.; это не гарантия мощности paired test.240 calibration sources/480 views нельзя трактовать как480 независимых. Secondary mask/noise/family comparisons описательные, pointwise, без claim simultaneous control. Нельзя выбирать лучший subgroup/seed вместо primary результата.

## Ресурсы, проверка и завершение

Development pilot4 sources/96 method sets/288 fits занял14.80s на1 core, numerical verifier PASS. Экстраполяция стоимости — предварительная. Main до4 CPU workers, BLAS/OMP=1; batches8 sources,900s на вызов с сохранением завершённых batches и resume. Если бюджет/численная ошибка делает опыт невыполнимым, сохранить partial и блокировку, не фабриковать завершение. Платные ресурсы/GPU не используются.

Нужны raw observations/fits/генераторная truth отдельно, manifest/code/config/threshold hashes, все seeds/failures; numerical verifier пересчитывает full NLL/BIC по SciPy, linear KKT и oracle/diagonal white control, split/metric denominators и primary bootstrap. Истинная covariance допускается только в oracle-ветви и отдельной диагностике. До final interpretation все эти артефакты сохраняются в GitHub (компактные ZIP или Releases с SHA256).
