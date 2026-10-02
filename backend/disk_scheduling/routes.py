"""
Day 5 - Disk Scheduling Routes
==============================
POST /simulate/disk

Expected JSON body:
{
    "user_id": 1,
    "request_queue": "98,183,37,122,14,124,65,67",
    "starting_head": 53,
    "disk_size": 200,
    "direction": "RIGHT"
}
(request_queue may also be a JSON list of ints; direction defaults to "RIGHT")
"""

import json

from flask import Blueprint, request, jsonify

from disk_scheduling.algorithms import run_all, pick_best, parse_request_queue
from db import db_connector

disk_bp = Blueprint("disk_scheduling", __name__)


def _explain(best_algo, results):
    fcfs_m = results["FCFS"]["total_head_movement"]
    best_m = results[best_algo]["total_head_movement"]

    if best_algo == "FCFS":
        text = ("FCFS won because the requests already arrived in a "
                "roughly efficient order, so reordering by seek distance "
                "wouldn't have saved much movement.")
    elif best_algo == "SSTF":
        text = (f"SSTF won with {best_m} total head movement vs FCFS's "
                f"{fcfs_m} — always jumping to the nearest request cuts "
                f"wasted seek distance, though it can starve far-away requests.")
    elif best_algo == "SCAN":
        text = (f"SCAN won with {best_m} vs FCFS's {fcfs_m} — sweeping in one "
                f"direction and servicing requests along the way avoided the "
                f"backtracking that hurt FCFS, while still bounding worst-case wait.")
    else:
        text = (f"C-SCAN won with {best_m} vs FCFS's {fcfs_m} — treating the "
                f"disk as circular gave more uniform wait times across requests "
                f"at the cost of a few extra seek units from the jump-back.")
    return text


@disk_bp.route("/simulate/disk", methods=["POST"])
def simulate_disk():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    raw_requests = data.get("request_queue")
    starting_head = data.get("starting_head")
    disk_size = data.get("disk_size", 200)
    direction = data.get("direction", "RIGHT")

    if not user_id or raw_requests is None or starting_head is None:
        return jsonify({"status": "error",
                        "message": "user_id, request_queue and starting_head are required"}), 400

    if direction not in ("LEFT", "RIGHT"):
        return jsonify({"status": "error", "message": "direction must be LEFT or RIGHT"}), 400

    try:
        requests_list = parse_request_queue(raw_requests)
        starting_head = int(starting_head)
        disk_size = int(disk_size)

        if not (0 <= starting_head < disk_size):
            raise ValueError(f"starting_head must be between 0 and {disk_size - 1}")
        for r in requests_list:
            if not (0 <= r < disk_size):
                raise ValueError(f"request {r} is outside disk range 0-{disk_size - 1}")

        req_str = ",".join(str(r) for r in requests_list)
        if len(req_str) > 255:
            raise ValueError("request queue too long (max 255 characters)")
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    try:
        results = run_all(requests_list, starting_head, disk_size, direction)
        best_algo, best_movement = pick_best(results)

        sim_id = db_connector.create_simulation(user_id=user_id, module_type="disk")
        db_connector.save_disk_inputs(
            sim_id, req_str, len(requests_list), starting_head, disk_size, direction
        )

        for name, res in results.items():
            db_connector.save_disk_result(
                sim_id, name, res["total_head_movement"],
                json.dumps(res["service_order"]),
            )

        db_connector.save_disk_training_row(
            sim_id, len(requests_list), best_algo, best_movement
        )

        return jsonify({
            "status": "success",
            "sim_id": sim_id,
            "input_stats": {
                "request_count": len(requests_list),
                "starting_head": starting_head,
                "disk_size": disk_size,
                "direction": direction,
            },
            "results": results,
            "recommendation": {
                "best_algorithm": best_algo,
                "total_head_movement": best_movement,
                "explanation": _explain(best_algo, results),
            },
        }), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@disk_bp.route("/simulations/disk/<int:sim_id>", methods=["GET"])
def get_disk_simulation(sim_id):
    """Fetch a past disk simulation's stored inputs and results."""
    try:
        sim = db_connector.run_query(
            "SELECT sim_id, user_id, module_type, created_at FROM simulations WHERE sim_id = :sim_id",
            {"sim_id": sim_id}, fetch=True,
        )
        if not sim:
            return jsonify({"status": "error", "message": "Simulation not found"}), 404

        inputs = db_connector.run_query(
            """SELECT request_queue, request_count, starting_head, disk_size, direction
               FROM disk_inputs WHERE sim_id = :sim_id""",
            {"sim_id": sim_id}, fetch=True,
        )
        results = db_connector.run_query(
            """SELECT algorithm, total_head_movement, service_order
               FROM disk_results WHERE sim_id = :sim_id""",
            {"sim_id": sim_id}, fetch=True,
        )
        return jsonify({"status": "success", "simulation": sim[0],
                        "inputs": inputs[0] if inputs else None, "results": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500