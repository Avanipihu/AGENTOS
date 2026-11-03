"""Tests for memory_simulator.py (matrix IDs M1-M4 from the project spec).

Run from the AGENTOS folder:  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory_simulator import DEFAULT_FRAME_CAPACITY, DEFAULT_REFERENCE_STRING, simulate


class TestBasicEvents(unittest.TestCase):
    def test_m1_hit_on_resident_page(self):
        for policy in ("FIFO", "LRU"):
            r = simulate([7, 7], 2, policy)
            self.assertEqual(r["trace"][1]["result"], "HIT")
            self.assertIsNone(r["trace"][1]["evicted"])
            self.assertEqual((r["hits"], r["faults"]), (1, 1))

    def test_m2_fault_with_free_frame_no_eviction(self):
        for policy in ("FIFO", "LRU"):
            r = simulate([1, 2], 3, policy)
            for e in r["trace"]:
                self.assertEqual(e["result"], "FAULT")
                self.assertIsNone(e["evicted"])
            self.assertEqual(r["trace"][-1]["frames"], [1, 2])
            self.assertEqual(r["evictions"], 0)

    def test_m3_fifo_evicts_oldest_loaded(self):
        # Page 1 is hit before 3 arrives; FIFO still evicts 1 (loaded first).
        r = simulate([1, 2, 1, 3], 2, "FIFO")
        last = r["trace"][-1]
        self.assertEqual((last["result"], last["evicted"]), ("FAULT", 1))
        self.assertEqual(last["frames"], [3, 2])

    def test_m3_lru_evicts_least_recently_used(self):
        # Same input: the hit on 1 makes 2 least recently used, so LRU evicts 2.
        r = simulate([1, 2, 1, 3], 2, "LRU")
        last = r["trace"][-1]
        self.assertEqual((last["result"], last["evicted"]), ("FAULT", 2))
        self.assertEqual(last["frames"], [1, 3])


class TestDefaultExperiment(unittest.TestCase):
    """Canonical Unit 4 experiment (22 references, 3 frames).

    Expected values were traced by hand from the FIFO/LRU definitions and
    cross-checked against an independent run; they are not copied from the
    simulator's own output.
    """

    def run_default(self, policy):
        return simulate(DEFAULT_REFERENCE_STRING, DEFAULT_FRAME_CAPACITY, policy)

    def test_fifo_default(self):
        r = self.run_default("FIFO")
        self.assertEqual([e["evicted"] for e in r["trace"] if e["evicted"] is not None],
                         [7, 0, 1, 2, 3, 0, 4, 2, 3, 0, 1, 2])
        self.assertEqual(r["trace"][-1]["frames"], [7, 0, 1])
        self.assertEqual((r["hits"], r["faults"], r["evictions"]), (7, 15, 12))
        self.assertAlmostEqual(r["hit_ratio"], 7 / 22)

    def test_lru_default(self):
        r = self.run_default("LRU")
        self.assertEqual([e["evicted"] for e in r["trace"] if e["evicted"] is not None],
                         [7, 1, 2, 3, 0, 4, 0, 3, 2])
        self.assertEqual(r["trace"][-1]["frames"], [1, 0, 7])
        self.assertEqual((r["hits"], r["faults"], r["evictions"]), (10, 12, 9))
        self.assertAlmostEqual(r["hit_ratio"], 10 / 22)

    def test_trace_totals_match_summary(self):
        for policy in ("FIFO", "LRU"):
            r = self.run_default(policy)
            trace = r["trace"]
            self.assertEqual(len(trace), len(DEFAULT_REFERENCE_STRING))
            self.assertEqual(sum(e["result"] == "HIT" for e in trace), r["hits"])
            self.assertEqual(sum(e["result"] == "FAULT" for e in trace), r["faults"])
            self.assertEqual(sum(e["evicted"] is not None for e in trace), r["evictions"])
            self.assertEqual(r["hits"] + r["faults"], len(trace))
            self.assertAlmostEqual(r["hit_ratio"], r["hits"] / len(trace))
            for e in trace:
                self.assertLessEqual(len(e["frames"]), DEFAULT_FRAME_CAPACITY)


class TestRepeatability(unittest.TestCase):
    def test_m4_same_input_same_output(self):
        for policy in ("FIFO", "LRU"):
            first = simulate(DEFAULT_REFERENCE_STRING, 3, policy)
            second = simulate(DEFAULT_REFERENCE_STRING, 3, policy)
            self.assertEqual(first, second)

    def test_input_list_not_modified(self):
        refs = list(DEFAULT_REFERENCE_STRING)
        simulate(refs, 3, "LRU")
        self.assertEqual(refs, DEFAULT_REFERENCE_STRING)


class TestInvalidInput(unittest.TestCase):
    def test_invalid_frame_capacity(self):
        for bad in (0, -1, 2.5, "3", None, True):
            with self.assertRaises(ValueError):
                simulate([1, 2], bad, "FIFO")

    def test_unknown_policy(self):
        for bad in ("OPT", "", None, 1):
            with self.assertRaises(ValueError):
                simulate([1, 2], 3, bad)

    def test_invalid_reference_string(self):
        with self.assertRaises(ValueError):
            simulate(None, 3, "FIFO")

    def test_policy_is_case_insensitive(self):
        self.assertEqual(simulate([1], 1, "lru")["policy"], "LRU")

    def test_empty_reference_string(self):
        r = simulate([], 3, "FIFO")
        self.assertEqual((r["hits"], r["faults"], r["evictions"], r["hit_ratio"]), (0, 0, 0, 0.0))


if __name__ == "__main__":
    unittest.main()
