# Skill: Problem refinement (01 → 02)
**Input:** approved 01-problem.md, memory/decisions.md. **Output:** 02-spec.md.
1. Restate the goal in one sentence. If you can't, the problem isn't clear; ask the human.
2. List users and what each needs.
3. Write explicit In scope / Out of scope. Anything vague goes to Out of scope or Open questions.
4. Write acceptance criteria as `AC-xx` rows, each with *how it will be verified*. A criterion nobody can test is not a criterion.
5. No solution design yet. No code.
6. Fact-only: each statement traces to 01 or a cited source. Write `Not specified in provided context.` instead of guessing.
7. Give each AC a Weight (default 1) and Blocker yes/no. Safety and integrity criteria are blockers.
**Done when:** every success bullet in 01 maps to at least one AC.
