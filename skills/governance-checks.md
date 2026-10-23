# Skill: Governance checks (07 → 08)
1. `python scripts/harness.py check` must print CHECK PASSED.
2. Every NEEDS_APPROVAL command is listed with who approved it.
3. Every escalation has a human decision recorded.
4. Release decision states ship/hold with a link to evaluation verdicts.
5. The governor prepares 08; a human approves it. Agents never run `approve`.
