# Как подключить AstroML research kit к Codex

## 0. Что внутри
`CODEX_MASTER_PROMPT_RU.md`: большое инженерное задание.
`AGENTS.md`: постоянные правила репозитория.
`.agents/skills/`: пять собственных skills для физики, статистики, Kaggle, литературы и защиты.
Это **инструкции**, а не установленное приложение и не готовая ML-модель. Их должен прочитать Codex в своём окружении.

## 1. GitHub / Codex Cloud
1. Создай приватный GitHub-репозиторий `microlensing-astroml-research`.
2. Распакуй содержимое архива В КОРЕНЬ репозитория с сохранением скрытой папки `.agents/skills/`.
3. Сделай commit и push. Открой репозиторий в Codex Cloud и отправь: «Прочитай AGENTS.md и CODEX_MASTER_PROMPT_RU.md, затем приступай к разделу 13 мастер-промпта».
4. Если текущая версия Codex не автообнаруживает project skills, попроси агента явно прочесть соответствующие `.agents/skills/<name>/SKILL.md`. Альтернатива — установить каждый skill в `${CODEX_HOME:-$HOME/.codex}/skills/` пользовательского окружения Codex. Возможность и путь зависят от конфигурации; проверь отображаемый список skills.
5. Позволяй запускать внешние команды и передавать данные в Kaggle только в доверенном, изолированном окружении с настроенными разрешениями.

## 2. Установка официального Kaggle CLI и официального skill
В своей контролируемой среде с Python 3.11+:

```bash
python -m pip install -U kaggle
kaggle --help
kaggle auth login
kaggle quota
```

Официальный skill: https://github.com/Kaggle/kaggle-cli/tree/main/skills

Пример ручной установки (в среде, где git и сеть доступны):
```bash
git clone --depth 1 https://github.com/Kaggle/kaggle-cli.git /tmp/kaggle-cli
mkdir -p .agents/skills/kaggle-cli
cp -R /tmp/kaggle-cli/skills/. .agents/skills/kaggle-cli/
```

Не копируй token в репозиторий. Авторизация через OAuth или локальный секрет. Если используешь Codex Cloud, доступ к Kaggle API зависит от политики исходящего интернета и секретов конкретного окружения. Автоустановка/автозапуск не гарантированы.

## 3. Как работать по этапам
- Сначала Codex создаёт научный план, проверяет физику, выполняет CPU tests и baseline; без GPU.
- Затем одобряешь конкретный Kaggle GPU run после проверки квоты и сметы.
- После запуска проверяешь status/logs/artifacts; Codex не должен выдавать план за эксперимент.
- После сравнения проверенных baseline утверждается научная гипотеза и только затем делается «новый» метод.
- Раз в несколько исследовательских итераций открывай `research/decision_journal.md` и проси объяснить каждое решение понятным языком.

## 4. Ограничение Colab
Colab Notebook даёт бесплатный интерактивный доступ к GPU по мере доступности; бесплатные сессии прерываются и ресурсы не гарантированы. Не нужно делать обход тайм-аутов и имитировать присутствие пользователя. Используй готовый notebook как резервный ручной запуск, а не как основу headless-задач.

## 5. Научная добросовестность и права
- Олимпиада требует самостоятельной защиты. Уточни разрешённость применения генеративного ИИ, фиксацию собственного вклада и документы научного руководителя у оргкомитета.
- Новизна, результаты, сроки, оценка и победа не гарантированы.
- Не публикуй токены/датасеты с ограниченной лицензией/приватные файлы.

## 6. Проверенные официальные источники (на 2026-10-23)
- https://olymp.bmstu.ru/ru/engeneering-olymp
- https://olymp.bmstu.ru/ru/FAQ
- https://github.com/Kaggle/kaggle-cli/blob/main/skills/SKILL.md
- https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md
- https://research.google.com/colaboratory/faq.html
- https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
- https://developers.openai.com/plugins/build/skills
- https://rges-pit.org/data-challenge/
- https://huggingface.co/datasets/RGES-PIT/MachineLearning
- https://arxiv.org/abs/2608.19419
