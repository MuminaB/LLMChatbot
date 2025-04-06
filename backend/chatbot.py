import mysql.connector
from db import get_db_connection
import requests
import re
from fuzzywuzzy import fuzz  # Import fuzzy matching
from fuzzywuzzy import process  # For finding the best match

def normalize_text(text):
    """Normalize text by converting to lowercase and removing punctuation."""
    return re.sub(r'[^a-zA-Z0-9 ]', '', text.strip().lower())

def get_best_matching_question(user_question, questions_list):
    """Finds the best matching question from the database using fuzzy matching."""
    best_match, score = process.extractOne(user_question, questions_list, scorer=fuzz.ratio)
    return best_match if score > 70 else None  # Set a threshold (e.g., 70%)

def get_answer_from_db(question):
    """Retrieve the answer for a given question from the database using fuzzy matching."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        print("Database connected successfully.")

        normalized_question = normalize_text(question)

        # Get all stored questions from the database
        cursor.execute("SELECT id, question FROM questions")
        stored_questions = {row["id"]: normalize_text(row["question"]) for row in cursor.fetchall()}

        # Find the best match
        best_match = get_best_matching_question(normalized_question, list(stored_questions.values()))
        if best_match:
            question_id = [key for key, value in stored_questions.items() if value == best_match][0]
            cursor.execute("SELECT answer FROM answers WHERE question_id = %s", (question_id,))
            result = cursor.fetchone()
            if result:
                print(f"Found best match: {best_match} -> Answer: {result['answer']}")
                return result["answer"]

        print("No close match found in DB.")
        return None
    except Exception as e:
        print(f"Error retrieving answer from DB: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def fetch_from_rmu_website(question):
    """Attempts to fetch an answer from the RMU website."""
    try:
        print("Fetching answer from RMU website...")
        r = requests.get("https://rmu.edu.gh/api/faq", params={"query": question}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("answer"):
                print(f"RMU API response: {data['answer']}")
                return data["answer"]
    except Exception as e:
        print(f"Error fetching from RMU website: {e}")
    return None

def get_chatbot_response(question):
    """Main function to handle chatbot logic."""
    print(f"User asked: {question}")

    # Define common greetings and responses
    greetings = {
        "hi": "Hello! How can I assist you today?",
        "hello": "Hi there! How can I help?",
        "hey": "Hey! What can I do for you?",
        "good morning": "Good morning! How can I assist you?",
        "good afternoon": "Good afternoon! Need any help?",
        "good evening": "Good evening! Feel free to ask me anything.",
    }

    # Normalize input (lowercase) and check if it's a greeting
    normalized_question = normalize_text(question)
    for greet in greetings:
        if normalized_question.startswith(greet):
            return greetings[greet]

    # Try to fetch from DB first using fuzzy matching
    answer = get_answer_from_db(question)
    if answer:
        return answer

    # If not in DB, try fetching from RMU website
    answer = fetch_from_rmu_website(question)
    if answer:
        return answer

    # Final fallback
    return "I'm sorry, I couldn't find the answer. Please visit [RMU Website](https://rmu.edu.gh) for more information."
