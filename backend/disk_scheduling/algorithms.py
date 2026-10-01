"""
Disk Scheduling Algorithms
==========================
Implements: FCFS, SSTF, SCAN, C-SCAN

All functions take the same input and return the same output shape.

Input:
    requests:      list of ints, track numbers requested, e.g. [98,183,37,122,14,124,65,67]
    start_head:    int, current head position
    disk_size:     int, total number of tracks (0 to disk_size-1). Needed for SCAN/C-SCAN
                   to know where the "end of disk" is.
    direction:     "LEFT" or "RIGHT" — which way the head is initially moving
                   (only used by SCAN and C-SCAN)

Output:
    {
        "algorithm": "FCFS",
        "service_order": [98, 183, 37, 122, 14, 124, 65, 67],
        "total_head_movement": 640,
        "seek_sequence": [53, 98, 183, 37, ...]   # head position at each step, start included
    }
"""


def _summarize(name, start_head, order):
    seek_sequence = [start_head] + order
    total_movement = sum(abs(seek_sequence[i + 1] - seek_sequence[i])
                          for i in range(len(seek_sequence) - 1))
    return {
        "algorithm": name,
        "service_order": order,
        "total_head_movement": total_movement,
        "seek_sequence": seek_sequence,
    }


def fcfs(requests, start_head, disk_size=200, direction=None):
    """First Come First Serve — service requests in the order they arrived."""
    order = list(requests)
    return _summarize("FCFS", start_head, order)


def sstf(requests, start_head, disk_size=200, direction=None):
    """Shortest Seek Time First — always service whichever pending request
    is closest to the current head position."""
    remaining = list(requests)
    order = []
    current = start_head

    while remaining:
        closest = min(remaining, key=lambda r: abs(r - current))
        order.append(closest)
        remaining.remove(closest)
        current = closest

    return _summarize("SSTF", start_head, order)


def _summarize_with_path(name, start_head, full_path, service_order):
    """full_path includes disk-edge waypoints (for correct movement calc);
    service_order lists only the actual requests serviced (for display)."""
    seek_sequence = [start_head] + full_path
    total_movement = sum(abs(seek_sequence[i + 1] - seek_sequence[i])
                          for i in range(len(seek_sequence) - 1))
    return {
        "algorithm": name,
        "service_order": service_order,
        "total_head_movement": total_movement,
        "seek_sequence": seek_sequence,
    }


def scan(requests, start_head, disk_size=200, direction="RIGHT"):
    """SCAN (elevator algorithm) — head sweeps all the way to the end of the
    disk (even if no request is there), servicing requests as it passes,
    then reverses direction and sweeps back."""
    left = sorted(r for r in requests if r < start_head)
    right = sorted(r for r in requests if r >= start_head)
    last_track = disk_size - 1

    if direction == "RIGHT":
        full_path = right + [last_track] + list(reversed(left))
    else:
        full_path = list(reversed(left)) + [0] + right

    service_order = [x for x in full_path if x in requests]
    return _summarize_with_path("SCAN", start_head, full_path, service_order)


def c_scan(requests, start_head, disk_size=200, direction="RIGHT"):
    """C-SCAN (circular SCAN) — head sweeps to one edge of the disk,
    services requests along the way, jumps to the OPPOSITE edge without
    servicing anything on the jump, then continues in the same direction.
    This gives more uniform wait times than plain SCAN."""
    left = sorted(r for r in requests if r < start_head)
    right = sorted(r for r in requests if r >= start_head)
    last_track = disk_size - 1

    if direction == "RIGHT":
        full_path = right + [last_track, 0] + left
    else:
        full_path = list(reversed(left)) + [0, last_track] + list(reversed(right))

    service_order = [x for x in full_path if x in requests]
    return _summarize_with_path("C_SCAN", start_head, full_path, service_order)


def run_all(requests, start_head, disk_size=200, direction="RIGHT"):
    """Runs all four algorithms on the same input."""
    return {
        "FCFS": fcfs(requests, start_head, disk_size, direction),
        "SSTF": sstf(requests, start_head, disk_size, direction),
        "SCAN": scan(requests, start_head, disk_size, direction),
        "C_SCAN": c_scan(requests, start_head, disk_size, direction),
    }


def pick_best(results, metric="total_head_movement"):
    """Returns (best_algorithm, value) — lower head movement is better."""
    best_algo = min(results, key=lambda algo: results[algo][metric])
    return best_algo, results[best_algo][metric]


def parse_request_queue(raw):
    """Accepts '98,183,37' or [98,183,37] -> list of ints."""
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.replace(" ", ",").split(",") if p.strip()]
    else:
        parts = list(raw)
    if not parts:
        raise ValueError("request queue is empty")
    try:
        return [int(p) for p in parts]
    except (TypeError, ValueError):
        raise ValueError("request queue must contain only integers")


if __name__ == "__main__":
    # Classic textbook example: requests, head starts at 53, disk size 200
    requests = [98, 183, 37, 122, 14, 124, 65, 67]
    start = 53

    for direction in ["RIGHT", "LEFT"]:
        print(f"\n--- direction = {direction} ---")
        results = run_all(requests, start, disk_size=200, direction=direction)
        for name, res in results.items():
            print(f"{name}: order={res['service_order']} "
                  f"movement={res['total_head_movement']}")
        best, val = pick_best(results)
        print(f"Best: {best} ({val})")