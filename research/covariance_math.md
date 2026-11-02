# Математическая спецификация COV05

Ниже вывод для реализованного алгоритма, а не утверждение о новом статистическом методе. Первичные определения/прочитанный охват: [Hogg/GPML notes](reading_notes/L03_L04_likelihood.md). Численная независимая проверка: [calibration verifier](../reports/checks/cov05_calibration_verifier.json); evaluation verifier публикуется после завершения опыта.

## Полный likelihood и линейный профиль

Для наблюдений y, mean m=X(θ)β и C(φ)=LLᵀ:

ℒ(θ,β,φ)=½‖L⁻¹(y−Xβ)‖²+Σᵢlog Lᵢᵢ+(n/2)log(2π).

Первое слагаемое — quadratic residual, второе — ½logdet C. Если C оценивается, выкидывание logdet создаёт стимул неограниченно раздувать дисперсию. [Negative control](../reports/checks/likelihood_2026-11-02.json) проверяет именно эту ошибку; это не detector benchmark.

При фиксированных θ,φ линейные β находятся NNLS: min β≥0 ‖ỹ−X̃β‖², где X̃=L⁻¹X и ỹ=L⁻¹y. Constant: X=1; PSPL: X=[A(u),1], β=[Fs,Fb]; Gaussian: X=[exp(−(t−tc)²/(2w²)),1], β=[amplitude,baseline]. Число полных mean-параметров:1,5,4. Данные не получают baseline=1 из truth: обе линейные компоненты оцениваются.

Независимая KKT-проверка вычисляет g=X̃ᵀ(X̃β−ỹ). Для βⱼ>0 должно быть gⱼ≈0; для βⱼ=0 — gⱼ≥0. Проверяются все сохранённые выбранные fits, включая flagged nonconverged nonlinear solutions. KKT не доказывает global optimality nonlinear θ/φ.

NNLS не всегда численно надёжен для практически исчезнувшего Gaussian basis. В первой calibration наблюдался inf coefficient при finite residual norm. Такой набор параметров не задаёт доступный fit. До evaluation введена проверка finite coefficients/norm/NLL; objective получает явный numerical-failure penalty, событие сохраняется. Нельзя заменять inf на произвольное большое число и выдавать это за оценённую амплитуду.

## Covariance и score

Practical covariance:

Cᵢⱼ=(sσᵢ)²δᵢⱼ+a²(1+√3dᵢⱼ/ℓ)exp(−√3dᵢⱼ/ℓ), dᵢⱼ=|tᵢ−tⱼ|.

GP latent values интегрированы в эту Gaussian density. φ=(s,a,ℓ) оптимизируется вместе с mean shape; полная Bayesian marginalization по φ/θ не выполняется. Bounds/starts/caps — [protocol](experiment_05_protocol.md). SPD обеспечивается положительным diagonal term; никакой скрытый jitter не меняет модель. Oracle имеет fixed true C, diagonal — fixed diag(σ_report²).

BIC=2ℒ+klog n; k=(1,5,4) для fixed C и ещё3 для estimated C. Score=min(BIC_constant,BIC_Gaussian)−BIC_PSPL. Больший score предпочитает PSPL среди этих моделей. Это не posterior class probability. Условия классической BIC-аппроксимации могут нарушаться при parameter bounds, слабой идентифицируемости и локальных минимумах; работа использует score как заранее выбранную эвристику.

По каждому mean выбирается лучший converged start, иначе лучший finite с flag failure. Operational rule принимает score только если все три mean fits converged; иначе reject. AUC по finite scores и operational FPR/recall имеют разный смысл. Отказы не удаляются из знаменателя recall_all/FPR_all.

## Почему GP может помогать и мешать

В eigenbasis C квадратичное слагаемое имеет вид ½Σr̃ᵢ²/λᵢ, а normalization —½Σlogλᵢ. Увеличение covariance eigenvalue в направлении гладкого остатка уменьшает его штраф. Это полезно для correlated noise, но способно сделать неверный mean приемлемым или поглотить отличительную часть сигнала. Logdet ограничивает, но не запрещает такой компромисс. Конкурирующие means имеют одинаковую covariance family и fitting budget, чтобы одно объяснение не получало скрытого преимущества.

Этот механизм мотивирует контроль recall при уменьшении FPR. COV05 не идентифицирует причинный вклад absorption отдельно от optimizer failures, model misspecification и порога. Нельзя по одному ΔFPR утверждать доказанную пользу GP.

## Независимость и интервалы

Source unit объединяет latent shape, nuisance, draw шума, классы, маски и kernels. Точки одной кривой и counterfactual views не независимы. Calibration имеет240 sources/480 dependent negative views; evaluation360 sources. Разбиение выполнено до views; IDs не пересекаются.

Для одного evaluation scenario отрицательные источники независимы условно на frozen policy. Clopper–Pearson95% по FP/360 описывает эту условную величину. При0/360 верхняя двусторонняя95% граница положительна:1−0.025^(1/360)≈1.02%; нулевые FP не доказывают нулевой риск.

Primary paired bootstrap дополнительно учитывает calibration variation: независимо resample240 calibration и360 evaluation source clusters, стратифицированно по seed; оба calibration noise views и все evaluation counterfactuals идут вместе. Threshold каждого метода пересчитывается только из resampled calibration. Методы сравниваются на общих source draws.500 реплик — ограниченная точность percentile tails, не асимптотическая гарантия покрытия при любых populations. Все draws сохраняются для независимого пересчёта.

Target calibration FPR5% — empirical operating point, не finite-sample Neyman–Pearson control. Pooled white/Matérn threshold не гарантирует subgroup FPR5%, особенно для unseen OU/missingness. FDR зависит от prevalence; balanced toy FDR нельзя переносить на редкие survey events.
