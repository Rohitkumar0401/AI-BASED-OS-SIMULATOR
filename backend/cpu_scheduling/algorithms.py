"""
CPU Scheduling Algorithms
=========================
Implements: FCFS, SJF (non-preemptive), SRTF (preemptive SJF), Round Robin

Every function takes the SAME input shape and returns the SAME output shape,
so the Flask layer (or anything else) can run all four on one input and
compare them directly.

Input:
    processes: list of dicts, each like:
        {"pid": "P1", "arrival_time": 0, "burst_time": 5, "priority": None}

Output (for every algorithm):
    {
        "algorithm": "FCFS",
        "gantt_chart": [{"pid": "P1", "start": 0, "end": 5}, ...],
        "per_process": {
            "P1": {"waiting_time": 0, "turnaround_time": 5, "completion_time": 5}
        },
        "avg_waiting_time": 2.5,
        "avg_turnaround_time": 6.0,
        "context_switches": 3
    }
"""

from copy import deepcopy


def _summarize(processes, gantt_chart, completion_time):
    """Shared helper: turn a gantt chart + completion times into the
    standard metrics block (waiting time, turnaround time, averages)."""
    per_process = {}
    total_wait = 0
    total_turnaround = 0

    for p in processes:
        pid = p["pid"]
        ct = completion_time[pid]
        turnaround = ct - p["arrival_time"]
        waiting = turnaround - p["burst_time"]
        per_process[pid] = {
            "waiting_time": waiting,
            "turnaround_time": turnaround,
            "completion_time": ct,
        }
        total_wait += waiting
        total_turnaround += turnaround

    n = len(processes)
    # context switches = number of times the running process changes in the gantt chart
    context_switches = 0
    for i in range(1, len(gantt_chart)):
        if gantt_chart[i]["pid"] != gantt_chart[i - 1]["pid"]:
            context_switches += 1

    return {
        "gantt_chart": gantt_chart,
        "per_process": per_process,
        "avg_waiting_time": round(total_wait / n, 2),
        "avg_turnaround_time": round(total_turnaround / n, 2),
        "context_switches": context_switches,
    }


def fcfs(processes):
    """First Come First Serve — non-preemptive, ordered by arrival time."""
    procs = sorted(deepcopy(processes), key=lambda p: p["arrival_time"])
    time = 0
    gantt_chart = []
    completion_time = {}

    for p in procs:
        start = max(time, p["arrival_time"])
        end = start + p["burst_time"]
        gantt_chart.append({"pid": p["pid"], "start": start, "end": end})
        completion_time[p["pid"]] = end
        time = end

    result = _summarize(processes, gantt_chart, completion_time)
    result["algorithm"] = "FCFS"
    return result


def sjf(processes):
    """Shortest Job First — non-preemptive. At each idle point, picks the
    waiting process with the smallest burst time."""
    procs = deepcopy(processes)
    n = len(procs)
    completed = set()
    time = 0
    gantt_chart = []
    completion_time = {}

    while len(completed) < n:
        # processes that have arrived and are not yet completed
        available = [p for p in procs if p["arrival_time"] <= time and p["pid"] not in completed]

        if not available:
            # no process has arrived yet — jump forward in time
            next_arrival = min(p["arrival_time"] for p in procs if p["pid"] not in completed)
            time = next_arrival
            continue

        # pick shortest burst time; tie-break by arrival time
        chosen = min(available, key=lambda p: (p["burst_time"], p["arrival_time"]))
        start = time
        end = start + chosen["burst_time"]
        gantt_chart.append({"pid": chosen["pid"], "start": start, "end": end})
        completion_time[chosen["pid"]] = end
        time = end
        completed.add(chosen["pid"])

    result = _summarize(processes, gantt_chart, completion_time)
    result["algorithm"] = "SJF"
    return result


def srtf(processes):
    """Shortest Remaining Time First — preemptive version of SJF.
    Re-evaluates which process should run at every unit of time."""
    procs = deepcopy(processes)
    n = len(procs)
    remaining = {p["pid"]: p["burst_time"] for p in procs}
    completion_time = {}
    time = 0
    completed = 0
    gantt_chart = []
    current_pid = None
    segment_start = None

    max_time_guard = sum(p["burst_time"] for p in procs) + max(p["arrival_time"] for p in procs) + 1

    while completed < n and time <= max_time_guard:
        available = [p for p in procs if p["arrival_time"] <= time and remaining[p["pid"]] > 0]

        if not available:
            # flush any open segment, then jump to next arrival
            if current_pid is not None:
                gantt_chart.append({"pid": current_pid, "start": segment_start, "end": time})
                current_pid = None
            future = [p["arrival_time"] for p in procs if remaining[p["pid"]] > 0]
            time = min(future)
            continue

        chosen = min(available, key=lambda p: (remaining[p["pid"]], p["arrival_time"]))

        if chosen["pid"] != current_pid:
            # process switch: close out previous segment
            if current_pid is not None:
                gantt_chart.append({"pid": current_pid, "start": segment_start, "end": time})
            current_pid = chosen["pid"]
            segment_start = time

        remaining[chosen["pid"]] -= 1
        time += 1

        if remaining[chosen["pid"]] == 0:
            gantt_chart.append({"pid": chosen["pid"], "start": segment_start, "end": time})
            completion_time[chosen["pid"]] = time
            current_pid = None
            completed += 1

    # merge back-to-back identical segments (can happen at boundaries)
    merged = []
    for seg in gantt_chart:
        if merged and merged[-1]["pid"] == seg["pid"] and merged[-1]["end"] == seg["start"]:
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg)

    result = _summarize(processes, merged, completion_time)
    result["algorithm"] = "SRTF"
    return result


def round_robin(processes, quantum=2):
    """Round Robin — each process gets a fixed time slice (quantum),
    then goes to the back of the ready queue if it isn't finished."""
    procs = deepcopy(processes)
    n = len(procs)
    remaining = {p["pid"]: p["burst_time"] for p in procs}
    arrival = {p["pid"]: p["arrival_time"] for p in procs}
    completion_time = {}
    gantt_chart = []

    procs_by_arrival = sorted(procs, key=lambda p: p["arrival_time"])
    time = procs_by_arrival[0]["arrival_time"]
    queue = []
    in_queue = set()
    idx = 0  # pointer into procs_by_arrival for who has "arrived"

    def enqueue_new_arrivals(current_time):
        nonlocal idx
        while idx < n and procs_by_arrival[idx]["arrival_time"] <= current_time:
            pid = procs_by_arrival[idx]["pid"]
            if pid not in in_queue and remaining[pid] > 0:
                queue.append(pid)
                in_queue.add(pid)
            idx += 1

    enqueue_new_arrivals(time)

    while queue:
        pid = queue.pop(0)
        in_queue.discard(pid)

        run_time = min(quantum, remaining[pid])
        start = time
        end = start + run_time
        gantt_chart.append({"pid": pid, "start": start, "end": end})
        remaining[pid] -= run_time
        time = end

        # anyone who arrived DURING this slice joins the queue before the
        # current process is re-added (standard RR convention)
        enqueue_new_arrivals(time)

        if remaining[pid] > 0:
            queue.append(pid)
            in_queue.add(pid)
        else:
            completion_time[pid] = time

        # if queue is empty but processes remain, jump to next arrival
        if not queue and len(completion_time) < n:
            future_pids = [p for p in procs if remaining[p["pid"]] > 0]
            if future_pids:
                time = max(time, min(p["arrival_time"] for p in future_pids))
                enqueue_new_arrivals(time)

    result = _summarize(processes, gantt_chart, completion_time)
    result["algorithm"] = "ROUND_ROBIN"
    return result


def run_all(processes, quantum=2):
    """Runs all four algorithms on the same input and returns a dict
    keyed by algorithm name — this is what feeds the recommendation engine."""
    return {
        "FCFS": fcfs(processes),
        "SJF": sjf(processes),
        "SRTF": srtf(processes),
        "ROUND_ROBIN": round_robin(processes, quantum=quantum),
    }


def pick_best(results, metric="avg_waiting_time"):
    """Given the output of run_all(), returns (best_algorithm_name, value)
    based on the chosen metric (lower is better)."""
    best_algo = min(results, key=lambda algo: results[algo][metric])
    return best_algo, results[best_algo][metric]


if __name__ == "__main__":
    # quick manual sanity check
    sample = [
        {"pid": "P1", "arrival_time": 0, "burst_time": 5, "priority": 2},
        {"pid": "P2", "arrival_time": 1, "burst_time": 3, "priority": 1},
        {"pid": "P3", "arrival_time": 2, "burst_time": 8, "priority": 3},
        {"pid": "P4", "arrival_time": 3, "burst_time": 6, "priority": 4},
    ]

    all_results = run_all(sample, quantum=2)
    for algo, res in all_results.items():
        print(f"\n=== {algo} ===")
        print("Gantt:", res["gantt_chart"])
        print("Avg Waiting Time:", res["avg_waiting_time"])
        print("Avg Turnaround Time:", res["avg_turnaround_time"])
        print("Context Switches:", res["context_switches"])

    best, val = pick_best(all_results)
    print(f"\nBest algorithm by avg waiting time: {best} ({val})")
