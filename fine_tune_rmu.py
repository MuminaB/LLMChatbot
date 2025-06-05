import os
import time
from dotenv import load_dotenv
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

print("Uploading dataset2.jsonl for fine-tuning…")
upload_resp = openai.File.create(
    file=open("dataset2.jsonl", "rb"),
    purpose="fine-tune"
)
file_id = upload_resp.id
print(f" ➜ Uploaded. File ID = {file_id}")

print("Starting fine-tune job on gpt-3.5-turbo…")
ft_job = openai.FineTuningJob.create(
    training_file=file_id,
    model="gpt-3.5-turbo",
    suffix="rmu-v2"
)
job_id = ft_job.id
print(f" ➜ Job created. ID = {job_id}")

print("Polling status every 30 seconds…")
while True:
    status_resp = openai.FineTuningJob.retrieve(job_id)
    status = status_resp.status
    print(f"    Status: {status}")
    if status in ("succeeded", "failed"):
        break
    time.sleep(30)

if status == "succeeded":
    new_model = status_resp.fine_tuned_model
    print(f"\n🎉 Fine-tune succeeded! New model: {new_model}")
else:
    print("\n❌ Fine-tune failed. Check logs in the OpenAI dashboard.")
