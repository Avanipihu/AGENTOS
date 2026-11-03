"""AgentOS file-system module: simulated directory tree, operations and permissions.

Educational simulation for the AgentOS OS case study (Unit 5).
Everything lives in program state. No real files are read, written or deleted.

Usage:
    python file_system_simulator.py        # default workspace + demo scenario
"""

import argparse
import posixpath

AGENTS = ("Research Agent", "Coding Agent", "Report Agent")
OPERATIONS = ("list", "read", "write", "create", "delete", "mkdir", "stat", "search")

# Permission letters. A rule grants a set of letters on a path prefix.
#   r = read file / list directory / stat / search
#   w = write (overwrite) an existing file
#   c = create a file or directory
#   d = delete a file or empty directory
# The longest matching prefix wins. No matching rule means access is denied.
DEFAULT_PERMISSIONS = {
    "Research Agent": {"/workspace": "r", "/workspace/notes": "rwcd"},
    "Coding Agent": {"/workspace/notes": "r", "/workspace/results": "rwcd"},
    "Report Agent": {"/workspace/notes": "r", "/workspace/results": "r",
                     "/workspace/reports": "rwcd"},
}

REQUIRED_PERMISSION = {
    "list": "r", "read": "r", "stat": "r", "search": "r",
    "write": "w", "create": "c", "mkdir": "c", "delete": "d",
}

# Initial simulated files: path -> placeholder content.
DEFAULT_FILES = {
    "/workspace/notes/source_notes.txt": "page-reference notes\n",
    "/workspace/results/results.csv": "run,faults\n",
    "/workspace/reports/final_report.md": "# Final report\n",
}
DEFAULT_DIRECTORIES = ("/workspace", "/workspace/notes", "/workspace/results",
                       "/workspace/reports")


class _Node:
    """One entry in the tree: a directory or a file, with its attributes."""

    def __init__(self, name, is_dir, owner, tick, content=""):
        self.name = name
        self.is_dir = is_dir
        self.owner = owner
        self.created = tick
        self.modified = tick
        self.content = content       # files only
        self.version = 1             # files only: +1 on every successful write
        self.children = {} if is_dir else None

    @property
    def size(self):
        return 0 if self.is_dir else len(self.content)


class FileSystem:
    """Simulated hierarchical file system with per-agent access control.

    Time is a logical counter that increases by one per operation, so runs are
    deterministic (no wall-clock timestamps).
    """

    def __init__(self, permissions=None):
        self.permissions = {a: dict(r) for a, r in
                            (permissions or DEFAULT_PERMISSIONS).items()}
        self.root = _Node("", True, "system", 0)
        self.log = []
        self._tick = 0

    # ---------- path helpers ----------

    @staticmethod
    def parse_path(path):
        """Return the list of path components for an absolute path.

        Raises ValueError for non-string, relative, empty or '..'-containing
        paths. '/' gives []. Repeated and trailing slashes are tolerated.
        """
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError(f"path must be an absolute string starting with '/', got {path!r}")
        parts = [p for p in path.split("/") if p not in ("", ".")]
        if ".." in parts:
            raise ValueError("'..' is not allowed in simulated paths")
        return parts

    @staticmethod
    def _join(parts):
        return "/" + "/".join(parts)

    def _lookup(self, parts):
        node = self.root
        for p in parts:
            if not node.is_dir or p not in node.children:
                return None
            node = node.children[p]
        return node

    def _allowed(self, agent, op, path):
        needed = REQUIRED_PERMISSION[op]
        best_len, best = -1, ""
        for prefix, letters in self.permissions[agent].items():
            norm = posixpath.normpath(prefix)
            if path == norm or path.startswith(norm.rstrip("/") + "/"):
                if len(norm) > best_len:
                    best_len, best = len(norm), letters
        return needed in best

    # ---------- main entry point ----------

    def execute(self, agent, operation, path, content=None, expected_version=None):
        """Run one operation for an agent and return a result dict.

        Never raises for a bad request: invalid input, denial and conflicts are
        returned (and logged) with a reason, and the tree is left unchanged.

        Result keys: success (bool), status ("OK", "DENIED", "ERROR" or
        "CONFLICT"), reason, agent, operation, path and data (operation output).

        content       - text for write/create; name substring for search.
        expected_version - optional, for write: reject the write if the file's
                        version differs (stale read detection).
        """
        self._tick += 1
        status, reason, data = self._run(agent, operation, path, content, expected_version)
        entry = {"step": self._tick, "agent": agent, "operation": operation,
                 "path": path, "status": status, "reason": reason}
        self.log.append(entry)
        return {"success": status == "OK", "status": status, "reason": reason,
                "agent": agent, "operation": operation, "path": path, "data": data}

    def _run(self, agent, op, path, content, expected_version):
        if agent not in self.permissions:
            return "DENIED", f"unknown agent {agent!r}", None
        if op not in OPERATIONS:
            return "ERROR", f"unknown operation {op!r}; expected one of {OPERATIONS}", None
        try:
            parts = self.parse_path(path)
        except ValueError as err:
            return "ERROR", f"invalid path: {err}", None
        norm = self._join(parts)

        # Protection is checked before existence so denials do not reveal
        # whether a path the agent cannot access exists.
        if not self._allowed(agent, op, norm):
            return "DENIED", (f"{agent} has no '{REQUIRED_PERMISSION[op]}' permission "
                              f"on {norm}"), None

        handler = getattr(self, "_op_" + op)
        return handler(agent, parts, norm, content, expected_version)

    # ---------- operations (each returns (status, reason, data)) ----------

    def _op_list(self, agent, parts, norm, content, expected_version):
        node = self._lookup(parts)
        if node is None:
            return "ERROR", f"{norm} does not exist", None
        if not node.is_dir:
            return "ERROR", f"{norm} is a file, not a directory", None
        entries = [(n + "/" if c.is_dir else n) for n, c in sorted(node.children.items())]
        return "OK", "listed", entries

    def _op_stat(self, agent, parts, norm, content, expected_version):
        node = self._lookup(parts)
        if node is None:
            return "ERROR", f"{norm} does not exist", None
        return "OK", "stat", self._attributes(node, norm)

    def _op_read(self, agent, parts, norm, content, expected_version):
        node = self._lookup(parts)
        if node is None:
            return "ERROR", f"{norm} does not exist", None
        if node.is_dir:
            return "ERROR", f"{norm} is a directory, not a file", None
        return "OK", "read", {"content": node.content, "version": node.version}

    def _op_write(self, agent, parts, norm, content, expected_version):
        if not isinstance(content, str):
            return "ERROR", "write needs string content", None
        node = self._lookup(parts)
        if node is None:
            return "ERROR", f"{norm} does not exist (use create)", None
        if node.is_dir:
            return "ERROR", f"{norm} is a directory, not a file", None
        if expected_version is not None and expected_version != node.version:
            return "CONFLICT", (f"stale write: based on version {expected_version}, "
                                f"file is at version {node.version}"), None
        node.content = content
        node.version += 1
        node.modified = self._tick
        return "OK", f"written, now version {node.version}", {"version": node.version}

    def _op_create(self, agent, parts, norm, content, expected_version):
        if not parts:
            return "ERROR", "cannot create the root directory", None
        if content is not None and not isinstance(content, str):
            return "ERROR", "create content must be a string", None
        parent = self._lookup(parts[:-1])
        if parent is None or not parent.is_dir:
            return "ERROR", f"parent directory of {norm} does not exist", None
        if parts[-1] in parent.children:
            return "ERROR", f"{norm} already exists", None
        parent.children[parts[-1]] = _Node(parts[-1], False, agent, self._tick, content or "")
        return "OK", "created", {"version": 1}

    def _op_mkdir(self, agent, parts, norm, content, expected_version):
        if not parts:
            return "ERROR", "root directory already exists", None
        parent = self._lookup(parts[:-1])
        if parent is None or not parent.is_dir:
            return "ERROR", f"parent directory of {norm} does not exist", None
        if parts[-1] in parent.children:
            return "ERROR", f"{norm} already exists", None
        parent.children[parts[-1]] = _Node(parts[-1], True, agent, self._tick)
        return "OK", "directory created", None

    def _op_delete(self, agent, parts, norm, content, expected_version):
        if not parts:
            return "ERROR", "cannot delete the root directory", None
        node = self._lookup(parts)
        if node is None:
            return "ERROR", f"{norm} does not exist", None
        if node.is_dir and node.children:
            return "ERROR", f"{norm} is a non-empty directory", None
        del self._lookup(parts[:-1]).children[parts[-1]]
        return "OK", "deleted", None

    def _op_search(self, agent, parts, norm, content, expected_version):
        if not isinstance(content, str) or not content:
            return "ERROR", "search needs a non-empty name substring in content", None
        start = self._lookup(parts)
        if start is None:
            return "ERROR", f"{norm} does not exist", None
        matches = []

        def walk(node, node_parts):
            for name, child in sorted(node.children.items()):
                child_parts = node_parts + [name]
                child_path = self._join(child_parts)
                # Only report paths this agent is allowed to read.
                if content in name and self._allowed(agent, "search", child_path):
                    matches.append(child_path)
                if child.is_dir:
                    walk(child, child_parts)

        if start.is_dir:
            walk(start, parts)
        elif content in start.name:
            matches.append(norm)
        return "OK", f"{len(matches)} match(es)", matches

    # ---------- inspection helpers (not agent operations) ----------

    def _attributes(self, node, path):
        return {"path": path, "type": "directory" if node.is_dir else "file",
                "size": node.size, "owner": node.owner, "created": node.created,
                "modified": node.modified,
                "version": None if node.is_dir else node.version}

    def tree(self):
        """Return the directory tree as indented text (for the report figure)."""
        lines = ["/"]

        def walk(node, prefix):
            items = sorted(node.children.items())
            for i, (name, child) in enumerate(items):
                last = i == len(items) - 1
                label = name + "/" if child.is_dir else f"{name} (v{child.version}, {child.size} B)"
                lines.append(prefix + ("`-- " if last else "|-- ") + label)
                if child.is_dir:
                    walk(child, prefix + ("    " if last else "|   "))

        walk(self.root, "")
        return "\n".join(lines)

    def summary(self):
        """Counts of log outcomes, for the evaluation tables."""
        counts = {"OK": 0, "DENIED": 0, "ERROR": 0, "CONFLICT": 0}
        for e in self.log:
            counts[e["status"]] += 1
        counts["total"] = len(self.log)
        return counts


def build_default_workspace():
    """Return the AgentOS shared workspace with its three files and access rules."""
    fs = FileSystem()
    for d in DEFAULT_DIRECTORIES:               # parents are listed before children
        parts = fs.parse_path(d)
        fs._lookup(parts[:-1]).children[parts[-1]] = _Node(parts[-1], True, "system", 0)
    for path, text in DEFAULT_FILES.items():
        parts = fs.parse_path(path)
        fs._lookup(parts[:-1]).children[parts[-1]] = _Node(parts[-1], False, "system", 0, text)
    return fs


# The fixed scenario used in the report: (agent, operation, path, content, expected_version)
DEFAULT_SCENARIO = [
    ("Research Agent", "list", "/workspace", None, None),
    ("Research Agent", "read", "/workspace/notes/source_notes.txt", None, None),
    ("Research Agent", "write", "/workspace/notes/source_notes.txt", "page-reference notes\nrevisited\n", None),
    ("Coding Agent", "read", "/workspace/notes/source_notes.txt", None, None),
    ("Coding Agent", "write", "/workspace/results/results.csv", "run,faults\nFIFO,15\nLRU,12\n", None),
    ("Report Agent", "read", "/workspace/results/results.csv", None, None),
    ("Report Agent", "create", "/workspace/reports/summary.md", "# Summary\n", None),
    ("Report Agent", "write", "/workspace/reports/final_report.md", "# Final report\nFIFO 15, LRU 12 faults\n", None),
    ("Report Agent", "write", "/workspace/results/results.csv", "tampered\n", None),   # denied
    ("Research Agent", "delete", "/workspace/reports/final_report.md", None, None),   # denied
    ("Coding Agent", "read", "/workspace/results/missing.csv", None, None),           # error
    ("Coding Agent", "read", "workspace/results/results.csv", None, None),            # invalid path
    ("Coding Agent", "search", "/workspace/results", "results", None),
    ("Report Agent", "delete", "/workspace/reports/summary.md", None, None),
    # Optional version check: a write based on version 1 after the file reached version 2.
    ("Coding Agent", "write", "/workspace/results/results.csv", "run,faults\nLRU,12\n", 1),  # conflict
]


def run_scenario(scenario=None):
    """Replay a scenario on a fresh default workspace; return (fs, results)."""
    fs = build_default_workspace()
    results = [fs.execute(a, op, p, content=c, expected_version=v)
               for a, op, p, c, v in (scenario or DEFAULT_SCENARIO)]
    return fs, results


def format_log(fs):
    """Return the audit log as a plain-text table."""
    lines = [f"{'Step':>4}  {'Agent':<15}  {'Operation':<9}  {'Status':<8}  {'Path':<38}  Reason"]
    for e in fs.log:
        lines.append(f"{e['step']:>4}  {e['agent']:<15}  {e['operation']:<9}  "
                     f"{e['status']:<8}  {str(e['path']):<38}  {e['reason']}")
    return "\n".join(lines)


def main(argv=None):
    argparse.ArgumentParser(description="AgentOS file-system simulator demo").parse_args(argv)
    print("Initial directory tree:")
    print(build_default_workspace().tree())
    fs, _ = run_scenario()
    print("\nAudit log:")
    print(format_log(fs))
    print("\nFinal directory tree:")
    print(fs.tree())
    s = fs.summary()
    print(f"\nOperations: {s['total']}   OK: {s['OK']}   Denied: {s['DENIED']}   "
          f"Error: {s['ERROR']}   Conflict: {s['CONFLICT']}")


if __name__ == "__main__":
    main()
