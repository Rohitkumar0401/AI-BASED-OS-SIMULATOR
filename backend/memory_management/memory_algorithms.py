"""
Memory Management - Page Replacement Algorithms
===============================================
Implements: FIFO, LRU, Optimal

Every function takes the SAME input and returns the SAME output shape,
so all three can be run on one input and compared directly.

Input:
    reference_string: list of ints, e.g. [7, 0, 1, 2, 0, 3, 0, 4]
    frame_count:      int, number of physical frames (>= 1)

Output:
    {
        "algorithm": "FIFO",
        "page_faults": 15,
        "page_hits": 5,
        "hit_ratio": 0.25,
        "trace": [
            {"page": 7, "frames": [7], "result": "MISS", "evicted": None},
            ...
        ]
    }
"""

from collections import deque


def _build_result(name, refs, trace, faults):
    hits = len(refs) - faults
    return {
        "algorithm": name,
        "page_faults": faults,
        "page_hits": hits,
        "hit_ratio": round(hits / len(refs), 2) if refs else 0.0,
        "trace": trace,
    }


def fifo(refs, frame_count):
    """First-In-First-Out: evict the page that has been in memory longest."""
    frames = deque()
    trace = []
    faults = 0

    for page in refs:
        evicted = None
        if page in frames:
            result = "HIT"
        else:
            result = "MISS"
            faults += 1
            if len(frames) == frame_count:
                evicted = frames.popleft()
            frames.append(page)
        trace.append({"page": page, "frames": list(frames),
                      "result": result, "evicted": evicted})

    return _build_result("FIFO", refs, trace, faults)


def lru(refs, frame_count):
    """Least Recently Used: evict the page not used for the longest time.
    `frames` is kept ordered from least recent (front) to most recent (back)."""
    frames = []
    trace = []
    faults = 0

    for page in refs:
        evicted = None
        if page in frames:
            result = "HIT"
            frames.remove(page)      # move to most-recent position
            frames.append(page)
        else:
            result = "MISS"
            faults += 1
            if len(frames) == frame_count:
                evicted = frames.pop(0)   # least recently used
            frames.append(page)
        trace.append({"page": page, "frames": list(frames),
                      "result": result, "evicted": evicted})

    return _build_result("LRU", refs, trace, faults)


def optimal(refs, frame_count):
    """Optimal (Belady's): evict the page whose next use is farthest in the
    future (or never used again). Needs future knowledge, so it is a
    theoretical benchmark, not something a real OS can implement."""
    frames = []
    trace = []
    faults = 0

    for i, page in enumerate(refs):
        evicted = None
        if page in frames:
            result = "HIT"
        else:
            result = "MISS"
            faults += 1
            if len(frames) == frame_count:
                future = refs[i + 1:]
                farthest_page = None
                farthest_dist = -1
                for f in frames:
                    if f in future:
                        dist = future.index(f)
                    else:
                        dist = float("inf")   # never used again -> best victim
                    if dist > farthest_dist:
                        farthest_dist = dist
                        farthest_page = f
                    if dist == float("inf"):
                        break
                frames.remove(farthest_page)
                evicted = farthest_page
            frames.append(page)
        trace.append({"page": page, "frames": list(frames),
                      "result": result, "evicted": evicted})

    return _build_result("OPTIMAL", refs, trace, faults)


def run_all(refs, frame_count):
    """Runs all three algorithms on the same input."""
    return {
        "FIFO": fifo(refs, frame_count),
        "LRU": lru(refs, frame_count),
        "OPTIMAL": optimal(refs, frame_count),
    }


def pick_best_practical(results):
    """Picks the best REAL-WORLD algorithm (FIFO or LRU).

    OPTIMAL is excluded from the label on purpose: it can never lose (it is
    the theoretical minimum), and it can't be implemented in a real OS since
    it needs future knowledge. If it were allowed, every training row would
    be labelled OPTIMAL and the ML model would learn nothing useful.

    On a tie, FIFO is preferred (same faults, lower bookkeeping overhead).
    Returns (best_algorithm, page_faults).
    """
    fifo_faults = results["FIFO"]["page_faults"]
    lru_faults = results["LRU"]["page_faults"]
    if lru_faults < fifo_faults:
        return "LRU", lru_faults
    return "FIFO", fifo_faults


def parse_reference_string(raw):
    """Accepts '7,0,1,2' or [7,0,1,2] and returns a list of ints.
    Raises ValueError on bad input."""
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.replace(" ", ",").split(",") if p.strip()]
    else:
        parts = list(raw)
    if not parts:
        raise ValueError("reference string is empty")
    try:
        return [int(p) for p in parts]
    except (TypeError, ValueError):
        raise ValueError("reference string must contain only integers")


if __name__ == "__main__":
    # Classic textbook example: expected FIFO=15, LRU=12, OPTIMAL=9 faults
    refs = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
    results = run_all(refs, 3)
    for name, res in results.items():
        print(f"{name}: faults={res['page_faults']} hits={res['page_hits']} "
              f"hit_ratio={res['hit_ratio']}")
    print("Best practical:", pick_best_practical(results))