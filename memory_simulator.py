"""AgentOS memory module: FIFO and LRU page-replacement simulator.

Educational simulation for the AgentOS OS case study (Unit 4).
Page IDs are abstract references; no real memory is managed.

Usage:
    python memory_simulator.py                       # default experiment, both policies
    python memory_simulator.py --policy LRU --frames 4 --refs 1 2 3 4 1 2
"""

import argparse

POLICIES = ("FIFO", "LRU")
DEFAULT_REFERENCE_STRING = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
DEFAULT_FRAME_CAPACITY = 3


def simulate(reference_string, frame_capacity, policy):
    """Replay reference_string with frame_capacity frames under policy.

    Returns a dict with the policy, capacity, a step-by-step trace and the
    summary metrics (hits, faults, evictions, hit_ratio).
    Raises ValueError for invalid capacity, unknown policy or bad input.
    """
    # bool is a subclass of int, so exclude it explicitly.
    if not isinstance(frame_capacity, int) or isinstance(frame_capacity, bool) or frame_capacity < 1:
        raise ValueError(f"frame_capacity must be a positive integer, got {frame_capacity!r}")
    if not isinstance(policy, str) or policy.upper() not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}; expected one of {POLICIES}")
    if not isinstance(reference_string, (list, tuple)):
        raise ValueError("reference_string must be a list or tuple of page IDs")
    policy = policy.upper()

    frames = []  # physical frame slots, in slot order
    order = []   # replacement order: index 0 is the next victim
                 # FIFO -> order of loading; LRU -> least recently used first
    trace = []
    hits = faults = evictions = 0

    for step, page in enumerate(reference_string, start=1):
        evicted = None
        if page in frames:
            hits += 1
            result = "HIT"
            if policy == "LRU":          # a hit refreshes recency; FIFO ignores hits
                order.remove(page)
                order.append(page)
        else:
            faults += 1
            result = "FAULT"
            if len(frames) < frame_capacity:   # a free frame exists
                frames.append(page)
            else:                              # all frames full: evict a victim
                evicted = order.pop(0)
                frames[frames.index(evicted)] = page
                evictions += 1
            order.append(page)

        trace.append({
            "step": step,
            "page": page,
            "result": result,
            "frames": list(frames),   # copy, so later steps do not change it
            "evicted": evicted,
        })

    total = len(reference_string)
    return {
        "policy": policy,
        "frame_capacity": frame_capacity,
        "reference_string": list(reference_string),
        "trace": trace,
        "hits": hits,
        "faults": faults,
        "evictions": evictions,
        "hit_ratio": hits / total if total else 0.0,
    }


def format_result(result):
    """Return a plain-text table of the trace and summary for a result dict."""
    lines = [
        f"Policy: {result['policy']}   Frames: {result['frame_capacity']}   "
        f"Reference string: {result['reference_string']}",
        f"{'Step':>4}  {'Page':>4}  {'Result':<6}  {'Frames':<20}  Evicted",
    ]
    for e in result["trace"]:
        evicted = "-" if e["evicted"] is None else str(e["evicted"])
        lines.append(f"{e['step']:>4}  {str(e['page']):>4}  {e['result']:<6}  "
                     f"{str(e['frames']):<20}  {evicted}")
    lines.append(f"Hits: {result['hits']}   Faults: {result['faults']}   "
                 f"Evictions: {result['evictions']}   Hit ratio: {result['hit_ratio']:.4f}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="FIFO/LRU page-replacement simulator")
    parser.add_argument("--policy", choices=POLICIES + ("BOTH",), default="BOTH")
    parser.add_argument("--frames", type=int, default=DEFAULT_FRAME_CAPACITY)
    parser.add_argument("--refs", type=int, nargs="+", default=DEFAULT_REFERENCE_STRING)
    args = parser.parse_args(argv)

    policies = POLICIES if args.policy == "BOTH" else (args.policy,)
    for i, policy in enumerate(policies):
        if i:
            print()
        try:
            print(format_result(simulate(args.refs, args.frames, policy)))
        except ValueError as err:
            parser.error(str(err))


if __name__ == "__main__":
    main()
