#!/usr/bin/env python3
"""Agent harness CLI. Standard library only.

Enforces the six layers defined in harness/harness.json:
  status   - show the eight-step chain and any gate violations      (Execution layer)
  check    - validate the whole chain; non-zero exit on any failure  (Execution + Loop)
  approve  - human-only sign-off of one artifact                     (Permission layer)
  guard    - classify a shell command: ALLOW / NEEDS_APPROVAL / DENY (Permission layer)
  loop     - record an evaluation verdict, route feedback, stop      (Memory + Loop)
  score    - weighted score, blockers, test-integrity, regression    (Loop layer)
  learn    - propose a reusable learning with evidence               (Memory layer)
  promote  - human-only: approve a learning with >=2 sources         (Memory layer)
  rebaseline - human-only: accept an intentional drop in tests       (Permission layer)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "harness" / "harness.json").read_text())
ARTIFACTS = ROOT / "artifacts"
STEPS = CONFIG["execution_layer"]["steps"]
PERM = CONFIG["permission_layer"]
LOOP = CONFIG["loop_layer"]
FEEDBACK = ROOT / CONFIG["memory_layer"]["feedback_log"]

AC_RE = re.compile(r"\bAC-\d{2}\b")
TASK_RE = re.compile(r"\bT-\d{2}\b")


# ---------------------------------------------------------------- artifacts
def read_header(path: Path) -> dict:
    """Parse the '---' front-matter block at the top of an artifact."""
    if not path.exists():
        return {"status": "MISSING"}
    text = path.read_text()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    meta.setdefault("status", "DRAFT")
    return meta


def write_header(path: Path, updates: dict) -> None:
    text = path.read_text()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    meta = read_header(path)
    meta.update(updates)
    block = "---\n" + "\n".join(f"{k}: {v}" for k, v in meta.items()) + "\n---\n"
    path.write_text(block + (text[m.end():] if m else text))


def body(path: Path) -> str:
    text = path.read_text() if path.exists() else ""
    return re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)


def is_filled(path: Path) -> bool:
    """A template still containing TODO markers counts as not started."""
    return path.exists() and "TODO" not in body(path)


def table_rows(path: Path) -> list[list[str]]:
    rows = []
    for line in body(path).splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*-", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append(cells)
    return rows


def step_path(n: int) -> Path:
    return ARTIFACTS / STEPS[n - 1]["file"]


# ---------------------------------------------------------------- checks
def gate_violations() -> list[str]:
    errs = []
    for s in STEPS[1:]:
        prev = read_header(step_path(s["n"] - 1))
        cur_path = step_path(s["n"])
        if is_filled(cur_path) and prev.get("status") != "APPROVED":
            errs.append(f"GATE: {s['file']} has content but step {s['n']-1} is not APPROVED (skipped ahead)")
    for s in STEPS:
        h = read_header(step_path(s["n"]))
        if h.get("status") == "APPROVED":
            if h.get("approved_by") not in PERM["human_approvers"]:
                errs.append(f"APPROVAL: {s['file']} approved_by '{h.get('approved_by')}' is not a human approver")
            if h.get("approved_by") and h.get("approved_by") == h.get("author"):
                errs.append(f"APPROVAL: {s['file']} approved by its own author")
    return errs


def chain_checks() -> list[str]:
    errs = []
    spec = step_path(2)
    acs = sorted(set(AC_RE.findall(body(spec))))
    if is_filled(spec) and not acs:
        errs.append("SPEC: 02-spec.md defines no acceptance criteria (AC-xx)")

    tasks_p = step_path(6)
    if is_filled(tasks_p):
        covered = set()
        for row in table_rows(tasks_p):
            if row and TASK_RE.fullmatch(row[0]):
                if len(row) < 4 or not row[2]:
                    errs.append(f"TASKS: {row[0]} has no owner")
                if len(row) >= 5 and not row[4]:
                    errs.append(f"TASKS: {row[0]} names no proving test")
                covered |= set(AC_RE.findall(" ".join(row)))
        for ac in acs:
            if ac not in covered:
                errs.append(f"TASKS: {ac} is not owned by any task")

    ev = step_path(7)
    if is_filled(ev):
        verdicts = {}
        for row in table_rows(ev):
            if row and AC_RE.fullmatch(row[0]):
                if len(row) < 4 or not row[2] or row[2].lower() in {"", "-", "n/a"}:
                    errs.append(f"EVAL: {row[0]} has no evidence")
                verdicts[row[0]] = row[-1].upper() if row else ""
        for ac in acs:
            if ac not in verdicts:
                errs.append(f"EVAL: {ac} has no verdict")
            elif verdicts[ac] not in LOOP["verdicts"]:
                errs.append(f"EVAL: {ac} verdict '{verdicts[ac]}' not in {LOOP['verdicts']}")
    return errs


# ---------------------------------------------------------------- commands
def cmd_status(_):
    print(f"{'#':<3}{'artifact':<28}{'role':<11}{'status':<10}{'filled':<7}approved_by")
    for s in STEPS:
        p = step_path(s["n"])
        h = read_header(p)
        print(f"{s['n']:<3}{s['file']:<28}{s['role']:<11}{h.get('status',''):<10}"
              f"{'yes' if is_filled(p) else 'no':<7}{h.get('approved_by','')}")
    errs = gate_violations()
    print("\n" + ("\n".join(errs) if errs else "No gate violations."))
    return 1 if errs else 0


def cmd_check(_):
    errs = gate_violations() + chain_checks()
    for e in errs:
        print("FAIL", e)
    print("CHECK PASSED" if not errs else f"\n{len(errs)} problem(s)")
    return 1 if errs else 0


def cmd_approve(a):
    if a.by not in PERM["human_approvers"]:
        print(f"DENY: '{a.by}' is not in human_approvers. Agents never approve.")
        return 1
    p = step_path(a.step)
    if not is_filled(p):
        print(f"DENY: {p.name} is still a template (contains TODO).")
        return 1
    if a.step > 1 and read_header(step_path(a.step - 1)).get("status") != "APPROVED":
        print(f"DENY: step {a.step-1} must be APPROVED first.")
        return 1
    if read_header(p).get("author") == a.by:
        print("DENY: author cannot approve their own artifact.")
        return 1
    write_header(p, {"status": "APPROVED", "approved_by": a.by,
                     "approved_on": dt.date.today().isoformat()})
    print(f"APPROVED {p.name} by {a.by}")
    return 0


def classify(command: str) -> str:
    human_only = r"harness\.py\s+(" + "|".join(PERM["human_only_commands"]) + r")\b"
    for pat in PERM["deny_patterns"] + [human_only]:
        if re.search(pat, command, re.I):
            return "DENY"
    for pat in PERM["approval_patterns"]:
        if re.search(pat, command, re.I):
            return "NEEDS_APPROVAL"
    return "ALLOW"


def cmd_guard(a):
    """Exit codes: 0 allow, 2 block (works as a PreToolUse hook)."""
    command = a.command
    if a.hook:  # hook mode: JSON on stdin with tool_input.command
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
    verdict = classify(command)
    msg = {"ALLOW": "allowed",
           "NEEDS_APPROVAL": "needs explicit human approval (deploying/publishing action)",
           "DENY": "denied by permission layer (destructive or self-approving)"}[verdict]
    print(f"{verdict}: {msg}", file=sys.stderr if verdict != "ALLOW" else sys.stdout)
    return 0 if verdict == "ALLOW" else 2


def task_owner(task: str) -> str:
    for row in table_rows(step_path(6)):
        if row and row[0] == task and len(row) > 2:
            return row[2]
    return "unknown"


def cmd_loop(a):
    history = [h for h in read_jsonl(FEEDBACK) if h["task"] == a.task]
    iteration = 1 + len(history)
    verdict = a.verdict.upper()
    limit = LOOP["max_iterations_per_task"]
    # Escalation ladder: count how many times in a row this same criterion has failed.
    repeats = 1
    for h in reversed(history):
        if h["verdict"] != "PASS" and h["criteria"] == a.criteria:
            repeats += 1
        else:
            break

    if verdict == "PASS":
        action = "STOP: PASS"
    elif iteration >= limit:
        action = f"ESCALATE: {limit} iterations reached, human decision required"
    elif repeats >= LOOP["alternate_approach_after_repeats"]:
        action = (f"REFINE-ALTERNATE: {a.criteria or 'this criterion'} failed {repeats}x in a row. "
                  f"Route to {task_owner(a.task)}; do NOT repeat the previous fix, try a different approach "
                  f"(iteration {iteration+1}/{limit})")
    else:
        action = f"REFINE: route to {task_owner(a.task)} and re-run (iteration {iteration+1}/{limit})"

    entry = {"ts": dt.datetime.now().isoformat(timespec="seconds"), "task": a.task,
             "criteria": a.criteria, "verdict": verdict, "iteration": iteration,
             "note": a.note, "action": action}
    FEEDBACK.parent.mkdir(exist_ok=True)
    with FEEDBACK.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    if action.startswith("ESCALATE"):
        gov = step_path(8)
        with gov.open("a") as f:
            f.write(f"\n| {entry['ts']} | {a.task} | {a.criteria} | {a.note} | ESCALATED | |\n")
    print(action)
    return 0 if verdict == "PASS" else (3 if action.startswith("ESCALATE") else 1)


# ---------------------------------------------------------------- scoring (Loop layer)
MEM = CONFIG["memory_layer"]
SCORES = ROOT / MEM["scores"]
BASELINE = ROOT / MEM["test_baseline"]
CANDIDATES = ROOT / MEM["candidates"]


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def spec_criteria() -> dict:
    """AC id -> {weight, blocker} from the 02-spec acceptance table (Weight/Blocker columns optional)."""
    rows, header, out = table_rows(step_path(2)), [], {}
    for row in rows:
        if row and row[0].lower() == "id":
            header = [h.lower() for h in row]
        elif row and AC_RE.fullmatch(row[0]):
            cell = lambda name, d: row[header.index(name)] if name in header and header.index(name) < len(row) else d
            out[row[0]] = {"weight": float(cell("weight", "1") or 1),
                           "blocker": cell("blocker", "no").lower() in {"yes", "y", "true"}}
    return out


def test_counts() -> dict:
    """Test-integrity signal: number of test functions and assertions under tests/."""
    files = list((ROOT / "tests").rglob("test_*.py")) if (ROOT / "tests").exists() else []
    text = "\n".join(f.read_text() for f in files)
    return {"tests": len(re.findall(r"\bdef test_", text)),
            "asserts": len(re.findall(r"\bassert\w*\b", text))}


def cmd_score(_):
    crit = spec_criteria()
    verdicts = {r[0]: r[-1].upper() for r in table_rows(step_path(7)) if r and AC_RE.fullmatch(r[0])}
    pts = LOOP["verdict_points"]
    blockers, total_w, total = [], 0.0, 0.0
    print(f"{'criterion':<10}{'verdict':<9}{'points':<8}{'weight':<8}blocker")
    for ac, c in crit.items():
        v = verdicts.get(ac, "FAIL")
        p = pts.get(v, 0)
        total_w += c["weight"]; total += p * c["weight"]
        print(f"{ac:<10}{v:<9}{p:<8}{c['weight']:<8}{'yes' if c['blocker'] else ''}")
        if c["blocker"] and v != "PASS":
            blockers.append(f"{ac} is a blocker criterion and is {v}")
    score = round(total / total_w, 2) if total_w else 0.0

    # Test-integrity: tests or asserts must never go down between iterations.
    now = test_counts()
    base = json.loads(BASELINE.read_text()) if BASELINE.exists() else None
    if base and (now["tests"] < base["tests"] or now["asserts"] < base["asserts"]):
        blockers.append(f"TEST-INTEGRITY: tests/asserts dropped {base} -> {now} (weakened or deleted tests)")
    elif not base or now != base:
        BASELINE.write_text(json.dumps(now))  # ratchet upward only

    history = read_jsonl(SCORES)
    prev = history[-1]["score"] if history else None
    notes = []
    if prev is not None and score < prev:
        notes.append(f"REGRESSION: {prev} -> {score}; restore what broke before new work")
    n = LOOP["plateau_rounds"]
    recent = [h["score"] for h in history[-n:]] + [score]
    if len(recent) > n and max(recent) - min(recent) == 0 and score < LOOP["pass_threshold"]:
        notes.append(f"PLATEAU: score stuck at {score} for {n + 1} rounds; surface to human")
    verdict = "PASS" if score >= LOOP["pass_threshold"] and not blockers else "ITERATE"

    entry = {"ts": dt.datetime.now().isoformat(timespec="seconds"), "iteration": len(history) + 1,
             "score": score, "verdict": verdict, "blockers": blockers, "notes": notes, "tests": now}
    with SCORES.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"\nscore {score}/10 (threshold {LOOP['pass_threshold']})  iteration {entry['iteration']}")
    print("progression:", " -> ".join(str(h["score"]) for h in history + [entry]))
    for line in blockers + notes:
        print(line)
    print("VERDICT:", verdict)
    return 0 if verdict == "PASS" else 1


def require_human(name: str) -> bool:
    if name not in PERM["human_approvers"]:
        print(f"DENY: '{name}' is not in human_approvers.")
        return False
    return True


def cmd_rebaseline(a):
    if not require_human(a.by):
        return 1
    BASELINE.write_text(json.dumps(test_counts()))
    with (ROOT / MEM["decisions"]).open("a") as f:
        f.write(f"- {dt.date.today()} · tests · test baseline reset to {test_counts()} · {a.reason} · {a.by}\n")
    print("REBASELINED", test_counts())
    return 0


# ---------------------------------------------------------------- memory (evidence-gated learning)
def cmd_learn(a):
    """Agents may propose learnings. Repeated observations accumulate sources."""
    rows = read_jsonl(CANDIDATES)
    for r in rows:
        if r["key"] == a.key:
            if a.source not in r["sources"]:
                r["sources"].append(a.source)
            r["occurrences"] += 1
            break
    else:
        rows.append({"key": a.key, "text": a.text, "sources": [a.source], "occurrences": 1,
                     "state": "candidate", "created": dt.date.today().isoformat()})
    write_jsonl(CANDIDATES, rows)
    r = next(r for r in rows if r["key"] == a.key)
    ready = len(r["sources"]) >= MEM["promote_min_sources"]
    print(f"CANDIDATE {a.key}: {len(r['sources'])} source(s) -> {'PROMOTE-READY' if ready else 'needs more evidence'}")
    return 0


def cmd_promote(a):
    if not require_human(a.by):
        return 1
    rows = read_jsonl(CANDIDATES)
    r = next((r for r in rows if r["key"] == a.key), None)
    if not r:
        print(f"DENY: no candidate '{a.key}'"); return 1
    if len(r["sources"]) < MEM["promote_min_sources"]:
        print(f"DENY: needs {MEM['promote_min_sources']} independent sources, has {r['sources']}"); return 1
    r.update(state="approved", approved_by=a.by, approved_on=dt.date.today().isoformat())
    write_jsonl(CANDIDATES, rows)
    with (ROOT / MEM["learnings"]).open("a") as f:
        f.write(f"- {r['approved_on']} · {r['text']} (evidence: {', '.join(r['sources'])})\n")
    # Materialize approved learnings where GitHub Copilot auto-loads them.
    approved = [x for x in rows if x["state"] == "approved"]
    out = ROOT / MEM["materialized_to"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("---\napplyTo: \"**\"\n---\n<!-- generated by harness.py promote; do not edit -->\n"
                   "# Approved learnings\n" + "".join(f"- {x['text']}\n" for x in approved))
    print(f"PROMOTED {a.key} -> {MEM['learnings']} and {MEM['materialized_to']}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    ap = sub.add_parser("approve"); ap.add_argument("step", type=int); ap.add_argument("--by", required=True)
    ap.set_defaults(fn=cmd_approve)
    gp = sub.add_parser("guard"); gp.add_argument("command", nargs="?", default="")
    gp.add_argument("--hook", action="store_true"); gp.set_defaults(fn=cmd_guard)
    lp = sub.add_parser("loop"); lp.add_argument("--task", required=True)
    lp.add_argument("--verdict", required=True, choices=["PASS", "FAIL", "PARTIAL", "pass", "fail", "partial"])
    lp.add_argument("--criteria", default=""); lp.add_argument("--note", default="")
    lp.set_defaults(fn=cmd_loop)
    sub.add_parser("score").set_defaults(fn=cmd_score)
    rp = sub.add_parser("rebaseline"); rp.add_argument("--by", required=True)
    rp.add_argument("--reason", required=True); rp.set_defaults(fn=cmd_rebaseline)
    le = sub.add_parser("learn"); le.add_argument("--key", required=True); le.add_argument("--text", required=True)
    le.add_argument("--source", required=True); le.set_defaults(fn=cmd_learn)
    pr = sub.add_parser("promote"); pr.add_argument("--key", required=True); pr.add_argument("--by", required=True)
    pr.set_defaults(fn=cmd_promote)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
