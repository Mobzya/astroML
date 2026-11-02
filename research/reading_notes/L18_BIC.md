# L18: BIC и границы применимости — COV05 interpretation audit

G. Schwarz (1978), *Estimating the Dimension of a Model*, Annals of Statistics6(2),461–464, DOI[10.1214/aos/1176344136](https://doi.org/10.1214/aos/1176344136). Прочитан извлечённый основной текст §§1–3, PDF2–4=journal461–463, refs PDF5; страницы461–462 также визуально. PDF1 — JSTOR cover. Формулы извлечены частично неверно; основной критерий и proposition сверены визуально. Доказательство лемм не сертифицировано независимо. URL/hash/охват сохранены в source_access и matrix; PDF не перепубликуется.

Критерий максимизирует log maximized likelihood−(k/2)log n, эквивалентно минимуму2NLL+klog n. Это large-sample expansion. В статье явно рассматриваются iid observations, линейные submanifolds exponential family и локально положительные bounded prior densities. Основной remainder bounded в n при заданных условиях.

**Применение к AstroML — наша оценка:** finite96/58 correlated observations, nonlinear mean, nuisance GP и parameter boundaries не являются прямой областью этой теоремы. Поэтому численно правильно посчитанный BIC-score остаётся эвристикой; density verifier не доказывает Bayesian evidence, global optimization или FPR guarantee. Успех оценивается отдельной source-disjoint evaluation с frozen calibration. Протокол и метод по этому дополнительному чтению не изменены.
