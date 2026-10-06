"""
Day 6 - Deadlock Detection Routes
=================================
POST /simulate/deadlock

Expected JSON body:
{
    "user_id": 1,
    "allocation": [[0,1,0],[2,0,0],[3,0,2],[2,1,1],[0,0,2]],
    "max": [[7,5,3],[3,2,2],[9,0,2],[2,2,2],[4,3,3]],
    "available": [3,3,2]
}
(allocation/max may also be strings like "0,1,0;2,0,0"; available may be "3,3,2")

Optional bonus request-check, in the SAME call:
{
    ... same as above ...,
    "request_check": {"process_index": 1, "request": [1,0,2]}
}
"""

import json

from flask import Blueprint, request, jsonify

from deadlock.algorithms import (
    safety_algorithm, can_request_be_granted, parse_matrix, parse_vector
)
from db import db_connector

deadlock_bp = Blueprint("deadlock", __name__)


def _explain(result):
    if result["is_safe"]:
        seq = " -> ".join(f"P{p}" for p in result["safe_sequence"])
        return (f"The system is in a SAFE state. One safe execution order is: "
                f"{seq}. Every process can eventually get its maximum claim "
                f"met with the resources currently available plus what gets "
                f"released as each process finishes.")
    else:
        stuck = ", ".join(f"P{p}" for p in result["deadlocked_processes"])
        return (f"The system is in an UNSAFE state. Process(es) {stuck} cannot "
                f"guarantee completion — there's no order in which the currently "
                f"available resources (plus released resources) can satisfy "
                f"their remaining needs. This doesn't mean a deadlock has "
                f"definitely occurred yet, but it means one could, depending "
                f"on what these processes actually request next.")


@deadlock_bp.route("/simulate/deadlock", methods=["POST"])
def simulate_deadlock():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    raw_allocation = data.get("allocation")
    raw_max = data.get("max")
    raw_available = data.get("available")

    if not user_id or raw_allocation is None or raw_max is None or raw_available is None:
        return jsonify({"status": "error",
                        "message": "user_id, allocation, max, and available are all required"}), 400

    try:
        available = parse_vector(raw_available)
        m = len(available)
        allocation = parse_matrix(raw_allocation, expected_cols=m)
        max_matrix = parse_matrix(raw_max, expected_cols=m)

        if len(max_matrix) != len(allocation):
            raise ValueError("allocation and max must have the same number of process rows")

        n = len(allocation)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    try:
        result = safety_algorithm(allocation, max_matrix, available)
    except ValueError as e:
        # algorithms.py validates allocation<=max etc — treat as bad input, not server error
        return jsonify({"status": "error", "message": str(e)}), 400

    try:
        sim_id = db_connector.create_simulation(user_id=user_id, module_type="deadlock")

        db_connector.save_deadlock_inputs(
            sim_id, n, m,
            json.dumps(allocation), json.dumps(max_matrix),
            ",".join(str(a) for a in available),
        )

        db_connector.save_deadlock_result(
            sim_id, result["is_safe"],
            ",".join(str(p) for p in result["safe_sequence"]),
            ",".join(str(p) for p in result["deadlocked_processes"]),
        )

        # label for the AI layer: SAFE or UNSAFE; "metric" is just 1/0 for consistency
        db_connector.save_deadlock_training_row(
            sim_id, n,
            "SAFE" if result["is_safe"] else "UNSAFE",
            1.0 if result["is_safe"] else 0.0,
        )

        response = {
            "status": "success",
            "sim_id": sim_id,
            "input_stats": {"process_count": n, "resource_count": m},
            "result": result,
            "explanation": _explain(result),
        }

        # optional bonus: resource-request check in the same call
        req_check = data.get("request_check")
        if req_check:
            try:
                process_index = int(req_check["process_index"])
                req_vector = parse_vector(req_check["request"])
                if not (0 <= process_index < n):
                    raise ValueError(f"process_index must be between 0 and {n - 1}")
                grant_result = can_request_be_granted(
                    allocation, max_matrix, available, process_index, req_vector
                )
                response["request_check_result"] = grant_result
            except (ValueError, KeyError, TypeError) as e:
                response["request_check_result"] = {"error": str(e)}

        return jsonify(response), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@deadlock_bp.route("/simulations/deadlock/<int:sim_id>", methods=["GET"])
def get_deadlock_simulation(sim_id):
    """Fetch a past deadlock simulation's stored inputs and results."""
    try:
        sim = db_connector.run_query(
            "SELECT sim_id, user_id, module_type, created_at FROM simulations WHERE sim_id = :sim_id",
            {"sim_id": sim_id}, fetch=True,
        )
        if not sim:
            return jsonify({"status": "error", "message": "Simulation not found"}), 404

        inputs = db_connector.run_query(
            """SELECT process_count, resource_count, allocation_matrix, max_matrix, available_vector
               FROM deadlock_inputs WHERE sim_id = :sim_id""",
            {"sim_id": sim_id}, fetch=True,
        )
        results = db_connector.run_query(
            """SELECT is_safe, safe_sequence, deadlocked_processes
               FROM deadlock_results WHERE sim_id = :sim_id""",
            {"sim_id": sim_id}, fetch=True,
        )
        return jsonify({"status": "success", "simulation": sim[0],
                        "inputs": inputs[0] if inputs else None,
                        "results": results[0] if results else None})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500