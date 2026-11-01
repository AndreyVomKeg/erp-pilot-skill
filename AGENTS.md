# Rules for agents working in this repository

This repository holds agent skills (directories with a `SKILL.md`) that are installed
on several hosts. Every change you push here is distributed to those hosts, so the
rules below are not optional.

## Layout

- One skill = one top-level directory containing `SKILL.md` (e.g. `erp-pilot/`).
- Baselines for the security scanner live in `.skillspector/<skill-dir-name>.yaml`
  — never inside the skill directory itself.
- `examples/` and `docs/` are not skills and must not contain a `SKILL.md`.

## Before every push

1. Run the unit tests and the smoke test exactly as `.github/workflows/validate.yml` does.
2. Run the security scanner on every skill you touched:

       skillspector scan ./<skill> --no-llm --baseline .skillspector/<skill>.yaml --fail-on-findings

   (omit `--baseline` if the skill has no baseline yet). Install with
   `pip install git+https://github.com/NVIDIA/skillspector.git` if missing.
3. Push to a branch and open a pull request. Do not push to `main` directly —
   `main` is protected and requires the `validate` check to pass.

## When the scanner reports a finding

- First read the finding and the flagged line. Decide whether it is real.
- A **real** problem (network calls, `curl | bash`, `subprocess`, `eval`, instructions
  to ignore safety rules, hidden/zero-width characters, credentials) is fixed in the
  skill. Never suppress it.
- A **verified false positive** is suppressed with a *glob rule* in
  `.skillspector/<skill>.yaml`, with a `reason` that explains why it is harmless.
  Do not use fingerprints (they break on every edit) and do not widen a rule beyond
  the file and rule id that actually need it.
- Never delete or disable the scanner step or the hidden-character step in
  `.github/workflows/validate.yml`, and never add `continue-on-error` to them.

## Content rules

- Skills are written in Russian; Cyrillic text next to Latin identifiers is expected
  and already accepted in the baselines (rule AE4).
- Skills must stay project-agnostic: no company names, domains, or account names
  (the CI frontmatter step rejects some of them explicitly).
- `SKILL.md` must start with YAML frontmatter whose `name` equals the directory name
  and whose `description` is a single quoted string of at most 1024 characters.
