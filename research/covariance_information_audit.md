# COV05: аудит доступной информации и сравнений

Проверены конкретные функции scientific snapshot [5add9ea5ea16b59fc33706def4afcf3bfef784c5](https://github.com/Mobzya/astroML/tree/5add9ea5ea16b59fc33706def4afcf3bfef784c5), совпадающего по scientific fingerprint с freeze/evaluation4a94d44. Это локальный аудит реализации, не формальное доказательство безопасности произвольного будущего кода.

## Канал информации

| Этап | Доступ | Роль |
|---|---|---|
| source_manifest/generate_pair | namespace/seed/source split; latent physics/nuisance | Генерация disjoint sources до views |
| source_views | истинные clean means/sigma/noise C/center/masks | Создание контрфактических наблюдений; true peak используется только здесь для вмешательства |
| Observations | t,flux,sigma_report | Единственный практический вход |
| fit_covariance_models diagonal | Observations, фиксированный optimizer budget | C=diag(sigma_report²) |
| fit_covariance_models estimated | Observations, тот же mean family/budget | s,a,ell оцениваются отдельно под каждым mean |
| fit_covariance_models oracle | Observations + явно privileged true covariance | Диагностический контроль, не практический кандидат |
| calibration analysis | source IDs, Gaussian negative labels, converged scores | Единственный источник threshold; две noise views остаются одним source cluster |
| evaluation analysis/verifier | frozen policy, outcomes/labels; отдельно generator truth только для проверок | Метрики/контроль корректности после prediction; не fit и не подбор |

`compute` в [runner](https://github.com/Mobzya/astroML/blob/5add9ea5ea16b59fc33706def4afcf3bfef784c5/scripts/run_covariance05.py) передаёт known=true_c только при mode=oracle, иначе None. Оно не передаёт fit-функции family/noise/condition/source_id/SNR/t0/clean means. Сам fitter дополнительно отвергает non-None covariance в любом practical mode. Unit regression проверяет этот guard. [Generator](https://github.com/Mobzya/astroML/blob/5add9ea5ea16b59fc33706def4afcf3bfef784c5/src/microlens/cov_simulation.py) сохраняет truth отдельно от observation records.

Начальные mean centers берутся из argmax наблюдаемого flux или фиксированного положения в наблюдаемом span; истинный t0 не используется. s/a/ell starts одинаковы для всех классов и noise scenarios. Global threshold выбирается отдельно на метод и затем не зависит от hidden noise/family/mask. Oracle отдельно получает knowledge kernel/true sigma по дизайну; этот контроль нельзя объявлять observation-only улучшением.

## Справедливость и границы

- Внутри COV05 одна и та же observation идёт всем трём режимам. Constant/PSPL/Gaussian имеют одинаковую covariance family внутри режима и одинаковые3 mean/noise starts. Estimated fit имеет больше параметров и большую вычислительную стоимость; это не равный CPU-time benchmark.
- True Matérn представлен в practical family: s=1/.65, a/median(report_sigma)=.8/.65, ell12 находятся внутри bounds. White limit приблизителен из-за positive amplitude floor. OU имеет иной kernel, а не только новую реализацию Matérn; это ограниченный model shift, не все реальные systematics.
- R2 использует другой optimizer и9 starts. Между R2 и COV05 нельзя приписывать разницу метрик только covariance. Primary effect estimated−diagonal сравнивается на общих COV05 источниках и предзаданном OU/complete/Gaussian scenario.
- Peak40 — generator intervention по истинному center, одинаковая для matched классов. Это не алгоритм поиска peak по наблюдениям и не модель случайной survey selection. Длительность пробела может косвенно указывать возможный центр, но detector не получает отдельного t0/label input.
- Baseline/peak excess/analytic FWHM согласованы до конечного sampling. У double bump совпадает outer FWHM и envelope center; максимумы расположены иначе. Observed maximum после шума/пропусков не обязан совпадать ни между классами, ни с analytic peak.
- Calibration/evaluation split source-level. Один noise draw и его masked/class/kernel views — один кластер;360 sources не превращаются в9720 независимых событий. Факт совпадения noise draws, masks, reported sigma и white oracle/diagonal проверяет independent verifier.

## Чего аудит не доказывает

Не доказывает global nonlinear optimization, корректность Gaussian/noise assumptions для телескопа, Bayesian interpretation BIC или event prevalence. Практические FPR/recall могут проиграть даже при корректном канале информации и density. Внешняя проверка, оценка параметров линзы, реальные отрицательные классы и CNN в COV05 не выполнены.

**Метка negative относится к синтетической PSPL-vs-alternative задаче.** В частности, double bump здесь — заданная сумма Gaussian, а не утверждение, что всякая реальная двухпиковая кривая не является линзированием. Binary-lens/finite-source/parallax events и переменные звёзды требуют иной модели/разметки. Эта работа не оценивает completeness детектора всех физических видов микролинзирования.
