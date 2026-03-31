import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Test both App Password formats
passwords_to_test = [
    "ugvjtxkboucnerre",  # Without spaces
    "ugvj txkb oucn erre"  # With spaces
]

GMAIL_ADDRESS = "brotherprintermmk@gmail.com"
BROTHER_PRINTER_EMAIL = "44653980797@print.brother.com"

for i, password in enumerate(passwords_to_test, 1):
    print(f"\n=== Test {i}: {'Without spaces' if i == 1 else 'With spaces'} ===")
    print(f"Password: '{password}'")
    
    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = BROTHER_PRINTER_EMAIL
        msg["Subject"] = f"Test Print {i}"
        
        body = f"Test email {i} from bot"
        msg.attach(MIMEText(body, "plain"))
        
        print("🔄 Connecting to Gmail...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, password)
            print("✅ Login successful!")
            server.sendmail(GMAIL_ADDRESS, BROTHER_PRINTER_EMAIL, msg.as_string())
            print("✅ Email sent successfully!")
            print("🖨️ Check your printer!")
            break  # Stop if successful
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        print(f"Error type: {type(e).__name__}")
        continue

print("\n=== Test Complete ===")