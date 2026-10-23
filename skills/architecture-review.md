# Skill: Architecture review (03 → 04)
1. Name each component and its single responsibility.
2. List dependencies (services, packages, identities, networks) and mark each resolved or blocked.
3. Stress-test on paper: what happens when a dependency is down, input is malformed, the agent is wrong, the human is unavailable?
4. Azure-first: prefer managed identity over keys, private endpoints over public, least-privilege RBAC.
**Done when:** verdict says proceed, or the spec goes back to 02 with reasons.
