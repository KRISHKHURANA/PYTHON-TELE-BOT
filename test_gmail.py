import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
BROTHER_PRINTER_EMAIL = os.getenv("BROTHER_PRINTER_EMAIL")

print(f"Gmail Address: {GMAIL_ADDRESS}")
print(f"App Password: {GMAIL_APP_PASSWORD}")
print(f"Printer Email: {BROTHER_PRINTER_EMAIL}")

try:
    # Test Gmail connection
    print("\n🔄 Testing Gmail connection...")
    
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = BROTHER_PRINTER_EMAIL
    msg["Subject"] = "Test Print"
    
    body = "This is a test email from your Telegram bot"
    msg.attach(MIMEText(body, "plain"))
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        print("📡 Connecting to Gmail SMTP...")
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        print("✅ Login successful!")
        
        server.sendmail(GMAIL_ADDRESS, BROTHER_PRINTER_EMAIL, msg.as_string())
        print("✅ Test email sent successfully!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e).__name__}")