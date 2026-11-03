# File-System Module: Simulated Directory Tree, Operations and Permissions

Owner: Member 2 (file-system module). Covers Unit 5: file attributes, file operations, pathnames, tree-structured directories, protection.

Educational simulation only. All state is in memory; no real file is read, written or deleted.

## Run

From the `AGENTOS/` folder (Python 3.8+, standard library only):

```bash
python file_system_simulator.py                 # demo scenario: trees, audit log, summary
python -m unittest tests.test_file_system_simulator -v
```

## Interface (for integration)

```python
from file_system_simulator import build_default_workspace

fs = build_default_workspace()
r = fs.execute("Coding Agent", "write", "/workspace/results/results.csv", content="run,faults\n")
```

`execute(agent, operation, path, content=None, expected_version=None)` never raises for a bad request. It returns and logs:

| Key | Meaning |
|---|---|
| `success` | `True` only when `status == "OK"` |
| `status` | `OK`, `DENIED` (protection), `ERROR` (invalid path/operation/state) or `CONFLICT` (stale version) |
| `reason` | Human-readable explanation |
| `agent`, `operation`, `path` | The request |
| `data` | Operation output (list entries, read content and version, stat attributes, search matches) |

| Operation | Needs | Notes |
|---|---|---|
| `list` | `r` | Directory entries; sub-directories end in `/` |
| `read` | `r` | Returns `{content, version}` |
| `stat` | `r` | Path, type, size, owner, created, modified, version |
| `search` | `r` | `content` is a name substring; only paths the agent may read are returned |
| `write` | `w` | Existing file only; increments `version`; optional `expected_version` |
| `create` | `c` | New file in an existing directory |
| `mkdir` | `c` | New directory in an existing directory |
| `delete` | `d` | File or empty directory; root cannot be deleted |

`fs.log` holds one entry per call (`step`, `agent`, `operation`, `path`, `status`, `reason`). `fs.tree()` returns the directory tree as text for the report figure. `fs.summary()` returns outcome counts.

## Design

- **Tree:** nodes are directories or files. Attributes are name, type, size, owner, created, modified and version. Time is a logical counter (one tick per operation), so runs are deterministic.
- **Paths:** absolute only. Repeated slashes and `.` are ignored. Relative paths, `..` and non-strings give an `ERROR`.
- **Protection:** each agent has rules `path prefix -> letters` (`r`, `w`, `c`, `d`). The longest matching prefix decides. No matching rule means denied. Protection is checked before existence, so a denial does not reveal whether a path exists.
- **Version check (optional extension):** `write(..., expected_version=n)` is rejected with `CONFLICT` if the file is no longer at version `n`. Without `expected_version` a write is always accepted, which is the unprotected lost-update case.

### Default workspace and access rules

```
/
`-- workspace/
    |-- notes/source_notes.txt
    |-- reports/final_report.md
    `-- results/results.csv
```

| Agent | `/workspace` | `/workspace/notes` | `/workspace/results` | `/workspace/reports` |
|---|---|---|---|---|
| Research Agent | r | rwcd | r (inherited) | r (inherited) |
| Coding Agent | none | r | rwcd | none |
| Report Agent | none | r | r | rwcd |

## Tests (spec matrix F1-F4 and more)

`tests/test_file_system_simulator.py`: F1 listing/path/stat/search, F2 create-read-write-delete and logging, F3 denial (with unchanged state), F4 invalid path/operation, version check, and repeatability. Measured output is in `outputs/file_system_log.txt`.

## Limitations

- Single user-space simulation: no inodes, disk blocks, allocation methods or free-space management.
- Permissions are per agent and per path prefix only. There are no groups, owners' rights or ACL inheritance rules beyond longest-prefix match.
- No concurrency: operations run one at a time, so the version check models stale reads, not real races or locks.
- `search` matches names only, not content.
