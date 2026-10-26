# erp-pilot-skill

Skill «ERP Pilot» для Perplexity Computer: проводит изменение ERP (TRID ERP Supabase, TRID.Immo, VG Portal)
от брифа до приёмки по восьми этапам — Preflight → Requirements → Briefing → Spec → Plan → Development →
Code review → Acceptance — со сквозной трассировкой «требование → спека → тикет → приёмка» и живым дашбордом.

```
erp-pilot/                 # сам skill (папка = name в SKILL.md)
  SKILL.md                 # хаб: режимы, глубина, 8 шагов, границы
  references/phases.md     # вход/выход этапов, таблица глубины, чек-лист ревью
  references/dashboard.md  # схема state.json, тексты этапов RU/EN, публикация дашборда
  scripts/pilot.py         # CLI состояния прогона (stdlib), scripts/README.md — команды
  templates/*.md           # requirements / spec / plan / acceptance
  assets/dashboard/        # шаблон дашборда (RU/EN, светлая/тёмная тема)
examples/demo-run/         # пример прогона и отрендеренный дашборд
```

![Дашборд ERP Pilot](docs/dashboard-preview.png)

## Установка в Perplexity

```bash
cd erp-pilot-skill && zip -r erp-pilot.zip erp-pilot
```
Загрузить `erp-pilot.zip` на странице Skills (My Skills или в проект). Либо попросить Computer:
«добавь skill из репозитория AndreyVomKeg/erp-pilot-skill».

## Проверка

```bash
agentskills validate erp-pilot/
python3 erp-pilot/scripts/pilot.py --dir examples/demo-run status
python3 erp-pilot/scripts/pilot.py --dir examples/demo-run render --out /tmp/dashboard.html
```

## Соседние skills

`trid-grill` (опрос и ADR), `trid-tickets` (разбивка), `trid-code-review` (ревью PR), `trid-diagnose` (ошибки),
`trid-brandbook` (UI-стандарт). ERP Pilot вызывает их на своих этапах, если они установлены, иначе использует
встроенные чек-листы.
