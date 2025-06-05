import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

def send_signup_email(name, to_email):
    msg = EmailMessage()
    msg['Subject'] = "🎓 RMU Chatbot Account Created"
    msg['From'] = os.getenv("EMAIL_SENDER")
    msg['To'] = to_email
    msg.set_content(f"""Hello {name},

Your RMU Chatbot account was created successfully. You can now log in and begin using the bot for academic support and information.

Regards,  
RMU Bot Team
""")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg)
    except Exception as e:
        print("❌ Email failed to send:", e)
        return str(e)
 