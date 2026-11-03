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
