# Дашборд и схема `state.json`

Дашборд — один файл `dashboard/index.html`, в который `pilot.py render` встраивает актуальный `state.json`
(без запросов к сети, работает с диска и как статический сайт). Шаблон — `assets/dashboard/index.html`,
плейсхолдер `__STATE__`. Переключатели: тема (светлая/тёмная, только в памяти страницы — Web Storage в превью запрещён), язык RU/EN,
кнопка «обновить» перезагружает страницу. Таймер активного этапа считается в браузере от `started_at`.

## Рендер и публикация

1. `python3 scripts/pilot.py --dir .pilot/<run-id> render` → `.pilot/<run-id>/dashboard/index.html`.
   Рендер локальный и дешёвый — делай после каждой команды, изменившей состояние.
2. Опубликуй папку `.pilot/<run-id>/dashboard` как статический сайт (платформенный деплой сайта;
   имя сайта = `title.ru` прогона). При повторной публикации обновляй тот же сайт, а не создавай новый.
   Дашборд содержит тексты требований и спецификаций целевого продукта — публикуй только с ограничением доступа
   (приватный артефакт, защищённый хостинг). Если платформа даёт лишь общедоступную ссылку, спроси пользователя
   в Preflight и запиши решение: `pilot.py set --constraint "Дашборд: <публично | приватно | только локальный рендер>"`.
3. Адрес → `pilot.py set --dashboard-url <url>`; он показывается в карточке прогона и в отчёте.
4. Публикуй на каждых воротах, при закрытии этапа и в финале — чтобы в момент любого вопроса к пользователю
   дашборд был актуален. Между этими точками достаточно локального рендера.

## Схема `state.json` (schema 1)

```json
{
  "schema": 1,
  "run": {
    "id": "2026-10-26-erp-pilot-check",
    "title": {"ru": "Проверка ERP Pilot", "en": "ERP Pilot check"},
    "mode": "semi-automatic",
    "depth": "normal",
    "started_at": "2026-10-26T18:56:00+01:00",
    "finished_at": null,
    "repo": "acme/erp",
    "branch": "pilot/2026-10-26-erp-pilot-check",
    "pr_url": null,
    "dashboard_url": null,
    "constraints": ["PR-only", "миграции применяет администратор после слияния"],
    "helpers": {"review": "my-review-skill"}
  },
  "phases": [
    {"id": "preflight", "status": "active", "started_at": "...", "finished_at": null,
     "note": {"ru": "…", "en": "…"}}
  ],
  "requirements": [
    {"id": "R-1", "text": "…", "source": "бриф, абзац 2", "kind": "functional",
     "status": "open", "spec": null, "tickets": [], "note": null, "reason": null}
  ],
  "tickets": [
    {"id": "T-1", "title": "…", "requirements": ["R-1"], "depends_on": [],
     "acceptance": ["…"], "status": "todo", "url": null}
  ],
  "log": [
    {"at": "2026-10-26T18:56:00+01:00", "phase": "preflight", "event": "run created"}
  ]
}
```

### Словари статусов

| Поле | Значения |
|---|---|
| `phases[].status` | `ahead` · `active` · `done` · `skipped` |
| `requirements[].status` | `open` · `specified` · `planned` · `implemented` · `verified` · `dropped` |
| `requirements[].kind` | `functional` · `data` · `ui` · `security` · `ops` · `proposed` |
| `tickets[].status` | `todo` · `in_progress` · `review` · `done` · `dropped` |
| `run.mode` | `manual` · `semi-automatic` · `automatic` |
| `run.depth` | `light` · `normal` · `deep` |
| `run.helpers` | объект `роль → имя навыка`; роли `interview` · `tickets` · `review` · `diagnose` · `design` |

Порядок этапов фиксирован: `preflight, requirements, briefing, spec, plan, development, code_review, acceptance`.
`pilot.py` не даёт открыть этап, пока предыдущий не `done|skipped`, не закрывает этап с пропусками трассировки
и не даёт пропустить `requirements` и `acceptance`. Переходы `R-n` — только вперёд (`open → specified → planned →
implemented → verified`), `dropped` из любого статуса с `reason`; назад — `--reopen` с записью в журнал.

## Тексты карточки этапов (по умолчанию, можно переопределить `--note-ru/--note-en`)

| Этап | RU заголовок / подзаголовок | EN |
|---|---|---|
| preflight | Настраиваю репозиторий и дашборд / Дальше бриф станет требованиями, и ни одно не потеряется до конца | Setting up the repo and the dashboard / Next, the brief becomes requirements, and none of them gets lost before the end |
| requirements | Превращаю бриф в нумерованные требования / Каждое R-n получит источник и дойдёт до приёмки | Turning the brief into numbered requirements / Every R-item gets a source and will reach acceptance |
| briefing | Уточняю неясные требования / Вопросы привязаны к номерам R-n | Clarifying unclear requirements / Questions are tied to R-numbers |
| spec | Пишу спецификацию / У каждого требования появляется решение S-n | Writing the spec / Every requirement gets a decision S-n |
| plan | Собираю план и тикеты / Вертикальные T-n с зависимостями и критериями приёмки | Building the plan and tickets / Vertical T-items with dependencies and acceptance criteria |
| development | Реализую тикеты / Коммиты по T-n, один PR на прогон | Implementing tickets / Commits per T-item, one PR per run |
| code_review | Ревью по двум осям / Стандарты репозитория и соответствие спеке | Two-axis code review / Repo standards and spec compliance |
| acceptance | Приёмка / Каждое R-n проверено или снято с причиной | Acceptance / Every R-item verified or dropped with a reason |

## Визуальные решения (зафиксированы по макету)

- Светлая тема по умолчанию; фон `#f4f5f8`, карточки белые, радиус 20 px, тонкая рамка.
- Карточка активного этапа — индиго `#2f49e0`, крупный таймер справа, под ним «в “<этап>”».
- Полоса прогресса из 8 сегментов: `done` — светлый индиго, `active` — градиент оранжевый→жёлтый, `ahead` — приглушённый.
- Чипы режима и глубины — pill с рамкой; логотип `ERP` + чёрный блок `Pilot`.
- Типографика Inter (системный fallback), крупный заголовок 32 px, текст таблиц 14 px, переносы в ячейках.
