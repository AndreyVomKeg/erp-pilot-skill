#!/usr/bin/env python3
"""ERP Pilot run state CLI (stdlib only).

State lives in <dir>/state.json. Every command rewrites the file atomically and
appends a log entry. Run `pilot.py -h` or see scripts/README.md.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PHASES = [
    "preflight",
    "requirements",
    "briefing",
    "spec",
    "plan",
    "development",
    "code_review",
    "acceptance",
]

PHASE_NOTES = {
    "preflight": {
        "ru": ["Настраиваю репозиторий и дашборд",
               "Дальше бриф станет требованиями, и ни одно не потеряется до конца."],
        "en": ["Setting up the repo and the dashboard",
               "Next, the brief becomes requirements, and none of them gets lost before the end."],
    },
    "requirements": {
        "ru": ["Превращаю бриф в нумерованные требования",
               "Каждое R-n получит источник и дойдёт до приёмки."],
        "en": ["Turning the brief into numbered requirements",
               "Every R-item gets a source and will reach acceptance."],
    },
    "briefing": {
        "ru": ["Уточняю неясные требования", "Вопросы привязаны к номерам R-n."],
        "en": ["Clarifying unclear requirements", "Questions are tied to R-numbers."],
    },
    "spec": {
        "ru": ["Пишу спецификацию", "У каждого требования появляется решение S-n."],
        "en": ["Writing the spec", "Every requirement gets a decision S-n."],
    },
    "plan": {
        "ru": ["Собираю план и тикеты", "Вертикальные T-n с зависимостями и критериями приёмки."],
        "en": ["Building the plan and tickets", "Vertical T-items with dependencies and acceptance criteria."],
    },
    "development": {
        "ru": ["Реализую тикеты", "Коммиты по T-n, один PR на прогон."],
        "en": ["Implementing tickets", "Commits per T-item, one PR per run."],
    },
    "code_review": {
        "ru": ["Ревью по двум осям", "Стандарты репозитория и соответствие спеке."],
        "en": ["Two-axis code review", "Repo standards and spec compliance."],
    },
    "acceptance": {
        "ru": ["Приёмка", "Каждое R-n проверено или снято с причиной."],
        "en": ["Acceptance", "Every R-item verified or dropped with a reason."],
    },
}

REQ_STATUSES = ["open", "specified", "planned", "implemented", "verified", "dropped"]
REQ_KINDS = ["functional", "data", "ui", "security", "ops", "proposed"]
TICKET_STATUSES = ["todo", "in_progress", "review", "done", "dropped"]
MODES = ["manual", "semi-automatic", "automatic"]
DEPTHS = ["light", "normal", "deep"]

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "dashboard" / "index.html"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def die(msg: str, code: int = 2) -> None:
    print(f"pilot: {msg}", file=sys.stderr)
    sys.exit(code)


class State:
    def __init__(self, path: Path):
        self.path = path
        if not path.exists():
            die(f"{path} not found; run `pilot.py init --dir {path.parent}` first")
        self.data = json.loads(path.read_text(encoding="utf-8"))

    def save(self) -> None:
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, self.path)

    def log(self, event: str, phase: str | None = None) -> None:
        phase = phase or self.active_phase_id() or ""
        self.data.setdefault("log", []).append({"at": now_iso(), "phase": phase, "event": event})

    def active_phase_id(self) -> str | None:
        for p in self.data["phases"]:
            if p["status"] == "active":
                return p["id"]
        return None

    def phase(self, pid: str) -> dict:
        for p in self.data["phases"]:
            if p["id"] == pid:
                return p
        die(f"unknown phase {pid}; valid: {', '.join(PHASES)}")

    def find(self, coll: str, iid: str) -> dict:
        for it in self.data[coll]:
            if it["id"] == iid:
                return it
        die(f"{iid} not found in {coll}")

    def next_id(self, coll: str, prefix: str) -> str:
        nums = [int(i["id"].split("-")[1]) for i in self.data[coll] if i["id"].startswith(prefix + "-")]
        return f"{prefix}-{(max(nums) + 1) if nums else 1}"


# ---------- commands ----------

def cmd_init(a: argparse.Namespace) -> None:
    d = Path(a.dir)
    path = d / "state.json"
    if path.exists() and not a.force:
        die(f"{path} exists; use --force to overwrite")
    d.mkdir(parents=True, exist_ok=True)
    run_id = a.id or d.name
    started = now_iso()
    data = {
        "schema": 1,
        "run": {
            "id": run_id,
            "title": {"ru": a.title_ru, "en": a.title_en or a.title_ru},
            "mode": a.mode,
            "depth": a.depth,
            "started_at": started,
            "finished_at": None,
            "repo": a.repo,
            "branch": a.branch or f"pilot/{run_id}",
            "pr_url": None,
            "dashboard_url": None,
            "constraints": [],
        },
        "phases": [
            {"id": p, "status": "ahead", "started_at": None, "finished_at": None,
             "note": {"ru": PHASE_NOTES[p]["ru"], "en": PHASE_NOTES[p]["en"]}}
            for p in PHASES
        ],
        "requirements": [],
        "tickets": [],
        "log": [{"at": started, "phase": "preflight", "event": "run created"}],
    }
    data["phases"][0].update(status="active", started_at=started)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name in ("requirements.md", "spec.md", "plan.md", "acceptance.md"):
        src = HERE.parent / "templates" / name
        dst = d / name
        if src.exists() and not dst.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"created {path}")


def cmd_set(a: argparse.Namespace) -> None:
    s = State(Path(a.dir) / "state.json")
    run = s.data["run"]
    changed = []
    for key in ("dashboard_url", "pr_url", "repo", "branch", "mode", "depth"):
        val = getattr(a, key)
        if val is not None:
            run[key] = val
            changed.append(key)
    if a.title_ru:
        run["title"]["ru"] = a.title_ru
        changed.append("title.ru")
    if a.title_en:
        run["title"]["en"] = a.title_en
        changed.append("title.en")
    if a.constraint:
        run.setdefault("constraints", []).extend(a.constraint)
        changed.append("constraints")
    if not changed:
        die("nothing to set")
    s.log("run updated: " + ", ".join(changed))
    s.save()
    print("ok: " + ", ".join(changed))


def cmd_phase(a: argparse.Namespace) -> None:
    s = State(Path(a.dir) / "state.json")
    p = s.phase(a.phase)
    idx = PHASES.index(a.phase)
    t = now_iso()
    if a.action == "start":
        if idx > 0 and s.data["phases"][idx - 1]["status"] not in ("done", "skipped"):
            die(f"previous phase {PHASES[idx - 1]} is not done/skipped")
        active = s.active_phase_id()
        if active and active != a.phase:
            die(f"phase {active} is still active; finish it first")
        p.update(status="active", started_at=p["started_at"] or t)
    elif a.action in ("done", "skip"):
        if p["status"] != "active" and a.action == "done":
            die(f"phase {a.phase} is not active")
        p.update(status="done" if a.action == "done" else "skipped", finished_at=t)
        if a.phase == "acceptance" and a.action == "done":
            problems = traceability_problems(s.data)
            if problems:
                die("acceptance cannot close:\n  " + "\n  ".join(problems))
            s.data["run"]["finished_at"] = t
        if idx + 1 < len(PHASES) and a.auto_next:
            nxt = s.data["phases"][idx + 1]
            nxt.update(status="active", started_at=t)
    if a.note_ru:
        p["note"]["ru"] = [a.note_ru, a.note_ru_sub or p["note"]["ru"][1]]
    if a.note_en:
        p["note"]["en"] = [a.note_en, a.note_en_sub or p["note"]["en"][1]]
    s.log(f"phase {a.phase} {a.action}", a.phase)
    s.save()
    print(f"ok: {a.phase} -> {p['status']}")


def cmd_req(a: argparse.Namespace) -> None:
    s = State(Path(a.dir) / "state.json")
    if a.req_cmd == "add":
        rid = s.next_id("requirements", "R")
        s.data["requirements"].append({
            "id": rid, "text": a.text, "source": a.source, "kind": a.kind,
            "status": "open", "spec": None, "tickets": [], "note": None, "reason": None,
        })
        s.log(f"{rid} added")
        print(rid)
    elif a.req_cmd == "set":
        r = s.find("requirements", a.id)
        if a.status:
            if a.status == "dropped" and not (a.reason or r.get("reason")):
                die("dropped requires --reason")
            r["status"] = a.status
        if a.spec:
            r["spec"] = a.spec
            if r["status"] == "open":
                r["status"] = "specified"
        if a.ticket:
            for t in a.ticket:
                s.find("tickets", t)
                if t not in r["tickets"]:
                    r["tickets"].append(t)
            if r["status"] in ("open", "specified"):
                r["status"] = "planned"
        if a.text:
            r["text"] = a.text
        if a.reason:
            r["reason"] = a.reason
        if a.kind:
            r["kind"] = a.kind
        s.log(f"{a.id} updated -> {r['status']}")
        print(f"ok: {a.id} {r['status']}")
    elif a.req_cmd == "note":
        r = s.find("requirements", a.id)
        r["note"] = (r["note"] + "\n" if r["note"] else "") + a.text
        s.log(f"{a.id} note added")
        print("ok")
    elif a.req_cmd == "list":
        for r in s.data["requirements"]:
            print(f"{r['id']:5} {r['status']:12} {r['kind']:10} spec={r['spec'] or '-':5} "
                  f"tickets={','.join(r['tickets']) or '-'}  {r['text']}")
        return
    s.save()


def cmd_ticket(a: argparse.Namespace) -> None:
    s = State(Path(a.dir) / "state.json")
    if a.ticket_cmd == "add":
        tid = s.next_id("tickets", "T")
        for r in a.req:
            s.find("requirements", r)
        for d in a.depends_on:
            s.find("tickets", d)
        s.data["tickets"].append({
            "id": tid, "title": a.title, "requirements": a.req, "depends_on": a.depends_on,
            "acceptance": a.acceptance, "status": "todo", "url": a.url,
        })
        for r in a.req:
            req = s.find("requirements", r)
            if tid not in req["tickets"]:
                req["tickets"].append(tid)
            if req["status"] in ("open", "specified"):
                req["status"] = "planned"
        s.log(f"{tid} added for {', '.join(a.req)}")
        print(tid)
    elif a.ticket_cmd == "set":
        t = s.find("tickets", a.id)
        if a.status:
            t["status"] = a.status
            if a.status == "done":
                for rid in t["requirements"]:
                    req = s.find("requirements", rid)
                    all_done = all(s.find("tickets", x)["status"] in ("done", "dropped") for x in req["tickets"])
                    if all_done and req["status"] in ("planned", "specified", "open"):
                        req["status"] = "implemented"
        if a.url:
            t["url"] = a.url
        if a.title:
            t["title"] = a.title
        s.log(f"{a.id} -> {t['status']}")
        print(f"ok: {a.id} {t['status']}")
    elif a.ticket_cmd == "list":
        for t in s.data["tickets"]:
            print(f"{t['id']:5} {t['status']:12} req={','.join(t['requirements'])}  {t['title']}")
        return
    s.save()


def cmd_log(a: argparse.Namespace) -> None:
    s = State(Path(a.dir) / "state.json")
    s.log(a.message)
    s.save()
    print("ok")


def traceability_problems(data: dict, phase: str = "acceptance") -> list[str]:
    out: list[str] = []
    for r in data["requirements"]:
        if r["status"] == "dropped":
            if not r.get("reason"):
                out.append(f"{r['id']} dropped without reason")
            continue
        if phase in ("spec", "plan", "development", "code_review", "acceptance") and not r["spec"]:
            out.append(f"{r['id']} has no spec (S-n)")
        if phase in ("plan", "development", "code_review", "acceptance") and not r["tickets"]:
            out.append(f"{r['id']} has no tickets")
        if phase == "acceptance" and r["status"] != "verified":
            out.append(f"{r['id']} is {r['status']}, expected verified or dropped")
    if phase in ("development", "code_review", "acceptance"):
        for t in data["tickets"]:
            if phase == "acceptance" and t["status"] not in ("done", "dropped"):
                out.append(f"{t['id']} is {t['status']}, expected done or dropped")
            if not t["requirements"]:
                out.append(f"{t['id']} is not linked to any requirement")
    return out


def cmd_check(a: argparse.Namespace) -> None:
    s = State(Path(a.dir) / "state.json")
    phase = a.phase or s.active_phase_id() or "acceptance"
    problems = traceability_problems(s.data, phase)
    if problems:
        print(f"{len(problems)} problem(s) for phase {phase}:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print(f"ok: no traceability gaps for phase {phase}")


def cmd_render(a: argparse.Namespace) -> None:
    d = Path(a.dir)
    s = State(d / "state.json")
    tpl = Path(a.template) if a.template else TEMPLATE
    if not tpl.exists():
        die(f"template {tpl} not found")
    html = tpl.read_text(encoding="utf-8")
    if "__STATE__" not in html:
        die("template has no __STATE__ placeholder")
    payload = json.dumps(s.data, ensure_ascii=False).replace("</", "<\\/")
    out = Path(a.out) if a.out else d / "dashboard" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html.replace("__STATE__", payload), encoding="utf-8")
    print(f"rendered {out}")


def cmd_status(a: argparse.Namespace) -> None:
    s = State(Path(a.dir) / "state.json")
    run = s.data["run"]
    print(f"{run['id']}  mode={run['mode']} depth={run['depth']}  repo={run['repo']} branch={run['branch']}")
    for p in s.data["phases"]:
        mark = {"done": "✓", "active": "▶", "skipped": "–", "ahead": "·"}[p["status"]]
        print(f"  {mark} {p['id']:13} {p['status']}")
    rs = s.data["requirements"]
    ts = s.data["tickets"]
    print(f"requirements: {len(rs)}  tickets: {len(ts)}  dashboard: {run['dashboard_url'] or '-'}")


# ---------- parser ----------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="pilot.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".", help="run directory containing state.json (default: .)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="create a new run")
    p.add_argument("--id", help="run id (default: directory name)")
    p.add_argument("--title-ru", required=True)
    p.add_argument("--title-en")
    p.add_argument("--mode", choices=MODES, default="semi-automatic")
    p.add_argument("--depth", choices=DEPTHS, default="normal")
    p.add_argument("--repo", required=True, help="owner/name of the target repository")
    p.add_argument("--branch")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("set", help="update run fields")
    for key in ("dashboard-url", "pr-url", "repo", "branch", "title-ru", "title-en"):
        p.add_argument("--" + key)
    p.add_argument("--mode", choices=MODES)
    p.add_argument("--depth", choices=DEPTHS)
    p.add_argument("--constraint", action="append", help="repeatable repository constraint")
    p.set_defaults(fn=cmd_set)

    p = sub.add_parser("phase", help="start / done / skip a phase")
    p.add_argument("phase", choices=PHASES)
    p.add_argument("action", choices=["start", "done", "skip"])
    p.add_argument("--auto-next", action="store_true", help="activate the next phase after done/skip")
    p.add_argument("--note-ru")
    p.add_argument("--note-ru-sub")
    p.add_argument("--note-en")
    p.add_argument("--note-en-sub")
    p.set_defaults(fn=cmd_phase)

    p = sub.add_parser("req", help="requirements")
    rs = p.add_subparsers(dest="req_cmd", required=True)
    q = rs.add_parser("add")
    q.add_argument("text")
    q.add_argument("--source", required=True, help="where in the brief this comes from")
    q.add_argument("--kind", choices=REQ_KINDS, default="functional")
    q = rs.add_parser("set")
    q.add_argument("id")
    q.add_argument("--status", choices=REQ_STATUSES)
    q.add_argument("--spec", help="S-n")
    q.add_argument("--ticket", action="append", help="T-n (repeatable)")
    q.add_argument("--text")
    q.add_argument("--kind", choices=REQ_KINDS)
    q.add_argument("--reason", help="required for --status dropped")
    q = rs.add_parser("note")
    q.add_argument("id")
    q.add_argument("text")
    rs.add_parser("list")
    p.set_defaults(fn=cmd_req)

    p = sub.add_parser("ticket", help="tickets")
    ts = p.add_subparsers(dest="ticket_cmd", required=True)
    q = ts.add_parser("add")
    q.add_argument("title")
    q.add_argument("--req", action="append", required=True, help="R-n (repeatable)")
    q.add_argument("--depends-on", action="append", default=[], help="T-n (repeatable)")
    q.add_argument("--acceptance", action="append", default=[], help="acceptance criterion (repeatable)")
    q.add_argument("--url")
    q = ts.add_parser("set")
    q.add_argument("id")
    q.add_argument("--status", choices=TICKET_STATUSES)
    q.add_argument("--url")
    q.add_argument("--title")
    ts.add_parser("list")
    p.set_defaults(fn=cmd_ticket)

    p = sub.add_parser("log", help="append a journal entry")
    p.add_argument("message")
    p.set_defaults(fn=cmd_log)

    p = sub.add_parser("check", help="traceability check; exit 1 on gaps")
    p.add_argument("--phase", choices=PHASES)
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("render", help="render dashboard HTML with embedded state")
    p.add_argument("--out")
    p.add_argument("--template")
    p.set_defaults(fn=cmd_render)

    p = sub.add_parser("status", help="print a short summary")
    p.set_defaults(fn=cmd_status)
    return ap


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.fn(args)
