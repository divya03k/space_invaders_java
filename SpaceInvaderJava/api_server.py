from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import mysql.connector
import os
from datetime import datetime

# ---------------------------------------------------------------------
# 🔹 Load environment variables
# ---------------------------------------------------------------------
load_dotenv()

TIDB_CONFIG = {
    "host": os.getenv("TIDB_HOST"),
    "port": int(os.getenv("TIDB_PORT", 4000)),
    "user": os.getenv("TIDB_USER"),
    "password": os.getenv("TIDB_PASSWORD"),
    "database": os.getenv("TIDB_DATABASE"),
    "ssl_ca": os.getenv("TIDB_SSL_CA")

}
API_SERVER = os.getenv("API_SERVER", "http://localhost:5000")

# ---------------------------------------------------------------------
# 🧩 Initialize Flask App
# ---------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------
# 🛠️ Database connection helper
# ---------------------------------------------------------------------
def get_db_connection():
    """Establish and return a TiDB (MySQL) connection"""
    try:
        conn = mysql.connector.connect(**TIDB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ TiDB connection failed: {e}")
        return None

# ---------------------------------------------------------------------
# 🏗️ API ENDPOINTS
# ---------------------------------------------------------------------

@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    """Return top 10 leaderboard entries"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                id INT AUTO_INCREMENT PRIMARY KEY,
                player_name VARCHAR(50),
                score INT,
                level INT,
                last_played DATETIME
            )
        """)
        cursor.execute("SELECT player_name, score, level, last_played FROM leaderboard ORDER BY score DESC LIMIT 10")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data), 200
    except Exception as e:
        print(f"⚠️ Failed to fetch leaderboard: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/save_score", methods=["POST"])
def save_score():
    """Insert or update player score"""
    payload = request.get_json()
    player_name = payload.get("player_name")
    score = payload.get("score", 0)
    level = payload.get("level", 1)

    if not player_name:
        return jsonify({"error": "Player name is required"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                id INT AUTO_INCREMENT PRIMARY KEY,
                player_name VARCHAR(50),
                score INT,
                level INT,
                last_played DATETIME
            )
        """)
        cursor.execute("SELECT score FROM leaderboard WHERE player_name=%s", (player_name,))
        existing = cursor.fetchone()

        if existing:
            if score > existing[0]:
                cursor.execute(
                    "UPDATE leaderboard SET score=%s, level=%s, last_played=%s WHERE player_name=%s",
                    (score, level, datetime.now(), player_name)
                )
        else:
            cursor.execute(
                "INSERT INTO leaderboard (player_name, score, level, last_played) VALUES (%s, %s, %s, %s)",
                (player_name, score, level, datetime.now())
            )

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"⚠️ Failed to save score: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------
# 🚀 Run Flask API
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
