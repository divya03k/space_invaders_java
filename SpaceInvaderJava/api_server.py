from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import os
import firebase_admin
from firebase_admin import credentials, db


app = Flask(__name__)
CORS(app)



FIREBASE_CRED = "serviceAccountKey.json"
FIREBASE_DB_URL = "https://spaceinvadersjava-default-rtdb.firebaseio.com/" # <-- replace with YOUR Firebase URL

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED)
    firebase_admin.initialize_app(cred, {
        "databaseURL": FIREBASE_DB_URL
    })


leaderboard_ref = db.reference("leaderboard")
admin_users_ref = db.reference("admin_users")

QUESTIONS_FILE = "questions.txt"

@app.route("/")
def home():
    return jsonify({"message": "Java Quiz Game API (Firebase) is running successfully!"})


@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    try:
        data = leaderboard_ref.get() or {}
        # Sort by score (descending)
        sorted_data = sorted(data.items(), key=lambda x: x[1].get("score", 0), reverse=True)
        leaderboard = [{"player_name": k, **v} for k, v in sorted_data]
        return jsonify(leaderboard)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/update_score", methods=["POST"])
def update_score():
    try:
        data = request.get_json()
        player_name = data.get("player_name")
        score = data.get("score")
        level = data.get("level")

        if not player_name or score is None or level is None:
            return jsonify({"error": "Missing required fields"}), 400

        leaderboard_ref.child(player_name).update({
            "score": score,
            "level": level
        })

        return jsonify({"success": True, "message": "Score updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin_login", methods=["POST"])
def admin_login():
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Missing credentials"}), 400

        # Get admin data from Firebase
        admin_data = admin_users_ref.child(username).get()

        if not admin_data:
            return jsonify({"error": "Invalid username"}), 401

        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        if hashed_input == admin_data.get("password_hash"):
            return jsonify({"success": True, "message": "Login successful!"}), 200
        else:
            return jsonify({"error": "Invalid password"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/get_questions", methods=["GET"])
def get_questions():
    if not os.path.exists(QUESTIONS_FILE):
        return jsonify({"error": "questions.txt file not found"}), 404

    questions = []
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                question_data = {
                    "question": parts[0],
                    "option1": parts[1],
                    "option2": parts[2],
                    "option3": parts[3],
                    "option4": parts[4],
                    "correct_answer": parts[5]
                }
                questions.append(question_data)

    return jsonify(questions)


@app.route("/api/upload_questions", methods=["POST"])
def upload_questions():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        content = file.stream.read().decode("utf-8")
        with open(QUESTIONS_FILE, "a", encoding="utf-8") as f:
            f.write("\n" + content.strip())

        return jsonify({"success": True, "message": "Questions added successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
