import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, session
from flask_cors import CORS
from chatbot import get_chatbot_response
from db import get_db_connection
import json
import openai
import re
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from utils.email_utils import send_signup_email
import uuid

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

app.secret_key = os.getenv("SECRET_KEY", "fallback_key_for_dev")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Use .env or fallback
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")

# Get connection to the sheet
def get_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)
    # Open your sheet and specific worksheet
    sheet = client.open("Chatbot_Logs").worksheet("Messages")  # adjust to match your sheet names
    return sheet

# Log a row of chat data
def log_chat(user_id, user_msg, intent, fallback, latency_ms, bot_reply):
    sheet = get_sheet()
    sheet.append_row([
        datetime.utcnow().isoformat(),
        user_id,
        user_msg,
        intent,
        str(fallback),
        round(latency_ms),
        bot_reply
    ])

def detect_intent(message):
    prompt = (
    "You are an intent classifier for a university chatbot. Return only the intent label. "
    "Possible labels: admission_info, program_info, fees, hostel_info, contact, general_query, "
    "application_deadline, course_structure, location, scholarship, registration_help, unknown.\n\n"

    "User: What are the admission requirements?\nIntent: admission_info\n"
    "User: Tell me about the Nautical Science program.\nIntent: program_info\n"
    "User: How much is the tuition?\nIntent: fees\n"
    "User: Do you offer accommodation?\nIntent: hostel_info\n"
    "User: Where is the school located?\nIntent: location\n"
    "User: What are the deadlines for applying?\nIntent: application_deadline\n"
    "User: Do you offer any scholarships?\nIntent: scholarship\n"
    "User: Can you help me register my courses?\nIntent: registration_help\n"
    "User: Hello\nIntent: general_query\n"
    "User: I want to speak to someone\nIntent: contact\n"
    f"User: {message}\nIntent:"
    )


    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    intent = response.choices[0].message['content'].strip().lower()

    allowed_intents = [
        "admission_info", "program_info", "fees", "hostel_info", "contact",
        "general_query", "application_deadline", "course_structure",
        "location", "scholarship", "registration_help", "unknown"
    ]

    return intent if intent in allowed_intents else "unknown"


@app.route('/')
def home():
    if 'student_id' in session:
        return redirect(url_for('chat_interface'))
    return redirect(url_for('student_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_id'] = admin['id']
            session['admin_name'] = admin['full_name']
            return redirect(url_for('admin_dashboard'))
        else:
            return "❌ Invalid admin credentials"

    return render_template('admin/admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    return redirect(url_for('admin_login'))


@app.before_request
def restrict_admin_routes():
    admin_only = request.path.startswith('/admin') and not request.path.startswith('/admin/login')
    if admin_only and 'admin_id' not in session:
        return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
def admin_dashboard():
    dataset_path = 'data/rmu_openai_chatbot_dataset.jsonl'
    sample_count = 0
    last_updated = "N/A"
    avg_rating = 0
    feedback_count = 0


    try:
        with open(dataset_path, 'r') as f:
            sample_count = sum(1 for _ in f)
        last_modified = os.path.getmtime(dataset_path)
        last_updated = datetime.fromtimestamp(last_modified).strftime('%d %B %Y, %I:%M %p')

    except FileNotFoundError:
        pass

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*), AVG(rating) FROM feedbacks')
    result = cursor.fetchone()
    if result:
        feedback_count = result[0]
        avg_rating = round(result[1], 2) if result[1] else 0
    conn.close()

    return render_template('admin/dashboard.html', 
                           sample_count=sample_count, 
                           last_updated=last_updated,
                           avg_rating=avg_rating,
                           feedback_count=feedback_count)

@app.route('/admin/view-qa')
def view_qa():
    qas = []
    with open('data/rmu_openai_chatbot_dataset.jsonl', 'r') as file:
        for line in file:
            try:
                item = json.loads(line.strip())
                if 'messages' in item:
                    qas.append(item)
            except json.JSONDecodeError:
                continue
    return render_template('admin/view_qa.html', qas=qas)


@app.route('/admin/add-qa', methods=['GET', 'POST'])
def add_qa():
    if request.method == 'POST':
        user_msg = request.form['user']
        bot_msg = request.form['bot']

        new_entry = {
            "messages": [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": bot_msg}
            ]
        }

        try:
            with open('data/rmu_openai_chatbot_dataset.jsonl', 'a') as file:
                file.write(json.dumps(new_entry) + '\n')
        except Exception as e:
            return f"Error: {e}"

        return redirect(url_for('view_qa'))

    return render_template('admin/add_qa.html')

@app.route('/admin/edit-qa/<int:qa_id>', methods=['GET', 'POST'])
def edit_qa(qa_id):
    dataset_path = 'data/rmu_openai_chatbot_dataset.jsonl'

    # Read all existing lines
    with open(dataset_path, 'r') as file:
        lines = [json.loads(line.strip()) for line in file if line.strip()]

    if request.method == 'POST':
        user_msg = request.form['user']
        bot_msg = request.form['bot']

        # Replace the selected conversation
        lines[qa_id] = {
            "messages": [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": bot_msg}
            ]
        }

        # Overwrite the file
        with open(dataset_path, 'w') as file:
            for item in lines:
                file.write(json.dumps(item) + '\n')

        return redirect(url_for('view_qa'))

    # Pre-fill the form with selected entry
    current = lines[qa_id]["messages"]
    return render_template('admin/edit_qa.html', qa_id=qa_id, user=current[0]["content"], bot=current[1]["content"])

@app.route('/admin/delete-qa/<int:qa_id>')
def delete_qa(qa_id):
    dataset_path = 'data/rmu_openai_chatbot_dataset.jsonl'

    try:
        with open(dataset_path, 'r') as file:
            lines = [json.loads(line.strip()) for line in file if line.strip()]

        if 0 <= qa_id < len(lines):
            del lines[qa_id]

            with open(dataset_path, 'w') as file:
                for item in lines:
                    file.write(json.dumps(item) + '\n')
    except Exception as e:
        return f"Error deleting conversation: {e}"

    return redirect(url_for('view_qa'))


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # # Guest access control
    # if session.get("guest"):
    #     session['guest_queries'] = session.get('guest_queries', 0) + 1
    #     if session['guest_queries'] > 5:
    #         return jsonify({"response": "🚫 Guest limit reached. Please sign up to continue using the chatbot."})

    start_time = datetime.utcnow()

    bot_reply = get_chatbot_response(user_message)

    latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

    intent = detect_intent(user_message)
    fallback = (intent == "unknown")

    user_id = session.get("student_id", "guest")

    # ✅ Log to Google Sheet
    log_chat(
        user_id=user_id,
        user_msg=user_message,
        intent=intent,
        fallback=fallback,
        latency_ms=latency_ms,
        bot_reply=bot_reply
    )

    return jsonify({"response": bot_reply})
@app.route("/reset", methods=["POST"])
def reset_chat():
    from chatbot import chat_history
    # if session.get("guest") and session.get("guest_queries", 0) >= 5:
    #    return jsonify({"message": "🚫 Guest limit reached. You cannot start a new chat."}), 403


    chat_history.clear()
    # Re-add system instruction after reset
    chat_history.append({
        "role": "system",
        "content": "You are RMU’s official chatbot. Provide accurate, context-aware responses about the university."
    })
    return jsonify({"message": "Chat history cleared."})


@app.route("/save-session", methods=["POST"])
def save_session():
    from chatbot import chat_history
    data = request.get_json()
    messages = data.get("messages")

    # Detect if guest or student
    is_guest = session.get("guest", False)
    student_id = session.get("student_id") if not is_guest else None

    # Generate or reuse guest ID
    guest_id = None
    if is_guest:
        if 'guest_id' not in session:
            session['guest_id'] = f"guest_{int(datetime.utcnow().timestamp())}"
        guest_id = session['guest_id']

    # 🔍 Generate session name based on last used chat number
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if is_guest:
        cursor.execute("""
            SELECT session_name FROM chat_sessions
            WHERE guest_id = %s AND session_name LIKE 'Chat %%'
            ORDER BY created_at DESC LIMIT 1
        """, (guest_id,))
    else:
        cursor.execute("""
            SELECT session_name FROM chat_sessions
            WHERE student_id = %s AND session_name LIKE 'Chat %%'
            ORDER BY created_at DESC LIMIT 1
        """, (student_id,))

    result = cursor.fetchone()
    if result and result["session_name"].startswith("Chat "):
        try:
            last_number = int(result["session_name"].split(" ")[1])
            session_name = f"Chat {last_number + 1}"
        except (IndexError, ValueError):
            session_name = "Chat 1"
    else:
        session_name = "Chat 1"

    # ✅ Insert session
    try:
        cursor.execute(
            """
            INSERT INTO chat_sessions (session_name, messages, student_id, user_type, guest_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            (
                session_name,
                json.dumps(messages),
                student_id,
                'guest' if is_guest else 'student',
                guest_id
            )
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Session save error: {e}")
        return jsonify({"message": "Failed to save session."}), 500
    finally:
        conn.close()

    return jsonify({"message": f"{session_name} saved successfully."})

@app.route("/sessions", methods=["GET"])
def list_sessions():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    is_guest = session.get("guest", False)
    student_id = session.get("student_id") if not is_guest else None
    guest_id = session.get("guest_id") if is_guest else None

    if is_guest:
        cursor.execute("SELECT id, session_name, created_at FROM chat_sessions WHERE guest_id = %s ORDER BY created_at DESC", (guest_id,))
    else:
        cursor.execute("SELECT id, session_name, created_at FROM chat_sessions WHERE student_id = %s ORDER BY created_at DESC", (student_id,))

    sessions = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(sessions)

@app.route("/load-session/<int:session_id>", methods=["GET"])
def load_session(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT messages FROM chat_sessions WHERE id = %s", (session_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return jsonify(json.loads(result[0]))
    else:
        return jsonify({"error": "Session not found"}), 404

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    rating = data.get('rating')
    comment = data.get('comment')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO feedbacks (rating, comment) VALUES (%s, %s)",
        (rating, comment)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {'message': 'Feedback submitted successfully!'}, 200

@app.route("/delete-session/<int:session_id>", methods=["POST"])
def delete_session(session_id):
    is_guest = session.get("guest", False)
    student_id = session.get("student_id") if not is_guest else None
    guest_id = session.get("guest_id") if is_guest else None

    conn = get_db_connection()
    cursor = conn.cursor()

    if is_guest:
        cursor.execute("DELETE FROM chat_sessions WHERE id = %s AND guest_id = %s", (session_id, guest_id))
    else:
        cursor.execute("DELETE FROM chat_sessions WHERE id = %s AND student_id = %s", (session_id, student_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Chat deleted ✅"})


@app.route('/admin/view-feedbacks')
def view_feedbacks():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM feedbacks ORDER BY submitted_at DESC')
    feedbacks = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin/view_feedbacks.html', feedbacks=feedbacks)


@app.route('/admin/download-feedbacks')
def download_feedbacks():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM feedbacks ORDER BY submitted_at DESC')
    feedbacks = cursor.fetchall()
    cursor.close()
    conn.close()

    # Convert datetime objects to strings
    for item in feedbacks:
        if isinstance(item['submitted_at'], (datetime, )):
            item['submitted_at'] = item['submitted_at'].strftime('%Y-%m-%d %H:%M:%S')

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"feedbacks_{today}.json"

    response = Response(
        json.dumps(feedbacks, indent=2),
        mimetype='application/json'
    )
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@app.route('/admin/view-chat-history')
def view_chat_history():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cs.id,
            CASE
                WHEN cs.user_type = 'guest' THEN CONCAT('Guest_', cs.guest_id, ', ', cs.session_name)
                ELSE CONCAT(s.full_name, ', ', cs.session_name)
            END AS session_name,
            cs.created_at
        FROM chat_sessions cs
        LEFT JOIN students s ON cs.student_id = s.id
        WHERE cs.is_archived = FALSE
        ORDER BY cs.created_at DESC
    """)

    sessions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin/view_chat_history.html', sessions=sessions)


@app.route('/admin/archive-session/<int:session_id>', methods=['POST'])
def archive_session(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE chat_sessions SET is_archived = TRUE WHERE id = %s", (session_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_chat_history'))

@app.route('/admin/archived-sessions')
def view_archived_sessions():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cs.id,
               CASE
                   WHEN cs.user_type = 'guest' THEN CONCAT('Guest_', cs.guest_id, ', ', cs.session_name)
                   ELSE CONCAT(s.full_name, ', ', cs.session_name)
               END AS session_name,
               cs.created_at
        FROM chat_sessions cs
        LEFT JOIN students s ON cs.student_id = s.id
        WHERE cs.is_archived = TRUE
        ORDER BY cs.created_at DESC
    """)
    sessions = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('admin/view_archived_sessions.html', sessions=sessions)

@app.route('/admin/uploaded-files')
def view_uploaded_files():
    upload_dir = 'uploads'
    files = []

    if os.path.exists(upload_dir):
        for fname in os.listdir(upload_dir):
            if fname.endswith('.jsonl') or fname.endswith('.json'):
                full_path = os.path.join(upload_dir, fname)
                upload_time = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%Y-%m-%d %H:%M:%S')
                files.append({
                    "filename": fname,
                    "size_kb": os.path.getsize(full_path) // 1024,
                    "uploaded_at": upload_time
                })

    return render_template('admin/view_uploaded_files.html', files=files)

@app.route('/admin/restore-session/<int:session_id>', methods=['POST'])
def restore_session(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE chat_sessions SET is_archived = FALSE WHERE id = %s", (session_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_archived_sessions'))

@app.route('/admin/load-session/<int:session_id>')
def admin_load_session(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT messages FROM chat_sessions WHERE id = %s', (session_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        return jsonify(json.loads(result[0]))
    else:
        return jsonify({"error": "Session not found"}), 404

@app.route('/admin/upload-dataset', methods=['GET', 'POST'])
def upload_dataset():
    upload_dir = 'uploads'
    files = []

    # Always load current uploaded files
    if os.path.exists(upload_dir):
        for fname in os.listdir(upload_dir):
            if fname.endswith('.jsonl') or fname.endswith('.json'):
                full_path = os.path.join(upload_dir, fname)
                uploaded_at = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%Y-%m-%d %H:%M:%S')
                files.append({
                    "filename": fname,
                    "size_kb": os.path.getsize(full_path) // 1024,
                    "uploaded_at": uploaded_at
                })

    # Upload logic
    if request.method == 'POST':
        if 'dataset' not in request.files:
            return "⚠️ No file part", 400

        file = request.files['dataset']
        if file.filename == '':
            return "⚠️ No selected file", 400

        if file and (file.filename.endswith('.jsonl') or file.filename.endswith('.json')):
            upload_path = os.path.join(upload_dir, file.filename)
            os.makedirs(upload_dir, exist_ok=True)
            file.save(upload_path)
            return redirect(url_for('upload_dataset'))  # Refresh with new list

        return "⚠️ Invalid file type. Only .jsonl or .json allowed.", 400

    return render_template('admin/upload_training_data.html', files=files)

@app.route('/admin/view-upload/<filename>')
def view_uploaded_file(filename):
    upload_path = os.path.join('uploads', filename)
    if not os.path.exists(upload_path):
        return f"❌ File {filename} not found.", 404

    lines = []
    try:
        with open(upload_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 50:  # Limit preview to first 50 lines
                    break
                lines.append(line.strip())
    except Exception as e:
        return f"❌ Error reading file: {e}"

    return render_template('admin/view_file_preview.html', filename=filename, lines=lines)

@app.route('/admin/upload-success')
def upload_dataset_success():
    return "✅ Upload successful! (You can process this file later if needed.)"

@app.route('/signup', methods=['GET', 'POST'])
def student_signup():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "❌ Passwords do not match"

        if not re.match(r"^[a-zA-Z0-9._%+-]+@st\.rmu\.edu\.gh$", email):
            return "❌ Only RMU student emails are allowed."

        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO students (full_name, email, password_hash) VALUES (%s, %s, %s)",
                (full_name, email, hashed_pw)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            return f"❌ Error: {e}"
        finally:
            cursor.close()
            conn.close()

        # ✅ Send email
        try:
            send_signup_email(full_name, email)
        except Exception as e:
            return f"❌ Email Error: {e}"

        return redirect(url_for('student_login'))

    return render_template('student/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
        student = cursor.fetchone()
        cursor.close()
        conn.close()

        if student and check_password_hash(student['password_hash'], password):
            session['student_id'] = student['id']
            session['student_name'] = student['full_name']
            session['student_email'] = student['email']
            return redirect(url_for('chat_interface'))  # Replace with actual chatbot page route
        else:
            return "❌ Invalid email or password"

    return render_template('student/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('student_login'))

@app.route('/chatbot')
def chat_interface():
    guest_mode = session.get('guest', False)
    name = session.get('student_name', 'Guest')

    # Inject student_id or guest_id into JS sessionStorage using a script block
    student_id = session.get("student_id")
    guest_id = session.get("guest_id")

    return render_template('index.html',
        guest=guest_mode,
        student_name=name,
        student_id=student_id,
        guest_id=guest_id
    )

@app.route('/guest')
def guest_login():
    session.clear()
    session['guest'] = True
    session['student_name'] = 'Guest'

    # 🔒 Generate and persist guest ID for this browser session
    if 'guest_id' not in session:
        session['guest_id'] = f"guest_{int(datetime.utcnow().timestamp())}"

    return redirect(url_for('chat_interface'))

@app.route('/admin/view-memory')
def view_memory():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, corrected_question, corrected_answer, created_at
        FROM memory_corrections
        ORDER BY created_at DESC
    """)
    corrections = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Format date as DD-MM-YYYY HH:MM
    for c in corrections:
        c['created_at'] = c['created_at'].strftime('%d-%m-%Y %H:%M:%S')

    return render_template("admin/view_memory.html", corrections=corrections)

@app.route('/admin/edit-memory/<int:id>', methods=['GET', 'POST'])
def edit_memory(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        question = request.form['question']
        answer = request.form['answer']
        cursor.execute(
            "UPDATE memory_corrections SET corrected_question = %s, corrected_answer = %s WHERE id = %s",
            (question, answer, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('view_memory'))

    cursor.execute("SELECT * FROM memory_corrections WHERE id = %s", (id,))
    memory = cursor.fetchone()
    conn.close()
    return render_template('admin/edit_memory.html', memory=memory)

@app.route('/admin/delete-memory/<int:id>')
def delete_memory(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM memory_corrections WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_memory'))

@app.route('/admin/add-memory', methods=['GET', 'POST'])
def add_memory():
    if request.method == 'POST':
        question = request.form['question']
        answer = request.form['answer']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memory_corrections (corrected_question, corrected_answer) VALUES (%s, %s)",
            (question, answer)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('view_memory'))

    return render_template('admin/add_memory.html')

if __name__ == "__main__":
    app.run(debug=True)
