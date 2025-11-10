from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import os
import json
import firebase_admin
from firebase_admin import credentials, db

# ---------------------------------------------------------------------
# 🌐 Flask App Setup
# ---------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------
# 🔥 Firebase Initialization (Local + Render Compatible)
# ---------------------------------------------------------------------
def init_firebase():
    try:
        if firebase_admin._apps:
            print("⚙️ Firebase already initialized.")
            return firebase_admin.get_app()

        cred_json = os.environ.get("FIREBASE_CRED")
        db_url = os.environ.get("FIREBASE_DB_URL")

        if cred_json and db_url:
            # 🟢 Running on Render
            try:
                # Handle escaped newlines in environment variable
                # Replace both \\n and actual \n patterns
                cred_json = cred_json.replace('\\n', '\n').replace('\\\\n', '\n')
                cred_dict = json.loads(cred_json)
                
                # Ensure private_key has proper newlines
                if 'private_key' in cred_dict:
                    cred_dict['private_key'] = cred_dict['private_key'].replace('\\n', '\n')
                
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {"databaseURL": db_url})
                print("✅ Firebase initialized using Render environment variables.")
                print(f"✅ Database URL: {db_url}")
            except json.JSONDecodeError as je:
                print(f"🔥 JSON parsing error: {je}")
                print(f"🔥 Credential length: {len(cred_json)}")
                raise
            except Exception as e:
                print(f"🔥 Firebase credential error: {e}")
                raise
        else:
            # 🟢 Running locally
            local_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
            if not os.path.exists(local_path):
                print(f"⚠️ Local credential file not found at {local_path}")
                print("⚠️ Attempting to use environment variables as fallback...")
                
                # Fallback: try to use environment variables even if not explicitly set
                if not cred_json:
                    raise FileNotFoundError(
                        f"Firebase credential file not found at {local_path} and FIREBASE_CRED environment variable not set.\n"
                        "Please either:\n"
                        "1. Place serviceAccountKey.json in the SpaceInvaderJava directory, OR\n"
                        "2. Set FIREBASE_CRED and FIREBASE_DB_URL environment variables"
                    )
                else:
                    # Use environment variables as fallback
                    cred_json = cred_json.replace('\\n', '\n').replace('\\\\n', '\n')
                    cred_dict = json.loads(cred_json)
                    if 'private_key' in cred_dict:
                        cred_dict['private_key'] = cred_dict['private_key'].replace('\\n', '\n')
                    cred = credentials.Certificate(cred_dict)
                    db_url = db_url or "https://space-invaders-java-default-rtdb.firebaseio.com/"
                    firebase_admin.initialize_app(cred, {"databaseURL": db_url})
                    print("✅ Firebase initialized using environment variables (fallback).")
            else:
                cred = credentials.Certificate(local_path)
                firebase_admin.initialize_app(cred, {
                    "databaseURL": "https://space-invaders-java-default-rtdb.firebaseio.com/"
                })
                print("✅ Firebase initialized using local credentials.")

        return firebase_admin.get_app()

    except Exception as e:
        print(f"🔥 Firebase initialization failed: {e}")
        print(f"🔥 Error type: {type(e).__name__}")
        import traceback
        print(f"🔥 Traceback: {traceback.format_exc()}")
        raise SystemExit("❌ Stopping app: Firebase initialization unsuccessful!")

# ---------------------------------------------------------------------
# 🚀 Initialize Firebase FIRST before any db.reference()
# ---------------------------------------------------------------------
firebase_app = init_firebase()

# ---------------------------------------------------------------------
# 🔗 Firebase Database References (AFTER init)
# ---------------------------------------------------------------------
if not firebase_admin._apps:
    raise SystemExit("❌ Firebase not initialized! Exiting...")

leaderboard_ref = db.reference("leaderboard", app=firebase_app)
admin_users_ref = db.reference("admin_users", app=firebase_app)

QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), "questions.txt")

# ---------------------------------------------------------------------
# ✅ Root Route
# ---------------------------------------------------------------------
@app.route("/")
def home():
    return jsonify({"message": "Java Quiz Game API (Firebase Realtime DB) is running successfully!"})

# ---------------------------------------------------------------------
# 🏆 Get Leaderboard
# ---------------------------------------------------------------------
@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    try:
        data = leaderboard_ref.get() or {}
        sorted_data = sorted(data.items(), key=lambda x: x[1].get("score", 0), reverse=True)
        leaderboard = [{"player_name": k, **v} for k, v in sorted_data]
        return jsonify(leaderboard)
    except Exception as e:
        print("⚠️ Firebase leaderboard fetch error:", e)
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

        leaderboard_ref.child(player_name).update({
            "score": score,
            "level": level
        })

        return jsonify({"success": True, "message": "Score updated successfully!"})
    except Exception as e:
        print("⚠️ Firebase update failed:", e)
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

        admin_data = admin_users_ref.child(username).get()
        if not admin_data:
            return jsonify({"error": "Invalid username"}), 401

        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        if hashed_input == admin_data.get("password_hash"):
            return jsonify({"success": True, "message": "Login successful!"}), 200
        else:
            return jsonify({"error": "Invalid password"}), 401
    except Exception as e:
        print("⚠️ Admin login error:", e)
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------
# 📋 Get All Questions
# ---------------------------------------------------------------------
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
# 🚀 Run the app
# ---------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
