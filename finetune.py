from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.fine_tuning.jobs.create(
    training_file="file-7j7bH8ANqULhffktLZ1BKp", 
    model="gpt-3.5-turbo"
)

print("✅ Fine-tuning started.")
print("📦 Job ID:", response.id)
