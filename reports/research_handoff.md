# AstroML: итоговый handoff — 02.11.2026

Ограниченная исследовательская цель выполнена: обзор выбранных первоисточников, два новых проверенных опыта, отрицательные результаты/ограничения и [рукопись](../defense/manuscript.md). Личная готовность участника, конкурсная регистрация, реальный survey pilot и CV не выполнены и не подразумеваются.

## Главные выводы

- R2: ΔAUCpeak−random=−.3923,95%CI[−.4178;−.3687] при равных58 точках; random40 frozen FPR13.89%, peak40 recall10%. [Отчёт](reconstruction_02.md).
- COV05: primary estimated FPR.83% vs6.39%,recall.28% vs77.22%; ΔFPR−5.56п.п.[−9.72;−2.78], Δrecall−76.94п.п.[−83.89;−70.56]. Совместный критерий пользы не поддержан. [Отчёт](experiment_05.md).
- Estimated correct-mean fits в primary имели55/360PSPL и159/360Gaussian missed feasible improvements. Это exploratory oracle control, не practical исправление. Convergence не удостоверяет global optimum.
- Correct covariance не гарантирует unknown-negative control: OU double-bump oracle FPR51.67%, diagonal8.06%; secondary descriptive outcome. Никаких выводов о всех GP/всех микролинзированиях/чёрных дырах.

## Постоянные scientific snapshots

- [R2 результат/артефакты d8e20b9](https://github.com/Mobzya/astroML/tree/d8e20b920308ecf3985f969e5bf207092a72e9fa/reports), [policy freeze a0eb03b](https://github.com/Mobzya/astroML/commit/a0eb03bc31f664fecffc14171266fe33208a9163).
- [COV05 результат/CI/verifier 37033bb](https://github.com/Mobzya/astroML/tree/37033bb2545e5b7b37c8cdf26c8aa5e13e5a8a63/reports), [code/policy freeze4a94d44](https://github.com/Mobzya/astroML/tree/4a94d440186a34c1a8de4cdc0b76d0f4cd715871).
- [COV raw index](covariance05/artifacts.json), [R2 raw index](reconstruction02/artifacts.json), [COV full restore proof](checks/cov05_complete_restore.json), [scientific freeze audit](checks/cov05_freeze_audit.json), [verification helper hashes](checks/cov05_verification_provenance.json).
- [Источники/реальный охват](../research/literature_matrix.csv), [PDF hashes](../research/reading_notes/source_access.json), [code snapshots ближайших работ](../research/reading_notes/code_sources.json).

87480 COV evaluation fits и6480 R2 fits независимо проверены; COV maxNLL discrepancy6.37e−12. Seed/config/version/source IDs/runtime и все54 method/scenario combinations сохранены. Raw data не являются9720 независимыми событиями: source unit360. Hist2–4 REPORTED_ONLY/oldStage5 UNVERIFIED остаются неизменными.

## Продолжение с новой машины

Не рассчитывать на `/workspace`/`.venv`. Клонировать main, установить requirements-lock и пакет по README; [подробная инструкция](covariance05/REPRODUCE.md). Restore скрипт проверяет ZIP и каждый batch, не перезаписывает папки. Все360 sources/90 data files восстановлены из Git. Release asset upload401 сохранён как ограничение; credentials не менялись, использован обычный разрешённый git push компактных shards.

Не повторять DONE tasks и не запускать второй fitting process. Научные runs завершены; для обычной проверки нужен verifier, не новый fit. Не тюнинговать по закрытым evaluation. Новый optimizer/CV/real-data pilot — новый scope и protocol/namespace, а не продолжение старых таблиц.

## Точный следующий шаг участника

Выполнить из нового checkout команды восстановления/verification из README, выбрать один source из `reports/covariance05/illustrative_cases.json`, объяснить его ошибку и записать личную заметку в contributions. Затем отредактировать рукопись, подготовить конкурсное оформление и зарегистрировать тему/ИУ5 до01.12.2026 по проверенным01.11 правилам. Не выдавать работу Codex за уже проверенный личный вклад. Письма/подача документов не выполнялись.

## Автоматизация

**Пауза подтверждена сервисом02.11.2026 в05:17:32UTC: is_enabled=false.** Изменено только собственное восьмичасовое задание AstroML после успешного push рукописи/handoff1af2b0f. Другие автоматизации не менялись. Очередь полностью DONE; нового автоматического исследования нет. Возобновление с иным scope — отдельное решение пользователя.
