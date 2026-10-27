"""Guard tests for erp-pilot/scripts/pilot.py (stdlib unittest)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "erp-pilot" / "scripts" / "pilot.py"


class PilotCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "2026-01-01-demo"
        self.ok("init", "--title-ru", "Тест", "--repo", "acme/erp")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # helpers
    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(PILOT), "--dir", str(self.dir), *args],
                              capture_output=True, text=True)

    def ok(self, *args: str) -> str:
        r = self.cli(*args)
        self.assertEqual(r.returncode, 0, f"{args}\n{r.stderr}{r.stdout}")
        return r.stdout.strip()

    def fail(self, *args: str, contains: str = "") -> str:
        r = self.cli(*args)
        self.assertNotEqual(r.returncode, 0, f"expected failure for {args}\n{r.stdout}")
        if contains:
            self.assertIn(contains, r.stderr + r.stdout)
        return r.stderr

    def state(self) -> dict:
        return json.loads((self.dir / "state.json").read_text(encoding="utf-8"))

    def append(self, name: str, text: str) -> None:
        with (self.dir / name).open("a", encoding="utf-8") as fh:
            fh.write("\n" + text + "\n")

    def through_plan(self) -> None:
        """Bring a run with R-1/T-1 to an active Development phase."""
        self.ok("req", "add", "r1", "--source", "бриф, абзац 1")
        self.append("requirements.md", "| R-1 | r1 | functional | бриф, абзац 1 | |")
        self.ok("phase", "preflight", "done", "--auto-next")
        self.ok("phase", "requirements", "done", "--auto-next")
        self.ok("phase", "briefing", "skip", "--auto-next")
        self.ok("req", "set", "R-1", "--spec", "S-1")
        self.append("spec.md", "### S-1 — R-1: r1")
        self.ok("phase", "spec", "done", "--auto-next")
        self.ok("ticket", "add", "t1", "--req", "R-1")
        self.ok("phase", "plan", "done", "--auto-next")

    # init
    def test_init_fills_placeholders(self) -> None:
        text = (self.dir / "requirements.md").read_text(encoding="utf-8")
        self.assertIn("2026-01-01-demo", text)
        self.assertNotIn("<run-id>", text)
        self.assertNotIn("<дата>", text)
        self.assertEqual(self.state()["run"]["helpers"], {})

    # phases
    def test_skip_guards(self) -> None:
        self.fail("phase", "acceptance", "skip", contains="cannot be skipped")
        self.fail("phase", "requirements", "skip", contains="cannot be skipped")
        self.fail("phase", "development", "skip", contains="only the active or the next")
        self.ok("phase", "preflight", "skip")  # active phase may be skipped
        self.assertEqual(self.state()["phases"][0]["status"], "skipped")
        self.ok("phase", "requirements", "start")

    def test_done_requires_traceability(self) -> None:
        self.ok("req", "add", "r1", "--source", "бриф")
        self.ok("phase", "preflight", "done", "--auto-next")
        self.fail("phase", "requirements", "done", contains="no row in requirements.md")
        self.append("requirements.md", "| R-1 | r1 | functional | бриф | |")
        self.ok("phase", "requirements", "done", "--auto-next")
        self.ok("phase", "briefing", "done", "--auto-next")
        self.fail("phase", "spec", "done", contains="has no spec")
        self.ok("req", "set", "R-1", "--spec", "S-1")
        self.fail("phase", "spec", "done", contains="spec.md has no heading")
        self.append("spec.md", "### S-1 — R-1: r1")
        self.ok("phase", "spec", "done", "--auto-next")
        self.fail("phase", "plan", "done", contains="no live tickets")

    def test_force_is_journaled(self) -> None:
        self.ok("req", "add", "r1", "--source", "бриф")
        self.ok("phase", "preflight", "done", "--auto-next")
        self.ok("phase", "requirements", "done", "--force")
        events = [e["event"] for e in self.state()["log"]]
        self.assertTrue(any("FORCED" in e for e in events), events)

    def test_acceptance_cannot_close_with_gaps(self) -> None:
        self.through_plan()
        self.ok("ticket", "set", "T-1", "--status", "done")
        self.ok("phase", "development", "done", "--auto-next")
        self.ok("phase", "code_review", "done", "--auto-next")
        self.fail("phase", "acceptance", "done", contains="expected verified or dropped")
        self.ok("req", "set", "R-1", "--status", "verified")
        self.fail("phase", "acceptance", "done", contains="no row in acceptance.md")
        self.append("acceptance.md", "| R-1 | открыть список | превью | ✓ | |")
        self.ok("phase", "acceptance", "done")
        self.assertIsNotNone(self.state()["run"]["finished_at"])

    def test_reopen_needs_flag_and_is_logged(self) -> None:
        self.ok("phase", "preflight", "done")
        self.fail("phase", "preflight", "start", contains="--reopen")
        self.ok("phase", "preflight", "start", "--reopen")
        self.assertIn("phase preflight reopened", [e["event"] for e in self.state()["log"]])

    def test_development_allows_review_but_not_todo(self) -> None:
        self.through_plan()
        self.fail("phase", "development", "done", contains="expected review, done or dropped")
        self.ok("ticket", "set", "T-1", "--status", "review")
        self.ok("phase", "development", "done", "--auto-next")
        self.fail("phase", "code_review", "done", contains="expected done or dropped")

    # requirements
    def test_req_status_forward_only(self) -> None:
        self.through_plan()
        self.fail("req", "set", "R-1", "--status", "verified", contains="not done/dropped")
        self.ok("ticket", "set", "T-1", "--status", "done")
        self.assertEqual(self.state()["requirements"][0]["status"], "implemented")
        self.ok("req", "set", "R-1", "--status", "verified")
        self.fail("req", "set", "R-1", "--status", "open", contains="--reopen")
        self.ok("req", "set", "R-1", "--status", "open", "--reopen")
        self.assertIn("R-1 reopened: verified -> open", [e["event"] for e in self.state()["log"]])

    def test_dropped_needs_reason_and_reopen_clears_it(self) -> None:
        self.ok("req", "add", "r1", "--source", "бриф")
        self.fail("req", "set", "R-1", "--status", "dropped", contains="--reason")
        self.ok("req", "set", "R-1", "--status", "dropped", "--reason", "снято")
        self.fail("req", "set", "R-1", "--status", "open")
        self.ok("req", "set", "R-1", "--status", "open", "--reopen")
        self.assertIsNone(self.state()["requirements"][0]["reason"])

    def test_verified_needs_spec_and_ticket(self) -> None:
        self.ok("req", "add", "r1", "--source", "бриф")
        self.fail("req", "set", "R-1", "--status", "verified", contains="without a spec")
        self.ok("req", "set", "R-1", "--spec", "S-1")
        self.fail("req", "set", "R-1", "--status", "verified", contains="without a live ticket")

    # tickets
    def test_ticket_drop_recomputes_requirement(self) -> None:
        self.ok("req", "add", "r1", "--source", "бриф")
        self.ok("req", "set", "R-1", "--spec", "S-1")
        self.ok("ticket", "add", "t1", "--req", "R-1")
        self.assertEqual(self.state()["requirements"][0]["status"], "planned")
        self.ok("ticket", "set", "T-1", "--status", "dropped")
        self.assertEqual(self.state()["requirements"][0]["status"], "specified")
        self.ok("ticket", "set", "T-1", "--status", "done")
        self.assertEqual(self.state()["requirements"][0]["status"], "implemented")
        self.ok("ticket", "set", "T-1", "--status", "in_progress")
        self.assertEqual(self.state()["requirements"][0]["status"], "planned")

    def test_ticket_requires_requirement(self) -> None:
        r = self.cli("ticket", "add", "t1")
        self.assertNotEqual(r.returncode, 0)

    # misc
    def test_helpers_and_render(self) -> None:
        self.ok("set", "--helper", "review=my-review-skill", "--constraint", "PR-only")
        self.fail("set", "--helper", "nonsense=x", contains="unknown helper role")
        self.assertEqual(self.state()["run"]["helpers"]["review"], "my-review-skill")
        self.ok("render")
        html = (self.dir / "dashboard" / "index.html").read_text(encoding="utf-8")
        self.assertIn('"schema": 1'.replace(" ", ""), html.replace(" ", ""))
        self.assertNotIn("__STATE__", html)

    def test_check_exit_codes(self) -> None:
        self.ok("check", "--phase", "preflight")
        self.ok("req", "add", "r1", "--source", "бриф")
        r = self.cli("check", "--phase", "spec")
        self.assertEqual(r.returncode, 1)
        self.assertIn("has no spec", r.stdout)


if __name__ == "__main__":
    unittest.main()
