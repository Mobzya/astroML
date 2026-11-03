# COV06 v1 — protocol before main data

03.11.2026. Разработка COV06-A завершена на отдельном development namespace; [numerical gate](../reports/cov06_numerical_validation.md) проверил2304fits/57304improvements, но classification performance не оценивалась. Старые R2/COV05 event-level evaluation/truth закрыты. Здесь фиксируется **новый** основной опыт. Конфигурация: [experiment_06.json](../configs/experiment_06.json).

## Вопрос, primary contrast и критерий

Проверяем пользу observation-only correlation estimation сверх общего rescaling sigma. **Primary scenario:** OU noise+reported-sigma bias, complete,SNR15, Gaussian negatives. Primary comparison: new estimated covariance−scale-only. Target calibration FPR5% — empirical operating point, не NP guarantee.

Практическая гипотеза поддержана только при одновременном выполнении:

- upper two-sided95% joint-source-bootstrap CI ΔFPR<0;
- lower95% CI Δrecall≥−.05 (допустимая потеря не более5п.п.);
- new estimated coverage≥.80 в primary scenario.

Снижение FP при почти исчезнувших TP не является успехом. Failure/negative/inconclusive outcome сохраняется. High AUC или улучшение относительно старого3-start алгоритма не заменяет primary comparison со scale-only. Этот критерий не гарантирует FPR5% в любом subgroup/реальном обзоре.

## Источники, splits и размер

Namespace `astroml-cov06-main-20261103-v1`, seeds620301/620302/620303. До views назначить80calibration+120evaluation source units на seed:240/360. Каждый unit содержит общие latent physics/nuisance/times/errors/noise vector, оба класса и все masks/kernels. IDs disjoint между development/calibration/evaluation и отдельным stress namespace. Нельзя пересчитывать размер выборки по тысячам зависимых views.

SNR15 означает analytic PSPL peak excess/nominal white sigma, n96,240дней, исходный prior как simulation.py: u0U[.15,1],t0U[60,180]d,tElogU[8,35]d,FsU[.3,.9],Fb1−Fs. Gaussian same baseline/analytic peak/center/excess FWHM; noise/cadence/sigma matched. Masks complete96/random40=58/peak40=58. True t0 задаёт только генераторную peak mask, не detector.

При FPR5% и360 independent negatives nominal SE≈1.15п.п.; CP intervals остаются широкими.240cal sources/480negative views не являются480 независимыми. Это exploratory attainable precision, не мощностная гарантия эффекта или тест1% tail. Примерный бюджет выбран по development cost до main, не по желаемым числам результата. Сокращение sample после открытия evaluation запрещено.

## Noise и matrix

Calibration: white и Matérn3/2 biased, complete,PSPL/Gaussian. Evaluation: white/Matérn3/2 biased/OU biased × complete/random40/peak40 × PSPL/Gaussian. Всего6480observed curves, но360independent eval sources. Double bump/новые negatives вынесены в отдельный заранее fixed stress protocol, а не выбираются по результатам main.

True noise: diag(sigma_true²)+a²K, a=.8median(full sigma_true),ell12d; white имеетa0. Matérn kernel(1+sqrt3d/ell)exp(−sqrt3d/ell), OUexp(−d/ell). Correlated cases report.65sigma_true, white reports true. Shared standard normal vector преобразуется Cholesky каждой C и остаётся одинаковой между классами. Noise и scale interventions совместны; scale-only comparator нужен для частичного отделения их вклада. Не утверждать полной causal ablation всех компонентов.

## Методы и fixed compute policy

Один COV06-A, выбранный **до main** по development numerical criteria. Практические режимы получают только Observations:

1. New diagonal: fixed reported C, scaled-NNLS six-start mean engine.
2. New scale-only: те же selected mean parameters/flags, analytic clipped sqrt(Q/n),noise count+1.
3. New estimated: exact nested q0 relative GP variance, three noise warm starts from observed diagonal, retained feasible incumbent,noise count+3.
4. Original3-start estimated algorithm — неизменённый baseline implementation на **новых** observations,noise count+3; его положительный floor и starts отличаются и явно сохраняются.
5. Fixed true-C oracle: только diagnostic privileged branch, общий six-start mean engine. Не практический кандидат и не guaranteed classification ceiling.

Constant/PSPL/Gaussian families/counts1/5/4, все bounds/starts/tolerance/fallback как [development design](cov06/optimizer_design.md). Один candidate, никаких новых вариантов/optimizer tuning по main или stress. Maxiter120,maxfun2000 per start; new objective counter hard-caps actual likelihood requests. Legacy SciPy nfev может слегка превышать nominal maxfun при differences: фактический счёт публикуется, старый алгоритм не переписывается ради удобства. No hidden jitter; SPD/numerical failures сохранены.

Selected NLL находится в1e−8max(1,|best feasible NLL|) от best recorded practical point. Converged endpoint допускается только в этой tolerance; иначе explicit fallback. Operational valid требует successful selected endpoint/exact linear/analytic inherited solution всех3means; fallback приводит к reject. Полные знаменатели не меняются. Score=min(BICconstant,BICGaussian)−BICPSPL, BIC2NLL+klogn. GP latent values marginalized, hyperparameters optimized; BIC heuristic, не probability/evidence guarantee.

## Freeze и calibration

До calibration/evaluation сохранить main protocol/config, stress protocol/config, generator tests, new runner/pilot verification и clean scientific code. CPU smoke — отдельные development-only IDs, не main первыеN. Перед evaluation policy/source IDs/score hashes/fingerprint отправить в GitHub и подтвердить successful push.

По каждому из5methods один global threshold на complete Gaussian calibration negatives, pooled white/Matérn:480dependent views/240sources. Invalid score=−infinity. Ascending index ceil(.95*n)−1, следующий float выше (ties conservative). Nonfinite selected threshold => explicit no-positive policy. Не выбирать candidate по calibration classification outcomes; здесь выбирается только заранее заданный empirical threshold rule. В дальнейшем не condition threshold на hidden noise/SNR/class/mask.

## Метрики и uncertainty

Каждый9noise/mask scenario/method: counts/recall_all/FPR_all/CP95/coverage/rejects/FPR_accepted/selective risk/balanced FDR, raw score AUC и empirical average precision (AP). AP определяется по grouped ties как sum precision_at_score_group×recall_increment; prevalence synthetic1/2, partner dependence сохраняется bootstrap. AP/AUC — score-ranking diagnostics с finite fallback/sentinel, не probabilities/telescope precision. PR arrays/zero denominators явно сохранены. Brier не считать без probability model.

Primary CI:500percentile source-bootstrap replicates, seed620607. Отдельно resample240cal и360eval, стратифицированно по3seeds; cal noise views и eval counterfactuals держать вместе, одинаковые IDs для всех методов. Refit threshold **только из bootstrap calibration**, не evaluation; сохранить все ΔFPR/Δrecall draws и independent weighted-count recomputation. Additional per-scenario CP conditional on fixed policy; не binomial pooling across masks/noise. Per-seed tables обязательны. Secondary conditions, AP/AUC и legacy/oracle contrasts descriptive, pointwise, без simultaneous error-control claim.

## Artifact и runtime policy

До2CPU workers/1BLASthread, учитывая observed2-core quota; при другом executor записать фактическую quota/RSS. Batches4source units.900s call limit проверяется между batches; сохранять actual overshoot и cumulative runtime. Total fit wall budget calibration1800s/evaluation7200s по всем invocations/resumes; сумма лимитов не обещание compute allocation. Если budget исчерпан до required sources, PARTIAL_RESOURCE_LIMIT/BLOCKED, не полный benchmark, без post-eval shrink/cherry-picking. Перед новым call оценить remaining session/batch cost; не запускать неделимый segment в конце окна.

По development192views/219.16s на1worker ожидаются порядка1.25–1.5CPU-seconds/curve с oracle и I/O, но это лишь экстраполяция.6480eval curves на2-core quota ориентировочно70–90min плюс calibration/verification/checkpoints; новые actual costs могут отличаться. Не создавать платный GPU/compute.

Raw observed t/flux/sigma, separate truth, все selected fits/parameters/start initial+endpoint statuses/counts/failures и source manifests сохраняются в immutable Git shards (не пытаться обходить прежний Releases401). **Для main optimizer trajectories применяется bounded encoding:** сохранять first/best feasible witnesses сθ/coefficients и весь scalar incumbent-NLL history, количество исходных points и явный `full_step_parameters_archived=false`. Все initial/endpoint θ/NLL/messages/nfev сохраняются; не заявлять сохранение/переоценку всех intermediate parameter vectors main. Full development trace57,304points уже проверен/архивирован отдельно. Main verifier независимо проверяет selected/initial/best witness densities/KKT, analytic scale и сохранённые scalar history/selection invariants; это не formal proof всех никогда не записанных probes.

Такой encoding не меняет fitting/score/policy, только serialization. Проектная цель<=50MiB compressed per main phase, shard<=8MiB; измерить actual bytes/source на pre-main smoke. Если persistent storage cap не проходит, пересмотреть **до main data** encoding без изменения алгоритма, с новой code fingerprint и pilot; не начинать невосстановимый опыт. Не удалять единственную копию до remote SHA/hash validation.

## Independent verification и completion

Нужны density via independent SciPy reference, linear KKT/primal/parameter bounds, exact scale-only nesting, policy/code/library continuity, dataflow guard, source uniqueness/disjointness/matching/masks, completed-source checksums, independent metrics/primary-bootstrap counts и corruption/restore controls. Oracle feasible-point control — post-prediction diagnosis, не extra input/practical repair. Publish all failures/negative outcomes, cost and constraints.

W1-COV06-EVAL DONE означает сохранённый полный output, а scientific outcome принимается только после W1-COV06-VERIFY. Main bug discovery не разрешает менять detector и повторять ту же evaluation; сохранить invalid/incomplete outcome и blocker. После этого stress выполняет тот же frozen detector/policy без winner selection.
