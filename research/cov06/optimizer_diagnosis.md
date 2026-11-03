# W1-DIAG-READ: почему convergence не гарантирует хорошего competing fit

03.11.2026. Это кодовый/литературный аудит и собственные математические выводы, **не новый эксперимент**. Читались scientific implementation и первичные источники, перечисленные ниже. Старые R2/COV05 event-level observations/predictions/truth не открывались; опубликованный aggregate negative finding используется только как мотивация. Ни новая частота провалов, ни FPR/AUC здесь не оценивались.

## Что реально прочитано

- Byrd/Lu/Nocedal/Zhu: авторский *A Limited Memory Algorithm for Bound Constrained Optimization*, **NAM-08, revised May1994**, PDF2–4 (printed1–3), §§1–2; cover/PDF4 visual. Related journal DOI10.1137/0916069 относится к1995, но журнал отдельно не прочитан. Прочитанный report описывает quadratic model, projection/active bounds и feasible line search с sufficient decrease; здесь не получена гарантия global optimum. Более поздние разделы и performance tables не читались.
- SciPy1.18.1: `_lbfgsb_py.py` options/return-status loop и весь Python wrapper `_nnls.py`. Installed files byte-equal release-tag files; immutable upstream commit указан в source_access. `ftol` контролирует relative improvement, `gtol` — projected gradient. Maxfun может быть превышен при numerical differentiation; budgets проверяются после итерации. Compiled internals не аудированы.
- GPML §5.4.1, book112–113: повторно использован уже прочитанный source для различения integrated latent GP и optimized hyperparameters; новое полное чтение книги не заявляется.
- Golub/Pereyra1973, DOI10.1137/0710036: **только publisher abstract**. Он рассматривает устранение unconstrained linear coefficients и constant-rank derivative framework. Нельзя приписать ему smoothness theorem для changing NNLS active sets.

[Версии, scopes, SHA256 и immutable code links](../reading_notes/cov06_source_access.json). Полные чужие тексты/код не перепубликуются.

## Наблюдаемая архитектура старого кода

Ссылка: [covariance.py at6f88ff7](https://github.com/Mobzya/astroML/blob/6f88ff7c37470d5e92e8542b590013be4f537d8c/src/microlens/covariance.py).

1. Для Gaussian три mean starts имеют widths.05/.15/.2 от observed span; center — observed argmax либо.5span. Noise starts сопоставлены через `zip`: это3 совместных старта, не9 Cartesian combinations. Hidden t0/class нигде не используются.
2. Gaussian design=[exp(−(t−center)²/(2width²)),1]. Center допускается за observed interval, width может быть узким. На удалённых/узких basis signal column может численно исчезнуть. Это допускаемые параметры, не автоматически нарушение bounds.
3. `profile_linear` whitened NNLS не нормирует columns. Finite coefficients/norm/NLL guard уже существует; exceptions становятся objective penalty1e100. Такой penalty не является statistical likelihood, и endpoint с ним исключается из доступных кандидатов.
4. В candidates сохраняются только конечные endpoints. Начальная допустимая NLL и промежуточные допустимые points не образуют сохраняемого incumbent. Затем **лучший converged endpoint предпочитается всем finite nonconverged endpoints**, даже с меньшей NLL. Это точное свойство выбора в строках154–155, не доказательство, что такое предпочтение объясняет все прежние провалы.
5. `opt.success` берётся из solver stop status. В старом вызове ftol=1e−10, gtol не переопределён (SciPy default1e−5), numerical differences без jac. Ни projected-gradient, ни relative-improvement stop сами по себе не удостоверяют global best model.
6. Положительный amplitude floor1e−4 в log-coordinate не содержит точный GP amplitude0. Поэтому «estimated family точно включает diagonal case» нельзя утверждать без оговорки/новой параметризации.

## Собственный анализ: локальная плоскость

При fixed covariance обозначим Gaussian mean `m=b+a*g(theta)`, a≥0. Пока NNLS active face a=0 сохраняется в некоторой окрестности, optimal baseline и residual не зависят от shape theta; profiled objective там постоянна. В частности direct derivative `∂m/∂theta=a∂g/∂theta` равна0. Joint optimizer может завершиться на такой плоскости после оптимизации noise parameters, хотя в другом basin существует лучшее объяснение. На переходах active set smoothness нельзя предполагать без проверки.

Это возможный механизм, следующий из модели/кода. Он не устанавливает эмпирическую долю, единственную причину всех published failures или общий дефект L-BFGS-B. GP noise способен конкурировать с mean; это отдельный statistical tradeoff, который нельзя смешивать с доказанным numerical missed point. Улучшение optimizer не гарантирует classification gain.

## Собственный анализ: допустимая точка и selection

Если вычислены finite feasible points P для одного и того же mean/noise family, сохранение `min_{p∈P}NLL(p)` гарантирует non-worsening относительно **этих вычисленных практических points**. В P можно включить observation-only initial warm points и finite iterates, а не generator truth. Гарантия не относится к неизвестному global minimum и не разрешает скрыто переименовывать nonconverged candidate в converged.

Нужны отдельные поля: chosen point origin, actual solver flag, fallback/incumbent use и operational validity. Best objective и convergence — разные измерения. Простое уменьшение tolerance или увеличение числа starts без такого учёта не доказывает устранение локального провала.

## Собственный анализ: scale-only — сильный дешёвый comparator

Пусть D=diag(sigma_report²), C=s²D, s∈[.5;3]. Для fixed shape θ NNLS coefficients не зависят от positive common s: whitened residual norm только умножается на1/s. Если `Q=||D^(−1/2)(y−Xβ)||²`, то

`NLL(s)=Q/(2s²)+n log(s)+.5 logdet(D)+(n/2)log(2π)`.

Следовательно, `s_hat=clip(sqrt(Q/n),.5,3)`. Profile NLL строго возрастает по Q (derivative1/(2s_hat²)>0), поэтому оптимальная mean shape та же, что при reported diagonal, в рамках одинаковых bounds/NNLS family. При конечной оптимизации можно **переиспользовать diagonal fitted point** и честно унаследовать его flags. Это не даёт global-optimum certificate, но изолирует gain от общей variance rescaling. Parameter count+1, не+3.

## Проверяемые требования к следующему design

- Неотрицательность, finite decoded coefficients, full density/logdet и KKT проверяются независимо. Positive column rescaling сохраняет NNLS cone в точной арифметике; near-zero и exact-zero columns требуют раздельной документированной политики. Нельзя молча обрезать огромную амплитуду и считать NLL прежней.
- Новый fitter сохраняет initial feasible incumbent и все finite candidate outcomes; selected NLL не хуже каждого saved candidate с указанной tolerance. Convergence и rejection/fallback фиксируются отдельно до calibration.
- Warm start берётся из observed diagonal/scale-only solution, без hidden labels/true duration/covariance. Если модель noise допускает variance q=0, exact nested diagonal/scale-only limit механически проверяется. При amplitude² параметризации derivative по amplitude у0 исчезает; variance-coordinate q устраняет именно это искусственное нулевое направление, не все local minima.
- Scale-only analytic estimate сверяется с независимым bounded scalar minimizer и Gaussian density; совпадение mean profile/limits проверяется на новых deterministic/development fixtures.
- Development candidate выбирается по numerical invariants/feasible improvements/стоимости. Нужны новые independent data и заранее frozen performance protocol; никакого выбора по старым или новым evaluation scores.

Следующий этап — W1-OPT-SPEC: конкретные parameterization, starts, budgets, selection/fallback semantics и regression criteria до нового code/development data. Сейчас ни один из кандидатов ещё не реализован и main evaluation не создана.
