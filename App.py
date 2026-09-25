"""
Day 2 — Flask Skeleton
======================
Goal: prove Flask can talk to Oracle through db_connector.py by inserting
a test row into `users` and `simulations`, then reading it back.

Run with:  python app.py
Then visit: http://127.0.0.1:5000/
and:        http://127.0.0.1:5000/test-db
"""

from flask import Flask, jsonify, request
from db import db_connector

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "AI-Based OS Simulator backend is running.",
        "routes": ["/", "/test-db", "/users (POST)", "/users (GET)"]
    })


@app.route("/test-db")
def test_db():
    """
    Sanity check: creates (or reuses) a test user, creates a simulation
    row for them, then reads both back. If this works end-to-end,
    Flask <-> Oracle is wired correctly.
    """
    try:
        # 1. Check if our test user already exists (avoid duplicate UNIQUE errors on repeat runs)
        existing = db_connector.run_query(
            "SELECT user_id, name, roll_no, email FROM users WHERE roll_no = :roll_no",
            {"roll_no": "TEST001"},
            fetch=True,
        )

        if existing:
            user_id = existing[0]["user_id"]
            user_row = existing[0]
        else:
            user_id = db_connector.run_query(
                """INSERT INTO users (name, roll_no, email)
                   VALUES (:name, :roll_no, :email)
                   RETURNING user_id INTO :out_id""",
                {"name": "Test Student", "roll_no": "TEST001", "email": "test001@example.com"},
                returning_id=True,
            )
            user_row = {"user_id": user_id, "name": "Test Student",
                        "roll_no": "TEST001", "email": "test001@example.com"}

        # 2. Create a simulation row for this user
        sim_id = db_connector.create_simulation(user_id=user_id, module_type="cpu")

        # 3. Read the simulation back to prove the round trip works
        sim_row = db_connector.run_query(
            "SELECT sim_id, user_id, module_type, created_at FROM simulations WHERE sim_id = :sim_id",
            {"sim_id": sim_id},
            fetch=True,
        )

        return jsonify({
            "status": "success",
            "message": "Connected to Oracle and wrote/read data successfully.",
            "user": user_row,
            "simulation": sim_row[0] if sim_row else None,
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "hint": "Check backend/db/db_connector.py credentials (user, password, dsn) "
                    "and confirm schema.sql has been run in Oracle."
        }), 500


@app.route("/users", methods=["POST"])
def create_user():
    """Creates a real user. Expects JSON: {"name": "...", "roll_no": "...", "email": "..."}"""
    data = request.get_json(force=True)
    name = data.get("name")
    roll_no = data.get("roll_no")
    email = data.get("email")

    if not all([name, roll_no, email]):
        return jsonify({"status": "error", "message": "name, roll_no, and email are all required"}), 400

    try:
        user_id = db_connector.run_query(
            """INSERT INTO users (name, roll_no, email)
               VALUES (:name, :roll_no, :email)
               RETURNING user_id INTO :out_id""",
            {"name": name, "roll_no": roll_no, "email": email},
            returning_id=True,
        )
        return jsonify({"status": "success", "user_id": user_id}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/users", methods=["GET"])
def list_users():
    """Returns all users — useful for confirming what's actually in the DB."""
    try:
        users = db_connector.run_query(
            "SELECT user_id, name, roll_no, email, created_at FROM users ORDER BY user_id",
            fetch=True,
        )
        return jsonify({"status": "success", "count": len(users), "users": users})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)