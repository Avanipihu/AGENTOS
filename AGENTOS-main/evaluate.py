"""AgentOS evaluation runner: reproduces every number used in the report.

Runs the unit tests, maps them to the test matrix (M1-M4, F1-F4 in the project
spec), replays the memory and file-system experiments twice to check they are
repeatable, and writes the results to outputs/.

Usage (from the AGENTOS folder):
    python evaluate.py            # run everything, rewrite outputs/
    python evaluate.py --check    # run everything, fail if outputs/ is out of date
"""

import argparse
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from file_system_simulator import build_default_workspace, format_log, run_scenario  # noqa: E402
from memory_simulator import (DEFAULT_FRAME_CAPACITY, DEFAULT_REFERENCE_STRING,  # noqa: E402
                              POLICIES, format_result, simulate)

OUTPUT_DIR = os.path.join(HERE, "outputs")

# Test matrix from the project specification (section 10).
MATRIX = [
    ("M1", "Request a page already in a frame", "Hit increments; no fault"),
    ("M2", "Request a missing page while a frame is free", "Fault increments; page loads without eviction"),
    ("M3", "Request a missing page when all frames are full", "Fault and policy-selected eviction are recorded"),
    ("M4", "Rerun the same input/policy", "Identical counters and trace"),
    ("F1", "List directory and resolve valid path", "Correct entries/path returned"),
    ("F2", "Create/read/write/delete a permitted file", "Operation succeeds and log is updated"),
    ("F3", "Agent attempts a denied operation", "Operation is rejected, with reason logged"),
    ("F4", "Invalid path or operation", "Clear error; simulated state remains valid"),
]

# Extra workloads. Every number in the report comes from running these.
WORKLOADS = [
    ("A (Unit 4 notes string)", DEFAULT_REFERENCE_STRING),
    ("B (short mixed string)", [1, 2, 3, 1, 4, 2, 5, 1, 2, 3]),
    ("C (cyclic loop)", [1, 2, 3, 4] * 4),
    ("D (Belady string)", [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]),
]


# ---------- test execution ----------

class _Collector(unittest.TextTestResult):
    """Records pass/fail per test id."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = {}

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes[test.id()] = "PASS"

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes[test.id()] = "FAIL"

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes[test.id()] = "ERROR"


def run_tests():
    # Same discovery as `python -m unittest discover -s tests` (tests/ has no __init__.py).
    suite = unittest.defaultTestLoader.discover(os.path.join(HERE, "tests"))
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, resultclass=_Collector, verbosity=0)
    result = runner.run(suite)
    return result.outcomes, result.testsRun, stream.getvalue()


def matrix_status(outcomes):
    """Map each matrix ID to its tests (by the test_<id>_ name prefix) and status."""
    rows = []
    for mid, desc, expected in MATRIX:
        names = sorted(t for t in outcomes
                       if re.search(rf"\.test_{mid.lower()}_", t))
        if not names:
            status = "NO TEST"
        elif all(outcomes[t] == "PASS" for t in names):
            status = "PASS"
        else:
            status = "FAIL"
        rows.append((mid, desc, expected, [n.split(".")[-1] for n in names], status))
    return rows


# ---------- experiments ----------

def memory_experiment():
    runs = {p: simulate(DEFAULT_REFERENCE_STRING, DEFAULT_FRAME_CAPACITY, p) for p in POLICIES}
    again = {p: simulate(DEFAULT_REFERENCE_STRING, DEFAULT_FRAME_CAPACITY, p) for p in POLICIES}
    return runs, runs == again


def workload_table():
    rows = []
    for name, refs in WORKLOADS:
        for frames in (3,):
            r = {p: simulate(refs, frames, p) for p in POLICIES}
            rows.append((name, len(refs), frames, r["FIFO"], r["LRU"]))
    return rows


def frame_sweep(refs, frame_counts):
    return [(f, simulate(refs, f, "FIFO")["faults"], simulate(refs, f, "LRU")["faults"])
            for f in frame_counts]


def file_experiment():
    fs1, res1 = run_scenario()
    fs2, res2 = run_scenario()
    same = (format_log(fs1) == format_log(fs2) and res1 == res2 and fs1.tree() == fs2.tree())
    return fs1, same


# ---------- report text ----------

def build_outputs():
    outcomes, n_tests, test_text = run_tests()
    matrix = matrix_status(outcomes)
    mem_runs, mem_same = memory_experiment()
    fs, fs_same = file_experiment()
    s = fs.summary()

    memory_txt = "\n\n".join(format_result(mem_runs[p]) for p in POLICIES) + "\n"

    file_txt = "\n".join([
        "Initial directory tree:", build_default_workspace().tree(), "",
        "Audit log:", format_log(fs), "",
        "Final directory tree:", fs.tree(), "",
        f"Operations: {s['total']}   OK: {s['OK']}   Denied: {s['DENIED']}   "
        f"Error: {s['ERROR']}   Conflict: {s['CONFLICT']}", ""])

    matrix_md = ["# Test matrix (generated by `evaluate.py`)", "",
                 "| ID | Test | Expected behaviour | Covering tests | Status |",
                 "|---|---|---|---|---|"]
    for mid, desc, expected, names, status in matrix:
        covering = "<br>".join(f"`{n}`" for n in names) or "-"
        matrix_md.append(f"| {mid} | {desc} | {expected} | {covering} | **{status}** |")
    passed = sum(1 for o in outcomes.values() if o == "PASS")
    matrix_md += ["", f"Total tests run: {n_tests}; passed: {passed}.", ""]

    summary = ["# Evaluation results (generated by `evaluate.py`)", "",
               "All values below were produced by running the code. Do not edit by hand.", "",
               "## 1. Memory: FIFO vs LRU on the default experiment", "",
               f"Reference string ({len(DEFAULT_REFERENCE_STRING)} references): "
               f"`{DEFAULT_REFERENCE_STRING}`, frames: {DEFAULT_FRAME_CAPACITY}", "",
               "| Policy | Hits | Faults | Evictions | Hit ratio |", "|---|---:|---:|---:|---:|"]
    for p in POLICIES:
        r = mem_runs[p]
        summary.append(f"| {p} | {r['hits']} | {r['faults']} | {r['evictions']} | {r['hit_ratio']:.4f} |")

    summary += ["", "## 2. Memory: other workloads (3 frames)", "",
                "Used to check whether one policy wins on every input.", "",
                "| Workload | Refs | FIFO faults | LRU faults | Fewer faults |", "|---|---:|---:|---:|---|"]
    for name, n, frames, fifo, lru in workload_table():
        better = "LRU" if lru["faults"] < fifo["faults"] else \
                 "FIFO" if fifo["faults"] < lru["faults"] else "tie"
        summary.append(f"| {name} | {n} | {fifo['faults']} | {lru['faults']} | {better} |")

    belady = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
    summary += ["", "## 3. Memory: frame-count sweep on workload D", "",
                f"Reference string: `{belady}`", "",
                "| Frames | FIFO faults | LRU faults |", "|---:|---:|---:|"]
    for f, fifo, lru in frame_sweep(belady, range(1, 6)):
        summary.append(f"| {f} | {fifo} | {lru} |")
    summary += ["", "More frames can increase FIFO faults (Belady's anomaly) but never "
                "increase LRU faults, which is a stack algorithm. Check the table above "
                "before quoting this in the report.", ""]

    summary += ["## 4. File system: default scenario", "",
                "| Outcome | Count |", "|---|---:|",
                f"| OK | {s['OK']} |", f"| DENIED | {s['DENIED']} |",
                f"| ERROR | {s['ERROR']} |", f"| CONFLICT (stale version) | {s['CONFLICT']} |",
                f"| Total operations | {s['total']} |", "",
                "Full audit log: `outputs/file_system_log.txt`.", "",
                "## 5. Reproducibility", "",
                f"- Memory experiment repeated twice, identical results: **{mem_same}**",
                f"- File-system scenario repeated twice, identical log/tree: **{fs_same}**", "",
                "## 6. Test status", "",
                f"- Tests run: {n_tests}, passed: {passed}",
                f"- Matrix IDs passing: {sum(1 for m in matrix if m[4] == 'PASS')} of {len(matrix)}", ""]

    files = {
        "memory_results.txt": memory_txt,
        "file_system_log.txt": file_txt,
        "test_matrix.md": "\n".join(matrix_md),
        "results_summary.md": "\n".join(summary),
    }
    ok = (all(m[4] == "PASS" for m in matrix) and mem_same and fs_same
          and all(o == "PASS" for o in outcomes.values()))
    return files, ok, test_text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the AgentOS evaluation")
    parser.add_argument("--check", action="store_true",
                        help="do not write; fail if outputs/ differs from a fresh run")
    args = parser.parse_args(argv)

    files, ok, test_text = build_outputs()
    if not ok:
        print("EVALUATION FAILED: a test or reproducibility check did not pass.")
        print(test_text)
        return 1

    if args.check:
        stale = []
        for name, text in files.items():
            path = os.path.join(OUTPUT_DIR, name)
            if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
                stale.append(name)
        if stale:
            print("outputs/ is out of date: " + ", ".join(stale) + ". Run `python evaluate.py`.")
            return 1
        print("All checks passed; outputs/ is up to date.")
        return 0

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for name, text in files.items():
        with open(os.path.join(OUTPUT_DIR, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    print("All tests and reproducibility checks passed.")
    print("Wrote: " + ", ".join(f"outputs/{n}" for n in files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
