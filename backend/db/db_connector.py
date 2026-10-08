"""
Database connector for the OS Simulator project — ORACLE VERSION.
Uses the python-oracledb library (no separate Oracle Client install needed
in "thin" mode) to talk to the schema defined in db/oracle_schema.sql.

Install with: pip install oracledb
"""

import oracledb

# ---- Update these to match your local Oracle setup ----
DB_CONFIG = {
    "user": "your_oracle_username",       # e.g. "system" or your own schema user
    "password": "your_oracle_password",
    "dsn": "localhost:1521/XE",            # host:port/service_name — XE is the default XE service
}


def get_connection():
    """Returns a fresh Oracle connection using DB_CONFIG (thin mode, no client install needed)."""
    return oracledb.connect(**DB_CONFIG)


def run_query(query, params=None, fetch=False, returning_id=False):
    """
    Runs a single query.
    - fetch=True         -> for SELECT, returns list of dict rows
    - returning_id=True  -> for INSERT, use with a RETURNING clause to get the new ID
    - otherwise          -> for UPDATE/DELETE/plain INSERT, returns rowcount
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if returning_id:
                # Oracle needs an explicit output variable to get an identity value back
                out_id = cursor.var(int)
                cursor.execute(query, {**(params or {}), "out_id": out_id})
                conn.commit()
                return out_id.getvalue()[0]

            cursor.execute(query, params or {})

            if fetch:
                columns = [col[0].lower() for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]

            conn.commit()
            return cursor.rowcount
    finally:
        conn.close()


# ------------------------------------------------------------
# Convenience helpers used by app.py
# Note the ":name" bind-variable style (Oracle), not "%s" (MySQL),
# and "RETURNING ... INTO :out_id" to get the new auto-generated ID back.
# ------------------------------------------------------------

def create_simulation(user_id, module_type):
    return run_query(
        """INSERT INTO simulations (user_id, module_type)
           VALUES (:user_id, :module_type)
           RETURNING sim_id INTO :out_id""",
        {"user_id": user_id, "module_type": module_type},
        returning_id=True,
    )


def save_cpu_processes(sim_id, processes):
    for p in processes:
        run_query(
            """INSERT INTO cpu_processes
               (sim_id, process_label, arrival_time, burst_time, priority)
               VALUES (:sim_id, :label, :arrival, :burst, :priority)""",
            {
                "sim_id": sim_id,
                "label": p["pid"],
                "arrival": p["arrival_time"],
                "burst": p["burst_time"],
                "priority": p.get("priority"),
            },
        )


def save_cpu_inputs(sim_id, process_count, avg_burst_time, burst_time_variance,
                     avg_arrival_gap, time_quantum=None):
    return run_query(
        """INSERT INTO cpu_inputs
           (sim_id, process_count, avg_burst_time, burst_time_variance,
            avg_arrival_gap, time_quantum)
           VALUES (:sim_id, :pc, :abt, :btv, :aag, :tq)
           RETURNING input_id INTO :out_id""",
        {
            "sim_id": sim_id, "pc": process_count, "abt": avg_burst_time,
            "btv": burst_time_variance, "aag": avg_arrival_gap, "tq": time_quantum,
        },
        returning_id=True,
    )


def save_cpu_result(sim_id, algorithm, avg_waiting_time, avg_turnaround_time,
                     context_switches, gantt_chart_json):
    return run_query(
        """INSERT INTO cpu_results
           (sim_id, algorithm, avg_waiting_time, avg_turnaround_time,
            context_switches, gantt_chart_json)
           VALUES (:sim_id, :algo, :awt, :atat, :cs, :gantt)
           RETURNING result_id INTO :out_id""",
        {
            "sim_id": sim_id, "algo": algorithm, "awt": avg_waiting_time,
            "atat": avg_turnaround_time, "cs": context_switches, "gantt": gantt_chart_json,
        },
        returning_id=True,
    )


def save_training_row(sim_id, module_type, process_count, avg_burst_time,
                       burst_time_variance, best_algorithm, best_metric_value):
    return run_query(
        """INSERT INTO training_dataset
           (sim_id, module_type, process_count, avg_burst_time,
            burst_time_variance, best_algorithm, best_metric_value)
           VALUES (:sim_id, :module_type, :pc, :abt, :btv, :best_algo, :best_val)
           RETURNING record_id INTO :out_id""",
        {
            "sim_id": sim_id, "module_type": module_type, "pc": process_count,
            "abt": avg_burst_time, "btv": burst_time_variance,
            "best_algo": best_algorithm, "best_val": best_metric_value,
        },
        returning_id=True,
    )


def save_ai_recommendation(sim_id, recommended_algorithm, confidence_score,
                            explanation_text, model_version="v1"):
    return run_query(
        """INSERT INTO ai_recommendations
           (sim_id, recommended_algorithm, confidence_score,
            explanation_text, model_version)
           VALUES (:sim_id, :rec_algo, :conf, :expl, :ver)
           RETURNING rec_id INTO :out_id""",
        {
            "sim_id": sim_id, "rec_algo": recommended_algorithm,
            "conf": confidence_score, "expl": explanation_text, "ver": model_version,
        },
        returning_id=True,
    )


# ------------------------------------------------------------
# Memory management helpers (Day 4)
# ------------------------------------------------------------

def save_memory_inputs(sim_id, reference_string, reference_length,
                        frame_count, unique_pages):
    return run_query(
        """INSERT INTO memory_inputs
           (sim_id, reference_string, reference_length, frame_count, unique_pages)
           VALUES (:sim_id, :ref_str, :ref_len, :frames, :uniq)
           RETURNING input_id INTO :out_id""",
        {"sim_id": sim_id, "ref_str": reference_string, "ref_len": reference_length,
         "frames": frame_count, "uniq": unique_pages},
        returning_id=True,
    )


def save_memory_result(sim_id, algorithm, page_faults, page_hits, hit_miss_trace):
    return run_query(
        """INSERT INTO memory_results
           (sim_id, algorithm, page_faults, page_hits, hit_miss_trace)
           VALUES (:sim_id, :algo, :faults, :hits, :trace)
           RETURNING result_id INTO :out_id""",
        {"sim_id": sim_id, "algo": algorithm, "faults": page_faults,
         "hits": page_hits, "trace": hit_miss_trace},
        returning_id=True,
    )


def save_memory_training_row(sim_id, frame_count, unique_pages,
                              best_algorithm, best_metric_value):
    return run_query(
        """INSERT INTO training_dataset
           (sim_id, module_type, frame_count, unique_pages,
            best_algorithm, best_metric_value)
           VALUES (:sim_id, 'memory', :frames, :uniq, :best_algo, :best_val)
           RETURNING record_id INTO :out_id""",
        {"sim_id": sim_id, "frames": frame_count, "uniq": unique_pages,
         "best_algo": best_algorithm, "best_val": best_metric_value},
        returning_id=True,
    )


# ------------------------------------------------------------
# Disk scheduling helpers (Day 5)
# ------------------------------------------------------------

def save_disk_inputs(sim_id, request_queue, request_count, starting_head,
                      disk_size, direction):
    return run_query(
        """INSERT INTO disk_inputs
           (sim_id, request_queue, request_count, starting_head, disk_size, direction)
           VALUES (:sim_id, :reqs, :count, :head, :size, :dir)
           RETURNING input_id INTO :out_id""",
        {"sim_id": sim_id, "reqs": request_queue, "count": request_count,
         "head": starting_head, "size": disk_size, "dir": direction},
        returning_id=True,
    )


def save_disk_result(sim_id, algorithm, total_head_movement, service_order):
    return run_query(
        """INSERT INTO disk_results
           (sim_id, algorithm, total_head_movement, service_order)
           VALUES (:sim_id, :algo, :movement, :order)
           RETURNING result_id INTO :out_id""",
        {"sim_id": sim_id, "algo": algorithm, "movement": total_head_movement,
         "order": service_order},
        returning_id=True,
    )


def save_disk_training_row(sim_id, request_count, best_algorithm, best_metric_value):
    return run_query(
        """INSERT INTO training_dataset
           (sim_id, module_type, request_count, best_algorithm, best_metric_value)
           VALUES (:sim_id, 'disk', :count, :best_algo, :best_val)
           RETURNING record_id INTO :out_id""",
        {"sim_id": sim_id, "count": request_count,
         "best_algo": best_algorithm, "best_val": best_metric_value},
        returning_id=True,
    )


# ------------------------------------------------------------
# Deadlock detection helpers (Day 6)
# ------------------------------------------------------------

def save_deadlock_inputs(sim_id, process_count, resource_count,
                          allocation_matrix_json, max_matrix_json, available_vector):
    return run_query(
        """INSERT INTO deadlock_inputs
           (sim_id, process_count, resource_count, allocation_matrix,
            max_matrix, available_vector)
           VALUES (:sim_id, :pc, :rc, :alloc, :max_m, :avail)
           RETURNING input_id INTO :out_id""",
        {"sim_id": sim_id, "pc": process_count, "rc": resource_count,
         "alloc": allocation_matrix_json, "max_m": max_matrix_json, "avail": available_vector},
        returning_id=True,
    )


def save_deadlock_result(sim_id, is_safe, safe_sequence_str, deadlocked_processes_str):
    return run_query(
        """INSERT INTO deadlock_results
           (sim_id, is_safe, safe_sequence, deadlocked_processes)
           VALUES (:sim_id, :is_safe, :seq, :deadlocked)
           RETURNING result_id INTO :out_id""",
        {"sim_id": sim_id, "is_safe": 1 if is_safe else 0,
         "seq": safe_sequence_str, "deadlocked": deadlocked_processes_str},
        returning_id=True,
    )


def save_deadlock_training_row(sim_id, process_count, best_algorithm, best_metric_value):
    """For deadlock, the 'label' is simply SAFE or UNSAFE — this feeds a
    future classifier that predicts, from process/resource counts and
    utilization, whether a given configuration is likely to be safe."""
    return run_query(
        """INSERT INTO training_dataset
           (sim_id, module_type, process_count, best_algorithm, best_metric_value)
           VALUES (:sim_id, 'deadlock', :pc, :best_algo, :best_val)
           RETURNING record_id INTO :out_id""",
        {"sim_id": sim_id, "pc": process_count,
         "best_algo": best_algorithm, "best_val": best_metric_value},
        returning_id=True,
    )


if __name__ == "__main__":
    # quick manual connectivity check
    try:
        conn = get_connection()
        print("Connected to Oracle successfully:", conn.version)
        conn.close()
    except Exception as e:
        print("Connection failed:", e)