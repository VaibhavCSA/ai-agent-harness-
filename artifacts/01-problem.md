---
status: APPROVED
author: AMA-Cohort-2-brief
approved_by: Vaibhav
approved_on: 2026-10-23
---
# 01 · Problem: AI Coding Agent Harness

## Context
In a hands-on lab (AMA Cohort 2, "Build Your AI Coding Agent Harness") the goal is to
"engineer the system around the agent". A raw use case should reach working code through
a governed, evaluated, self-refining path instead of one unchecked AI chat.

## Problem
AI coding agents fail more from a missing system around them than from weak models.
They start coding before the problem is clear, nobody defines "done" up front, they grade
their own work, they can run unsafe commands, they forget past decisions, and they loop
without knowing when to stop.

## What we are building
A harness around a coding agent with six layers:
1. Tool: what the agent CAN do (read, search, edit, run)
2. Context: what it SEES (problem, repo, instructions, evidence)
3. Execution: how it RUNS (roles, handoffs, skills, checkpoints)
4. Permission: what it CAN'T do (boundaries, approvals, safe operations)
5. Memory: what it REMEMBERS (feedback, decisions, reusable learning)
6. Loop: how it IMPROVES (evaluate, route feedback, refine, stop)

Work moves through eight markdown artifacts. Each one is the input to the next:
01-problem → 02-spec → 03-spec-analysis → 04-architecture-review →
05-plan → 06-tasks → 07-evaluation → 08-governance

## Success looks like
- Every step produces a reviewable artifact; nothing skips ahead.
- Acceptance criteria are defined in the spec, before any code exists.
- Evaluation records criteria, evidence and a verdict for each output.
- Failures route back to the task that owns them; the loop ends on PASS
  or escalates to a human at an iteration limit.
- Human approval, escalation and an audit trail are recorded at governance.

## Constraints
- Azure / Microsoft-first; agent tools include Work IQ for enterprise context.
- Humans approve key gates; agents never approve their own work.
- No destructive or deploying actions without explicit human approval.

## Output
A governed artifact chain that is evaluated, refined and stopped intentionally.
