---
status: APPROVED
author: analyst-agent
approved_by: Vaibhav
approved_on: 2026-10-23
---
# 02 · Spec: AI Coding Agent Harness

Input: `01-problem.md` (approved). Skill: `skills/problem-refinement.md`.

## Goal (one sentence)
A repo-level harness that forces any coding agent (GitHub Copilot agent mode, Claude Code,
Azure AI Foundry agents) through eight gated artifacts, blocks unsafe actions, and ends every
work loop on PASS or a human escalation.

## Users
| Who | Needs |
|---|---|
| Human lead (approver) | Review each artifact, approve gates, see an audit trail |
| Coding agent(s) | Clear instructions, the right context per step, a tool to self-check |
| Evaluator agent | Criteria fixed in advance, a place to record evidence + verdict |

## In scope
- Eight artifact templates with a status header (DRAFT / APPROVED, author, approved_by).
- A CLI (`scripts/harness.py`) enforcing gates, permissions and the loop.
- Agent instructions (`AGENTS.md`, `.github/copilot-instructions.md`) and seven reusable skills.
- Memory files: decisions, feedback log, learnings.

## Out of scope (v1)
- Running the coding agent itself (the harness wraps whatever agent you use).
- Live Work IQ / Azure DevOps integration (documented as extension points).
- Multi-user approval workflows (single approver list in config).

## Acceptance criteria (fixed before any code; evaluated in 07)
| ID | Criterion | How it is verified | Weight | Blocker |
|---|---|---|---|---|
| AC-01 | `harness.py status` lists all eight artifacts with role, status and approver | unit test + manual run | 1 | no |
| AC-02 | If step N has content while step N-1 is not APPROVED, `check` fails with a GATE error | unit test | 2 | yes |
| AC-03 | A filled spec with no `AC-xx` criteria fails `check` | unit test | 1 | no |
| AC-04 | Every AC needs a row in 07-evaluation with evidence and a verdict in {PASS, FAIL, PARTIAL} | unit test | 1 | no |
| AC-05 | Every AC is owned by at least one task in 06-tasks, and every task has an owner | unit test | 1 | no |
| AC-06 | Only names in `human_approvers` can approve; an author cannot approve its own artifact; an agent running `harness.py approve` is DENIED by the guard | unit test | 2 | yes |
| AC-07 | `guard` returns DENY for destructive commands, NEEDS_APPROVAL for deploy/publish commands, ALLOW otherwise; non-ALLOW exits 2 so it can block as a hook | unit test | 2 | yes |
| AC-08 | `loop` FAIL routes to the task owner; PASS stops; reaching `max_iterations_per_task` returns ESCALATE and appends to 08-governance | unit test | 1 | no |
| AC-09 | Every loop verdict is appended to `memory/feedback.jsonl` with timestamp, task, criteria, iteration and action | unit test | 1 | no |
| AC-10 | Standard library only; Python 3.10+; tests run with `python -m unittest discover -s tests` | CI run | 1 | no |
| AC-11 | `score` turns 07 verdicts into a weighted 0–10 score; PASS only when score ≥ threshold AND no blocker criterion is failing | unit test | 1 | no |
| AC-12 | If test functions or assertions drop versus the last iteration, `score` reports a TEST-INTEGRITY blocker; only a human `rebaseline` (with a reason, logged to decisions) accepts the drop | unit test | 2 | yes |
| AC-13 | The same criterion failing twice in a row returns REFINE-ALTERNATE (different approach required); score regression and plateau are flagged | unit test | 1 | no |
| AC-14 | Agents can only propose learnings (`learn`); `promote` is human-only, needs ≥2 independent sources, and writes approved learnings to `.github/instructions/` so Copilot loads them | unit test | 1 | no |
| AC-15 | Every role in harness.json has a `.github/agents/<role>.agent.md` with a `tools:` list; only coder and evaluator get terminal tools | unit test (spec lint) | 1 | no |

Scoring: PASS=10, PARTIAL=5, FAIL=0, weighted mean; pass threshold 8.0 (harness.json). Blocker = must be PASS regardless of the score.

## Non-functional
- Everything is plain markdown + JSON so it diffs cleanly in pull requests (the PR *is* the audit trail).
- Config in one file (`harness/harness.json`) so a team can tune limits without code changes.

## Open questions (to resolve in 03-spec-analysis)
- Q1: Should PARTIAL count as an iteration toward the limit? (current: yes, and it counts toward the alternate-approach ladder)
- Q2: Is one human approver per gate enough, or do 04 and 08 need two?
- Q3: Should NEEDS_APPROVAL commands be logged to 08-governance automatically?
