import os
import re
import requests
import subprocess
import fitz
import ollama
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fuzzywuzzy import fuzz, process
from db import get_db_connection

load_dotenv()

# --- 1. GREETING RESPONSES ---
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

def normalize_text(text):
    return re.sub(r'[^a-zA-Z0-9 ]', '', text.strip().lower())

def get_best_matching_question(user_question, questions_list):
    best_match, score = process.extractOne(user_question, questions_list, scorer=fuzz.ratio)
    return best_match if score > 70 else None

# --- 2. DATABASE MATCHING ---
def get_answer_from_db(user_question):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        normalized = normalize_text(user_question)

        cursor.execute("SELECT id, question FROM questions")
        questions = {row["id"]: normalize_text(row["question"]) for row in cursor.fetchall()}
        match = get_best_matching_question(normalized, list(questions.values()))

        if match:
            qid = [k for k, v in questions.items() if v == match][0]
            cursor.execute("SELECT answer FROM answers WHERE question_id = %s", (qid,))
            ans = cursor.fetchone()
            if ans:
                print(f"✅ Matched DB question: {match}")
                return ans["answer"]

        # Synonym fallback
        cursor.execute("SELECT s.question_id, s.synonym FROM synonyms s JOIN questions q ON s.question_id = q.id")
        syns = {row["question_id"]: normalize_text(row["synonym"]) for row in cursor.fetchall()}
        syn_match = get_best_matching_question(normalized, list(syns.values()))

        if syn_match:
            sid = [k for k, v in syns.items() if v == syn_match][0]
            cursor.execute("SELECT answer FROM answers WHERE question_id = %s", (sid,))
            syn_ans = cursor.fetchone()
            if syn_ans:
                print(f"✅ Matched synonym: {syn_match}")
                return syn_ans["answer"]

        return None
    except Exception as e:
        print(f"DB error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

# --- 3. OLLAMA LLaMA 3.2 GENERATION ---
SYSTEM_PROMPT = """
You are RMU-Bot, the official intelligent assistant for the Regional Maritime University (RMU), located in Ghana, West Africa.

IMPORTANT INSTRUCTION:
- "RMU" ALWAYS refers to the "Regional Maritime University in Ghana".
- NEVER refer to Rochester Institute of Technology, Robert Morris University, or any other meaning of RMU.
- Your job is to ONLY support questions related to RMU Ghana.

Use the official RMU websites and handbook for answers.
If you are unsure about something, say so or recommend contacting RMU support.
"""



RMU_LINKS = [
    "https://admissions.rmu.edu.gh/foreign",
    "https://admissions.rmu.edu.gh/index.php",
    "https://yen.com.gh/111886-regional-maritime-university-fees-courses-admission.html",
    "https://infopeeps.com/regional-maritime-university-admission-forms/",
    "https://infopeeps.com/regional-maritime-university-courses-and-fees/",
    "https://rmu.edu.gh/",
    "https://en.m.wikipedia.org/wiki/Regional_Maritime_University",
    "https://rmu.edu.gh/frequently-asked-questions/"
]

RMU_PDF_URL = "https://rmu.edu.gh/wp-content/uploads/2021/03/UNDERGRADUATE-STUDENTS-HANDBOOK-23032021.pdf"

def fetch_html_text(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")
        for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
            tag.decompose()
        return f"[{url}]\n" + soup.get_text(separator='\n', strip=True)[:2000]
    except Exception as e:
        return f"[Failed to fetch: {url}]"

def extract_pdf_text(url):
    try:
        r = requests.get(url)
        with open("temp_rmu.pdf", "wb") as f:
            f.write(r.content)
        doc = fitz.open("temp_rmu.pdf")
        return "\n".join([page.get_text() for page in doc])[:3000]
    except Exception as e:
        return "[PDF extract failed]"

def generate_with_ollama(user_question):
    print("⚙️ Using LLaMA 3.2 to generate response...")
    website_text = "\n\n".join([fetch_html_text(url) for url in RMU_LINKS])
    pdf_text = extract_pdf_text(RMU_PDF_URL)
    context = f"{website_text}\n\n{pdf_text}"

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{context}"},
            {"role": "user", "content": user_question}
        ]
    )

    output = response["message"]["content"].strip()

    # Filter out incorrect interpretations
    if any(x in output.lower() for x in ["rochester", "robert morris", "pennsylvania", "rit"]):
        print("🚫 Incorrect RMU interpretation detected. Using fallback.")
        return None

    return output



# --- 4. USAGE LOGGING ---
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
        print(f"Usage log error: {e}")
    finally:
        cursor.close()
        conn.close()

# --- 5. MAIN ENTRY FUNCTION ---
def get_chatbot_response(user_input, session_id=None):
    normalized = normalize_text(user_input)

    for greet in greetings:
        if greet in normalized:
            return greetings[greet]

    # 1️⃣ First: Try LLaMA 3.2 with web+pdf knowledge
    try:
        print("Trying LLaMA 3.2...")
        website_text = "\n\n".join([fetch_html_text(url) for url in RMU_LINKS])
        pdf_text = extract_pdf_text(RMU_PDF_URL)
        context = f"{website_text}\n\n{pdf_text}"

        response = ollama.chat(
            model="llama3.2",
            messages=[
                {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{context}"},
                {"role": "user", "content": user_input}
            ]
        )
        llm_answer = response["message"]["content"].strip()
        if llm_answer and len(llm_answer.split()) > 3:  # filter empty or weak responses
            print("✅ LLaMA 3.2 answered.")
            return llm_answer
    except Exception as e:
        print(f"⚠️ LLaMA error: {e}")

    # 2️⃣ Second: Try database as fallback
    db_answer = get_answer_from_db(user_input)
    if db_answer:
        print("📦 Using fallback from database.")
        return db_answer

    # 3️⃣ No match found
    if session_id:
        log_usage_event(session_id, "unmatched_question", user_input)
    return "I'm sorry, I couldn't find an answer. Please contact university.registrar@rmu.edu.gh for assistance."
