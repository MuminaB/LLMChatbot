import os
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS  # Allow frontend requests from different origins
from chatbot import get_chatbot_response
from datetime import datetime
from db import get_db_connection


# Get the directory of the current file (backend folder)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Compute the path to the frontend folder
frontend_path = os.path.join(current_dir, '../frontend')

# Create the Flask app
#app = Flask(__name__, template_folder=frontend_path, static_folder=frontend_path)
app = Flask(__name__, template_folder=os.path.join(frontend_path, 'templates'),
            static_folder=os.path.join(frontend_path, 'static'))

# Enable CORS
CORS(app)

# Secret key for session management
app.secret_key = os.urandom(24)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM user_profiles WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and user["password"] == password:
            session["username"] = user["username"]
            session["role"] = user["role"]
            if user["role"] == "admin":
                return jsonify({"success": True, "redirect": "/admin"})
            else:
                return jsonify({"success": True, "redirect": "/"})


    # This handles GET request for /login and returns the login form
    return render_template("login.html")


@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))  # 🔒 Force login first
    return render_template("index.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/start-session", methods=["POST"])
def start_session():
    timestamp = datetime.now().strftime("session_%Y%m%d_%H%M%S")
    session_id = timestamp

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO conversation_sessions (session_id) VALUES (%s)", (session_id,))
        conn.commit()
        return jsonify({"session_id": session_id})
    except Exception as e:
        print("Error creating session:", e)
        return jsonify({"error": "Failed to start session"}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/chat", methods=["POST"])
def chat():
    print("✅ Received /chat POST request")
    data = request.json
    message = data.get("message", "")
    session_id = data.get("session_id")

    if not message or not session_id:
        return jsonify({"error": "Message and session_id are required"}), 400

    response = get_chatbot_response(message, session_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO conversation_logs (session_id, sender, message) VALUES (%s, %s, %s)",
            (session_id, 'user', message)
        )
        cursor.execute(
            "INSERT INTO conversation_logs (session_id, sender, message) VALUES (%s, %s, %s)",
            (session_id, 'bot', response)
        )
        conn.commit()
    except Exception as e:
        print("Error logging chat:", e)
    finally:
        cursor.close()
        conn.close()

    return jsonify({"response": response})


@app.route("/delete_chat/<int:chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM conversation_logs WHERE id = %s", (chat_id,))
        conn.commit()
        return '', 204
    except:
        conn.rollback()
        return 'Failed', 500
    finally:
        cursor.close()
        conn.close()

@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM questions")
    total_questions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user_profiles")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM feedback")
    feedback_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM conversation_sessions")
    session_count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_questions=total_questions,
        total_users=total_users,
        feedback_count=feedback_count,
        session_count=session_count
    )


if __name__ == "__main__":
    app.run(debug=True)
