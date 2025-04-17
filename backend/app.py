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

@app.route("/admin/qa")
def qa_manager():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT q.id, q.question, a.answer, i.name AS intent
        FROM questions q
        LEFT JOIN answers a ON a.question_id = q.id
        LEFT JOIN intents i ON q.intent_id = i.id
    """)
    qa_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin/qa.html", qa_list=qa_list)

@app.route("/admin/qa/add", methods=["GET", "POST"])
def add_qa():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        intent_id = request.form.get("intent_id")
        question = request.form.get("question").strip()
        answer = request.form.get("answer").strip()
        synonyms_raw = request.form.get("synonyms", "").strip()

        try:
            cursor.execute(
                "INSERT INTO questions (intent_id, question, category) VALUES (%s, %s, %s)",
                (intent_id, question, 'admin')
            )
            question_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO answers (question_id, answer) VALUES (%s, %s)",
                (question_id, answer)
            )

            if synonyms_raw:
                synonyms = [s.strip() for s in synonyms_raw.split(",") if s.strip()]
                for syn in synonyms:
                    cursor.execute(
                        "INSERT INTO synonyms (question_id, synonym) VALUES (%s, %s)",
                        (question_id, syn)
                    )

            conn.commit()
            return redirect(url_for('qa_manager'))

        except Exception as e:
            conn.rollback()
            print("Error adding Q&A:", e)
            return "Error occurred while saving", 500

        finally:
            cursor.close()
            conn.close()

    cursor.execute("SELECT id, name FROM intents ORDER BY name ASC")
    intents = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin/add_qa.html", intents=intents)

@app.route("/admin/qa/edit/<int:question_id>", methods=["GET", "POST"])
def edit_qa(question_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        intent_id = request.form.get("intent_id")
        question = request.form.get("question").strip()
        answer = request.form.get("answer").strip()
        synonyms_raw = request.form.get("synonyms", "").strip()

        try:
            # Update question
            cursor.execute(
                "UPDATE questions SET question = %s, intent_id = %s WHERE id = %s",
                (question, intent_id, question_id)
            )

            # Update answer
            cursor.execute(
                "UPDATE answers SET answer = %s WHERE question_id = %s",
                (answer, question_id)
            )

            # Delete old synonyms and insert new ones
            cursor.execute("DELETE FROM synonyms WHERE question_id = %s", (question_id,))
            if synonyms_raw:
                synonyms = [s.strip() for s in synonyms_raw.split(",") if s.strip()]
                for syn in synonyms:
                    cursor.execute(
                        "INSERT INTO synonyms (question_id, synonym) VALUES (%s, %s)",
                        (question_id, syn)
                    )

            conn.commit()
            return redirect(url_for('qa_manager'))

        except Exception as e:
            conn.rollback()
            print("Error editing Q&A:", e)
            return "Error occurred", 500

        finally:
            cursor.close()
            conn.close()

    # GET: load current data
    cursor.execute("SELECT * FROM questions WHERE id = %s", (question_id,))
    question_data = cursor.fetchone()

    cursor.execute("SELECT answer FROM answers WHERE question_id = %s", (question_id,))
    answer_data = cursor.fetchone()

    cursor.execute("SELECT GROUP_CONCAT(synonym SEPARATOR ', ') AS synonyms FROM synonyms WHERE question_id = %s", (question_id,))
    synonym_data = cursor.fetchone()

    cursor.execute("SELECT id, name FROM intents ORDER BY name ASC")
    intents = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/edit_qa.html",
        question=question_data,
        answer=answer_data["answer"] if answer_data else "",
        synonyms=synonym_data["synonyms"] if synonym_data else "",
        intents=intents
    )

@app.route("/admin/qa/delete/<int:question_id>")
def delete_qa(question_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM synonyms WHERE question_id = %s", (question_id,))
        cursor.execute("DELETE FROM answers WHERE question_id = %s", (question_id,))
        cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Error deleting Q&A:", e)
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('qa_manager'))

if __name__ == "__main__":
    app.run(debug=True)
