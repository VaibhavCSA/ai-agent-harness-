# Skill: Evaluation design (06 → 07)
You are the evaluator. You did not write the code you are grading.
1. One row per AC: `| AC-xx | T-xx | evidence | PASS/FAIL/PARTIAL |`.
2. Evidence must be reproducible: a test name, a command and its output, a link. "Looks good" is not evidence.
3. Run `python scripts/harness.py score` for the weighted score, blockers, test-integrity, regression and plateau.
4. For each FAIL/PARTIAL run `python scripts/harness.py loop --task T-xx --verdict FAIL --criteria AC-xx --note "<why>"` and follow the action it prints.
