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
