"""Tests for file_system_simulator.py (matrix IDs F1-F4 from the project spec).

Run from the AGENTOS folder:  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from file_system_simulator import (DEFAULT_SCENARIO, build_default_workspace,
                                   format_log, run_scenario)

RESEARCH, CODING, REPORT = "Research Agent", "Coding Agent", "Report Agent"
NOTES = "/workspace/notes/source_notes.txt"
RESULTS = "/workspace/results/results.csv"
REPORT_MD = "/workspace/reports/final_report.md"


class TestPathsAndListing(unittest.TestCase):
    def setUp(self):
        self.fs = build_default_workspace()

    def test_f1_list_directory(self):
        r = self.fs.execute(RESEARCH, "list", "/workspace")
        self.assertTrue(r["success"])
        self.assertEqual(r["data"], ["notes/", "reports/", "results/"])

    def test_f1_resolve_valid_path_and_attributes(self):
        r = self.fs.execute(RESEARCH, "stat", NOTES)
        self.assertTrue(r["success"])
        self.assertEqual(r["data"]["type"], "file")
        self.assertEqual(r["data"]["owner"], "system")
        self.assertEqual(r["data"]["version"], 1)
        self.assertEqual(r["data"]["size"], len("page-reference notes\n"))

    def test_f1_redundant_slashes_resolve_to_same_file(self):
        r = self.fs.execute(RESEARCH, "read", "/workspace//notes/./source_notes.txt/")
        self.assertTrue(r["success"])

    def test_f1_search_only_returns_readable_paths(self):
        found = self.fs.execute(RESEARCH, "search", "/workspace", "results")["data"]
        self.assertEqual(found, ["/workspace/results", RESULTS])
        # Coding Agent cannot read /workspace, so searching it is denied outright.
        self.assertEqual(self.fs.execute(CODING, "search", "/workspace", "results")["status"],
                         "DENIED")


class TestPermittedOperations(unittest.TestCase):
    def setUp(self):
        self.fs = build_default_workspace()

    def test_f2_create_read_write_delete(self):
        path = "/workspace/results/extra.csv"
        self.assertTrue(self.fs.execute(CODING, "create", path, "a\n")["success"])
        r = self.fs.execute(CODING, "read", path)
        self.assertEqual(r["data"], {"content": "a\n", "version": 1})
        w = self.fs.execute(CODING, "write", path, "b\n")
        self.assertTrue(w["success"])
        self.assertEqual(self.fs.execute(CODING, "read", path)["data"],
                         {"content": "b\n", "version": 2})
        self.assertTrue(self.fs.execute(CODING, "delete", path)["success"])
        self.assertEqual(self.fs.execute(CODING, "read", path)["status"], "ERROR")

    def test_f2_every_operation_is_logged_in_order(self):
        self.fs.execute(CODING, "read", RESULTS)
        self.fs.execute(CODING, "write", RESULTS, "x")
        self.fs.execute(REPORT, "write", RESULTS, "y")          # denied
        self.assertEqual([e["step"] for e in self.fs.log], [1, 2, 3])
        self.assertEqual([e["status"] for e in self.fs.log], ["OK", "OK", "DENIED"])
        self.assertEqual(self.fs.summary()["total"], 3)

    def test_f2_write_updates_version_size_and_modified_time(self):
        self.fs.execute(CODING, "write", RESULTS, "run,faults\nFIFO,15\n")
        attrs = self.fs.execute(CODING, "stat", RESULTS)["data"]
        self.assertEqual(attrs["version"], 2)
        self.assertEqual(attrs["size"], len("run,faults\nFIFO,15\n"))
        self.assertGreater(attrs["modified"], attrs["created"])

    def test_f2_mkdir_then_create_inside_it(self):
        self.assertTrue(self.fs.execute(REPORT, "mkdir", "/workspace/reports/drafts")["success"])
        self.assertTrue(self.fs.execute(REPORT, "create", "/workspace/reports/drafts/a.md")["success"])
        # A non-empty directory cannot be deleted.
        self.assertEqual(self.fs.execute(REPORT, "delete", "/workspace/reports/drafts")["status"],
                         "ERROR")


class TestProtection(unittest.TestCase):
    def setUp(self):
        self.fs = build_default_workspace()

    def test_f3_write_outside_own_area_is_denied_and_state_unchanged(self):
        before = self.fs.tree()
        r = self.fs.execute(REPORT, "write", RESULTS, "tampered")
        self.assertFalse(r["success"])
        self.assertEqual(r["status"], "DENIED")
        self.assertIn("no 'w' permission", r["reason"])
        self.assertEqual(self.fs.tree(), before)
        self.assertEqual(self.fs.log[-1]["status"], "DENIED")
        self.assertEqual(self.fs.log[-1]["reason"], r["reason"])

    def test_f3_read_only_agent_cannot_delete(self):
        self.assertEqual(self.fs.execute(RESEARCH, "delete", REPORT_MD)["status"], "DENIED")
        self.assertTrue(self.fs.execute(RESEARCH, "stat", REPORT_MD)["success"])   # still there

    def test_f3_agents_have_different_rights(self):
        # The same operation on the same path gives different outcomes per agent.
        self.assertTrue(self.fs.execute(CODING, "write", RESULTS, "ok")["success"])
        self.assertFalse(self.fs.execute(RESEARCH, "write", RESULTS, "no")["success"])
        self.assertTrue(self.fs.execute(RESEARCH, "read", RESULTS)["success"])

    def test_f3_unknown_agent_is_denied(self):
        self.assertEqual(self.fs.execute("Intruder", "read", NOTES)["status"], "DENIED")

    def test_denial_does_not_reveal_whether_path_exists(self):
        a = self.fs.execute(CODING, "read", "/workspace/reports/final_report.md")
        b = self.fs.execute(CODING, "read", "/workspace/reports/nothing.md")
        self.assertEqual((a["status"], b["status"]), ("DENIED", "DENIED"))


class TestInvalidRequests(unittest.TestCase):
    def setUp(self):
        self.fs = build_default_workspace()
        self.before = self.fs.tree()

    def _assert_error(self, result, text):
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "ERROR")
        self.assertIn(text, result["reason"])
        self.assertEqual(self.fs.tree(), self.before)     # state still valid and unchanged

    def test_f4_relative_path(self):
        self._assert_error(self.fs.execute(CODING, "read", "results/results.csv"), "absolute")

    def test_f4_dotdot_path(self):
        self._assert_error(self.fs.execute(CODING, "read", "/workspace/results/../notes/source_notes.txt"), "'..'")

    def test_f4_non_string_path(self):
        self._assert_error(self.fs.execute(CODING, "read", None), "invalid path")

    def test_f4_unknown_operation(self):
        self._assert_error(self.fs.execute(CODING, "rename", RESULTS), "unknown operation")

    def test_f4_missing_file(self):
        self._assert_error(self.fs.execute(CODING, "read", "/workspace/results/none.csv"), "does not exist")

    def test_f4_create_in_missing_directory(self):
        self._assert_error(self.fs.execute(CODING, "create", "/workspace/results/sub/a.csv"), "parent")

    def test_f4_create_existing_file(self):
        self._assert_error(self.fs.execute(CODING, "create", RESULTS), "already exists")

    def test_f4_write_needs_string_content(self):
        self._assert_error(self.fs.execute(CODING, "write", RESULTS, 123), "string content")

    def test_f4_read_a_directory(self):
        self._assert_error(self.fs.execute(RESEARCH, "read", "/workspace/notes"), "directory")

    def test_f4_cannot_delete_root(self):
        # No agent has a rule on "/", so this is denied rather than reaching the root check.
        self.assertEqual(self.fs.execute(CODING, "delete", "/")["status"], "DENIED")
        self.assertEqual(self.fs.tree(), self.before)


class TestVersionCheck(unittest.TestCase):
    """Optional extension: stale-write detection with expected_version."""

    def test_stale_write_rejected_and_fresh_write_accepted(self):
        fs = build_default_workspace()
        read = fs.execute(CODING, "read", RESULTS)["data"]            # version 1
        fs.execute(CODING, "write", RESULTS, "newer")                 # version 2 by another update
        stale = fs.execute(CODING, "write", RESULTS, "lost update", expected_version=read["version"])
        self.assertEqual(stale["status"], "CONFLICT")
        self.assertEqual(fs.execute(CODING, "read", RESULTS)["data"]["content"], "newer")
        fresh = fs.execute(CODING, "write", RESULTS, "merged", expected_version=2)
        self.assertTrue(fresh["success"])

    def test_without_version_check_the_lost_update_is_accepted(self):
        fs = build_default_workspace()
        fs.execute(CODING, "write", RESULTS, "newer")
        self.assertTrue(fs.execute(CODING, "write", RESULTS, "lost update")["success"])


class TestRepeatability(unittest.TestCase):
    def test_f_scenario_is_repeatable(self):
        fs1, res1 = run_scenario()
        fs2, res2 = run_scenario()
        self.assertEqual(format_log(fs1), format_log(fs2))
        self.assertEqual(res1, res2)
        self.assertEqual(fs1.tree(), fs2.tree())

    def test_default_scenario_outcomes(self):
        fs, _ = run_scenario()
        self.assertEqual(fs.summary(),
                         {"OK": 10, "DENIED": 2, "ERROR": 2, "CONFLICT": 1, "total": 15})
        self.assertEqual(len(fs.log), len(DEFAULT_SCENARIO))

    def test_f_scenario_does_not_touch_real_files(self):
        before = set(os.listdir(os.getcwd()))
        run_scenario()
        self.assertEqual(set(os.listdir(os.getcwd())), before)


if __name__ == "__main__":
    unittest.main()
