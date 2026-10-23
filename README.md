# AI Coding Agent Harness (AMA Cohort 2 lab)

"Engineer the system around the agent." This repo turns the six layers and eight-step flow
from the lab slide into files an agent must follow and a CLI that enforces them.

## Where each layer lives
| Layer | What it controls | Enforced by |
|---|---|---|
| 01 Tool | what the agent CAN do | `harness.json › tool_layer`, `AGENTS.md › Tools` |
| 02 Context | what it SEES | `AGENTS.md › Before every action`, previous artifact + step skill |
| 03 Execution | how it RUNS | `harness.json › execution_layer` roles, `harness.py status/check` gates |
| 04 Permission | what it CAN'T do | `harness.py guard` (+ hook in `.claude/settings.json`), human-only `approve` / `promote` / `rebaseline`, per-role `tools:` in `.github/agents/` |
| 05 Memory | what it REMEMBERS | `memory/` logs; `learn` → candidate, `promote` (human, 2+ sources) → `learnings.md` + `.github/instructions/learnings.instructions.md` |
| 06 Loop | how it IMPROVES | `score` (weighted, blockers, test-integrity, regression, plateau) + `loop` (REFINE → REFINE-ALTERNATE → ESCALATE) + retrospective agent |

## Run the lab
```bash
python scripts/harness.py status                 # where are we? (shows a GATE error until you approve 01)
python scripts/harness.py approve 1 --by Vaibhav    # human signs off the problem
#   review artifacts/02-spec.md (already drafted), edit if needed, then:
python scripts/harness.py approve 2 --by Vaibhav
#   ask your agent: "Follow AGENTS.md and complete the next step"
python scripts/harness.py guard "az group delete -n rg-demo"   # DENY
python scripts/harness.py loop --task T-01 --verdict FAIL --criteria AC-02 --note "gate not enforced"
python scripts/harness.py score                  # weighted 0-10 score, blockers, test-integrity, regression, plateau
python scripts/harness.py learn --key k --text "rule" --source feedback:T-01   # agent proposes a learning
python scripts/harness.py promote --key k --by Vaibhav                           # human approves (needs 2+ sources)
python scripts/harness.py check                  # the whole chain, CI-ready (non-zero on any problem)
python -m unittest discover -s tests -v          # 14 tests covering AC-01..AC-15
```
Change the approver name and limits in `harness/harness.json`.

## Wiring it to your agent
- **GitHub Copilot agent mode (VS Code):** reads `.github/copilot-instructions.md` → `AGENTS.md`. Pick a role from the Agent picker (`.github/agents/*.agent.md`); each role only gets the tools it needs.
- **Claude Code:** reads `AGENTS.md`; `.claude/settings.json` runs `guard` before every shell command and blocks on exit 2.
- **CI (GitHub Actions / Azure Pipelines):** run `harness.py check` and the tests on every PR so nobody, human or agent, merges a broken chain.

## Why it is built this way
- **Markdown + JSON only.** Every artifact and approval is a diff in a pull request, so the PR history is the audit trail.
- **Criteria IDs (`AC-xx`) thread the chain.** Spec defines them, tasks own them, evaluation proves them, `check` verifies the links. That's what makes "done" decided up front, not by the agent.
- **The harness is its own first use case.** 02-spec defines AC-01…AC-10 for the harness; the tests prove each one. Run the chain 03→08 on it to practise the flow end to end.

## v2: what was adopted from astha29may/AICodingAgentHarness
| Idea from the reference | How it landed here | Why |
|---|---|---|
| Weighted rubric + pass threshold | `score`, Weight/Blocker columns in 02-spec | A yes/no per criterion can't tell "almost there" from "nowhere close" |
| Blockers override the score | blocker criteria must PASS | A 9/10 with the safety guard broken is still a fail |
| Test-integrity check | tests/asserts may only go up; human `rebaseline` | Stops the agent passing by deleting tests |
| Escalation ladder, regression, plateau | REFINE-ALTERNATE, REGRESSION, PLATEAU | Retrying the same fix is the commonest wasted loop |
| Custom agent per role with scoped `tools:` | `.github/agents/` | Tool limits enforced by Copilot, not just by instructions |
| Fact-only problem statements | "Not specified in provided context." rule | Stops the analyst inventing requirements |
| Evidence-gated memory promotion | `learn` / `promote` (2+ sources, human) | One lucky observation shouldn't become a permanent rule |
| Memory materialized into instructions | `.github/instructions/learnings.instructions.md` | Copilot loads it automatically |
| Retrospective agent + ledger | `retrospective` agent, `skills/retrospective.md` | Improves the agents' specs, not just the code |
| Spec-lint tests | AC-15 test | The agent files themselves are tested |

Not adopted (yet): parallel build lanes with contracts, the benchmark suite (BM-01…09), token-efficiency logging, repo fingerprinting for cross-repo memory. Good next steps once the single-lane loop is solid.
