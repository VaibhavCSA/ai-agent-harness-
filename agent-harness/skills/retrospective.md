# Skill: Retrospective (after PASS or ESCALATE)
Goal: the harness gets better every run, with evidence, not vibes.
1. For each agent that took part, list its obligations from `.github/agents/<role>.agent.md` and `AGENTS.md`.
2. Replay what happened (artifacts, `memory/feedback.jsonl`, `memory/scores.jsonl`, git diff). Mark each obligation met / partly met / violated, with evidence (file, line, log entry).
3. Severity: Blocker (broke a hard rule) · Major (skipped a step that changed the outcome) · Minor (drift) · Positive (keep doing this).
4. Root cause: is the spec missing a rule, ambiguous, or contradictory? Fix the spec, not the symptom.
5. Write the ledger to `memory/agent-ledger.md`:
   `| date | agent | severity | obligation | expected | actual | evidence |`
6. Route each learning:
   - Spec gap → a one-line diff to that agent's `## Operating learnings`, shown to the human, applied only on approval.
   - Reusable principle → `python scripts/harness.py learn --key ... --text ... --source ...`. The human promotes it once there are 2+ independent sources.
7. Nothing new? Say "No new learnings this run". Never invent one to fill the loop.
