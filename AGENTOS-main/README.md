# AgentOS: OS Case Study on Memory and File Management

Operating Systems CA-3. Report-first case study supported by two small simulations. It is not a real OS, and the agents are workload labels, not real LLM agents.

| Module | File | Unit | Docs |
|---|---|---|---|
| Memory (FIFO / LRU page replacement) | `memory_simulator.py` | 4 | `docs/MEMORY_MODULE.md` |
| File system (tree, operations, permissions) | `file_system_simulator.py` | 5 | `docs/FILE_SYSTEM_MODULE.md` |
| Evaluation runner | `evaluate.py` | both | `outputs/` |

## Requirements

Python 3.8 or newer. Standard library only; nothing to install.

## Run

Run these from the repository root:

```bash
python memory_simulator.py                    # FIFO and LRU on the default experiment
python file_system_simulator.py               # file-system demo scenario
python -m unittest discover -s tests -v       # all tests
python evaluate.py                            # tests + reproducibility checks, rewrites outputs/
python evaluate.py --check                    # fails if outputs/ is out of date
```

## Evidence for the report

`python evaluate.py` regenerates these files from the code. Do not edit them by hand.

| File | Contents |
|---|---|
| `outputs/results_summary.md` | Memory metrics, extra workloads, frame sweep, file-system outcome counts, reproducibility |
| `outputs/memory_results.txt` | Full FIFO/LRU traces |
| `outputs/file_system_log.txt` | Directory trees and the audit log |
| `outputs/test_matrix.md` | Matrix IDs M1-M4 and F1-F4 mapped to tests, with status |

## Repository layout

```
memory_simulator.py
file_system_simulator.py
evaluate.py
tests/            test_memory_simulator.py, test_file_system_simulator.py
outputs/          generated results
docs/             module docs and report sections
```
