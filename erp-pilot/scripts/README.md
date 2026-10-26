# `pilot.py` — состояние прогона

Только стандартная библиотека Python 3.10+. Все команды принимают `--dir <папка прогона>` (по умолчанию текущая).

```bash
P="python3 <skill>/scripts/pilot.py --dir .pilot/2026-10-26-erp-pilot-check"

$P init --title-ru "Проверка ERP Pilot" --title-en "ERP Pilot check" \
        --repo AndreyVomKeg/trid-erp-supabase --mode semi-automatic --depth normal
$P set --dashboard-url https://…  --constraint "PR-only" --constraint "миграции только из main"

$P phase preflight done --auto-next           # закрыть этап и открыть следующий
$P phase requirements done; $P phase briefing start
$P phase briefing skip --auto-next            # допустимо при light

$P req add "Список заказов фильтруется по складу" --source "бриф, абзац 2" --kind functional   # → R-1
$P req note R-1 "Ответ пользователя: склад по умолчанию — из профиля"
$P req set R-1 --spec S-1                     # → specified
$P ticket add "Фильтр по складу в OrdersList" --req R-1 --acceptance "фильтр сохраняется в URL"  # → T-1, R-1 → planned
$P ticket set T-1 --status in_progress --url https://github.com/…/issues/12
$P ticket set T-1 --status done               # R-1 → implemented, если все тикеты закрыты
$P req set R-1 --status verified
$P req set R-2 --status dropped --reason "пользователь снял 26.10: не нужно в этом релизе"

$P check --phase plan                         # пропуски для этапа; код 1, если есть
$P check                                      # полная трассировка (acceptance)
$P render                                     # → .pilot/<run-id>/dashboard/index.html
$P status; $P req list; $P ticket list; $P log "комментарий в журнал"
```

Правила, зашитые в скрипт: этап открывается только после `done|skipped` предыдущего; одновременно активен один этап;
`acceptance done` не пройдёт при пропусках трассировки; `dropped` требует `--reason`; тикет без `--req` не создаётся.
