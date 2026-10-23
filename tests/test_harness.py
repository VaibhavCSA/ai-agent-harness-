"""Each test proves one acceptance criterion from artifacts/02-spec.md.
Tests run against a throwaway copy of the repo so the real artifacts are never touched."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class HarnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(REPO, self.tmp / "r", ignore=shutil.ignore_patterns(".git", "__pycache__", "tests"))
        self.root = self.tmp / "r"
        (self.root / "memory" / "feedback.jsonl").write_text("")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_h(self, *args, stdin=None):
        return subprocess.run([sys.executable, str(self.root / "scripts" / "harness.py"), *args],
                              capture_output=True, text=True, input=stdin)

    def art(self, name):
        return self.root / "artifacts" / name

    def fill(self, name, body, author="planner-agent"):
        self.art(name).write_text(f"---\nstatus: DRAFT\nauthor: {author}\napproved_by:\napproved_on:\n---\n{body}\n")

    def approve_through(self, n):
        for i in range(1, n + 1):
            r = self.run_h("approve", str(i), "--by", "Vaibhav")
            self.assertEqual(r.returncode, 0, r.stdout)

    def spec_acs(self):
        import re
        return sorted(set(re.findall(r"\bAC-\d{2}\b", self.art("02-spec.md").read_text())))

    def write_eval(self, verdicts):
        rows = "\n".join(f"| {a} | T-01 | tests/test_harness.py | {v} |" for a, v in verdicts.items())
        self.fill("07-evaluation.md", "| Criterion | Task | Evidence | Verdict |\n|---|---|---|---|\n" + rows,
                  author="evaluator-agent")

    def write_tests(self, n_tests, n_asserts):
        d = self.root / "tests"; d.mkdir(exist_ok=True)
        body = "".join(f"def test_{i}():\n    pass\n" for i in range(n_tests)) + "assert True\n" * n_asserts
        (d / "test_app.py").write_text(body)

    # AC-01
    def test_ac01_status_lists_eight(self):
        out = self.run_h("status").stdout
        for i in range(1, 9):
            self.assertIn(f"0{i}-", out)

    # AC-02
    def test_ac02_gate_blocks_skipping_ahead(self):
        self.fill("05-plan.md", "1. build it")
        r = self.run_h("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("GATE: 05-plan.md", r.stdout)

    # AC-03
    def test_ac03_spec_without_criteria_fails(self):
        self.fill("02-spec.md", "# spec\nJust build a thing.", author="analyst-agent")
        self.assertIn("defines no acceptance criteria", self.run_h("check").stdout)

    # AC-04
    def test_ac04_evaluation_needs_evidence_and_verdict(self):
        self.fill("07-evaluation.md", "| Criterion | Task | Evidence | Verdict |\n|---|---|---|---|\n"
                                      "| AC-01 | T-01 | | MAYBE |", author="evaluator-agent")
        out = self.run_h("check").stdout
        self.assertIn("EVAL: AC-01 has no evidence", out)
        self.assertIn("verdict 'MAYBE'", out)
        self.assertIn("EVAL: AC-02 has no verdict", out)

    # AC-05
    def test_ac05_every_ac_owned_by_a_task(self):
        self.fill("06-tasks.md", "| Task | Description | Owner | Criteria |\n|---|---|---|---|\n"
                                 "| T-01 | build status | | AC-01 |")
        out = self.run_h("check").stdout
        self.assertIn("TASKS: T-01 has no owner", out)
        self.assertIn("TASKS: AC-02 is not owned by any task", out)

    # AC-06
    def test_ac06_only_humans_approve(self):
        self.assertIn("DENY", self.run_h("approve", "1", "--by", "analyst-agent").stdout)
        self.assertIn("DENY", self.run_h("approve", "3", "--by", "Vaibhav").stdout)  # template / out of order
        self.fill("01-problem.md", "problem", author="Vaibhav")
        self.assertIn("own artifact", self.run_h("approve", "1", "--by", "Vaibhav").stdout)
        self.assertEqual(self.run_h("guard", "python scripts/harness.py approve 2 --by Vaibhav").returncode, 2)

    # AC-07
    def test_ac07_guard_classifies_commands(self):
        cases = {"rm -rf /": "DENY", "az group delete -n rg-prod": "DENY", "terraform destroy": "DENY",
                 "git push origin main": "NEEDS_APPROVAL", "azd up": "NEEDS_APPROVAL",
                 "pytest -q": "ALLOW", "git status": "ALLOW"}
        for cmd, want in cases.items():
            r = self.run_h("guard", cmd)
            self.assertIn(want, r.stdout + r.stderr, cmd)
            self.assertEqual(r.returncode, 0 if want == "ALLOW" else 2, cmd)
        hook = json.dumps({"tool_name": "Bash", "tool_input": {"command": "rm -rf build"}})
        self.assertEqual(self.run_h("guard", "--hook", stdin=hook).returncode, 2)

    # AC-08 + AC-09
    def test_ac08_ac09_loop_routes_stops_escalates_and_logs(self):
        self.fill("06-tasks.md", "| Task | Description | Owner | Criteria |\n|---|---|---|---|\n"
                                 "| T-03 | guard | planner | AC-07 |")
        r1 = self.run_h("loop", "--task", "T-03", "--verdict", "FAIL", "--criteria", "AC-07", "--note", "hook exit 0")
        self.assertIn("REFINE: route to planner", r1.stdout)
        r2 = self.run_h("loop", "--task", "T-03", "--verdict", "PARTIAL", "--criteria", "AC-07")
        self.assertIn("REFINE-ALTERNATE", r2.stdout)  # AC-13: same criterion failed twice
        r3 = self.run_h("loop", "--task", "T-03", "--verdict", "FAIL", "--criteria", "AC-07")
        self.assertIn("ESCALATE", r3.stdout)
        self.assertEqual(r3.returncode, 3)
        self.assertIn("ESCALATED", self.art("08-governance.md").read_text())
        self.assertIn("STOP: PASS", self.run_h("loop", "--task", "T-04", "--verdict", "PASS").stdout)
        log = [json.loads(l) for l in (self.root / "memory" / "feedback.jsonl").read_text().splitlines()]
        self.assertEqual(len(log), 4)
        self.assertEqual({"ts", "task", "criteria", "verdict", "iteration", "note", "action"}, set(log[0]))

    # end-to-end: a fully approved, fully evaluated chain passes
    def test_happy_path_check_passes(self):
        self.approve_through(2)
        for name in ["03-spec-analysis.md", "04-architecture-review.md", "05-plan.md"]:
            self.fill(name, "done")
            self.run_h("approve", name[1], "--by", "Vaibhav")
        acs = self.spec_acs()
        self.fill("06-tasks.md", "| Task | Description | Owner | Criteria |\n|---|---|---|---|\n"
                                 f"| T-01 | all | planner | {', '.join(acs)} |")
        self.run_h("approve", "6", "--by", "Vaibhav")
        rows = "\n".join(f"| {a} | T-01 | tests/test_harness.py | PASS |" for a in acs)
        self.fill("07-evaluation.md", "| Criterion | Task | Evidence | Verdict |\n|---|---|---|---|\n" + rows,
                  author="evaluator-agent")
        r = self.run_h("check")
        self.assertEqual(r.returncode, 0, r.stdout)

    # AC-11
    def test_ac11_weighted_score_and_blockers(self):
        acs = self.spec_acs()
        self.write_eval({a: "PASS" for a in acs})
        r = self.run_h("score")
        self.assertIn("score 10.0/10", r.stdout); self.assertEqual(r.returncode, 0)
        # one blocker criterion failing forces ITERATE even with a high score
        v = {a: "PASS" for a in acs}; v["AC-07"] = "FAIL"
        self.write_eval(v)
        r = self.run_h("score")
        self.assertIn("AC-07 is a blocker", r.stdout); self.assertIn("VERDICT: ITERATE", r.stdout)
        self.assertIn("REGRESSION", r.stdout)  # AC-13: score went down

    # AC-12
    def test_ac12_test_integrity_and_human_rebaseline(self):
        self.write_eval({a: "PASS" for a in self.spec_acs()})
        self.write_tests(3, 3); self.run_h("score")
        self.write_tests(2, 3)  # a test was deleted
        r = self.run_h("score")
        self.assertIn("TEST-INTEGRITY", r.stdout); self.assertIn("VERDICT: ITERATE", r.stdout)
        self.assertIn("DENY", self.run_h("rebaseline", "--by", "coder-agent", "--reason", "x").stdout)
        self.assertEqual(self.run_h("guard", "python scripts/harness.py rebaseline --by Vaibhav --reason x").returncode, 2)
        self.assertEqual(self.run_h("rebaseline", "--by", "Vaibhav", "--reason", "merged duplicate tests").returncode, 0)
        self.assertIn("VERDICT: PASS", self.run_h("score").stdout)
        self.assertIn("merged duplicate tests", (self.root / "memory" / "decisions.md").read_text())

    # AC-13
    def test_ac13_plateau_flagged(self):
        v = {a: "PASS" for a in self.spec_acs()}; v["AC-01"] = v["AC-03"] = v["AC-04"] = v["AC-05"] = "FAIL"
        self.write_eval(v)
        for _ in range(2):
            self.run_h("score")
        self.assertIn("PLATEAU", self.run_h("score").stdout)

    # AC-14
    def test_ac14_learning_is_evidence_gated_and_human_promoted(self):
        args = ["learn", "--key", "no-mocks-for-guard", "--text", "Test the guard via subprocess, not mocks"]
        self.assertIn("needs more evidence", self.run_h(*args, "--source", "feedback:T-03").stdout)
        self.assertIn("DENY", self.run_h("promote", "--key", "no-mocks-for-guard", "--by", "Vaibhav").stdout)
        self.assertIn("PROMOTE-READY", self.run_h(*args, "--source", "review:PR-12").stdout)
        self.assertIn("DENY", self.run_h("promote", "--key", "no-mocks-for-guard", "--by", "evaluator-agent").stdout)
        self.assertEqual(self.run_h("promote", "--key", "no-mocks-for-guard", "--by", "Vaibhav").returncode, 0)
        inst = (self.root / ".github" / "instructions" / "learnings.instructions.md").read_text()
        self.assertIn("applyTo", inst); self.assertIn("subprocess, not mocks", inst)

    # AC-15
    def test_ac15_every_role_has_agent_spec_with_scoped_tools(self):
        cfg = json.loads((self.root / "harness" / "harness.json").read_text())
        for role in cfg["execution_layer"]["roles"]:
            spec = self.root / ".github" / "agents" / f"{role}.agent.md"
            self.assertTrue(spec.exists(), role)
            tools = [l for l in spec.read_text().splitlines() if l.startswith("tools:")]
            self.assertTrue(tools, f"{role} has no tools: list")
            has_exec = "execute/" in tools[0]
            self.assertEqual(has_exec, role in {"coder", "evaluator"}, role)


if __name__ == "__main__":
    unittest.main()
