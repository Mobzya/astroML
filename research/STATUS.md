# Состояние проекта — 02.11.2026

Источник: Mobzya/astroML main. Режим: последовательно в этом же чате Codex, без субагентов; запуск каждые8 часов, целевой бюджет около120 минут активной работы, checkpoint примерно каждые20 минут.

## Завершено в новой реализации

- Физическая основа, независимый MulensModel, source-disjoint matched generator,16 unit tests.
- LIT-01/02/03: первичная физика/blending, выбранные likelihood/GP разделы и MicroLIA/Microlensify/code. Реальный охват чтения записан в literature_matrix и заметках.
- R2 протокол, development pilot12 пар, main240 calibration +360 evaluation пар. Frozen policy commit a0eb03b до генерации evaluation. Independent verifier/CI PASS; сырые данные, fits, source manifests и checksums опубликованы.
- Новый R2: AUC complete .99485, random40 .96798, peak40 .57567; paired delta -.39231,95%CI[-.41785,-.36870]. Frozen random40 FPR13.89%; peak40 recall10%. Отчёт reports/reconstruction_02.md. Это synthetic SNR15 white-noise population, не survey performance.

## Текущая задача

**COV-EXPERIMENT IN_PROGRESS**. Protocol/development pilot/calibration complete. Independent8640 calibration fits/counterfactuals/thresholds PASS; frozen policy4a94d44 before evaluation. Evaluation360 sources running, durable checkpoint136/360 in compact ZIP shards and recovery manifest. Restore from Git tested; no need to trust retained workspace. GitHub Releases asset upload returned401; authorized Git storage works, no credential changes.

Scientific fitter remains frozen. Await full evaluation, independent density/metrics/joint-bootstrap verifier; do not tune from held-out scores.

## Статусы исторических материалов

Последняя документированная прежняя стадия4, но прежние исходники/raw artifacts отсутствуют. Старые цифры2–4 по-прежнему REPORTED_ONLY; исторический Stage5 UNVERIFIED. Новые R2 результаты не подменяют старые массивы и не доказывают завершение прежнего Stage5.

## Участник и олимпиада

Выбрана ИУ5, регистрация не подтверждена. Руководителя нет, самостоятельный вариант допускается. Личное понимание и вклад участника пока не проверены. Материалы для обучения и будущей защиты сохраняются отдельно.

Планировщик создан/включён; текущая первая scheduled-сессия началась02.11 около03:15UTC и ещё продолжается. Фактическую историю запусков уточнять по сервису и датированным отчётам, а не по одному last_run_time.
