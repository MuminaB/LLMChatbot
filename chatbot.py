import os
import json
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
import openai
import time
from db import get_db_connection


# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

# Load Q&A dataset (optional if no longer used)
with open("data/rmu_openai_chatbot_dataset.jsonl", "r") as f:
    qa_dataset = [json.loads(line) for line in f if line.strip()]

# System prompt
chat_history = [
    {
        "role": "system",
        "content": (
            "You are RMU’s official chatbot. Be very interactive with the users. Provide detailed, accurate, and context-rich answers "
            "about programs, departments, hostels, student life, and fees. Avoid referring users back to the website. "
            "Explain as much as possible.\n\n"
            "Important note: RMU accepts both Ghana Cedis and US Dollars for academic fees. A fixed exchange rate is usually announced each semester "
            "for those paying in Ghana Cedis. Always mention this if asked about currency, fees, or payment methods."
        )
    }
]


# ✅ Memory checker
def get_correction_from_memory(user_input):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT corrected_answer FROM memory_corrections WHERE %s LIKE CONCAT('%', corrected_question, '%') LIMIT 1",
        (user_input,)
    )
    result = cursor.fetchone()
    conn.close()
    return result['corrected_answer'] if result else None

# ✅ Chatbot response logic
def get_chatbot_response(user_input):
    # 1. Check memory
    correction = get_correction_from_memory(user_input)
    if correction:
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": correction})
        return correction

    # 2. Add user input
    chat_history.append({"role": "user", "content": user_input})

    # 3. Check if this is a correction statement
    correction_keywords = ["no", "not correct", "it's", "its", "the correct", "that's wrong"]
    if any(kw in user_input.lower() for kw in correction_keywords):
        last_user_input = ""
        last_bot_reply = ""
        for i in range(len(chat_history) - 2, -1, -1):  # Skip current message, look backwards
            if chat_history[i]["role"] == "user":
                last_user_input = chat_history[i]["content"]
            elif chat_history[i]["role"] == "assistant" and last_user_input:
                last_bot_reply = chat_history[i]["content"]
                break

        if last_user_input and last_bot_reply:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO memory_corrections (corrected_question, original_answer, corrected_answer) VALUES (%s, %s, %s)",
                (last_user_input, last_bot_reply, user_input)
            )
            conn.commit()
            conn.close()


    # 4. Send to OpenAI
    try:
        response = openai.ChatCompletion.create(
        model="ft:gpt-3.5-turbo-0125:personal:rmu-v2:Be3kCokl",  # or use "gpt-3.5-turbo" if not fine-tuned
        messages=chat_history,
        temperature=0.5,
        max_tokens=2000
    )


        bot_reply = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": bot_reply})
        return bot_reply

    except Exception as e:
        return f"Sorry, an error occurred: {e}"
