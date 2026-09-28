"""
Day 4 - Memory Management Routes
================================
POST /simulate/memory

Expected JSON body:
{
    "user_id": 1,
    "reference_string": "7,0,1,2,0,3,0,4,2,3,0,3,2,1,2,0,1,7,0,1",
    "frame_count": 3
}
(reference_string may also be a JSON list of ints)
"""

import json

from flask import Blueprint, request, jsonify

from memory_management.algorithms import (
    run_all, pick_best_practical, parse_reference_string
)
from db import db_connector

memory_bp = Blueprint("memory_management", __name__)


def _explain(best_algo, results, unique_pages, frame_count):
    fifo_f = results["FIFO"]["page_faults"]
    lru_f = results["LRU"]["page_faults"]
    opt_f = results["OPTIMAL"]["page_faults"]

    if best_algo == "LRU":
        text = (f"LRU won with {lru_f} faults vs FIFO's {fifo_f}. The reference "
                f"string re-uses recently accessed pages (locality of reference), "
                f"which LRU keeps in memory while FIFO evicts them just because "
                f"they are old.")
    elif fifo_f == lru_f:
        text = (f"FIFO and LRU tied at {fifo_f} faults, so FIFO is preferred: "
                f"same performance with less bookkeeping.")
    else:
        text = (f"FIFO won with {fifo_f} faults vs LRU's {lru_f}. Recency of use "
                f"was not a good predictor for this access pattern.")

    gap = results[best_algo]["page_faults"] - opt_f
    text += (f" Optimal (theoretical minimum, needs future knowledge) would "
             f"give {opt_f} faults, so the best real algorithm is {gap} "
             f"faults above the ideal.")
    if frame_count >= unique_pages:
        text += (" Note: frame count is >= unique pages, so only compulsory "
                 "faults occur and all algorithms perform the same.")
    return text


@memory_bp.route("/simulate/memory", methods=["POST"])
def simulate_memory():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    raw_refs = data.get("reference_string")
    frame_count = data.get("frame_count")

    if not user_id or raw_refs is None or frame_count is None:
        return jsonify({"status": "error",
                        "message": "user_id, reference_string and frame_count are required"}), 400

    try:
        refs = parse_reference_string(raw_refs)
        frame_count = int(frame_count)
        if frame_count < 1:
            raise ValueError("frame_count must be at least 1")
        ref_str = ",".join(str(p) for p in refs)
        if len(ref_str) > 255:
            raise ValueError("reference string too long (max 255 characters)")
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    try:
        results = run_all(refs, frame_count)
        best_algo, best_faults = pick_best_practical(results)
        unique_pages = len(set(refs))

        sim_id = db_connector.create_simulation(user_id=user_id, module_type="memory")
        db_connector.save_memory_inputs(sim_id, ref_str, len(refs),
                                        frame_count, unique_pages)

        for name, res in results.items():
            db_connector.save_memory_result(
                sim_id, name, res["page_faults"], res["page_hits"],
                json.dumps(res["trace"]),
            )

        db_connector.save_memory_training_row(
            sim_id, frame_count, unique_pages, best_algo, best_faults
        )

        return jsonify({
            "status": "success",
            "sim_id": sim_id,
            "input_stats": {
                "reference_length": len(refs),
                "unique_pages": unique_pages,
                "frame_count": frame_count,
            },
            "results": results,
            "recommendation": {
                "best_algorithm": best_algo,
                "page_faults": best_faults,
                "explanation": _explain(best_algo, results, unique_pages, frame_count),
            },
        }), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@memory_bp.route("/simulations/memory/<int:sim_id>", methods=["GET"])
def get_memory_simulation(sim_id):
    """Fetch a past memory simulation's stored inputs and results."""
    try:
        sim = db_connector.run_query(
            "SELECT sim_id, user_id, module_type, created_at FROM simulations WHERE sim_id = :sim_id",
            {"sim_id": sim_id}, fetch=True,
        )
        if not sim:
            return jsonify({"status": "error", "message": "Simulation not found"}), 404

        inputs = db_connector.run_query(
            """SELECT reference_string, reference_length, frame_count, unique_pages
               FROM memory_inputs WHERE sim_id = :sim_id""",
            {"sim_id": sim_id}, fetch=True,
        )
        results = db_connector.run_query(
            """SELECT algorithm, page_faults, page_hits
               FROM memory_results WHERE sim_id = :sim_id""",
            {"sim_id": sim_id}, fetch=True,
        )
        return jsonify({"status": "success", "simulation": sim[0],
                        "inputs": inputs[0] if inputs else None, "results": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500