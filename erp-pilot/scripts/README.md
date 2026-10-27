# `pilot.py` — состояние прогона

Только стандартная библиотека Python 3.10+. Все команды принимают `--dir <папка прогона>` (по умолчанию текущая).

```bash
P="python3 <skill>/scripts/pilot.py --dir .pilot/2026-10-26-lager-filter"

$P init --title-ru "Фильтр по складу" --title-en "Warehouse filter" \
        --repo acme/erp --mode semi-automatic --depth normal
$P set --dashboard-url https://…  --constraint "PR-only" --constraint "миграции применяет администратор"
$P set --helper review=my-review-skill --helper tickets=my-tickets-skill   # роли: interview, tickets, review, diagnose, design

$P phase preflight done --auto-next           # закрыть этап (с проверкой трассировки) и открыть следующий
$P phase requirements done; $P phase briefing start
$P phase briefing skip --auto-next            # допустимо при light; только активный или следующий этап
$P phase spec start --reopen                  # заново открыть закрытый этап (журналируется)
$P phase plan done --force                    # закрыть с пропусками — только по слову пользователя, журналируется

$P req add "Список заказов фильтруется по складу" --source "бриф, абзац 2" --kind functional   # → R-1
$P req note R-1 "Ответ пользователя: склад по умолчанию — из профиля"
$P req set R-1 --spec S-1                     # → specified
$P ticket add "Фильтр по складу в списке заказов" --req R-1 --acceptance "фильтр сохраняется в URL"  # → T-1, R-1 → planned
$P ticket set T-1 --status in_progress --url https://…/issues/12
$P ticket set T-1 --status review             # на ревью
$P ticket set T-1 --status done               # R-1 → implemented, когда все живые тикеты done
$P req set R-1 --status verified              # только при спеке и закрытых тикетах
$P req set R-2 --status dropped --reason "пользователь снял 26.10: не нужно в этом релизе"
$P req set R-2 --status open --reopen         # назад — только с --reopen (reason очищается, запись в журнал)

$P check --phase plan                         # пропуски для этапа; код 1, если есть
$P check                                      # полная трассировка (acceptance)
$P render                                     # → .pilot/<run-id>/dashboard/index.html
$P status; $P req list; $P ticket list; $P log "комментарий в журнал"
```

## Защиты, зашитые в скрипт

| Что | Правило |
|---|---|
| Порядок этапов | `start` только после `done`/`skipped` предыдущего; одновременно активен один этап; повторный `start` закрытого этапа — только `--reopen` |
| Закрытие этапа | `done` запускает проверку трассировки для этого этапа; при пропусках — отказ (код 2). `--force` закрывает с записью `FORCED …` в журнал |
| Пропуск этапа | `skip` — только активный или следующий этап; `requirements` и `acceptance` пропустить нельзя |
| Статусы `R-n` | только вперёд `open → specified → planned → implemented → verified`; `dropped` требует `--reason`; назад — `--reopen` |
| `implemented`/`verified` | нужны спека и живой тикет; `verified` — все тикеты `done`/`dropped` |
| Тикеты | без `--req` не создаются; смена статуса пересчитывает статус требований (`done` всех живых → `implemented`, все `dropped` → назад к `specified`) |
| Markdown-артефакты | `check` ищет `\| R-n \|` в `requirements.md` (с этапа Requirements) и `acceptance.md` (на Acceptance), заголовок `### S-n — R-n` в `spec.md` (с этапа Spec) |
| `init` | подставляет `<run-id>` и дату в шаблоны; не перезаписывает без `--force` |

Что проверяется на каждом этапе — таблица в `references/phases.md`. Полный набор правил покрыт `tests/test_pilot.py`
в репозитории навыка.
