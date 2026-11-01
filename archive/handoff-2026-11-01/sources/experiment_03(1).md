# Эксперимент 03 — калибровка и надёжность физического детектора

23.10.2026. Run `experiment03-main`. Итог: **A — локальное улучшение надёжности при сопоставимом coverage**. Область вывода — описанная
синтетическая задача; перенос на реальные обзоры и неизвестные семейства отдельно ограничен.

## 1. Постановка и предварительная регистрация

Проверяем, помогают ли observation-only характеристики ряда и физической подгонки
оценивать надёжность, уменьшать сдвиг FPR и отказываться от ненадёжных решений.
Не ставим задачу восстановления информации, которой нет среди наблюдений.
H3.1 — улучшение Brier/надёжности против одномерного BIC; H3.2 — меньшая
неоднородность achieved FPR; H3.3 — меньший риск при одинаковом coverage;
H3.4 — связь ухудшения с остатком различающего сигнала. Протокол
`research/experiment_03_protocol.md`, замороженный в 107079e до main. Это новый
development evaluation, не финальная независимая астрономическая проверка.

## 2. Независимый аудит этапа 2

Код PSPL/фотометрии, WLS, bounds/starts, likelihood/BIC, source splitting, парные
маски и Gaussian negatives проверены. Повторный verifier восстановил 15 600
χ²/BIC/score, максимальная разница 1.14e-13. AUC .975995 random40 и .586358
peak40 совпали с отчётом. Истинные параметры не передаются fitting.
Не найдено численного исправления PSPL, которое заменило бы прежние результаты.
Новая проверка known-means: при SNR15 median d complete/random40/peak40 =
6.015/4.805/.687; средняя ошибка oracle=.0040/.0177/.2966. PSPL null
noncentrality median=1153.86/699.87/.2833. Потеря сигнала существенна.
Oracle знает nuisance конкретной пары; это не composite Bayes error и не
обычный детектор. Подробности/таблица: `research/audit_03.md`,
`artifacts/experiment03-audit02/`. Старые данные не заменены.

## 3. Данные и независимость

Новый RNG namespace3003, SeedSequence(namespace,seed,index); seeds2027/2028/2029.
На seed100 train pairs,40 validation,100 calibration,120 evaluation,40 stress.
Всего 1200 latent pairs: train300,validation120,calibration300,evaluation360,stress120.
Внутри пары два контрфактических класса с одинаковыми nuisance; они зависимы.
Все noise/SNR/mask версии остаются в одном разделе. Source=event в этой симуляции;
это не идентичность реальных звёзд. Ranges и автоматическая проверка есть в manifest.
Stage2 namespace2002/2003 не используется для обучения; reserved stage1 test
не материализован. Модели заморожены перед calibration, пороги — перед evaluation.

PSPL priors: t0∼U[60,180] дней,u0∼U[.15,1],log tE∼U[log8,log35],
Fs∼U[.3,.9],Fb=1−Fs. Gaussian имеет baseline1, ту же continuous amplitude,
центр и точную FWHM. 96 jittered-stratified visits за 240 дней. sigma=amplitude/SNR
×exp(N(0,.15²)), не зависит от формы класса; общий z∼N(0,1), шум=sigma*z.
Маски удаляют ровно floor(n*f) точек: случайную permutation либо ближайшие
к true t0. Truth задаёт только вмешательство, не inference. В пересечении масок
наблюдения совпадают, random/peak имеют одинаковое n. SNR меняет sigma при общем z.

ID: SNR5/15/50 × complete/random25/peak25 —9 условий. OOD: SNR15 random40/peak40;
SNR3 complete/random40/peak40. Evaluation10080 рядов; repetitions не увеличивают
число независимых источников сверх 360. Дополнительный stress120 новых пар, три
условия SNR15 complete/random40/peak40, PSPL и два новых negative семейства.

## 4. Физические модели и признаки

$$u(t)=\sqrt{u_0^2+((t-t_0)/t_E)^2},\quad A(u)=\frac{u^2+2}{u\sqrt{u^2+4}},\quad F=F_sA+F_b.$$

Constant(k=1), PSPL(k=5), Gaussian background+amplitude·exp[−(t−center)²/(2width²)](k=4).
Одна known-sigma Gaussian likelihood, χ²=Σ[(F−model)/sigma]²,
BIC=χ²+Σlog(2πsigma²)+klog n. Score=min(BICconstant,BICgaussian)−BICpspl.
Он не вероятность и не доказательство физического происхождения. Fs/Fb и Gaussian
linear coefficients≥0;u0∈[.01,3],duration∈[span/1000,3span],center∈[first−span,last+span].
6 observation-derived starts, max_nfev100, analytic variable projection Jacobian.
Незавершённый старт может дать лучший χ²; failures сохраняются и не исключаются.

49 признаков: time10 (n/span/gaps, gap у fitted t0 и extrapolation), observation4
(visible SNR, excess, variability, skew), physics18 (BIC/χ²/residuals/fitted shape),
optimization17 (failures/bounds/near-best spread, center instability, local singular values).
Полный список в verification.json. API extract_features(Observation,fits), explicit
whitelist; label/scenario/family/IDs/true t0/true SNR/parameters запрещены.
Fitted peak может быть неустойчив: near-best center spread и extrapolation это отражают.
Локальная кривизна — proxy, не полноценный profile likelihood/доверительный интервал.
Дорогие полные profiles per curve не пересчитывались; stage2 profiles остаются
контекстом, но не признаками новых моделей. Это ограничение текущего набора признаков.

## 5. Известные алгоритмы и заморозка

A — raw BIC, один порог/seed по calibration ID mixture. B — StandardScaler+LR(score),
train labels учат сигмоиду, validation выбирает C. C — те же p/ranking B, но четыре
порога по observed SNR выше train median и maxgap/span>.1; calibration quantile
в каждом bin, fallback к общему при<30 независимых groups. D — LR49 features;
E — RF тех же features. LR C=.1/1/10, RF leaf5/20,160 trees,depth8,max_features.7.
Все настройки выбирались только на validation Brier; evaluation ничего не выбирает.
Нет дообучения на calibration. LR и RF стандартные sklearn алгоритмы, не новый метод.

F — confidence=p для положительного решения, иначе 1−p; отказ ниже calibration
quantile.2 (target coverage80%). Это вероятность именно принятого решения при
FPR threshold, который обычно не равен .5. Для A confidence заимствован у B;
A не имеет собственной вероятности/Brier. Политика отказа одинакова у сравнений.
C не меняет Brier/ROC B. Fixed80 risk использует только confidence для ранжирования;
это diagnostic curve, operational cutoff остаётся выбранным на calibration.

Validation-selected full-feature method: **E_forest**. Не выбран лучший seed.

| Seed | B C | D C | E leaf | B validation Brier | D validation Brier | E validation Brier |
|---|---|---|---|---|---|---|
| 2027 | 10 | 10 | 5 | 0.1434 | 0.1257 | 0.1182 |
| 2028 | 10 | 10 | 20 | 0.1346 | 0.1150 | 0.1126 |
| 2029 | 10 | 10 | 20 | 0.1367 | 0.1239 | 0.1173 |


## 6. Метрики, CI и первичные результаты

300 paired bootstrap, source resampling внутри seed: оба класса и все views
переносятся вместе. Calibration ресэмплируется независимо, её пороги/acceptance
cutoff пересчитываются; модели/quality cuts фиксированы. CI не включают полную
training/model-selection uncertainty. Pointwise exploratory95%, без поправки
за многочисленные сравнения. Probability prevalence=.5; AP/precision не
переносятся на редкость реальных событий. Mixture равновзвешена по условиям.
Brier оценивает probability quality, не только calibration component.

| Subset | Method | AUC95%CI | AP95%CI | Brier95%CI | FPR%95%CI | Recall%95%CI |
|---|---|---|---|---|---|---|
| ID_mixture | A_BIC | 0.892 [0.885; 0.899] | 0.909 [0.903; 0.914] | — | 4.4 [2.6; 6.0] | 61.0 [58.4; 64.0] |
| ID_mixture | B_score_logistic | 0.892 [0.885; 0.898] | 0.908 [0.903; 0.913] | 0.134 [0.130; 0.137] | 4.4 [2.6; 6.0] | 61.0 [58.4; 64.0] |
| ID_mixture | C_quality_bins | 0.892 [0.885; 0.898] | 0.908 [0.903; 0.913] | 0.134 [0.130; 0.137] | 4.7 [3.4; 6.5] | 60.5 [57.9; 64.0] |
| ID_mixture | D_logistic | 0.915 [0.909; 0.921] | 0.922 [0.916; 0.928] | 0.118 [0.114; 0.123] | 3.9 [2.6; 6.1] | 62.6 [59.1; 66.5] |
| ID_mixture | E_forest | 0.922 [0.916; 0.928] | 0.930 [0.924; 0.935] | 0.112 [0.108; 0.116] | 4.1 [2.7; 6.4] | 65.5 [61.8; 70.0] |
| ID_mixture | E_score_only | 0.887 [0.879; 0.894] | 0.903 [0.897; 0.909] | 0.133 [0.128; 0.138] | 4.4 [2.8; 6.4] | 61.2 [57.0; 63.8] |
| ID_mixture | E_no_time | 0.921 [0.915; 0.927] | 0.928 [0.922; 0.934] | 0.113 [0.109; 0.117] | 4.4 [3.0; 6.1] | 65.4 [61.2; 68.8] |
| ID_mixture | E_no_optimization | 0.922 [0.915; 0.928] | 0.929 [0.923; 0.935] | 0.112 [0.108; 0.116] | 3.9 [2.6; 6.0] | 65.6 [61.4; 69.4] |
| ID_mixture | E_no_physics | 0.900 [0.893; 0.906] | 0.910 [0.904; 0.916] | 0.128 [0.124; 0.132] | 4.0 [2.9; 5.3] | 60.0 [56.6; 63.2] |
| OOD_mixture | A_BIC | 0.671 [0.663; 0.680] | 0.715 [0.707; 0.724] | — | 7.7 [5.4; 10.8] | 31.9 [27.4; 35.9] |
| OOD_mixture | B_score_logistic | 0.671 [0.663; 0.679] | 0.715 [0.707; 0.724] | 0.229 [0.226; 0.232] | 7.7 [5.4; 10.8] | 31.9 [27.4; 35.9] |
| OOD_mixture | C_quality_bins | 0.671 [0.663; 0.679] | 0.715 [0.707; 0.724] | 0.229 [0.226; 0.232] | 4.7 [3.3; 7.1] | 25.1 [23.1; 28.8] |
| OOD_mixture | D_logistic | 0.710 [0.700; 0.721] | 0.727 [0.713; 0.741] | 0.217 [0.212; 0.221] | 8.0 [6.0; 12.2] | 32.7 [29.1; 38.6] |
| OOD_mixture | E_forest | 0.717 [0.707; 0.726] | 0.738 [0.729; 0.747] | 0.210 [0.207; 0.214] | 10.8 [6.9; 16.8] | 37.8 [32.6; 44.1] |
| OOD_mixture | E_score_only | 0.665 [0.655; 0.676] | 0.704 [0.694; 0.713] | 0.230 [0.226; 0.234] | 8.9 [5.7; 12.5] | 31.8 [27.1; 36.0] |
| OOD_mixture | E_no_time | 0.710 [0.702; 0.719] | 0.732 [0.723; 0.741] | 0.217 [0.214; 0.221] | 18.3 [12.2; 23.2] | 45.8 [38.4; 50.9] |
| OOD_mixture | E_no_optimization | 0.713 [0.704; 0.722] | 0.736 [0.727; 0.746] | 0.211 [0.207; 0.215] | 9.7 [6.2; 16.1] | 36.6 [30.8; 43.4] |
| OOD_mixture | E_no_physics | 0.681 [0.671; 0.693] | 0.707 [0.697; 0.718] | 0.220 [0.216; 0.223] | 7.1 [5.1; 11.8] | 28.7 [23.8; 34.1] |


Предзаданные парные контрасты (отрицательное значение благоприятно):

| Comparison | Estimate95%CI |
|---|---|
| H31_brier_D_minus_B | -0.0158 [-0.0188; -0.0127] |
| H31_brier_E_minus_B | -0.0219 [-0.0244; -0.0190] |
| H32_FPR_MAD_C_minus_A | -0.0198 [-0.0265; -0.0049] |
| H33_risk80_E_minus_B | -0.0285 [-0.0359; -0.0196] |


H3.1 поддерживается на ID по этому критерию; H3.2 поддерживается на ID по MAD; H3.3 поддерживается для E против B на ID при coverage80%.
Это локальные экспериментальные поддержки, не доказанные универсальные гипотезы.
H3.4 анализируется отдельно по known-means diagnostic ниже.


## 7. Фактический FPR по условиям

Target5% — процедура на calibration, не обещание achieved FPR=5% в каждой строке.
100cal pairs/seed и 9 зависимых views нельзя считать 900 независимыми negatives.

| Condition | Method | AUC95%CI | FPR%95%CI | Recall%95%CI |
|---|---|---|---|---|
| snr15_complete0 | A_BIC | 0.997 [0.995; 0.999] | 1.9 [0.6; 3.6] | 98.1 [95.6; 99.2] |
| snr15_complete0 | C_quality_bins | 0.997 [0.995; 0.999] | 1.4 [0.3; 3.3] | 97.2 [95.7; 98.9] |
| snr15_complete0 | D_logistic | 0.997 [0.995; 0.999] | 0.8 [0.0; 1.9] | 91.9 [88.3; 95.0] |
| snr15_complete0 | E_forest | 0.996 [0.992; 0.999] | 1.9 [0.6; 3.3] | 96.4 [93.3; 98.3] |
| snr15_peak0.25 | A_BIC | 0.665 [0.635; 0.694] | 1.7 [0.6; 4.2] | 10.6 [6.1; 15.0] |
| snr15_peak0.25 | C_quality_bins | 0.665 [0.635; 0.694] | 6.9 [3.6; 10.8] | 27.8 [19.2; 38.6] |
| snr15_peak0.25 | D_logistic | 0.706 [0.679; 0.736] | 7.8 [4.6; 12.9] | 36.9 [30.7; 44.3] |
| snr15_peak0.25 | E_forest | 0.707 [0.675; 0.739] | 4.2 [1.7; 7.8] | 33.3 [25.8; 41.8] |
| snr15_peak0.4 | A_BIC | 0.567 [0.544; 0.590] | 0.3 [0.0; 1.4] | 1.9 [0.3; 4.6] |
| snr15_peak0.4 | C_quality_bins | 0.566 [0.544; 0.589] | 5.6 [2.2; 8.9] | 14.4 [9.2; 20.1] |
| snr15_peak0.4 | D_logistic | 0.583 [0.557; 0.614] | 6.4 [3.3; 10.3] | 21.1 [16.7; 27.5] |
| snr15_peak0.4 | E_forest | 0.598 [0.572; 0.628] | 1.4 [0.6; 4.3] | 11.9 [8.9; 18.1] |
| snr15_random0.25 | A_BIC | 0.991 [0.986; 0.995] | 5.0 [2.5; 7.2] | 94.7 [92.2; 96.9] |
| snr15_random0.25 | C_quality_bins | 0.991 [0.986; 0.995] | 5.3 [2.8; 8.1] | 94.4 [92.2; 96.7] |
| snr15_random0.25 | D_logistic | 0.991 [0.986; 0.995] | 0.6 [0.0; 1.7] | 85.6 [80.4; 89.2] |
| snr15_random0.25 | E_forest | 0.989 [0.982; 0.994] | 2.5 [1.1; 5.0] | 93.9 [90.1; 96.4] |
| snr15_random0.4 | A_BIC | 0.977 [0.968; 0.984] | 7.8 [5.0; 11.4] | 90.8 [85.6; 93.3] |
| snr15_random0.4 | C_quality_bins | 0.977 [0.968; 0.984] | 7.2 [4.7; 11.5] | 91.4 [87.1; 94.4] |
| snr15_random0.4 | D_logistic | 0.977 [0.969; 0.983] | 2.8 [1.1; 4.9] | 80.6 [76.5; 85.0] |
| snr15_random0.4 | E_forest | 0.976 [0.966; 0.983] | 6.7 [3.3; 8.9] | 88.9 [84.7; 91.1] |
| snr3_complete0 | A_BIC | 0.685 [0.667; 0.705] | 11.9 [8.1; 18.1] | 34.2 [24.6; 41.7] |
| snr3_complete0 | C_quality_bins | 0.685 [0.667; 0.704] | 3.3 [1.1; 6.9] | 8.3 [4.7; 15.6] |
| snr3_complete0 | D_logistic | 0.687 [0.668; 0.708] | 7.5 [5.0; 13.3] | 22.8 [16.4; 31.9] |
| snr3_complete0 | E_forest | 0.684 [0.663; 0.706] | 18.6 [11.5; 30.3] | 42.2 [31.7; 56.3] |
| snr3_peak0.4 | A_BIC | 0.504 [0.498; 0.511] | 0.0 [0.0; 0.6] | 0.0 [0.0; 0.7] |
| snr3_peak0.4 | C_quality_bins | 0.505 [0.499; 0.511] | 4.2 [1.4; 7.1] | 4.2 [1.7; 8.1] |
| snr3_peak0.4 | D_logistic | 0.500 [0.485; 0.517] | 5.6 [3.1; 9.4] | 6.1 [3.9; 10.3] |
| snr3_peak0.4 | E_forest | 0.503 [0.491; 0.516] | 0.0 [0.0; 1.9] | 1.4 [0.1; 3.1] |
| snr3_random0.4 | A_BIC | 0.609 [0.593; 0.628] | 18.3 [11.8; 24.7] | 32.5 [22.8; 42.4] |
| snr3_random0.4 | C_quality_bins | 0.609 [0.593; 0.627] | 3.1 [1.4; 8.9] | 6.9 [4.0; 13.5] |
| snr3_random0.4 | D_logistic | 0.619 [0.599; 0.640] | 17.8 [12.8; 26.8] | 32.8 [25.3; 43.5] |
| snr3_random0.4 | E_forest | 0.622 [0.602; 0.643] | 27.5 [18.0; 41.1] | 44.4 [33.2; 56.5] |
| snr50_complete0 | A_BIC | 1.000 [1.000; 1.000] | 0.0 [0.0; 0.0] | 100.0 [100.0; 100.0] |
| snr50_complete0 | C_quality_bins | 1.000 [1.000; 1.000] | 0.0 [0.0; 0.0] | 100.0 [100.0; 100.0] |
| snr50_complete0 | D_logistic | 1.000 [1.000; 1.000] | 0.0 [0.0; 0.0] | 100.0 [100.0; 100.0] |
| snr50_complete0 | E_forest | 1.000 [1.000; 1.000] | 0.0 [0.0; 0.0] | 100.0 [100.0; 100.0] |
| snr50_peak0.25 | A_BIC | 0.854 [0.826; 0.879] | 1.1 [0.0; 2.2] | 38.1 [31.9; 43.9] |
| snr50_peak0.25 | C_quality_bins | 0.854 [0.826; 0.880] | 5.3 [2.4; 8.1] | 50.3 [43.6; 58.2] |
| snr50_peak0.25 | D_logistic | 0.865 [0.840; 0.889] | 6.4 [3.1; 10.7] | 59.4 [52.8; 66.4] |
| snr50_peak0.25 | E_forest | 0.879 [0.854; 0.903] | 2.5 [0.8; 5.6] | 52.2 [46.4; 63.8] |
| snr50_random0.25 | A_BIC | 1.000 [1.000; 1.000] | 0.0 [0.0; 0.0] | 100.0 [99.2; 100.0] |
| snr50_random0.25 | C_quality_bins | 1.000 [1.000; 1.000] | 0.0 [0.0; 0.0] | 99.7 [99.2; 100.0] |
| snr50_random0.25 | D_logistic | 1.000 [1.000; 1.000] | 0.0 [0.0; 0.0] | 99.7 [99.2; 100.0] |
| snr50_random0.25 | E_forest | 1.000 [1.000; 1.000] | 0.0 [0.0; 0.0] | 99.7 [99.2; 100.0] |
| snr5_complete0 | A_BIC | 0.828 [0.806; 0.849] | 11.1 [6.4; 15.4] | 54.7 [46.2; 61.9] |
| snr5_complete0 | C_quality_bins | 0.827 [0.806; 0.847] | 6.9 [4.2; 12.2] | 32.5 [26.0; 42.5] |
| snr5_complete0 | D_logistic | 0.830 [0.811; 0.852] | 4.2 [1.9; 8.2] | 36.7 [30.3; 44.9] |
| snr5_complete0 | E_forest | 0.848 [0.825; 0.870] | 8.3 [4.7; 12.8] | 50.3 [41.9; 59.7] |
| snr5_peak0.25 | A_BIC | 0.545 [0.529; 0.560] | 1.1 [0.0; 2.4] | 1.9 [0.6; 4.2] |
| snr5_peak0.25 | C_quality_bins | 0.545 [0.529; 0.560] | 6.4 [2.6; 10.1] | 11.1 [6.7; 16.8] |
| snr5_peak0.25 | D_logistic | 0.560 [0.536; 0.587] | 8.1 [5.7; 12.8] | 16.4 [12.5; 22.2] |
| snr5_peak0.25 | E_forest | 0.575 [0.553; 0.603] | 4.4 [2.1; 7.5] | 12.8 [8.1; 16.9] |
| snr5_random0.25 | A_BIC | 0.769 [0.749; 0.791] | 17.2 [10.4; 23.6] | 51.4 [44.0; 60.8] |
| snr5_random0.25 | C_quality_bins | 0.769 [0.748; 0.790] | 10.3 [6.9; 16.1] | 31.1 [25.1; 41.9] |
| snr5_random0.25 | D_logistic | 0.779 [0.757; 0.798] | 6.9 [3.9; 11.8] | 36.7 [29.3; 45.8] |
| snr5_random0.25 | E_forest | 0.784 [0.761; 0.804] | 12.8 [8.9; 20.3] | 51.1 [44.4; 61.7] |


![Фактический FPR](figures/experiment03/achieved_fpr.png)

График: complete SNR3/5/15/50 (3 — OOD), random/peak25% SNR5/15/50; таблица
дополнительно содержит OOD. Интервалы source-bootstrap с calibration uncertainty.
Нулевые bootstrap CI не доказывают нулевой population FPR. Например 0FP/360
независимых negatives имеет Wilson upper95%≈1.06%, а не гарантию 0%.

![Калибровка вероятностей](figures/experiment03/calibration.png)

Equal-width10 probability bins; частоты описательные, views зависимы. Brier CI
приведены выше. C совпадает с B по probability; A не рисуется как probability.


## 8. Отказ: оба определения FPR и сопоставимый coverage

Ниже operational cutoff с calibration, не новый quantile по evaluation labels.
FPRacc=FP среди принятых negatives / принятые negatives; FPall=принятые FP /
все negatives; recallall=принятые TP / все positives. Отказы не считаются правильными ответами.

| Subset | Method | Coverage% | Risk accepted% | FPRacc% | FPall% | Recallall% | Reject neg% | Reject pos% |
|---|---|---|---|---|---|---|---|---|
| ID_mixture | B_score_logistic | 80.0 [78.3; 81.6] | 14.1 [13.2; 15.1] | 5.4 [3.3; 7.5] | 4.4 [2.6; 6.0] | 61.0 [58.4; 64.0] | 19.3 [16.6; 22.0] | 20.7 [18.4; 22.9] |
| ID_mixture | C_quality_bins | 80.6 [79.3; 82.6] | 14.4 [13.7; 15.5] | 5.7 [4.1; 8.0] | 4.7 [3.4; 6.5] | 60.5 [57.9; 64.0] | 17.9 [14.8; 20.1] | 21.0 [18.1; 22.5] |
| ID_mixture | D_logistic | 79.9 [78.3; 82.4] | 12.7 [11.4; 14.0] | 4.8 [3.2; 7.5] | 3.9 [2.6; 6.1] | 62.6 [59.1; 66.5] | 19.2 [15.8; 20.8] | 21.0 [18.3; 23.9] |
| ID_mixture | E_forest | 80.3 [78.7; 82.3] | 11.4 [10.5; 12.6] | 5.0 [3.3; 7.5] | 4.1 [2.7; 6.0] | 65.5 [61.8; 69.7] | 19.3 [16.7; 21.6] | 20.2 [17.1; 22.7] |
| OOD_mixture | B_score_logistic | 64.3 [61.5; 67.1] | 32.7 [32.0; 34.2] | 12.3 [8.7; 17.0] | 7.7 [5.4; 10.8] | 31.9 [27.4; 35.9] | 37.7 [34.1; 40.4] | 33.7 [30.0; 37.3] |
| OOD_mixture | C_quality_bins | 60.4 [58.5; 63.6] | 33.0 [32.0; 34.1] | 7.7 [5.4; 11.9] | 4.7 [3.3; 7.1] | 25.1 [23.1; 28.8] | 39.5 [35.6; 42.3] | 39.8 [36.8; 41.3] |
| OOD_mixture | D_logistic | 62.2 [59.0; 66.1] | 29.7 [27.9; 31.4] | 12.7 [9.2; 18.9] | 8.0 [6.0; 12.2] | 32.7 [29.1; 38.6] | 37.2 [32.3; 40.4] | 38.4 [34.4; 41.8] |
| OOD_mixture | E_forest | 58.1 [54.6; 62.0] | 28.0 [26.7; 29.9] | 19.1 [12.4; 27.4] | 10.8 [6.9; 16.0] | 37.8 [32.6; 43.7] | 43.2 [39.1; 46.4] | 40.5 [36.2; 44.3] |


![Риск–покрытие](figures/experiment03/risk_coverage.png)

Нижняя кривая лучше при одном coverage. Evaluation quantile confidence в RC
служит только описанию кривой, не выбору рабочего порога. Таблица ниже фиксирует
ровно 80% acceptance (ceil при неполном числе); labels не участвуют в выборе top confidence.

| Subset | Method | Risk80%95%CI |
|---|---|---|
| ID_mixture | B_score_logistic | 14.1 [13.2; 15.0] |
| ID_mixture | D_logistic | 12.5 [11.6; 13.5] |
| ID_mixture | E_forest | 11.2 [10.3; 12.3] |
| OOD_mixture | B_score_logistic | 34.2 [33.5; 35.4] |
| OOD_mixture | D_logistic | 33.7 [32.6; 34.9] |
| OOD_mixture | E_forest | 33.1 [32.1; 34.2] |
| snr15_peak0.4 | B_score_logistic | 45.8 [44.2; 47.2] |
| snr15_peak0.4 | D_logistic | 41.7 [38.9; 43.7] |
| snr15_peak0.4 | E_forest | 41.3 [39.0; 43.8] |


## 9. Абляции и seed stability

Полная E минус comparator; все настройки comparator также выбраны validation.
Удаление feature group не удаляет все физические зависимости: time имеет
fitted-peak gap, optimizer — PSPL starts. E_no_physics не равно «без physical fit».
Эти дополнительные контрасты exploratory, а не новые primary hypotheses.

| Contrast | Subset | Metric | Difference95%CI |
|---|---|---|---|
| E_forest_minus_E_score_only | ID_mixture | brier | -0.0209 [-0.0234; -0.0185] |
| E_forest_minus_E_score_only | ID_mixture | risk_at_80 | -0.0392 [-0.0467; -0.0331] |
| E_forest_minus_E_score_only | OOD_mixture | brier | -0.0198 [-0.0229; -0.0161] |
| E_forest_minus_E_score_only | OOD_mixture | risk_at_80 | -0.0181 [-0.0297; -0.0073] |
| E_forest_minus_E_no_time | ID_mixture | brier | -0.0012 [-0.0021; -0.0003] |
| E_forest_minus_E_no_time | ID_mixture | risk_at_80 | -0.0019 [-0.0077; 0.0023] |
| E_forest_minus_E_no_time | OOD_mixture | brier | -0.0072 [-0.0085; -0.0056] |
| E_forest_minus_E_no_time | OOD_mixture | risk_at_80 | 0.0010 [-0.0092; 0.0077] |
| E_forest_minus_E_no_optimization | ID_mixture | brier | -0.0000 [-0.0009; 0.0007] |
| E_forest_minus_E_no_optimization | ID_mixture | risk_at_80 | -0.0012 [-0.0075; 0.0020] |
| E_forest_minus_E_no_optimization | OOD_mixture | brier | -0.0007 [-0.0019; 0.0004] |
| E_forest_minus_E_no_optimization | OOD_mixture | risk_at_80 | 0.0017 [-0.0071; 0.0073] |
| E_forest_minus_E_no_physics | ID_mixture | brier | -0.0160 [-0.0194; -0.0123] |
| E_forest_minus_E_no_physics | ID_mixture | risk_at_80 | -0.0270 [-0.0369; -0.0176] |
| E_forest_minus_E_no_physics | OOD_mixture | brier | -0.0095 [-0.0130; -0.0059] |
| E_forest_minus_E_no_physics | OOD_mixture | risk_at_80 | -0.0271 [-0.0406; -0.0135] |


Все seeds для основных сравнений (point estimates; CI учитывают source sampling выше):

| Seed | Subset | Method | AUC | Brier | FPR% | Recall% | Risk80% |
|---|---|---|---|---|---|---|---|
| 2027 | ID_mixture | B_score_logistic | 0.8891 | 0.1360 | 4.2 | 60.4 | 14.4 |
| 2027 | OOD_mixture | B_score_logistic | 0.6655 | 0.2309 | 7.2 | 30.5 | 35.4 |
| 2027 | ID_mixture | D_logistic | 0.9125 | 0.1201 | 4.9 | 63.4 | 13.1 |
| 2027 | OOD_mixture | D_logistic | 0.7127 | 0.2158 | 7.2 | 31.5 | 34.0 |
| 2027 | ID_mixture | E_forest | 0.9244 | 0.1103 | 3.6 | 65.7 | 11.1 |
| 2027 | OOD_mixture | E_forest | 0.7083 | 0.2143 | 11.2 | 35.7 | 34.1 |
| 2028 | ID_mixture | B_score_logistic | 0.8958 | 0.1316 | 5.2 | 62.7 | 13.8 |
| 2028 | OOD_mixture | B_score_logistic | 0.6748 | 0.2269 | 9.3 | 33.7 | 34.1 |
| 2028 | ID_mixture | D_logistic | 0.9200 | 0.1146 | 3.9 | 64.5 | 11.6 |
| 2028 | OOD_mixture | D_logistic | 0.7112 | 0.2163 | 8.8 | 33.5 | 33.4 |
| 2028 | ID_mixture | E_forest | 0.9234 | 0.1108 | 4.8 | 68.1 | 10.8 |
| 2028 | OOD_mixture | E_forest | 0.7208 | 0.2079 | 12.8 | 41.8 | 32.5 |
| 2029 | ID_mixture | B_score_logistic | 0.8909 | 0.1339 | 3.7 | 60.1 | 14.2 |
| 2029 | OOD_mixture | B_score_logistic | 0.6727 | 0.2295 | 6.5 | 31.5 | 33.5 |
| 2029 | ID_mixture | D_logistic | 0.9127 | 0.1194 | 2.8 | 59.8 | 13.3 |
| 2029 | OOD_mixture | D_logistic | 0.7090 | 0.2186 | 8.0 | 33.0 | 33.9 |
| 2029 | ID_mixture | E_forest | 0.9190 | 0.1145 | 3.8 | 62.7 | 12.1 |
| 2029 | OOD_mixture | E_forest | 0.7200 | 0.2086 | 8.5 | 35.8 | 32.9 |


## 10. Информация и физические параметры

Отдельно от feature matrix: d²=Σ[(muPSPL−muG)/sigma]², KL=d²/2.
При известных nuisance конкретной пары, равных priors и Gaussian errors
oracle error=Phi(−d/2). Для derivation LLR под классами имеет mean±d²/2
и variance d². Это не composite Bayes error, не input и не обещание достижимости.
Null noncentrality=Σ[(muPSPL−weighted mean(muPSPL))/sigma]² измеряет видимую
noiseless variability относительно лучшей константы. Разброс источников важен.

| Condition | Median d | d<1,% | Mean oracle error% | Median null noncentrality | MAE Fb | MARE u0 | MARE tE | PSPL failed% |
|---|---|---|---|---|---|---|---|---|
| snr15_complete0 | 6.172 | 0.0 | 0.37 | 1188.024 | 0.273 | 0.309 | 0.266 | 0.0 |
| snr15_peak0.25 | 2.424 | 29.2 | 17.00 | 3.983 | 0.455 | 1.037 | 3.065 | 13.3 |
| snr15_peak0.4 | 0.755 | 56.4 | 29.21 | 0.301 | 0.478 | 1.162 | 2.870 | 17.2 |
| snr15_random0.25 | 5.386 | 0.0 | 1.02 | 898.426 | 0.297 | 0.347 | 0.358 | 0.0 |
| snr15_random0.4 | 4.806 | 0.0 | 1.71 | 726.703 | 0.321 | 0.391 | 0.443 | 0.0 |
| snr3_complete0 | 1.234 | 21.9 | 26.80 | 47.521 | 0.413 | 0.568 | 5.031 | 0.0 |
| snr3_peak0.4 | 0.151 | 90.3 | 43.79 | 0.012 | 0.441 | 0.877 | 1.822 | 23.6 |
| snr3_random0.4 | 0.961 | 53.9 | 31.56 | 29.068 | 0.432 | 0.652 | 6.179 | 1.9 |
| snr50_complete0 | 20.575 | 0.0 | 0.00 | 13200.263 | 0.139 | 0.140 | 0.093 | 0.0 |
| snr50_peak0.25 | 8.080 | 8.6 | 6.78 | 44.254 | 0.398 | 1.117 | 1.276 | 6.7 |
| snr50_random0.25 | 17.954 | 0.0 | 0.00 | 9982.512 | 0.163 | 0.170 | 0.112 | 0.0 |
| snr5_complete0 | 2.057 | 0.0 | 15.48 | 132.003 | 0.372 | 0.492 | 2.801 | 0.0 |
| snr5_peak0.25 | 0.808 | 55.6 | 31.44 | 0.443 | 0.469 | 0.942 | 2.645 | 22.2 |
| snr5_random0.25 | 1.795 | 0.8 | 18.95 | 99.825 | 0.395 | 0.540 | 3.714 | 0.0 |


![Информация и параметры](figures/experiment03/information_parameters.png)

Все positive evaluation views, без выбора по качеству. По x privileged d,
по y реальные ошибки относительно generator truth, используемые только для анализа.
Correlation across repeated conditions описательная, не множество независимых
доказательств: Spearman {'Fb_abs_error': -0.4353132478119842, 'tE_relative_error': -0.5453227069139618, 'u0_relative_error': -0.48722838861715484}.

![Ошибки и наблюдаемый gap](figures/experiment03/error_vs_gap.png)

Бины и counts из error_vs_gap.csv; описательная зависимость, без ложных
point-independent error bars. Большой gap не гарантирует ошибку: важны положение
сигнала, длительность и шум. Низкое d говорит о трудности конкретной пары,
а высокое d при ошибке оставляет пространство для лучшего вывода/оценки nuisance.


## 11. Stress: новые отрицательные семейства

Это новое семейство симуляций, не реальные внешние наблюдения. Asymmetric Gaussian
имеет widths.5w/1.5w: общая FWHM та же. Periodic raised cosine имеет period=2FWHM.
Baseline floor1, continuous peak amplitude, sigma,z,cadence,masks одинаковы
с paired PSPL. Средний уровень periodic отличается как свойство формы,
не отдельная нормировка данных. Модели/пороги не менялись.120pairs/семейство;
PSPL повторно используется между семейными comparisons. CI здесь source-bootstrap
при фиксированных thresholds (calibration uncertainty не добавлялась), условные.

| Negative | Condition | Method | AUC95%CI | FPR%95%CI | Recall%95%CI | Coverage% | Selective error% |
|---|---|---|---|---|---|---|---|
| asymmetric | snr15_complete0 | A_BIC | 0.998 [0.994; 1.000] | 2.5 [0.0; 5.8] | 96.7 [93.3; 99.2] | 97.1 [95.0; 98.8] | 1.3 [0.0; 3.0] |
| asymmetric | snr15_peak0.4 | A_BIC | 0.544 [0.511; 0.574] | 2.5 [0.0; 5.0] | 3.3 [0.8; 6.7] | 75.0 [68.1; 81.7] | 48.3 [45.9; 50.8] |
| asymmetric | snr15_random0.4 | A_BIC | 0.969 [0.950; 0.983] | 12.5 [7.5; 18.3] | 90.8 [85.0; 95.0] | 87.9 [82.5; 92.1] | 7.6 [4.7; 11.0] |
| asymmetric | snr15_complete0 | C_quality_bins | 0.998 [0.994; 1.000] | 0.8 [0.0; 2.5] | 95.0 [91.2; 98.3] | 95.4 [92.1; 97.9] | 0.4 [0.0; 1.3] |
| asymmetric | snr15_peak0.4 | C_quality_bins | 0.543 [0.509; 0.578] | 13.3 [6.7; 20.4] | 13.3 [7.5; 20.0] | 86.2 [80.6; 91.7] | 48.8 [46.5; 51.2] |
| asymmetric | snr15_random0.4 | C_quality_bins | 0.970 [0.955; 0.983] | 11.7 [6.7; 17.1] | 88.3 [82.5; 93.3] | 86.2 [81.7; 91.2] | 7.2 [3.9; 10.3] |
| asymmetric | snr15_complete0 | D_logistic | 0.999 [0.998; 1.000] | 0.0 [0.0; 0.0] | 91.7 [87.5; 95.8] | 96.7 [94.6; 98.8] | 1.7 [0.0; 3.4] |
| asymmetric | snr15_peak0.4 | D_logistic | 0.602 [0.564; 0.640] | 14.2 [8.3; 20.8] | 30.8 [23.3; 39.6] | 67.1 [60.0; 74.2] | 41.0 [36.7; 45.2] |
| asymmetric | snr15_random0.4 | D_logistic | 0.974 [0.959; 0.988] | 5.0 [1.7; 8.8] | 79.2 [71.7; 85.8] | 88.8 [84.8; 92.5] | 6.1 [3.3; 9.3] |
| asymmetric | snr15_complete0 | E_forest | 0.999 [0.996; 1.000] | 0.0 [0.0; 0.0] | 95.8 [92.5; 98.3] | 97.9 [95.8; 99.4] | 1.7 [0.4; 3.4] |
| asymmetric | snr15_peak0.4 | E_forest | 0.585 [0.545; 0.621] | 5.0 [1.7; 9.2] | 14.2 [8.3; 20.4] | 45.4 [38.9; 54.2] | 39.4 [33.8; 44.3] |
| asymmetric | snr15_random0.4 | E_forest | 0.972 [0.953; 0.987] | 9.2 [4.2; 14.6] | 89.2 [84.2; 94.2] | 92.9 [89.2; 96.2] | 6.7 [3.6; 9.9] |
| periodic | snr15_complete0 | A_BIC | 0.983 [0.958; 1.000] | 1.7 [0.0; 4.2] | 96.7 [93.3; 99.2] | 96.7 [94.6; 98.8] | 0.9 [0.0; 2.1] |
| periodic | snr15_peak0.4 | A_BIC | 0.916 [0.871; 0.954] | 4.2 [1.7; 8.3] | 3.3 [0.8; 6.7] | 85.4 [81.2; 88.8] | 43.4 [39.7; 47.2] |
| periodic | snr15_random0.4 | A_BIC | 0.980 [0.951; 0.998] | 1.7 [0.0; 4.2] | 90.8 [85.8; 95.8] | 89.6 [85.4; 93.3] | 1.4 [0.0; 2.8] |
| periodic | snr15_complete0 | C_quality_bins | 0.983 [0.958; 1.000] | 2.5 [0.0; 5.0] | 95.0 [90.8; 98.3] | 96.2 [93.8; 98.3] | 1.3 [0.0; 2.7] |
| periodic | snr15_peak0.4 | C_quality_bins | 0.915 [0.870; 0.958] | 4.2 [0.8; 7.5] | 13.3 [7.5; 20.0] | 90.8 [87.3; 94.2] | 41.3 [36.8; 45.2] |
| periodic | snr15_random0.4 | C_quality_bins | 0.980 [0.951; 0.998] | 4.2 [1.2; 7.5] | 88.3 [82.5; 94.2] | 90.0 [85.4; 93.3] | 2.8 [0.9; 5.1] |
| periodic | snr15_complete0 | D_logistic | 0.757 [0.716; 0.799] | 31.7 [27.5; 35.0] | 91.7 [86.7; 95.8] | 96.7 [94.4; 98.6] | 18.1 [15.5; 20.9] |
| periodic | snr15_peak0.4 | D_logistic | 0.743 [0.695; 0.794] | 25.8 [20.0; 30.8] | 30.8 [22.5; 38.3] | 85.4 [81.0; 89.2] | 39.0 [32.5; 44.2] |
| periodic | snr15_random0.4 | D_logistic | 0.665 [0.610; 0.717] | 40.0 [34.2; 46.3] | 79.2 [73.3; 85.0] | 91.7 [88.3; 94.8] | 25.0 [21.5; 29.7] |
| periodic | snr15_complete0 | E_forest | 0.998 [0.995; 1.000] | 1.7 [0.0; 3.8] | 95.8 [92.5; 99.2] | 99.6 [98.8; 100.0] | 2.5 [0.8; 4.2] |
| periodic | snr15_peak0.4 | E_forest | 0.959 [0.923; 0.991] | 4.2 [0.8; 7.9] | 14.2 [7.5; 20.0] | 72.5 [67.7; 76.7] | 24.1 [19.2; 29.2] |
| periodic | snr15_random0.4 | E_forest | 0.991 [0.981; 0.998] | 1.7 [0.0; 4.2] | 89.2 [84.2; 94.6] | 95.0 [92.5; 97.5] | 2.6 [0.9; 4.8] |


![Примеры из сохранённых результатов](figures/experiment03/examples.png)

Выбор: первая lexicographic строка E, удовлетворяющая правилам success/false alarm/
refusal предотвращает ошибку. Это иллюстрации, не representative performance estimate;
правило и row IDs в examples.json. Fit показан только в retained times, без
придуманной реконструкции отсутствующего пика. Полные метрики включают все случаи.


## 12. Научная интерпретация и границы выводов

**Получен исход A с ограничением области применимости.** На новых источниках из
обучающего распределения набор наблюдаемых признаков улучшил probability quality и
риск при сопоставимом coverage. Универсальный надёжный детектор и контроль FPR при
произвольном сдвиге не получены. Это важнее положительного результата на ID.

### H3.1: признаки полезны в этой постановке

Validation выбрала E_forest до открытия evaluation. На ID Brier B=.13383, E=.11189;
парная разность−.02193,95%CI[−.02438;−.01904]. AUC .89195→.92212. Все три seed имеют
меньший Brier и risk80 для E, но CI условны на обученных моделях и priors. Прирост
сохраняется относительно нелинейного RF только на score: ΔBrier−.02092
[−.02337;−.01850]. Следовательно, это не только замена линейной сигмоиды деревьями.

Абляции сдерживают интерпретацию: удаление optimizer group практически не меняет
Brier (полная E минус E_no_optimization=−.000049,CI[−.000881;.000737]); убедительного
самостоятельного вклада этих proxy uncertainty features не установлено. Удаление
time group даёт небольшой Brier эффект, но risk80 contrast CI пересекает ноль.
Группа physics даёт заметный вклад: ΔBrier−.01599 [−.01944;−.01233], Δrisk80−.02701
[−.03695;−.01765]. Это сравнение групп, не доказательство причинной необходимости
каждого признака; соседние группы тоже используют physical fit. «Неопределённость
параметров сама по себе решила задачу» данные не поддерживают.

### H3.2: условные пороги уменьшают неоднородность, но не обеспечивают контроль

На девяти ID условиях mean |FPR−.05| падает с .04722 до .02747; Δ=−.01975
[−.02654;−.00494]. Максимальный point FPR A=17.22%, C=10.28%; оба превышают 5%.
Средний ID FPR C=4.72% не означает 4.72% в каждом режиме. В редком bin с большим gap
и высоким visible SNR оказалось 10/17/12 независимых calibration groups по seed,
поэтому сработал заранее предусмотренный pooled fallback. Эти bins требуют данных.

На OOD C уменьшает mean FPR7.67→4.67%, но recall31.89→25.06%. При SNR3 complete
recall падает 34.17→8.33%. Это tradeoff, не бесплатное улучшение. Вероятности B и C
одинаковы; C не улучшает Brier/ROC. Внутри одного seed положительная сигмоида B
сохраняет ранжирование raw BIC; небольшое различие pooled AUC A/B связано с разными
отображениями по seed. На asymmetric peak40 achieved FPR C=13.33%: условный контроль
не переносится автоматически на новое семейство альтернатив.

### H3.3: локальный выигрыш при 80%coverage, но отказ не защищает от уверенных FP

На ID fixed80 error B=14.101%, E=11.246%; Δ=−2.855 процентного пункта,
CI[−3.589;−1.957]. Operational cutoff, выбранный на calibration, дал E coverage80.262%
и selective error11.440%: выигрыш не объясняется отказом почти всем событиям.

При этом FPR среди принятых ID negatives=5.048%, accepted FP/всех negatives=4.074%.
На OOD эти показатели уже 19.080% и 10.833%, coverage58.139%, selective error27.998%.
Нельзя сравнивать последние 28% напрямую с 32.743% B, поскольку coverage B=64.306%.
При ровно 80% OOD error E=33.090%, B=34.201% — лишь небольшой point difference;
primary CI в протоколе был для ID, подтверждения универсального OOD выигрыша нет.

Особенно показателен OOD SNR3/random40: E FPR27.5%, а среди принятых negatives60%.
Почти все FP остаются принятыми: confidence=p у положительного решения высока даже
при ошибке. Отказ в основном убирает сомнительные отрицательные решения, а не
уверенные ложные тревоги. Такой selector не является самостоятельной защитой FPR.
Стоимость FN/FP и реальная prevalence могут изменить практическую ценность выигрыша.

### H3.4: потеря сигнала воспроизводится, но есть и проблема правила решения

На новой evaluation SNR15 complete/random40/peak40 median d=6.172/4.806/.755;
mean oracle error=.374%/1.714%/29.215%. При peak40 у 56.39% пар d<1,
PSPL median null noncentrality=.301, против 726.70 при random40. Это сильная
диагностическая поддержка потери сигнала в этой интервенции, а не только плохого
optimizer. Fb MAE растёт .273→.478, u0 MARE .309→1.162, tE MARE .266→2.870;
PSPL optimizer failure среди positives0→17.22%. Даже formal convergence нельзя
отождествлять с идентифицируемостью. Корреляции в §10 описательные, не causal proof.

Обычный E имеет peak40 AUC .5978 [ .5724;.6283 ], recall11.94%, FPR1.39%. При
operational refusal coverage53.75%, ошибка принятых 40.31%; даже при coverage30%
RC curve остаётся около 35% ошибки. Это не хорошая автоматизация и не основание
обещать восстановление отсутствующего пика нейросетью. Однако d распределено широко:
часть событий сохраняет информацию, и oracle знает больше обычного алгоритма.
Информационно-теоретическая невозможность composite задачи не доказана.

Контрпример обобщению «любой пропуск пика означает отсутствие информации» — periodic
stress: E AUC .9590, но recall всего 14.17% при исходном пороге. Здесь ранжирование
хорошее, рабочий порог не подходит новой альтернативе. Порог не донастраивался по
stress labels. Это демонстрирует различие decision/calibration failure и потери
формы в PSPL-versus-Gaussian. Дополнительный bootstrap этих двух stress семейств
условен на фиксированных thresholds, не включает calibration uncertainty.

### Что оказалось неожиданным и что нельзя считать надёжным

На periodic negatives полная LR D дала FPR31.67% complete и 40.0% random40, хотя её
ID Brier улучшился. При random40 operational coverage91.67%, selective error25%:
алгоритм остаётся уверен в незнакомой форме. E на том же stress имеет FPR1.67%,
но 120 независимых negatives/семейство недостаточно для заявления о точном низком FPR;
на asymmetric/random40 E уже 9.17%, на asymmetric/peak40 его coverage45.42% при
selective error39.45%. Неудачные результаты сохранены и не отфильтрованы.

Нельзя объявлять идеальную calibration, universal FPR5%, пользу любых uncertainty
features или готовность к реальной детекции. Нельзя считать 9 повторных условий
независимыми наблюдениями, prevalence=.5 реальным обзором, а toy periodic template —
всем классом переменных звёзд. Нет correlated noise, ошибок sigma, более широких
priors/finite-source/parallax/binary lenses. Вероятности RF могут использовать
узкие generator priors. Параметрические ошибки и oracle сводки без отдельных CI
в §10 — descriptive diagnostics; основной statistical support относится к
предзаданным pair-bootstrap contrasts, без защиты от множественных сравнений.

### Следующая наиболее ценная гипотеза

Проверить на новых source-disjoint данных, позволит ли **калибровка риска ложного
положительного решения с учётом качества и расширенного negative pool** уменьшить
OOD accepted-FPR относительно простого confidence RF при coverage≥80%. Включить
несколько непериодических/асимметричных переменных и correlated noise в development,
но оставить отдельное неизвестное семейство/шум для следующей evaluation; увеличить
независимую calibration для tail estimates. Сравнить простые bins/регрессию с
confidence margin, не начинать CNN ради архитектуры. Это новая проверяемая гипотеза,
а не обещание контроля неизвестного shift. Будущая физико-нейросетевая модель должна
решать переносимость decision reliability и корректный отказ; оснований требовать
от неё восстановления исчезнувшего сигнала пока нет.


## 13. Литература и статус новизны

Известны PSPL, blending degeneracy, probability calibration, reject option и
distribution shift. Использованные LR/RF/empirical quantiles не новые. Собственная
реализация — проверяемый paired protocol, 49 допустимых признаков, заморозка и
совместный анализ calibration/coverage/information. Новое для проекта — измеренные
сравнения; приоритет научной публикации/универсальная новизна не установлены.

Проверенные первичные методические источники (не прямое соревнование метрик):

- [Guo et al.,2017](https://proceedings.mlr.press/v70/guo17a/guo17a.pdf), §4: sigmoid calibration.
- [Geifman & El-Yaniv,2017](https://arxiv.org/pdf/1705.08500): fixed predictor/reject option.
- [Fisch et al.,2022/2024](https://arxiv.org/html/2208.12084v2): selective calibration, Brier.
- [Liang et al.,2024](https://arxiv.org/html/2405.05160v2): RC curves под shift.
- [Ovadia et al.,2019](https://proceedings.neurips.cc/paper/2019/hash/8558cb408c1d76621371888657d2eb1d-Abstract.html): shift и uncertainty.
- [Godines et al.](https://arxiv.org/html/2004.14347v1), §§2,4–5: microlensing RF и features.

Матрица literature_matrix.csv обновлена; Platt1999 original PDF timeout, mapping
проверен по Guo, не заявляем прочтение оригинала. Microlensify/MicroLIA из прежнего
обзора не воспроизводились. Полный systematic review ещё не завершён.


## 14. Реальное выполнение, проверки и ограничения

Main code commit 107079e15a535c1663efc7907d724bc0edf406e8; run wall 477.349s,
analysis bootstrap/figures 112.183s (отдельно). CPU4 workers,
BLAS/OMP1, sklearn n_jobs1; память snapshot, не полный peak, в resource_snapshots.jsonl.
Проверено 24120fit rows и 149040
предсказаний, max likelihood discrepancy9.09e-13.
Source splits/checksums, feature whitelist и saved predictions проверены;
reserved manifests неизменны. Tests:44passed/1skipped на pre-main; финальный log
в reports/checks/experiment03_pytest.log. MulensModel optional отсутствует.

Реально выполненные ключевые команды из корня репозитория:

```bash
../.venv/bin/python -m pytest -q
../.venv/bin/python -m ruff check src tests scripts/verify_experiment03.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ../.venv/bin/python scripts/verify_experiment02.py artifacts/experiment02-main
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ../.venv/bin/python -m microlens.information03 artifacts/experiment02-main artifacts/experiment03-audit02
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ../.venv/bin/python -m microlens.experiment03 --config configs/experiment_03_smoke.json --output artifacts/experiment03-smoke
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ../.venv/bin/python -m microlens.experiment03 --config configs/experiment_03_smoke.json --output artifacts/experiment03-smoke --resume
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ../.venv/bin/python -m microlens.experiment03 --config configs/experiment_03_smoke.json --output artifacts/experiment03-smoke-frozen
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ../.venv/bin/python -m microlens.experiment03 --config configs/experiment_03.json --output artifacts/experiment03-main
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ../.venv/bin/python -m microlens.experiment03_analysis artifacts/experiment03-main
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ../.venv/bin/python scripts/verify_experiment03.py artifacts/experiment03-main
../.venv/bin/python scripts/build_experiment03_report.py artifacts/experiment03-main
```

Для нового fit выбрать новый output; resume требует прежних code/config hashes.
Исторический fit snapshot107079e, analysis SHA отдельно в analysis_provenance.json.
Финальный source snapshot содержит analysis уточнение A_BIC Brier=None и дополнительные
paired ablation CI; они не меняют training, thresholds и saved primary predictions.
Старые smoke результаты сохранены, полный main второй раз не повторялся.

Файлы: configs/experiment_03*.json; src/microlens/{experiment03,experiment03_analysis,
reliability_features,information03}.py; tests/test_experiment03.py; verifier/report
scripts; research/{audit_03,experiment_03_protocol,literature*}; defense/experiment_03_notes.md.
Artifacts: raw tasks/observations/starts, separate generator truth/diagnostics,
models.pkl/frozen_models/frozen_thresholds, manifests/checksums/stdout, CSV predictions/
metrics/by-seed/stress/risk–coverage/reliability/information, six figures.

Не выполнены/заблокированы: реальная независимая фотометрия и полноценная calibration
при реальной prevalence, MulensModel crosscheck (пакет отсутствует), строгие FPR1%
и параметрические confidence coverage. GPU/Kaggle/Colab не требовались и не запускались;
их доступ не предполагается. Нет платных ресурсов/large dataset downloads.

С научным руководителем остаётся согласовать реальный negative pool/лицензии,
наблюдательный бюджет допустимых отказов и цену FP/FN. Эти решения не менялись
по evaluation. Для защиты — notes, собственный разбор ученика и раскрытие AI assistance.
Код, вычисления и черновой анализ выполнены Codex по заданию руководителя;
личное понимание/проверки ученика ещё не подтверждены.
