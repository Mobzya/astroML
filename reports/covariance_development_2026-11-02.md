# Covariance development pilot — 02.11.2026

До данных сохранён design commit7f8127f. Исполнялся clean code bec0e7d8a295df9d6e5ba0f1a4d3d99ac7091f05. Это только feasibility и numerical correctness, не оценка detector performance.

4 независимых source units,2 noise settings,2 signal families,complete/peak views:32 observations ×3 modes=96 method sets,288 competing mean fits. Runtime14.80s на одном процессе/одном BLAS thread. Для всех96 sets нашёлся converged start каждого mean; numerical exceptions0.

Independent SciPy density + linear-profile KKT verifier PASS:288 fits, max NLL difference6.394884621840902e-13. White-control oracle и diagonal NLL совпадают. Проверен запрет privileged covariance в practical API.19 unit tests прошли. Были исправлены ошибки development-скрипта до фактического запуска; failed formatting/parse attempts не выдаются за результаты.

[Raw archive](examples/covariance-development-v1.zip), [summary/SHA256](checks/covariance_development_summary.json), [verifier](checks/covariance_development_verifier.json). Случайная covariance main evaluation не создана. Качество классификации по этому pilot не использовалось для выбора thresholds или заявления победы метода.

Измеренная стоимость позволяет планировать600 новых sources; calibration subset будет меньше evaluation по числу noise/mask cases. Фактическое время неизвестно заранее; основной run ограничен900s на вызов с возобновлением. Следующий шаг — frozen COV protocol/config и независимый общий runner/verifier.
