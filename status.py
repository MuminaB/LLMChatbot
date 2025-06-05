from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

job = client.fine_tuning.jobs.retrieve("ftjob-zz49hI3KQS1WhdjUzwCF9BqV")
print("Status:", job.status)
print("Model name (if ready):", job.fine_tuned_model)
