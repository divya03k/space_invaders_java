from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import hashlib
import csv
import io
import os

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "div*03_08_06",
    "database": "space_invaders_db"
}

QUESTIONS_FILE = "questions.txt"  # Your text file


@app.route("/")
def home():
    return jsonify({"message": "Java Quiz Game API is running successfully!"})


# --- API: Get Leaderboard ---
@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT player_name, score, level, last_played
            FROM leaderboard
            ORDER BY score DESC LIMIT 20
        """)
        data = cursor.fetchall()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return jsonify(data)


# --- API: Admin Login ---
@app.route("/api/admin_login", methods=["POST"])
def admin_login():
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return jsonify({"error": "Missing credentials"}), 400

        hashed = hashlib.sha256(password.encode()).hexdigest()
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM admin_users WHERE username=%s AND password_hash=%s",
            (username, hashed)
        )
        user = cursor.fetchone()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return jsonify({"success": bool(user)}), (200 if user else 401)


# --- API: Get All Questions (from questions.txt) ---
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


# --- API: Upload New Questions (append to questions.txt) ---
@app.route("/api/upload_questions", methods=["POST"])
def upload_questions():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        content = file.stream.read().decode("utf-8")
        with open(QUESTIONS_FILE, "a", encoding="utf-8") as f:
            f.write("\n" + content.strip())

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"success": True, "message": "Questions added successfully!"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
