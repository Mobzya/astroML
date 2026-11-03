# Журнал решений

## 01.11.2026 — начальная организация

- Публичный Mobzya/astroml-microlensing: выбран пользователем.
- ИУ5: соответствует обработке сигналов, анализу данных и ML; регистрация пользователем отдельно.
- CV после основного результата: выбран пользователем; визуализация входит в демонстратор.
- Исходники прежних опытов не найдены: реконструкция вместо утверждения о восстановленном коде.
- Исторические метрики REPORTED_ONLY; Stage5 UNVERIFIED.
- CPU и полный logdet likelihood; oracle только диагностика.
- Минимальный smoke — один источник, не оценка качества и не основание для scientific claims.
- Численный протокол большого опыта не фиксируется до literature audit, development pilot и расчёта мощности.
- Архивные отчёты сохраняются как evidence; сломанные ссылки в них не переписываются под видимость наличия артефактов.

## 01.11.2026 — публикация и генератор

- Пользователь создал публичный Mobzya/astroML; это новое фактическое имя вместо первоначального astroml-microlensing.
- Первоначальное создание через GitHub CLI отклонено правами интеграции (403). Пользователь создал репозиторий сам; доступ на запись подтверждён.
- Новый генератор PSPL/Gaussian согласует analytic excess FWHM, амплитуду, baseline, cadence, sigma и noise draw. Все views одной пары зависимы.
- Проверка генератора: unit fixtures; научная evaluation ещё не создана/не открыта.

## 01.11.2026 — автоматическое последовательное исследование

Пользователь поручил цикл раз в 8 часов, исключительно в текущем чате Codex, без параллельных агентов. Приоритет — научная часть, без срочной реализации продукта; обязательное сохранение состояния и результатов в Mobzya/astroML. Первая задача LIT-01, затем likelihood/GP и ближайшие ML-аналоги, затем отдельный протокол controlled missingness. Доступность квот не наблюдается; расписание не гарантирует их обновление.

Создание и включение расписания подтверждено инструментом 01.11.2026 19:14 UTC. Задание привязано к текущему Codex thread. RRULE HOURLY/INTERVAL=8, старт 02.11.2026 06:15 Europe/Moscow. Это подтверждение настройки, не доказательство выполнения будущих запусков.

## 01.11.2026 — завершение LIT-01

По запросу пользователя первая задача выполнена сразу в текущем чате. Основной текст L01 и указанные разделы/рисунки L02 прочитаны; статусы не распространены на непрочитанные издательскую версию и контуры. Самостоятельный вклад формулируется как controlled reliability/missingness study; известное blending-вырождение не заявляется открытием. Независимые geometry/scaling controls PASS, без statistical evaluation. Следующий шаг LIT-02; расписание 8 часов сохраняется.

## 01.11.2026 — увеличение бюджета сессии

Пользователь предложил выделять около двух часов на один рабочий промежуток. Целевой бюджет увеличен с 60 до 120 минут активной работы; одна небольшая задача больше не является основанием закончить сессию, если есть доступные задачи и ресурсы. Интервал 8 часов, один чат/агент, научные ограничения и CPU pilot 50 sources/15 минут сохраняются. Checkpoint примерно каждые 20 минут. Точная длительность платформенного выполнения не гарантируется; искусственного ожидания и повторов успешных проверок ради времени нет.

## 02.11.2026 — LIT-02

Проверены конкретные likelihood/GP разделы, не заявляется полное чтение книги. Full Gaussian NLL, Cholesky и Matérn сверены. Negative control показал необходимость logdet; conditional GP illustration не выдаётся за detector performance. Practical covariance должна оцениваться без truth; optimized hyperparameters не означают полную model evidence. Следующая задача LIT-03 выполняется в этой же сессии.

## 02.11.2026 — LIT-03 и переход к R2

Проверены исходная MicroLIA статья2019 (arXiv2020), текущий код и Microlensify2026 в выбранных разделах. Original47 features не смешиваются с current148. Cleaned-test или selected real-positive recovery не заменяют наш frozen source-disjoint negative/positive test. Начинается R2 protocol для SNR15; претензии на глобальную алгоритмическую новизну нет.

## 02.11.2026 — R2 завершён, следующий COV-PROTOCOL

Новый controlled experiment прошёл по preregistered design:600 pairs,3 seeds,SNR15; freeze до evaluation, все raw/fit records сохранены. Эффект peak-vs-random поддержан, но calibration threshold не переносится на random40 (FPR13.89%). Peak40 recall10% при малом FPR нельзя объявлять полезным решением. Выбор covariance/новых методов на этой evaluation запрещён; для следующего опыта нужен новый namespace и development pilot.

### 02.11.2026 04:20 UTC — COV calibration numerical failure

At48/240 saved sources strict JSON rejected inf Gaussian amplitude; source20261122:00000135. NNLS can return infinite coefficient with finite norm for near-zero basis. Preserve failed partial archive/hash; reject nonfinite linear coefficients as numerical objective failure; add regression and restart calibration under new scientific fingerprint. Protocol/bounds/threshold rules unchanged, no evaluation generated or inspected.

### 02.11.2026 04:25 UTC — COV policy freeze

Restart completed240 calibration sources under clean5add9ea; density/KKT/matching/threshold independent verifier PASS8640fits. Three global thresholds committed before new evaluation generation. Calibration24/480 FP each;480 views arise from240 clustered sources. Proceed360 held-out source units, same methods/budget; do not tune from outcomes.

### 02.11.2026 — artifact endpoint unavailable

GitHub Release metadata creation succeeded but assets upload returned HTTP401 Bad credentials. No credential modification/retry via alternate endpoint. Existing authorized git push remains available; preserve compact <=40-source compressed shards and exact recovery manifest in Git. Raw batch files are not committed individually. Scientific method unchanged.

### 02.11.2026 — COV05 completed; SYNTHESIS begins

360-source evaluation/87480 fit rows/CI/metrics verifier PASS,maxNLL error6.37e−12. Freeze continuity and full Git restoration PASS. Primary ΔFPR−.05556 CI[−.09722,−.02778], Δrecall−.76944 CI[−.83889,−.70556]; joint hypothesis unsupported. Covariance estimated pipeline practically fails at this operating point; negative outcome preserved. Exploratory feasible-point failures bound interpretation to finite3-start implementation, not all GP methods. No retuning from evaluation. Begin final manuscript/handoff under existing queue; no new scientific run.

### 02.11.2026 — bounded research handoff and pause

Manuscript/handoff pushed1af2b0f and remote SHA confirmed. Artifact/link audit PASS99links/16archives/90evaluationfiles. Negative COV result preserved; no RF/CV/real-survey work or personal student contribution invented. Own AstroML automation update confirmed is_enabled=false at05:17:32UTC; only this job changed. All queue tasks DONE; future research requires new explicit scope, no repeated DONE evaluation.

## 02.11.2026 — владелец разрешил новую недельную кампанию

После объяснения прежней паузы пользователь поручил самостоятельно определить этапы ближайшей недели и настроить автоматический режим. Это явное разрешение нового scope: optimizer repair + scale-only ablation на новых независимых данных, заранее frozen stress matrix, небольшой внешний data audit и рукопись/защита. Baseline330f242 и его DONE entries не переоткрываются; старые evaluation закрыты для tuning. Подготовлены dependency queue и21 слот03–09ноября,06:15/14:15/22:15 Europe/Moscow,120min target; COUNT21 и финальный handoff ограничивают автономию. Никакой новый научный результат этой настройкой не заявляется. Включение сервиса фиксируется отдельно только после подтверждённого update.

### Подтверждение новой автоматизации

План5b04c94 и exact prompt f976205 pushed до update. Update+private peek подтвердили is_enabled=true, прежний thread, расписаниеDTSTART03.11.2026 06:15Europe/Moscow,HOURLY/INTERVAL8/COUNT21 и тот же prompt. Other automations unchanged. Первое/последнее окно рассчитаны из подтверждённого RRULE; null next_run_time не является proof of execution. Setup DONE; first science W1-DIAG-READ TODO, ни новых experiments, ни новых papers-read не заявлено.

## 03.11.2026 — первая научная сессия новой недели

Checkout/fetch/main6f88ff7, IDLE lease and no known live research runner checked. Acquire unique lease and mark W1-DIAG-READ IN_PROGRESS before scientific reading. Work only code/primary sources/published aggregate motivation; old event-level evaluation and truth closed. Target120min, continue next ready tasks sequentially; no new primary/main data generated at start.

### 03.11 — optimizer diagnosis complete

Selected primary-source scope and current code audit saved. opt.success is local stopping status; initial incumbent not retained and best-converged priority may discard lower finite points. Own scale-only derivation gives clipped sqrt(Q/n), same mean profile. These are mathematical/code claims, no new performance results. Continue W1-OPT-SPEC before coding or new data.

### 03.11 — COV06-A development specification

Freeze one candidate, not a broad hyperparameter search. q0 exact nested scale-only with direct variance coordinate; diagonal observed width starts, stable positive NNLS column scaling, all feasible improvements retained. Selected converged endpoint allowed only within1e−8 relative objective tolerance of best feasible; otherwise flagged fallback/reject.24 new development pairs, logical cap900s. Main protocol/thresholds remain a separate future gate.

### 03.11 — COV06-A development pilot completed

24source units,3seeds,192views; unchanged legacy estimated compared numerically on fresh sources, not old evaluation. Runtime219.16s,1worker/1BLASthread; logical ledger cumulative and raw immutable shards preserved.28unit tests pass. Continue independent verification before performance protocol; no AUC/FPR-based candidate selection.

### 03.11 — COV06-A independent numerical gate PASS

All2304selected fits and57304saved improvements independently verified;6negative controls and full48-file restore pass.29unit tests; explicit fallback retained3diagonal/scale and1newGP fits. New feasible-point diagnostic0/192views vslegacy18/192 on fresh development only; no causal isolated-component or classifier-performance claim. Select the single predeclared candidate using numerical criteria; main/stress protocols still required before calibration/evaluation.

### 03.11 — main COV06 protocol fixed before data

Primary estimated-vs-scale-only OU/complete/Gaussian,FPR reduction with recall noninferiority5pp andcoverage80%; empirical5% calibration,240cal/360eval new sources.5methods including original algorithm only on fresh data and privileged oracle.6480eval observations; double bump belongs to separate pre-main frozen stress matrix. Bounded witness+scalar history storage explicitly excludes full main intermediate vectors, preserves selected fits/starts/failures;<=50MiBphase and8MiBshard gate before main. No old/new evaluation tuning.

## 2026-11-03T04:18:16.913027+00:00 — W1-STRESS-PROTOCOL DONE; PILOT begins

Six cells fixed before main data;240new source units/3seeds, lowerSNR/OU/Matérn/masks/Gaussian+flare+double bump+constant+eclipse-like toys. Inherit same3 practical methods/thresholds, explicit matching exceptions, all-cell CP failure flags, bounded runtime/storage and deterministic generator gate. Protocol completion is not stress execution. Proceed to separate pre-main smoke; no main observations generated.

## 2026-11-03T04:24:43.788448+00:00 — pre-main implementation checkpoint

33unit tests + lint PASS before observations. Separate12source smoke namespace/216views/5arms; planned stop after4sources, archive/restore and resume remaining8 without refitting completed outputs. Cumulative900s logical cap includes both calls. Main source assignment precedes views, owner/process lock/receipts/version/fingerprint checks; logging-only delegation preserves original3-start output/objective calls. Deterministic stress fixtures and corruption examples pass. Bounded first/best+witness/history encoding preserves all decisions. Independent numerical verifier written but not yet run on smoke data. Pre-data development caught/fixed a missing import in logger test; no data were generated by failed unit test.

## 2026-11-03T04:27:20.412900+00:00 — smoke4/12 checkpoint

First call58.35s/4sources/72views/1080selected fits. Independent selected NLL/KKT PASS, but first implementation of separate initial/endpoint active-set reference dropped a tiny nonzero Gaussian column (4.01447NLL discrepancy). Corrected reference with positive column rescaling; added analytic1e-266-column regression. No fitter/candidate/data/policy change, fingerprint unchanged. Corrected4source verifier PASS (maxNLL6.82e-13),1147first/best witnesses and6336initial/end states checked. Save immutable partial shards, then restore and resume8remaining sources. No main data.

## 2026-11-03T04:32:01.325109+00:00 — W1-COV06-PILOT DONE; calibration begins

Actual12sources/216observations/3240selected fits,164.031fit-wall s across2calls (2workers1BLAS). First4 restored from pushed shards and skipped:8output hashes unchanged. Independent selected densities/KKT/bounds/3427first-best witnesses/19008initial-end states PASS;8scientific/admission corruptions detected;24JSONfiles restored. No classification metrics or main data. Lossless ZIP LZMA preserves exact JSON/float bytes and reduces projected eval storage70.1MB(DEFLATE4-source extrapolation) to43.13MB(12-source LZMA), below50MiB cap.34unit tests PASS. Conservative full pilot budget240s, not exact end-to-end. Proceed240source calibration only; freeze/push policy before evaluation.

Queue validator caught stale top-level current_task_id after task transitions (per-task states and lease were correct). Reconciled current/next to W1-COV06-CAL before any main data; validator rerun required. This is metadata correction, not a scientific acceptance proof.

## 2026-11-03T04:42:48.785965+00:00 — calibration live; statistical implementation frozen before evaluation

Calibration live: 176/240sources complete; preserve current PID, do not start second process. Pre-evaluation statistics+independent weighted verifier implemented,38unit tests PASS on fixtures; no evaluation observations. Finish numerical verification/archive/frozen global policy next. Independent metric verifier uses pairwise-score AUC/group-count AP, binomial-tail CP roots and weighted source multiplicities/calibration order statistics, rather than importing producer. Decision-only fixtures (no observations/fits) compare all180tables and3bootstrap test draws. Main design remains500draws. Ancillary tests/code preparation occurred during the same calibration task; actual fit-wall measurement includes executor contention. Remote push CI b6af911 confirmed success run41578721339; initial shortenedSHA filter had incorrectly returned no matching runs. No workflow rerun or auth changes. Archive helper now reuses checksum-validated immutable source shards across partial indexes, avoiding repeated large Git payloads.

## 2026-11-03T04:52:19.166561+00:00 — W1-COV06-CAL DONE; freeze before evaluation

240newcal sources/960views/14400fits,815.832s2calls2workers. Independent density/KKT15313witnesses/84480start states PASS,maxNLL2.27e-12;480files restored.5empirical thresholds independently checked,policySHA4028b724; raw shards7.83MB. Calibration larger than smoke storage estimate, so tested lossless solid ZIP container before evaluation: all480files byte-identical, projection47.71MB<50MiB. Scientific0052cec5 code/config and raw data unchanged; policy/stats committed before evaluation. First eval call only after successful push, no interim classification metrics; preserve partial data before session end.

## 2026-11-03T05:00:22.087967+00:00 — evaluation live; operational checkpoint

Evaluation live 32/360source units, one known fitting parent; do not start second process. Freeze continuity17files/Git objects/version/policy PASS. No interim classifier metrics. On call close archive raw completed clusters, then small continuation only if enough time; final save/release own lease about05:15UTC. Initial generation began only after successful44ec73e push+fetch HEAD/origin match. Frozen fitting/protocol/config/policy unchanged; statistical producer remains locked. Read-only audit verifies17scientific files across actual calibration start,freeze,evaluation start and current; source sets240/360disjoint,versions equal. CI44ec73e success run41580605288. Added portable restore/resume guide, no classifier performance or full-evaluation acceptance claimed. Current raw outputs are local until next closed-call archive; published calibration index/policy available now.

## 2026-11-03T05:06:51.843518+00:00 — first evaluation data checkpoint

Evaluation60/360sources closed first call811.666s;1080curves/16200mean-output records saved in immutable solid shards,120JSONfiles restored. Still IN_PROGRESS, numerical full/subset check not yet run and no classification metrics. After successful checkpoint push, run only2more batches(8sources), then final numerical subset verification/archive/lease release within session. Raw output count is not independent sample count or a scientific performance result. All class/mask/kernel views stay within each source. No code/config/policy/threshold/statistical-producer changes since opening evaluation.

## 2026-11-03T05:15:32.594633+00:00 — partial evaluation saved; final numerical scope

68/360sources archived/restored(136files),1224curves/18360selected fits;923.8776fit-wall s/2calls. Independent selected density/KKT/bounds/19431witnesses/107712start-state references PASS,maxNLL1.82e-12. One failed legacy ABNORMAL endpoint opt.fun != independently evaluated fun(opt.x), preserved as solver metadata; verifier bookkeeping corrected without changing detector/tolerances/policy/data. Fallback/nonconverged flags retained. No classifier metrics. Next: acquire NEW owner+push, restore latest index checkpoint-0068 if missing, preflight exact Python/NumPy/SciPy/fingerprint, resume remaining292sources at index68 under same frozen4028b724 policy. Never rerun completed sources; full360required before statistics/CI. Own lease released; process pools closed and recorded parent/worker PIDs absent. First verifier failure and diagnostic retained. Failed legacy solver opt.fun bookkeeping differs from physical likelihood at returned x; log mismatch, never repair detector or weaken selected-fit density tolerance. All68source selected/witness checks PASS.39unit tests/lint pass. Campaign continues, no week handoff/pause trigger.

## 2026-11-03T11:15:55.907411+00:00 — new same-chat session; resume evaluation

Resume existing W1-COV06-EVAL,68/360sources already durably archived; no known live runner, closed ledger923.8776s andIDLE lease. New unique owner; keep frozen0052cec5 scientific fingerprint,4028b724 policy,Python3.12.14/NumPy2.5.4/SciPy1.18.1. Preflight hashes/input isolation and continue remaining292at source index68 in <=900s calls,2CPU/1BLAS,source batches4,7200s cumulative phase cap. Checkpoint/push about20min and after calls. Do not compute classification metrics until360complete. Then only next dependency-ready task. Unique owner acquired; commit+push before compute. No other agent/chat/research process.
