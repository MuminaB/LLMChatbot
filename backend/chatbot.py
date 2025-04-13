import mysql.connector
import os
import re
import requests
import ollama
from dotenv import load_dotenv
from db import get_db_connection
from fuzzywuzzy import fuzz, process
import subprocess

def ensure_ollama_running(model_name="llama3.2"):
    """Ensure Ollama model is running by listing models and starting if needed."""
    try:
        # Check if the model is available locally
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if model_name not in result.stdout:
            print(f"Model '{model_name}' not found. Pulling from Ollama...")
            subprocess.run(["ollama", "pull", model_name], check=True)

        # Start the model in the background (non-blocking)
        subprocess.Popen(["ollama", "run", model_name])
        print(f"✅ Ollama model '{model_name}' started.")
    except Exception as e:
        print(f"❌ Failed to start Ollama model: {e}")


load_dotenv()

def normalize_text(text):
    """Normalize text by converting to lowercase and removing punctuation."""
    return re.sub(r'[^a-zA-Z0-9 ]', '', text.strip().lower())

def get_best_matching_question(user_question, questions_list):
    """Finds the best matching question from the database using fuzzy matching."""
    best_match, score = process.extractOne(user_question, questions_list, scorer=fuzz.ratio)
    return best_match if score > 70 else None

def get_answer_from_db(question):
    """Retrieve the answer using fuzzy matching from questions and synonyms."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        print("Database connected successfully.")

        normalized_question = normalize_text(question)

        # 1️⃣ Check questions table
        cursor.execute("SELECT id, question FROM questions")
        stored_questions = {row["id"]: normalize_text(row["question"]) for row in cursor.fetchall()}
        best_match = get_best_matching_question(normalized_question, list(stored_questions.values()))

        if best_match:
            question_id = [qid for qid, text in stored_questions.items() if text == best_match][0]
            cursor.execute("SELECT answer FROM answers WHERE question_id = %s", (question_id,))
            result = cursor.fetchone()
            if result:
                print(f"Matched with question: {best_match}")
                return result["answer"]

        # 2️⃣ If no match, try the synonyms table
        cursor.execute("""
            SELECT s.question_id, s.synonym FROM synonyms s
            JOIN questions q ON s.question_id = q.id
        """)
        synonyms = cursor.fetchall()
        normalized_synonyms = {row["question_id"]: normalize_text(row["synonym"]) for row in synonyms}
        best_syn_match = get_best_matching_question(normalized_question, list(normalized_synonyms.values()))

        if best_syn_match:
            syn_id = [sid for sid, text in normalized_synonyms.items() if text == best_syn_match][0]
            cursor.execute("SELECT answer FROM answers WHERE question_id = %s", (syn_id,))
            result = cursor.fetchone()
            if result:
                print(f"Matched with synonym: {best_syn_match}")
                return result["answer"]

        print("No match found in DB or synonyms.")
        return None
    except Exception as e:
        print(f"Error retrieving answer from DB: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def generate_with_ollama(question):
    """Generate a response using the Ollama LLM model."""
    try:
        ensure_ollama_running()  # <-- make sure it's running
        print("Querying Ollama model...")
        response = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": question}])
        answer = response.get("message", {}).get("content", "").strip()
        if answer:
            print("Ollama provided a response.")
            return answer
    except Exception as e:
        print(f"Ollama error: {e}")
    return None


def fetch_from_rmu_website(question):
    """Attempts to fetch an answer from the RMU website."""
    try:
        print("Fetching answer from RMU website...")
        r = requests.get("https://rmu.edu.gh/frequently-asked-questions/", params={"query": question}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            answer = data.get("answer")
            if answer:
                print("Found answer from RMU site.")
                return answer
    except Exception as e:
        print(f"RMU fallback failed: {e}")
    return None

def log_usage_event(session_id, event_type, description):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usage_logs (session_id, event_type, event_description) VALUES (%s, %s, %s)",
            (session_id, event_type, description)
        )
        conn.commit()
    except Exception as e:
        print(f"Failed to log usage event: {e}")
    finally:
        cursor.close()
        conn.close()


def get_chatbot_response(question, session_id=None):
    """Main function to handle chatbot logic with multiple fallbacks."""
    print(f"User asked: {question}")

    greetings = {
        "hi": "Hello! How can I assist you today?",
        "hello": "Hi there! How can I help?",
        "hey": "Hey! What can I do for you?",
        "good morning": "Good morning! How can I assist you?",
        "good afternoon": "Good afternoon! Need any help?",
        "good evening": "Good evening! Feel free to ask me anything.",
        "what's up": "Not much! Just here to help. What do you need assistance with?",
        "how are you": "I'm just a chatbot, but I'm here and ready to help!",
        "who are you": "I'm RMU's virtual assistant, here to answer your RMU-related questions!",
        "can you help me": "Of course! Let me know what you need help with.",
        "thank you": "You're welcome! Let me know if you need anything else.",
        "thanks": "You're welcome! Let me know if you need anything else.",
        "bye": "Goodbye! Have a great day!",
        "goodbye": "Goodbye! Have a great day!",
        "see you later": "See you later! Don't hesitate to ask if you need help again."
    }

    normalized_question = normalize_text(question)
    for greet in greetings:
        if greet in normalized_question:
            return greetings[greet]

    answer = get_answer_from_db(question)
    if answer:
        return answer

    answer = generate_with_ollama(question)
    if answer:
        return answer

    answer = fetch_from_rmu_website(question)
    if answer:
        return answer
    
    if session_id:
        log_usage_event(session_id, "unmatched_question", question)
    return "I'm sorry, I couldn't find the answer. Please contact university.registrar@rmu.edu.gh for further assistance."
