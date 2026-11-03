# W1-OPT-SPEC: COV06-A, specification before implementation/data

03.11.2026. Основание: [source-grounded diagnosis](optimizer_diagnosis.md). Это development specification, не performance protocol и не результат опыта. Main calibration/evaluation ещё не генерируются. Старый код/конфиги/outputs остаются неизменными.

## Один кандидат и отделённые baselines

Выбирается **одна** заранее описанная версия `COV06-A`: observed diagonal warm start, exact zero-variance nested case, scaled NNLS и retained feasible incumbent. Второго поискового варианта сейчас нет; methodological revision требует новой явно сохранённой design version до evaluation, с сохранением потраченного development бюджета. Правки ошибок реализации не являются поводом скрывать прежние failed outputs.

Новый модуль `src/microlens/covariance06.py`. Practical bundle получает только Observations+фиксированные resource options, вычисляет diagonal/scale/estimated с общим diagonal initialization. Отдельная oracle-ветвь принимает privileged C; practical API отвергает её. Source/class/noise labels, true sigma/t0/duration/SNR/clean means не аргументы inference. Original3-start estimated algorithm — unchanged import для numerical comparator на **новых** sources, не повтор старой evaluation. Как arms включать в main, решит последующий protocol до main данных.

## Общие mean families, bounds и наблюдаемые starts

Constant: один coefficient b≥0. PSPL: Fs,Fb≥0; shape logu0/normalized center/log(tE/span), u0[.01;3], center[-1;2] относительно min(t)/span, tE/span[.001;2]. Gaussian: amplitude,baseline≥0; center[-1;2], width/span[.001;2]. Counts1/5/4. Fits используют полный normalized flux, baseline=1 из truth не передаётся.

Diagonal/oracle nonlinear mean engine: три прежних deterministic shape starts плюс не более3 observation-derived starts (итого<=6, точные дубликаты убрать). Observed center = argmax(flux), baseline = median(flux). При positive observed excess H отметить точки выше baseline+H/2; estimated FWHM = span этих точек+median positive cadence. При отсутствии usable excess/cadence —.1observed span. Clip FWHM/span [.002;2]. Gaussian extra widths — FWHM/(2sqrt(2log2)) ×[.5,1,2], clipped в bounds; center observed. PSPL extra u0[.15,.5,1.5], tE=observedFWHM/pspl_fwhm(u0,1), clipped. Это initialization, не измерение истинной длительности.

Ни zero amplitude, ни center вне observed interval не запрещаются постфактум: такой fit может быть локально допустим. Нельзя выбирать старт/границу по generator truth или classification outcomes.

## Scaled nonnegative linear profile

Whiten X,y через Cholesky C=LLᵀ. Для каждого неzero column вычислить стабильный positive Euclidean norm: maxabs×sqrt(sum((column/maxabs)²)); нельзя возводить subnormal column в квадрат до scale. Решать NNLS для нормированных columns и восстанавливать β=gamma/norm. Exact-zero columns удалить с coefficient0; small-but-nonzero columns не отсекать epsilon-порогом. Если decoded β/mean/residual неfinite или norm reconstruction несогласованна — явный numerical failure, не clipping.

Recompute whitened residual norm/Q из solution, не доверять одному norm из NNLS. NLL=Q/2+sum(logdiagL)+(n/2)log2pi. Не скрывать jitter. Проверка: primal β≥0, independent KKT и Gaussian density по сохранённым coefficients. Column scaling сохраняет feasible cone в точной арифметике, но finite-precision проверки всё равно обязательны.

## Scale-only baseline

После diagonal profile с Q: s_hat=clip(sqrt(Q/n),.5,3). Та же shape/coefficients и их वास्तविक flags; NLL=Q/(2s_hat²)+nlog(s_hat)+sum(log sigma_report)+(n/2)log2pi. Scale profiling монотонно по Q; не требуется второй shape search. BIC signal count+1. Runtime отделяет shared diagonal initialization от дешёвого scale update.

## GP parameterization и warm starts

C=diag((s sigma_report)²)+q median(sigma_report)² K_Matern32(ell).

s∈[.5;3] в log coordinate; **q∈[0;16] прямо как relative variance**, ell∈[1;120]дней в log coordinate. При q0 есть точное C=s²D; derivative C по q не исчезает искусственно из-за amplitude² at zero. q0 делает ell неидентифицируемым — сохранять flag/оговорку, count noise parameters3 остаётся BIC heuristic.

Для каждого mean shape — его observed diagonal selected point. Три фиксированных noise starts `(s_hat,q,ell)`:

1. `(s_hat,0,12)` — exact scale-only feasible incumbent;
2. `(s_hat,.25,3)`;
3. `(s_hat,1,40)`.

Все три joint shape/noise optimizations имеют те же mean/noise bounds; starts не меняются по noise/class label. Если diagonal mean unavailable, estimated mean unavailable с явным initialization failure; не подставлять truth. Constant mean имеет noise-only optimization. Oracle использует fixed known C и общий<=6-start mean engine, не участвует в выборе practical candidate.

## Feasible incumbent, convergence и operational meaning

Перед minimize оценить initial point; сохранять каждый finite улучшивший objective point и начальные/конечные данные каждого start. Best finite candidate нельзя потерять из-за priority к худшему converged endpoint. Для сравнения numerical-equivalent points tolerance δ=1e−8×max(1,abs(best_feasible_NLL)).

Если есть реально converged endpoint с NLL<=best_feasible+δ, выбрать лучший из них; selected optimizer_success=True. Иначе выбрать лучший feasible point, fallback_used=True, optimizer_success=False. Таким образом selected NLL не хуже saved feasible incumbent+δ. Solver status не переписывать, flags всех starts сохранять. На finite-difference probes может появляться незначительно меньшая NLL; tolerance не должна отвергать хороший endpoint лишь из-за такого rounding-scale отличия.

Для development operational validity требует доступности и optimizer_success всех competing means; fallback приводит к reject и учитывается в полном знаменателе. Scale mode наследует mean flags diagonal и имеет analytic scale flag. Score=min(BIC_constant,BIC_Gaussian)−BIC_PSPL. Diagnostic raw score может использовать finite fallback, но operational metrics обязаны показывать coverage/rejections. Эту policy можно заморозить/уточнить в performance protocol только до evaluation и без использования evaluation outputs.

Хранить source-input hash, exact shape/noise parameters, β,Q,NLL,BIC, selected origin, best saved feasible point, initial incumbent NLL, δ/gap, solver messages/nit/nfev, failures by type/count и feasible-improvement trace. Нельзя объявлять global optimum или улучшение FPR по numerical guard.

## Compute caps и reproducibility

Фиксированные maxiter120; maxfun2000 на start, один BLAS thread. Hard objective-evaluation counter и optional monotonic deadline guard прерывают start с явным budget flag; SciPy maxfun может превышаться без внешнего guard. Global logical development pilot cap900s (включая любой resume/retry), внешний supervisor<=890s с резервом на сохранение. Полный objective penalty не считать доступным fit. Не запускать main ради измерения runtime.

Development config `configs/cov06_development.json`: новый namespace,24sources (3seeds×8), SNR15,n96, white/Matérn+reported sigma bias. PSPL/Gaussian × complete/peak40,8views/source. Proposed practical diagonal/scale/estimated плюс unchanged old3-start numerical comparator; known truth только отдельная oracle диагностика. Save raw records отдельно от truth. Один CPU worker первоначально; measured cost решит main workers/budget позднее. Во всём pilot sources независимы только по latent pair, а не views.

## Критерии следующей numerical verification

- All finite saved means satisfy bounds/primal feasibility, full density and independent KKT; stable near-zero design must not silently produce inf coefficients.
- Analytic scale solution agrees с independent bounded scalar NLL search; means unchanged, correct +1 parameter count.
- Selected NLL<=every saved feasible improvement+δ и exact nested scale-only candidate+δ. Forced lower nonconverged point не выдаётся за converged.
- q0 covariance exactly diagonal scaled; practical API rejects known C; input contains only t/flux/sigma.
- Tests include flat/boundary/duplicate-time/nearzero-column conditions and corruption negative controls; not just successful data examples.
- Development numerical gaps/cost report по всем source conditions/seeds без classification AUC/FPR selection. Старые event-level evaluation закрыты. PASS означает проверенные numerical claims в этих cases, не proof of global convergence или будущую scientific victory.

При невозможности этих gates сохраняется blocker и неизменённый отрицательный outcome; к main нельзя переходить без W1-OPT-VERIFY DONE. Calibration/evaluation и stress protocol идут отдельными следующими задачами очереди.
