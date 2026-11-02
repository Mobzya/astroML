# Настройка недельного этапа AstroML — 02.11.2026

Пользователь после проверки прежней паузы явно поручил самостоятельно определить этапы недели и включить автоматический режим. Работа этой настройки — планирование/очередь/валидация/настройка сервиса. **Новых научных опытов или прочитанных новых статей здесь не заявляется.**

## Основание и разрешённый scope

Прочитаны актуальные GitHub main330f242, AGENTS, AUTONOMOUS_RESEARCH, STATUS, очередь, decision_log, README/research_plan/recovery audit и релевантные skills. Checkout найден по remote Mobzya/astroML; рабочее дерево изначально чистое, fetch подтверждён. Исходные завершённые10 tasks скопированы без изменения в research/campaigns/baseline_2026-11-02_queue.json. Среда доступна, текущая network policy unrestricted/enforced; secret values не читались. Известных живых предыдущих Python research runners в текущем workspace не обнаружено; service history null не использовалась как доказательство отсутствия запусков.

Новая campaign week-2026-11-03-09: numerical diagnosis/literature → observation-only optimizer design/development/verification → scale-only ablation/COV06/stress protocols → CPU pilot → новая calibration/policy freeze → independent evaluation/verifier → bounded frozen stress → data feasibility audit → рукопись/защита/handoff. Максимум2 development candidates, отдельные новые namespaces, старые evaluation закрыты для настройки. UI/CV/платные ресурсы/письма/массовые загрузки не включены.

## Проверки настройки

- validate_week_plan.py проверяет DAG, статусы, сохранность baseline, ready selection и21 occurrence с8h interval. Negative controls: duplicate IDs, cycle, reopened baseline отвергаются; после setup выбирается W1-DIAG-READ, в финальное окно — W1-HANDOFF.
- Baseline handoff audit ограничен своей завершённой snapshot, чтобы новые TODO не выдавались за ошибку прежней науки. Архивы/fit rows/старые verification helper hashes не изменены.
- Ruff проверяет код; scientific experiment, fitting или повтор DONE этим validator не выполняются.
- Инструкции session lease/checkpoint/возобновления и новый finite stop condition сохранены; старый SYNTHESIS DONE не выключает новую кампанию.

## Запрошенное расписание

Переиспользуется одно существующее задание этого чата. План03–09ноября2026,06:15/14:15/22:15 Europe/Moscow; RRULE HOURLY/INTERVAL8/COUNT21. Первое запланированное окно03.11 03:15UTC; последнее09.11 19:15UTC; целевой финал последнего окна09.11 21:15UTC. Около120min активной работы, checkpoint примерно20min.21 slots — расписание, не обещание выполненных сессий/доступности лимитов.

План/queue/prompt успешно отправлены5b04c94/f976205 до update. Сервис подтвердил включение и read-back того же thread с COUNT21; new prompt совпадает с сохранённым файлом. W1-SETUP DONE, следующий W1-DIAG-READ TODO. [Подтверждение](checks/week_automation_confirmation.json), [readiness/календарь](checks/week_2026-11-03_plan.json). Новые campaign executions ещё не объявлены; next_run_time=null не трактуется как delivery ack. Пауза baseline была корректным прежним состоянием, а не подтверждённым сбоем планировщика. Недельный/5h quota не виден; ошибки доступа/квот не обходятся.
