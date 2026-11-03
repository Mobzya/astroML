# Состояние AstroML — новая неделя разрешена02.11.2026

**Baseline исследование завершено; новая недельная кампания03–09ноября разрешена и автоматизация включена.** Старые DONE остаются закрытыми. [План03–09ноября](WEEK_PLAN_2026-11-03.md), [активная очередь](task_queue.json), [baseline рукопись](../defense/manuscript.md), [baseline handoff](../reports/research_handoff.md).

W1-SETUP DONE: план/очередь/prompt сохранены, update и read-back сервиса подтверждены. 03.11 W1-DIAG-READ DONE: selected primary/code scopes, hashes и математический разбор сохранены. W1-OPT-SPEC DONE: COV06-A design/development config сохранены до кода/данных. W1-OPT-DEV DONE:24development sources/192views/2304selected fits,219.16s; raw artifacts сохранены. W1-OPT-VERIFY DONE:2304fits/57304incumbent points independently checked,maxNLL6.65e−12,6negative controls,29unit tests,48files restored. Один COV06-A принят по numerical criteria; main readiness требует нового protocol/pilot. W1-COV06-PROTOCOL DONE: main design/config сохранены до данных. W1-STRESS-PROTOCOL DONE:6fixed cells/240new sources, inherited policy и toy semantics. Текущая W1-COV06-PILOT IN_PROGRESS; main readiness ещё требует implementation/smoke/verification. Новые COV06/stress эксперименты ещё не выполнялись; это PLANNED scope, не полученные результаты.

## Подтверждённые результаты

- Выбранные первичные физика/blending/likelihood/GP/BIC и ближайшие MicroLIA/Microlensify sections/code: реальный охват и hashes в literature_matrix/reading_notes. Глобальная новизна не заявляется, внешние модели не запускались.
- R2:240 calibration+360 evaluation source pairs,3seeds,SNR15. Freeze a0eb03b до evaluation;6480 fit rows/metrics/CI independent verification PASS. ΔAUCpeak−random=−.3923 CI[−.4178;−.3687]. Frozen random40 FPR13.89%, peak40 recall10%. Raw archives и reports опубликованы.
- COV05:отдельные240cal+360evaluation sources; freeze4a94d44 до evaluation.87480 fit rows/metrics/joint bootstrap PASS,maxNLL error6.37e−12; source/core/policy continuity PASS. Primary estimated FPR.83% vsdiagonal6.39%,recall.28% vs77.22%; joint criterion **не выполнен**. Все primary fits converged, но oracle feasible-point diagnostic обнаружил159/360Gaussian и55/360PSPL missed improvements в estimated mode. Это ограничение конкретной finite3-start реализации, не всех GP.
- Все54 method/scenario combinations, отказы/start/numerical failures, seeds, версии, runtime, checksum и полные raw fits сохранены. Failed first calibration48saved+unsaved next batch раскрыта. Full restore360 sources/90 data files PASS. GitHub Releases asset upload401; компактные ZIP shards успешно сохранены обычным разрешённым push.
- Рукопись/handoff опубликованы1af2b0f; final artifact/link audit PASS.21 unit tests и CI, независимые физические/likelihood проверки. Проверенный outcome не равен global optimum, реальному survey performance или личной готовности ученика.

## Автоматизация

Историческая пауза baseline подтверждена02.11 05:17UTC. Владелец позже разрешил новый недельный scope. Планируется переиспользовать то же задание/чат:03–09ноября06:15/14:15/22:15 Europe/Moscow,COUNT21,120min target. **Включение подтверждено update и peek: is_enabled=true, тот же thread; service updated_at2026-11-02T21:10:15.423066+00:00.** Первое запланированное окно03.11 06:15МСК (03:15UTC), последнее09.11 22:15МСК. Service next_run_time=null; это подтверждение конфигурации, не запуска/доставки, новые21 окна ещё не объявляются выполненными. [Подтверждение](../reports/checks/week_automation_confirmation.json), [точный prompt](automation_prompt.md). Другие задания не меняются. Нельзя считать null next_run_time или старый last_run_time доказательством работы/сбоя. Недельные лимиты/их сброс не наблюдаются.

## Самостоятельная работа участника

Участнику: прочитать рукопись, из нового checkout восстановить COV05 и запустить verifier командами README, объяснить один false positive и записать собственную датированную заметку в contributions. Личный вклад и устная защита пока не проверены. Далее — своя редакция текста, оформление/регистрация и репетиция; новое исследование требует нового scope/protocol.

Выбрана ИУ5, регистрация не подтверждена. Тема/секция до01.12.2026, видео до10.01.2027 по правилам, проверенным01.11; перед подачей перепроверить текущие требования. Письма и заявки не отправлялись.

## Что не завершалось и не доказано

Исторические этапы2–4 остаются REPORTED_ONLY, прежний Stage5 UNVERIFIED. Новые R2/COV05 не восстанавливают прежние raw/code. RF/CNN, CV, внешний telescope pilot, распространённость событий, parameter coverage и идентификация чёрных дыр не проверены. Новый явно разрешённый scope указан в недельном плане; перечисленное не помечается выполненным автоматически.

## Остановка новой кампании

Прежний SYNTHESIS DONE не останавливает новую очередь. W1-HANDOFF выполняется после всего нового scope, фактической блокировки всех полезных задач или в финальное окно; незавершённое остаётся TODO/BLOCKED. Затем пауза только собственного AstroML задания. Старые научные выводы не меняются; numerical development результаты опубликованы; main performance ещё не измерялась.
