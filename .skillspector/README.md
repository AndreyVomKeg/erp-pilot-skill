# SkillSpector baselines

One file per skill: `.skillspector/<skill-dir-name>.yaml`.

CI (`.github/workflows/validate.yml`) finds every directory in this repository that
contains a `SKILL.md`, scans it with [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector)
and, if a baseline with the same name exists here, suppresses the findings listed in it.
A skill without a baseline is scanned with none — every finding fails the build.

To accept a verified false positive, add a glob rule (not a fingerprint — fingerprints
break on every edit) to the skill's baseline. Re-check locally:

    skillspector scan ./<skill> --no-llm --baseline .skillspector/<skill>.yaml --show-suppressed
