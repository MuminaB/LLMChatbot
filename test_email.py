import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

msg = EmailMessage()
msg["Subject"] = "Test Email from RMU Chatbot"
msg["From"] = os.getenv("EMAIL_SENDER")
msg["To"] = "muminatou.barrow@st.rmu.edu.gh"  # or your personal email to test
msg.set_content("This is a test email from your chatbot's SMTP setup.")

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_PASSWORD"))
        smtp.send_message(msg)
        print("✅ Email sent successfully!")
except Exception as e:
    print("❌ Email failed:", e)
