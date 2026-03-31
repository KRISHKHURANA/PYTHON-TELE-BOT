import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Your credentials
GMAIL_ADDRESS = "brotherprintermmk@gmail.com"
GMAIL_APP_PASSWORD = "ugvjtxkboucnerre"
BROTHER_PRINTER_EMAIL = "44653980797@print.brother.com"

print(f"Testing Gmail: {GMAIL_ADDRESS}")
print(f"Sending to printer: {BROTHER_PRINTER_EMAIL}")

try:
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = BROTHER_PRINTER_EMAIL
    msg["Subject"] = "Test Print"
    
    body = "Test email from bot"
    msg.attach(MIMEText(body, "plain"))
    
    print("Connecting to Gmail...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        print("Login successful!")
        server.sendmail(GMAIL_ADDRESS, BROTHER_PRINTER_EMAIL, msg.as_string())
        print("Email sent successfully!")
        
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e).__name__}")