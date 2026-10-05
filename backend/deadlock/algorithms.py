"""
Deadlock Detection — Banker's Algorithm
========================================
Given the current allocation of resources, the maximum each process may
ever need, and what's currently available, determines whether the system
is in a SAFE state (a safe sequence exists where every process can finish)
or an UNSAFE state (deadlock risk — some processes can never finish with
the resources that will ever become available to them).

Input:
    allocation:  2D list, allocation[i][j] = units of resource j held by process i
    max_matrix:  2D list, max_matrix[i][j] = max units of resource j process i may ever need
    available:   1D list, available[j] = units of resource j currently free

Output:
    {
        "is_safe": True,
        "need_matrix": [[...], ...],          # max - allocation, per process
        "safe_sequence": [1, 3, 4, 0, 2],      # process indices, in finishing order
        "deadlocked_processes": [],            # empty if safe
        "work_after_each_step": [[...], ...],  # available resources after each process finishes
    }
"""


def _validate(allocation, max_matrix, available):
    n = len(allocation)
    if n == 0:
        raise ValueError("allocation matrix must have at least one process")
    m = len(available)

    if len(max_matrix) != n:
        raise ValueError("allocation and max matrices must have the same number of processes (rows)")

    for i in range(n):
        if len(allocation[i]) != m:
            raise ValueError(f"allocation row {i} has {len(allocation[i])} columns, expected {m} (resource count)")
        if len(max_matrix[i]) != m:
            raise ValueError(f"max row {i} has {len(max_matrix[i])} columns, expected {m} (resource count)")
        for j in range(m):
            if max_matrix[i][j] < allocation[i][j]:
                raise ValueError(
                    f"process {i} is allocated more of resource {j} ({allocation[i][j]}) "
                    f"than its stated maximum ({max_matrix[i][j]}) — invalid input"
                )

    for j in range(m):
        total_allocated = sum(allocation[i][j] for i in range(n))
        # available[j] should represent what's free; this isn't strictly required
        # to equal (total_resources - total_allocated) since we don't know total
        # resources, but available can't be negative.
        if available[j] < 0:
            raise ValueError(f"available[{j}] cannot be negative")

    return n, m


def need_matrix(allocation, max_matrix):
    n = len(allocation)
    m = len(allocation[0]) if n else 0
    return [[max_matrix[i][j] - allocation[i][j] for j in range(m)] for i in range(n)]


def safety_algorithm(allocation, max_matrix, available):
    """Runs the Banker's safety algorithm. Returns a dict (see module docstring)."""
    n, m = _validate(allocation, max_matrix, available)
    need = need_matrix(allocation, max_matrix)

    work = list(available)
    finish = [False] * n
    safe_sequence = []
    work_after_each_step = []

    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):
                for j in range(m):
                    work[j] += allocation[i][j]
                finish[i] = True
                safe_sequence.append(i)
                work_after_each_step.append(list(work))
                progress = True

    is_safe = all(finish)
    deadlocked_processes = [] if is_safe else [i for i in range(n) if not finish[i]]

    return {
        "is_safe": is_safe,
        "need_matrix": need,
        "safe_sequence": safe_sequence if is_safe else [],
        "deadlocked_processes": deadlocked_processes,
        "work_after_each_step": work_after_each_step,
    }


def can_request_be_granted(allocation, max_matrix, available, process_index, request):
    """
    Bonus: the Resource-Request half of Banker's algorithm. Checks whether
    granting `request` (a vector of resource units) to process `process_index`
    right now would leave the system in a safe state. If yes, returns the
    resulting safe sequence; if no, the request must be denied/deferred.
    """
    n, m = _validate(allocation, max_matrix, available)
    need = need_matrix(allocation, max_matrix)

    if len(request) != m:
        raise ValueError(f"request must have {m} values (one per resource)")
    for j in range(m):
        if request[j] > need[process_index][j]:
            raise ValueError(
                f"process {process_index} requested more of resource {j} than its declared need — "
                f"this request violates its stated maximum claim"
            )
        if request[j] > available[j]:
            return {
                "can_grant": False,
                "reason": f"not enough of resource {j} currently available "
                          f"(requested {request[j]}, available {available[j]})",
            }

    # tentatively grant, then re-run safety check
    trial_available = [available[j] - request[j] for j in range(m)]
    trial_allocation = [row[:] for row in allocation]
    for j in range(m):
        trial_allocation[process_index][j] += request[j]

    result = safety_algorithm(trial_allocation, max_matrix, trial_available)
    return {
        "can_grant": result["is_safe"],
        "reason": ("granting this request leaves the system in a safe state"
                   if result["is_safe"] else
                   "granting this request would leave the system in an unsafe state"),
        "resulting_safe_sequence": result["safe_sequence"] if result["is_safe"] else [],
    }


def parse_matrix(raw, expected_cols=None):
    """Accepts a 2D list, or a string like '0,1,0;2,0,0;3,0,2' (rows separated
    by ';', values by ','), and returns a 2D list of ints."""
    if isinstance(raw, str):
        rows = [r.strip() for r in raw.split(";") if r.strip()]
        matrix = []
        for row in rows:
            values = [v.strip() for v in row.replace(" ", ",").split(",") if v.strip()]
            matrix.append([int(v) for v in values])
    else:
        matrix = [[int(v) for v in row] for row in raw]

    if not matrix:
        raise ValueError("matrix is empty")
    if expected_cols is not None:
        for i, row in enumerate(matrix):
            if len(row) != expected_cols:
                raise ValueError(f"row {i} has {len(row)} columns, expected {expected_cols}")
    return matrix


def parse_vector(raw):
    """Accepts a list, or '3,3,2' -> list of ints."""
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.replace(" ", ",").split(",") if p.strip()]
    else:
        parts = list(raw)
    if not parts:
        raise ValueError("vector is empty")
    return [int(p) for p in parts]


if __name__ == "__main__":
    # Classic Silberschatz textbook example: 5 processes, 3 resource types
    allocation = [
        [0, 1, 0],
        [2, 0, 0],
        [3, 0, 2],
        [2, 1, 1],
        [0, 0, 2],
    ]
    max_matrix = [
        [7, 5, 3],
        [3, 2, 2],
        [9, 0, 2],
        [2, 2, 2],
        [4, 3, 3],
    ]
    available = [3, 3, 2]

    result = safety_algorithm(allocation, max_matrix, available)
    print("Is safe:", result["is_safe"])
    print("Need matrix:", result["need_matrix"])
    print("Safe sequence (process indices):", result["safe_sequence"])

    # Bonus: can P1 request (1, 0, 2)? Textbook answer: yes, remains safe.
    req_result = can_request_be_granted(allocation, max_matrix, available, 1, [1, 0, 2])
    print("\nP1 requests (1,0,2):", req_result)

    # Force an unsafe example: drain available resources to almost nothing
    unsafe_available = [0, 0, 0]
    unsafe_result = safety_algorithm(allocation, max_matrix, unsafe_available)
    print("\nWith available=[0,0,0] -> is_safe:", unsafe_result["is_safe"],
          "deadlocked:", unsafe_result["deadlocked_processes"])