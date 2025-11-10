from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os
import hashlib

# ---------------------------------------------------------------------
# 🌐 Flask Setup
# ---------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------
# ⚙️ TiDB (MySQL-Compatible) Database Setup
# ---------------------------------------------------------------------
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("TIDB_HOST", "gateway01.ap-southeast-1.prod.aws.tidbcloud.com"),
            port=int(os.getenv("TIDB_PORT", "4000")),
            user=os.getenv("TIDB_USER", "root"),
            password=os.getenv("TIDB_PASSWORD", ""),
            database=os.getenv("TIDB_DATABASE", "space_invaders_db"),
            ssl_ca=os.getenv("TIDB_SSL_CA", ""),  # optional for local dev
        )
        return connection
    except Exception as e:
        print(f"🔥 Database connection failed: {e}")
        raise

# ---------------------------------------------------------------------
# 🏗️ Database Initialization
# ---------------------------------------------------------------------
def init_tables():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                player_name VARCHAR(100) PRIMARY KEY,
                score INT DEFAULT 0,
                level INT DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                username VARCHAR(100) PRIMARY KEY,
                password_hash VARCHAR(256) NOT NULL
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ TiDB tables initialized successfully.")
    except Exception as e:
        print(f"🔥 Table initialization failed: {e}")

init_tables()

# ---------------------------------------------------------------------
# ✅ Root Route
# ---------------------------------------------------------------------
@app.route("/")
def home():
    return jsonify({"message": "Java Quiz Game API (TiDB Edition) is running successfully!"})

# ---------------------------------------------------------------------
# 🏆 Get Leaderboard
# ---------------------------------------------------------------------
@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM leaderboard ORDER BY score DESC")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data)
    except Exception as e:
        print(f"⚠️ Leaderboard fetch error: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------
# 🆕 Update / Add Player Score
# ---------------------------------------------------------------------
@app.route("/api/update_score", methods=["POST"])
def update_score():
    try:
        data = request.get_json()
        player_name = data.get("player_name")
        score = data.get("score")
        level = data.get("level")

        if not player_name or score is None or level is None:
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO leaderboard (player_name, score, level)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE score = VALUES(score), level = VALUES(level)
        """, (player_name, score, level))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "message": "Score updated successfully!"})
    except Exception as e:
        print(f"⚠️ Update score error: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------
# 🔐 Admin Login
# ---------------------------------------------------------------------
@app.route("/api/admin_login", methods=["POST"])
def admin_login():
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Missing credentials"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin_users WHERE username = %s", (username,))
        admin_data = cursor.fetchone()
        cursor.close()
        conn.close()

        if not admin_data:
            return jsonify({"error": "Invalid username"}), 401

        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        if hashed_input == admin_data["password_hash"]:
            return jsonify({"success": True, "message": "Login successful!"})
        else:
            return jsonify({"error": "Invalid password"}), 401

    except Exception as e:
        print(f"⚠️ Admin login error: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------
# 📋 Get All Questions
# ---------------------------------------------------------------------
QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), "questions.txt")

@app.route("/api/get_questions", methods=["GET"])
def get_questions():
    if not os.path.exists(QUESTIONS_FILE):
        return jsonify({"error": "questions.txt file not found"}), 404

    questions = []
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                questions.append({
                    "question": parts[0],
                    "option1": parts[1],
                    "option2": parts[2],
                    "option3": parts[3],
                    "option4": parts[4],
                    "correct_answer": parts[5]
                })
    return jsonify(questions)

# ---------------------------------------------------------------------
# 📤 Upload Questions
# ---------------------------------------------------------------------
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
        print("⚠️ Upload questions error:", e)
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------
# 🚀 Run App
# ---------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
