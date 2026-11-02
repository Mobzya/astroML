# Состояние AstroML — новая неделя разрешена02.11.2026

**Baseline исследование завершено; новая недельная кампания подготавливается к включению.** Старые DONE остаются закрытыми. [План03–09ноября](WEEK_PLAN_2026-11-03.md), [активная очередь](task_queue.json), [baseline рукопись](../defense/manuscript.md), [baseline handoff](../reports/research_handoff.md).

Текущая настройка: W1-SETUP IN_PROGRESS. Следующая научная задача после подтверждённого включения — W1-DIAG-READ. Новые COV06/stress эксперименты ещё не выполнялись; это PLANNED scope, не полученные результаты.

## Подтверждённые результаты

- Выбранные первичные физика/blending/likelihood/GP/BIC и ближайшие MicroLIA/Microlensify sections/code: реальный охват и hashes в literature_matrix/reading_notes. Глобальная новизна не заявляется, внешние модели не запускались.
- R2:240 calibration+360 evaluation source pairs,3seeds,SNR15. Freeze a0eb03b до evaluation;6480 fit rows/metrics/CI independent verification PASS. ΔAUCpeak−random=−.3923 CI[−.4178;−.3687]. Frozen random40 FPR13.89%, peak40 recall10%. Raw archives и reports опубликованы.
- COV05:отдельные240cal+360evaluation sources; freeze4a94d44 до evaluation.87480 fit rows/metrics/joint bootstrap PASS,maxNLL error6.37e−12; source/core/policy continuity PASS. Primary estimated FPR.83% vsdiagonal6.39%,recall.28% vs77.22%; joint criterion **не выполнен**. Все primary fits converged, но oracle feasible-point diagnostic обнаружил159/360Gaussian и55/360PSPL missed improvements в estimated mode. Это ограничение конкретной finite3-start реализации, не всех GP.
- Все54 method/scenario combinations, отказы/start/numerical failures, seeds, версии, runtime, checksum и полные raw fits сохранены. Failed first calibration48saved+unsaved next batch раскрыта. Full restore360 sources/90 data files PASS. GitHub Releases asset upload401; компактные ZIP shards успешно сохранены обычным разрешённым push.
- Рукопись/handoff опубликованы1af2b0f; final artifact/link audit PASS.21 unit tests и CI, независимые физические/likelihood проверки. Проверенный outcome не равен global optimum, реальному survey performance или личной готовности ученика.

## Автоматизация

Историческая пауза baseline подтверждена02.11 05:17UTC. Владелец позже разрешил новый недельный scope. Планируется переиспользовать то же задание/чат:03–09ноября06:15/14:15/22:15 Europe/Moscow,COUNT21,120min target. **Сейчас ENABLE_PENDING; подтверждения включения ещё нет.** Другие задания не меняются. Нельзя считать null next_run_time или старый last_run_time доказательством работы/сбоя. Недельные лимиты/их сброс не наблюдаются.

## Самостоятельная работа участника

Участнику: прочитать рукопись, из нового checkout восстановить COV05 и запустить verifier командами README, объяснить один false positive и записать собственную датированную заметку в contributions. Личный вклад и устная защита пока не проверены. Далее — своя редакция текста, оформление/регистрация и репетиция; новое исследование требует нового scope/protocol.

Выбрана ИУ5, регистрация не подтверждена. Тема/секция до01.12.2026, видео до10.01.2027 по правилам, проверенным01.11; перед подачей перепроверить текущие требования. Письма и заявки не отправлялись.

## Что не завершалось и не доказано

Исторические этапы2–4 остаются REPORTED_ONLY, прежний Stage5 UNVERIFIED. Новые R2/COV05 не восстанавливают прежние raw/code. RF/CNN, CV, внешний telescope pilot, распространённость событий, parameter coverage и идентификация чёрных дыр не проверены. Новый явно разрешённый scope указан в недельном плане; перечисленное не помечается выполненным автоматически.
