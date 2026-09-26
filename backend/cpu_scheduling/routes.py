"""
Day 3 — CPU Scheduling Routes
=============================
Ties together:
  - cpu_scheduling/algorithms.py  (FCFS, SJF, SRTF, Round Robin)
  - db/db_connector.py            (Oracle inserts)

Exposes one endpoint: POST /simulate/cpu

Expected JSON body:
{
    "user_id": 1,
    "quantum": 2,
    "processes": [
        {"pid": "P1", "arrival_time": 0, "burst_time": 5, "priority": 2},
        {"pid": "P2", "arrival_time": 1, "burst_time": 3, "priority": 1},
        {"pid": "P3", "arrival_time": 2, "burst_time": 8, "priority": 3},
        {"pid": "P4", "arrival_time": 3, "burst_time": 6, "priority": 4}
    ]
}

Returns: JSON with results for all four algorithms, plus which one won
and why — this "why" is a simple rule-based explanation for now; Day 10-11
replaces it with a real trained model.
"""

import json
import statistics

from flask import Blueprint, request, jsonify

from cpu_scheduling.algorithms import run_all, pick_best
from db import db_connector

cpu_bp = Blueprint("cpu_scheduling", __name__)


def _compute_input_stats(processes):
    """Derives the feature columns cpu_inputs / training_dataset expect."""
    burst_times = [p["burst_time"] for p in processes]
    arrival_times = sorted(p["arrival_time"] for p in processes)

    avg_burst = statistics.mean(burst_times)
    burst_variance = statistics.pvariance(burst_times) if len(burst_times) > 1 else 0.0

    if len(arrival_times) > 1:
        gaps = [arrival_times[i + 1] - arrival_times[i] for i in range(len(arrival_times) - 1)]
        avg_arrival_gap = statistics.mean(gaps)
    else:
        avg_arrival_gap = 0.0

    return {
        "process_count": len(processes),
        "avg_burst_time": round(avg_burst, 2),
        "burst_time_variance": round(burst_variance, 2),
        "avg_arrival_gap": round(avg_arrival_gap, 2),
    }


def _explain(best_algo, stats):
    """Simple rule-based explanation, placeholder until the real ML model
    (Day 10-11) generates this from the trained classifier instead."""
    if best_algo == "SRTF":
        return (f"SRTF won because burst times vary a lot "
                 f"(variance={stats['burst_time_variance']}) — preempting to run "
                 f"shorter jobs first cut down average waiting time.")
    if best_algo == "SJF":
        return (f"SJF won because it also prioritizes shorter jobs "
                 f"(avg burst={stats['avg_burst_time']}), without SRTF's preemption overhead.")
    if best_algo == "ROUND_ROBIN":
        return ("Round Robin won because burst times were fairly even, so equal "
                "time-slicing didn't cost much in context switches, and gave fairer response times.")
    return (f"FCFS won because processes arrived in an order that was already "
            f"close to optimal (avg arrival gap={stats['avg_arrival_gap']}), "
            f"so reordering wouldn't have helped much.")


@cpu_bp.route("/simulate/cpu", methods=["POST"])
def simulate_cpu():
    data = request.get_json(force=True)

    user_id = data.get("user_id")
    processes = data.get("processes")
    quantum = data.get("quantum", 2)

    if not user_id or not processes:
        return jsonify({
            "status": "error",
            "message": "user_id and processes are required"
        }), 400

    try:
        # 1. Run all four algorithms on the same input
        all_results = run_all(processes, quantum=quantum)
        best_algo, best_value = pick_best(all_results, metric="avg_waiting_time")
        stats = _compute_input_stats(processes)

        # 2. Create the parent simulation row
        sim_id = db_connector.create_simulation(user_id=user_id, module_type="cpu")

        # 3. Save the raw process list
        db_connector.save_cpu_processes(sim_id, processes)

        # 4. Save the derived input stats
        db_connector.save_cpu_inputs(
            sim_id=sim_id,
            process_count=stats["process_count"],
            avg_burst_time=stats["avg_burst_time"],
            burst_time_variance=stats["burst_time_variance"],
            avg_arrival_gap=stats["avg_arrival_gap"],
            time_quantum=quantum,
        )

        # 5. Save each algorithm's result
        for algo_name, result in all_results.items():
            db_connector.save_cpu_result(
                sim_id=sim_id,
                algorithm=algo_name,
                avg_waiting_time=result["avg_waiting_time"],
                avg_turnaround_time=result["avg_turnaround_time"],
                context_switches=result["context_switches"],
                gantt_chart_json=json.dumps(result["gantt_chart"]),
            )

        # 6. Log the winner as a labeled training row for the future AI model
        db_connector.save_training_row(
            sim_id=sim_id,
            module_type="cpu",
            process_count=stats["process_count"],
            avg_burst_time=stats["avg_burst_time"],
            burst_time_variance=stats["burst_time_variance"],
            best_algorithm=best_algo,
            best_metric_value=best_value,
        )

        # 7. Build the explanation (rule-based for now)
        explanation = _explain(best_algo, stats)

        return jsonify({
            "status": "success",
            "sim_id": sim_id,
            "input_stats": stats,
            "results": all_results,
            "recommendation": {
                "best_algorithm": best_algo,
                "avg_waiting_time": best_value,
                "explanation": explanation,
            },
        }), 201

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@cpu_bp.route("/simulations/cpu/<int:sim_id>", methods=["GET"])
def get_cpu_simulation(sim_id):
    """Fetch a past CPU simulation's stored results — for the 'view past runs' feature."""
    try:
        sim = db_connector.run_query(
            "SELECT sim_id, user_id, module_type, created_at FROM simulations WHERE sim_id = :sim_id",
            {"sim_id": sim_id}, fetch=True,
        )
        if not sim:
            return jsonify({"status": "error", "message": "Simulation not found"}), 404

        processes = db_connector.run_query(
            """SELECT process_label, arrival_time, burst_time, priority
               FROM cpu_processes WHERE sim_id = :sim_id ORDER BY process_row_id""",
            {"sim_id": sim_id}, fetch=True,
        )
        results = db_connector.run_query(
            """SELECT algorithm, avg_waiting_time, avg_turnaround_time,
                      context_switches, gantt_chart_json
               FROM cpu_results WHERE sim_id = :sim_id""",
            {"sim_id": sim_id}, fetch=True,
        )

        return jsonify({
            "status": "success",
            "simulation": sim[0],
            "processes": processes,
            "results": results,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500