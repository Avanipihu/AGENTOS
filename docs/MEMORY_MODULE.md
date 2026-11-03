# Memory Module — FIFO / LRU Page-Replacement Simulator

Owner: Member 1 (memory module). Covers Unit 4: pages, frames, page hits/faults, FIFO and LRU.

Educational simulation only. Page IDs are abstract references, not real memory or LLM tokens.

## Requirements

Python 3.8 or newer. Only the standard library is used, so nothing needs to be installed.

## Run

Run these from the `AGENTOS/` folder:

```bash
# Default experiment: refs [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1], 3 frames, FIFO and LRU
python memory_simulator.py

# Custom run
python memory_simulator.py --policy LRU --frames 4 --refs 7 0 1 2 0 3 0 4

# Tests (stdlib unittest; `python -m pytest tests` also works if pytest is installed)
python -m unittest discover -s tests -v
```

## Interface (for integration)

```python
from memory_simulator import simulate

result = simulate(reference_string=[1, 2, 3, 1], frame_capacity=3, policy="FIFO")
```

| Input | Type | Rule |
|---|---|---|
| `reference_string` | list/tuple of page IDs | Can be empty |
| `frame_capacity` | int | Must be ≥ 1, otherwise `ValueError` |
| `policy` | str | `"FIFO"` or `"LRU"` (case-insensitive), otherwise `ValueError` |

Returned `dict`:

| Key | Meaning |
|---|---|
| `policy`, `frame_capacity`, `reference_string` | Run parameters (policy is upper-cased) |
| `trace` | One entry per reference: `step`, `page`, `result` (`"HIT"`/`"FAULT"`), `frames` (contents after the step), `evicted` (page or `None`) |
| `hits`, `faults`, `evictions` | Totals |
| `hit_ratio` | `hits / len(reference_string)`, or `0.0` for an empty string |

`format_result(result)` returns the plain-text table printed by the CLI. The function does no I/O and has no randomness. The same input always gives the same output.

## Algorithms

The simulator stores two lists:

- `frames`: the physical frame slots. A new page replaces the victim in that victim's slot.
- `order`: the replacement order. Index 0 is always the next victim.

For each requested page:

```
if page in frames:                 # HIT
    hits += 1
    if LRU: move page to end of order        # refresh recency
else:                              # FAULT
    faults += 1
    if a frame is free: put page in the free frame
    else: victim = order.pop(0); replace victim's slot with page; evictions += 1
    append page to end of order
```

- **FIFO** evicts the page that was **loaded earliest**. A hit does not change `order`.
- **LRU** evicts the page that was **used least recently**. A hit moves the page to the end of `order`.

The only difference between the two policies is how a hit is handled.

## Default experiment: measured output

The output below comes from `python memory_simulator.py` (3 frames). The CLI prints the hit ratio to 4 decimal places.

| Step | Page | FIFO | FIFO frames | FIFO evicted | LRU | LRU frames | LRU evicted |
|---:|---:|---|---|---|---|---|---|
| 1 | 7 | FAULT | [7] | - | FAULT | [7] | - |
| 2 | 0 | FAULT | [7, 0] | - | FAULT | [7, 0] | - |
| 3 | 1 | FAULT | [7, 0, 1] | - | FAULT | [7, 0, 1] | - |
| 4 | 2 | FAULT | [2, 0, 1] | 7 | FAULT | [2, 0, 1] | 7 |
| 5 | 0 | HIT | [2, 0, 1] | - | HIT | [2, 0, 1] | - |
| 6 | 3 | FAULT | [2, 3, 1] | 0 | FAULT | [2, 0, 3] | 1 |
| 7 | 0 | FAULT | [2, 3, 0] | 1 | HIT | [2, 0, 3] | - |
| 8 | 4 | FAULT | [4, 3, 0] | 2 | FAULT | [4, 0, 3] | 2 |
| 9 | 2 | FAULT | [4, 2, 0] | 3 | FAULT | [4, 0, 2] | 3 |
| 10 | 3 | FAULT | [4, 2, 3] | 0 | FAULT | [4, 3, 2] | 0 |
| 11 | 0 | FAULT | [0, 2, 3] | 4 | FAULT | [0, 3, 2] | 4 |
| 12 | 3 | HIT | [0, 2, 3] | - | HIT | [0, 3, 2] | - |
| 13 | 0 | HIT | [0, 2, 3] | - | HIT | [0, 3, 2] | - |
| 14 | 3 | HIT | [0, 2, 3] | - | HIT | [0, 3, 2] | - |
| 15 | 2 | HIT | [0, 2, 3] | - | HIT | [0, 3, 2] | - |
| 16 | 1 | FAULT | [0, 1, 3] | 2 | FAULT | [1, 3, 2] | 0 |
| 17 | 2 | FAULT | [0, 1, 2] | 3 | HIT | [1, 3, 2] | - |
| 18 | 0 | HIT | [0, 1, 2] | - | FAULT | [1, 0, 2] | 3 |
| 19 | 1 | HIT | [0, 1, 2] | - | HIT | [1, 0, 2] | - |
| 20 | 7 | FAULT | [7, 1, 2] | 0 | FAULT | [1, 0, 7] | 2 |
| 21 | 0 | FAULT | [7, 0, 2] | 1 | HIT | [1, 0, 7] | - |
| 22 | 1 | FAULT | [7, 0, 1] | 2 | HIT | [1, 0, 7] | - |

| Policy | Hits | Faults | Evictions | Hit ratio |
|---|---:|---:|---:|---:|
| FIFO | 7 | 15 | 12 | 0.3182 |
| LRU | 10 | 12 | 9 | 0.4545 |

On this 22-reference string from the Unit 4 notes, LRU had fewer faults (12 vs 15) and a higher hit ratio (0.4545 vs 0.3182) than FIFO. The policies first differ at step 6. The hit on page 0 at step 5 keeps page 0 resident under LRU, so step 7 is an LRU hit but a FIFO fault. Similarly, at step 16 FIFO evicts page 2 (oldest arrival) despite its hit at step 15, while LRU keeps it, so step 17 is an LRU hit but a FIFO fault. This is one input and one frame count; it does not rank the policies in general.

## Tests (spec matrix M1–M4 and more)

`tests/test_memory_simulator.py` covers the following cases:

- M1: a page hit.
- M2: a fault with a free frame and no eviction.
- M3: a full-frame eviction under FIFO and under LRU, using the same input. The two policies choose different victims.
- M4: repeatability.
- Invalid capacity, invalid policy, and an invalid reference string.
- The default-experiment results (traced by hand and cross-checked against an independent run).
- Trace totals that match the summary metrics.

## Limitations

- Demand paging only. There is no Optimal policy, no dirty or modified bits, no page tables, and no timing model.
- The model uses one global frame pool. Frames are not allocated per agent.
