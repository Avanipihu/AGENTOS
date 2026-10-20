# AgentOS: Memory-Management Section

*Draft for insertion into the faculty CA-3 case-study report. The numbering below follows the report outline in the project specification; the file-system portions of those sections are outside this draft.*

## 1. Introduction — memory-management context

AgentOS is a hypothetical shared workspace in which a Research Agent revisits source notes, a Coding Agent uses those notes while updating results, and a Report Agent uses the results to prepare a report. These names identify workload roles in an educational simulation. They are not operating-system processes or running language-model agents. The memory demonstration treats each requested context-page identifier as an abstract page reference and limits the workspace to three simulated frames [2]. It does not allocate physical RAM, implement virtual memory, or manage an LLM's token context.

The memory-management question is how two page-replacement rules behave when the same series of references must fit within this fixed capacity. The exercise relates a concrete workload to the Unit 4 treatment of demand paging, page faults, and replacement [1, pp. 34–52]. Its objective is to compare FIFO and LRU using reproducible event traces and measurements obtained from the program.

## 2. Problem statement and assumptions — memory component

The simulated workspace cannot keep every distinct referenced page in its three frames at once. For each page request, the program must decide whether that page is already resident; if it is missing, the program loads it into a free frame or evicts one resident page according to the selected policy. Both policies receive the identical input sequence and begin with empty frames. Page IDs have no assigned byte size, disk location, agent owner, or processing cost. A replacement is counted as an eviction only when all three frames are occupied [2].

## 3. Theoretical background — paging and replacement

In operating-system paging, a **page** is a block of a logical or virtual address space, while a **frame** is a block of physical memory into which a page can be mapped. The Unit 4 notes describe physical memory as organized into page frames and the memory-management unit (MMU) as mapping logical addresses to physical addresses [1, pp. 33–34]. Demand paging brings a needed page into memory only when it is referenced [1, p. 34].

For this simulation, a **page hit** means that the requested page ID is already in a simulated frame. A **page fault** means that it is absent. This is an operational definition for the program's resident-page lookup. It should not be confused with the **TLB hit ratio** discussed separately in the notes [1, p. 61]. In an actual demand-paged system, a reference to a nonresident valid page traps to the operating system, which finds a free frame or selects a victim, loads the page, updates its tables, and restarts the faulting instruction [1, pp. 38–41]. An invalid address may instead terminate the process [1, p. 38]. The AgentOS model records only the abstract hit, fault, load, and eviction events; it does not perform those hardware, disk, or instruction-restart actions.

**Page replacement** is required when a missing page must be loaded and no free frame remains. The lecture notes identify First-In, First-Out (FIFO) and Least Recently Used (LRU) among the replacement policies [1, pp. 40–52]. FIFO chooses the resident page that was loaded earliest; a hit does not change its arrival position. LRU chooses the resident page whose most recent reference is furthest in the past; every hit updates its recency. These definitions imply different victims when arrival order and recent use differ. More generally, a lower fault count for one policy on a particular reference string is an observation about that input, not a universal ranking. The notes discuss Belady's anomaly for FIFO and identify LRU as a stack algorithm without that anomaly [1, pp. 48, 52]; the three-frame experiment alone does not test varying frame counts.

## 4. Case description — reproducible memory workload

The fixed page-reference string is taken from the FIFO example in the Unit 4 notes [1, p. 48]:

`7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1`

There are **three frames**. FIFO and LRU each start from empty frames and process all 22 references in the displayed order. Page labels in this sequence are abstract identifiers, not actual content pages, bytes of agent state, or token-memory units. The notes show their own worked examples; the report's Results section uses only the output of the team's implementation (`memory_simulator.py`). No note-provided totals are substituted for program measurements.

## 5. Analysis and findings — illustrative hand trace

The following **separate, hand-worked illustration** uses the short sequence `1, 2, 3, 1, 4, 2` to make the policy difference visible. It is not the fixed experimental input, and its entries are not program results. `—` denotes an empty frame; frame columns retain their slot positions after replacement.

| Request | FIFO event | FIFO frames after request | FIFO eviction | LRU event | LRU frames after request | LRU eviction |
|---:|---|---|---|---|---|---|
| 1 | Fault | `1, —, —` | — | Fault | `1, —, —` | — |
| 2 | Fault | `1, 2, —` | — | Fault | `1, 2, —` | — |
| 3 | Fault | `1, 2, 3` | — | Fault | `1, 2, 3` | — |
| 1 | Hit | `1, 2, 3` | — | Hit | `1, 2, 3` | — |
| 4 | Fault | `4, 2, 3` | 1 | Fault | `1, 4, 3` | 2 |
| 2 | Hit | `4, 2, 3` | — | Fault | `1, 4, 2` | 3 |

FIFO's hit on the second request for page 1 does not alter the fact that page 1 was loaded first, so FIFO evicts it when page 4 arrives. LRU treats that hit as a recent use, so page 2 is the least recently used at that point. On the final request, FIFO still has page 2, whereas LRU must load it again.

**Program trace for the fixed experiment.** The table below is the output of `python memory_simulator.py` for the 22-reference string in Section 4 with three frames. Frame lists show slot contents after each request; a newly loaded page takes the evicted page's slot.

| Step | Page | FIFO | FIFO frames | FIFO evicted | LRU | LRU frames | LRU evicted |
|---:|---:|---|---|---|---|---|---|
| 1 | 7 | Fault | [7] | — | Fault | [7] | — |
| 2 | 0 | Fault | [7, 0] | — | Fault | [7, 0] | — |
| 3 | 1 | Fault | [7, 0, 1] | — | Fault | [7, 0, 1] | — |
| 4 | 2 | Fault | [2, 0, 1] | 7 | Fault | [2, 0, 1] | 7 |
| 5 | 0 | Hit | [2, 0, 1] | — | Hit | [2, 0, 1] | — |
| 6 | 3 | Fault | [2, 3, 1] | 0 | Fault | [2, 0, 3] | 1 |
| 7 | 0 | Fault | [2, 3, 0] | 1 | Hit | [2, 0, 3] | — |
| 8 | 4 | Fault | [4, 3, 0] | 2 | Fault | [4, 0, 3] | 2 |
| 9 | 2 | Fault | [4, 2, 0] | 3 | Fault | [4, 0, 2] | 3 |
| 10 | 3 | Fault | [4, 2, 3] | 0 | Fault | [4, 3, 2] | 0 |
| 11 | 0 | Fault | [0, 2, 3] | 4 | Fault | [0, 3, 2] | 4 |
| 12 | 3 | Hit | [0, 2, 3] | — | Hit | [0, 3, 2] | — |
| 13 | 0 | Hit | [0, 2, 3] | — | Hit | [0, 3, 2] | — |
| 14 | 3 | Hit | [0, 2, 3] | — | Hit | [0, 3, 2] | — |
| 15 | 2 | Hit | [0, 2, 3] | — | Hit | [0, 3, 2] | — |
| 16 | 1 | Fault | [0, 1, 3] | 2 | Fault | [1, 3, 2] | 0 |
| 17 | 2 | Fault | [0, 1, 2] | 3 | Hit | [1, 3, 2] | — |
| 18 | 0 | Hit | [0, 1, 2] | — | Fault | [1, 0, 2] | 3 |
| 19 | 1 | Hit | [0, 1, 2] | — | Hit | [1, 0, 2] | — |
| 20 | 7 | Fault | [7, 1, 2] | 0 | Fault | [1, 0, 7] | 2 |
| 21 | 0 | Fault | [7, 0, 2] | 1 | Hit | [1, 0, 7] | — |
| 22 | 1 | Fault | [7, 0, 1] | 2 | Hit | [1, 0, 7] | — |

Eviction order — FIFO: 7, 0, 1, 2, 3, 0, 4, 2, 3, 0, 1, 2; LRU: 7, 1, 2, 3, 0, 4, 0, 3, 2. Final frames — FIFO: [7, 0, 1]; LRU: [1, 0, 7].

## 6. Solution / implementation — policy logic and experiment method

**FIFO, step by step.** (1) Start with three empty frame slots and an empty arrival queue. (2) For each reference, record a hit if its page is already resident; do not change the queue. (3) Otherwise record a fault. If a slot is free, load the page there and append it to the queue. (4) If all slots are occupied, remove the queue's oldest page, record the eviction, replace it in its frame, and append the new page. The queue tracks *load order*, not last-use order [1, p. 48].

```text
FIFO(references, capacity = 3):
    frames = [empty] * capacity; arrival_queue = empty queue
    hits = faults = evictions = 0; trace = []
    for page in references:
        victim = none
        if page is in frames:
            hits += 1; event = "hit"
        else:
            faults += 1; event = "fault"
            if an empty slot exists:
                put page in that slot
            else:
                victim = remove front of arrival_queue
                replace victim with page in its frame
                evictions += 1
            append page to arrival_queue
        append (page, event, copy(frames), victim) to trace
    return trace, hits, faults, evictions, hits / length(references)
```

**LRU, step by step.** (1) Start with three empty slots and no last-use records. (2) For each reference, advance a monotonically increasing request counter. (3) On a hit, record the new last-use time for that page. (4) On a fault, use an empty frame if possible; otherwise evict the page with the oldest last-use time. (5) Load the requested page and record its last-use time. A counter is one implementation described in the notes [1, pp. 51–52].

```text
LRU(references, capacity = 3):
    frames = [empty] * capacity; last_use = empty map
    hits = faults = evictions = 0; trace = []
    for time, page in enumerate(references, start = 1):
        victim = none
        if page is in frames:
            hits += 1; event = "hit"
        else:
            faults += 1; event = "fault"
            if an empty slot exists:
                put page in that slot
            else:
                victim = resident page with minimum last_use value
                replace victim with page in its frame
                delete last_use[victim]; evictions += 1
        last_use[page] = time
        append (page, event, copy(frames), victim) to trace
    return trace, hits, faults, evictions, hits / length(references)
```

**Common experimental procedure.** Run each policy independently with the 22-reference string in Section 4 and a capacity of three frames. Reset all state and counters between runs. For every request, store the page ID, hit or fault, ordered frame contents after the request, and any evicted page. Count hits, faults, and evictions from that trace, and compute the **page-hit ratio** as `hits / 22` (or multiply by 100 for a percentage). Check that `hits + faults = 22`, that evictions occur only on faults with full frames, and that rerunning the same policy and input reproduces the same trace [2]. A zero-length sequence would require a separately defined ratio, but this fixed input is nonempty.

## 7. Results and discussion — measured program output

*Values below are from executing `python memory_simulator.py` (default experiment) and are checked by `tests/test_memory_simulator.py`. The full trace is in Section 5.*

| Policy | Reference count | Frames | Hits | Page faults | Evictions | Page-hit ratio |
|---|---:|---:|---:|---:|---:|---:|
| FIFO | 22 | 3 | 7 | 15 | 12 | 0.3182 |
| LRU | 22 | 3 | 10 | 12 | 9 | 0.4545 |

**Findings and discussion:**

1. **Victim divergence and hit influence:** The first divergence occurs at step 6 (request for page 3). Both policies hold `[2, 0, 1]` after the hit on page 0 at step 5. FIFO's arrival queue is then 0, 1, 2, so FIFO evicts page 0 despite that hit. LRU's least recently used page is 1, so LRU evicts page 1. As a result, step 7 (page 0) is an LRU hit but a FIFO fault. The two traces differ in event or victim at steps 6, 7, 16–18 and 20–22 (see Section 5).
2. **Hit and fault identity:** On this input, LRU incurs fewer faults (12 vs. 15) and achieves more hits (10 vs. 7). Both runs satisfy the identity `hits + faults = 22` (FIFO: 7 + 15 = 22; LRU: 10 + 12 = 22).
3. **Free slots vs. evictions:** In both policies, the first 3 faults fill the initially empty frames (steps 1–3). All remaining faults require evictions: FIFO has 15 − 3 = 12 evictions, whereas LRU has 12 − 3 = 9 evictions, i.e., 3 fewer replacements.
4. **Revisiting pages:** A hit leaves FIFO's arrival order unchanged but refreshes LRU's last-use order. At step 16, FIFO evicts page 2 because it is the oldest arrival (loaded at step 9), even though it was hit at step 15; step 17 then faults on page 2. LRU instead evicts page 0 (last used at step 13) and keeps page 2, so step 17 is an LRU hit.
5. **Generalizability:** These results describe one reference string at one frame count. They do not show how the policies compare on other reference strings or other frame capacities.

**Limitations.** The page-reference string is fixed and has no measured agent-specific timing or provenance. Three equal-capacity simulated frames are a teaching abstraction; the model does not include page size, address translation, TLB behavior, dirty-page writes, disk I/O latency, prefetching, or competing processes. Its hit ratio measures resident-page lookup, not TLB hits or end-to-end runtime. A single reference string and frame count cannot establish general policy superiority or assess Belady's anomaly. These boundaries follow the project's simulation scope [2] and the difference between this abstraction and the fuller page-fault sequence in the course notes [1, pp. 38–41].

## 8. Conclusion — memory component

This section presented a reproducible, bounded comparison of FIFO and LRU for an abstract agent-oriented workload. The lecture notes supply the paging and replacement concepts and the fixed reference sequence; the AgentOS project specification supplies the three-frame simulation boundary and measurement contract [1, 2]. On the 22-reference string with three frames, the executed simulator recorded 7 hits, 15 faults and 12 evictions for FIFO (hit ratio 0.3182), and 10 hits, 12 faults and 9 evictions for LRU (hit ratio 0.4545). The trace shows that LRU's advantage on this input comes from hits refreshing recency (for example, steps 5–7 and 15–17), which FIFO ignores. This result applies to this one input and frame count; the study makes no claim about general policy superiority, real operating-system performance, or LLM token memory, and it does not test Belady's anomaly.

## 9. References

[1] S. Borhade, *Unit 4: Memory Management*, Operating System lecture slides, Department of AIML, n.d. [PDF supplied for the course; slide/page numbers refer to the PDF pages.]

[2] *AgentOS — Project Specification and Execution Contract*, unpublished project specification, n.d. [Markdown document supplied with the case-study materials.]
