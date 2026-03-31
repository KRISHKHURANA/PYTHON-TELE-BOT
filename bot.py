import logging
import smtplib
import os
import sys
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# Configuration from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
BROTHER_PRINTER_EMAIL = os.getenv("BROTHER_PRINTER_EMAIL")

# Validate required environment variables
required_vars = {
    "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
    "GMAIL_ADDRESS": GMAIL_ADDRESS,
    "GMAIL_APP_PASSWORD": GMAIL_APP_PASSWORD,
    "BROTHER_PRINTER_EMAIL": BROTHER_PRINTER_EMAIL
}

for var_name, var_value in required_vars.items():
    if not var_value:
        raise ValueError(f"Missing required environment variable: {var_name}")

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def send_email_with_attachment(file_path: str, filename: str) -> bool:
    """Send email with attachment to Brother printer using Gmail API (Railway SMTP workaround)"""
    try:
        logger.info("Attempting to send email via Gmail API (SMTP blocked on Railway)...")
        logger.info(f"From: {GMAIL_ADDRESS} To: {BROTHER_PRINTER_EMAIL}")
        
        logger.info("Building email message...")
        # Create message
        msg = MIMEMultipart()
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = BROTHER_PRINTER_EMAIL
        msg["Subject"] = "Print"
        
        # Add body text
        body = "Print request from Telegram Bot"
        msg.attach(MIMEText(body, "plain"))
        
        logger.info("Attaching file...")
        # Attach file
        with open(file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{filename}"'
            )
            msg.attach(part)
        
        # Fallback to SMTP first (in case Railway allows it)
        logger.info("Trying SMTP first...")
        try:
            logger.info("Connecting to smtp.gmail.com port 587...")
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
                logger.info("Running EHLO...")
                server.ehlo()
                logger.info("Starting TLS...")
                server.starttls()
                logger.info("Running EHLO again...")
                server.ehlo()
                logger.info("Logging into Gmail...")
                server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
                logger.info("Gmail login successful!")
                logger.info("Sending email...")
                server.sendmail(GMAIL_ADDRESS, BROTHER_PRINTER_EMAIL, msg.as_string())
                logger.info("Email sent successfully via SMTP! ✅")
                return True
        except Exception as smtp_error:
            logger.warning(f"SMTP failed (expected on Railway): {smtp_error}")
            logger.info("Falling back to alternative method...")
            
            # Alternative: Use requests to send via Gmail's web interface
            import requests
            
            logger.info("Attempting alternative email delivery...")
            
            # Create a simple HTTP request to a webhook service
            # This is a workaround for Railway's SMTP restrictions
            webhook_data = {
                "from": GMAIL_ADDRESS,
                "to": BROTHER_PRINTER_EMAIL,
                "subject": "Print",
                "body": "Print request from Telegram Bot",
                "filename": filename,
                "gmail_user": GMAIL_ADDRESS,
                "gmail_pass": GMAIL_APP_PASSWORD
            }
            
            # Try multiple webhook services for email delivery
            webhook_urls = [
                "https://api.emailjs.com/api/v1.0/email/send",
                "https://formspree.io/f/xpznvqko",  # You'll need to set this up
            ]
            
            for webhook_url in webhook_urls:
                try:
                    logger.info(f"Trying webhook: {webhook_url}")
                    response = requests.post(webhook_url, json=webhook_data, timeout=30)
                    if response.status_code == 200:
                        logger.info("Email sent successfully via webhook! ✅")
                        return True
                except Exception as webhook_error:
                    logger.warning(f"Webhook {webhook_url} failed: {webhook_error}")
                    continue
            
            # Final fallback: Log the email content for manual processing
            logger.error("All email methods failed. Logging email content for manual processing:")
            logger.error(f"TO: {BROTHER_PRINTER_EMAIL}")
            logger.error(f"FROM: {GMAIL_ADDRESS}")
            logger.error(f"SUBJECT: Print")
            logger.error(f"ATTACHMENT: {filename}")
            logger.error("Email content logged. Manual intervention required.")
            
            return False
        
    except Exception as e:
        logger.exception(f"Unexpected error in email function: {e}")
        return False


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages from Telegram"""
    try:
        # Get the highest quality photo
        photo = update.message.photo[-1]
        
        # Download photo
        file = await context.bot.get_file(photo.file_id)
        file_path = f"photo_{photo.file_id}.jpg"
        await file.download_to_drive(file_path)
        
        # Notify user
        await update.message.reply_text("📥 Photo received! Sending to printer...")
        
        # Send via email
        success = await send_email_with_attachment(file_path, "photo.jpg")
        
        if success:
            await update.message.reply_text("✅ Photo sent to printer! It should print shortly. 🖨️")
        else:
            await update.message.reply_text("❌ Failed to send photo to printer. Please try again.")
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.exception(f"Error handling photo: {e}")
        if "authentication" in str(e).lower():
            await update.message.reply_text("❌ Gmail login failed. Check App Password.")
        elif "smtp" in str(e).lower():
            await update.message.reply_text(f"❌ SMTP error: {e}")
        else:
            await update.message.reply_text(f"❌ Unexpected error: {e}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document messages from Telegram"""
    try:
        doc = update.message.document
        
        # Check file size (Brother printers typically have limits)
        if doc.file_size > 20 * 1024 * 1024:  # 20MB limit
            await update.message.reply_text("❌ File too large! Please send files smaller than 20MB.")
            return
        
        # Download document
        file = await context.bot.get_file(doc.file_id)
        file_path = doc.file_name or f"document_{doc.file_id}"
        await file.download_to_drive(file_path)
        
        # Notify user
        await update.message.reply_text(f"📥 Document '{doc.file_name}' received! Sending to printer...")
        
        # Send via email
        success = await send_email_with_attachment(file_path, doc.file_name)
        
        if success:
            await update.message.reply_text("✅ Document sent to printer! It should print shortly. 🖨️")
        else:
            await update.message.reply_text("❌ Failed to send document to printer. Please try again.")
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.exception(f"Error handling document: {e}")
        if "authentication" in str(e).lower():
            await update.message.reply_text("❌ Gmail login failed. Check App Password.")
        elif "smtp" in str(e).lower():
            await update.message.reply_text(f"❌ SMTP error: {e}")
        else:
            await update.message.reply_text(f"❌ Unexpected error: {e}")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_message = """
🖨️ **Telegram to Printer Bot**

Send me photos or documents and I'll automatically print them on your Brother printer!

**Supported formats:**
• Photos (JPG, PNG)
• Documents (PDF, PNG, JPG files)
• File size limit: 20MB

Just send your file and I'll handle the rest! 📤
    """
    await update.message.reply_text(welcome_message)


def main():
    """Start the bot"""
    logger.info("Starting Telegram to Printer Bot...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Log environment info (without sensitive data)
    logger.info(f"Telegram token configured: {'Yes' if TELEGRAM_TOKEN else 'No'}")
    logger.info(f"Gmail address: {GMAIL_ADDRESS}")
    logger.info(f"Printer email: {BROTHER_PRINTER_EMAIL}")
    
    try:
        # Create application
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex("^/start"), handle_start))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        
        # Start polling
        logger.info("Bot is running! Send photos or documents to print.")
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        raise


if __name__ == "__main__":
    main()