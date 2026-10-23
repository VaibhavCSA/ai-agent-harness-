# AGENTS.md: rules for every coding agent in this repo

You work inside a harness. The system around you decides what you do next, not your own judgement of "done".

## Before every action
1. Read `harness/harness.json`, `artifacts/01-problem.md`, `memory/decisions.md`, `memory/learnings.md`.
2. Run `python scripts/harness.py status` to see which step is active.
3. Work only on the **first artifact that is not APPROVED**. Load the previous artifact and the skill named for that step.

## Roles (one Copilot custom agent each, in `.github/agents/`)
analyst (02, 03) · architect (04) · planner (05, 06) · coder (implements 06, test-first) · evaluator (07) · governor (08) · retrospective (after PASS) · human (approvals)
Set `author:` in the artifact header to your role, e.g. `author: analyst-agent`.

## Hard rules
- Do not write code before 06-tasks.md is APPROVED.
- Do not change acceptance criteria after 02 is approved. Propose a change in 03 and let the human decide.
- Never run `harness.py approve`, `promote` or `rebaseline`. They are human-only and the guard blocks them.
- Never weaken, skip or delete tests to get a PASS. `score` detects it.
- On REFINE-ALTERNATE, the last fix failed twice: try a different approach.
- Never grade work you wrote. The evaluator role is separate.
- Before any terminal command, run `python scripts/harness.py guard "<command>"`. DENY: don't. NEEDS_APPROVAL: stop and ask the human in chat.
- Edit only inside `artifacts/ src/ tests/ memory/`.
- When the loop prints ESCALATE, stop and hand over. Do not retry.

## The loop
coder → evaluator (`score`, `loop`) → REFINE / REFINE-ALTERNATE → coder … → PASS → governor → retrospective.
PASS = weighted score ≥ threshold and no blocker failing. ESCALATE = stop and hand to the human.

## Handoff
When your artifact is complete: remove all `TODO`, run `python scripts/harness.py check`, then tell the human
"Step N ready for review" with a three-line summary. Wait.

## Tools
READ repo + artifacts · SEARCH code + patterns · EDIT create/update · TERMINAL checks + tests (through guard) ·
WORK IQ enterprise context (meetings, mail, docs; cite what you used in the artifact) · WEB external info (cite URLs).
