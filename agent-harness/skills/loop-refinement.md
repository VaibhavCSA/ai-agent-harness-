# Skill: Loop refinement (07 ↔ 06)
EVALUATE → ROUTE FEEDBACK → REFINE + RE-RUN → PASS / ESCALATE.
1. Read the latest entries for your task in memory/feedback.jsonl before changing anything.
2. Fix only what the failed criterion points at. No scope creep.
   On REFINE-ALTERNATE the previous fix did not work twice: change approach, and write one line in memory/decisions.md saying what you are trying instead.
3. Re-run the evidence (tests) and hand back to the evaluator.
4. `score` flags REGRESSION (restore before new work) and PLATEAU (surface to human).
5. After `max_iterations_per_task` the loop stops on its own and a human decides. Do not try to work around the limit.
6. If the fix taught something reusable, propose it with `python scripts/harness.py learn`. Only a human promotes it.
