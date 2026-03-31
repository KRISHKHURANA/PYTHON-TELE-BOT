import logging
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
import requests
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

# Load environment variables
load_dotenv()

# Configuration from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
BROTHER_PRINTER_EMAIL = os.getenv("BROTHER_PRINTER_EMAIL")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

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
    """Send email with attachment to Brother printer using SendGrid API (Railway compatible)"""
    try:
        logger.info("Attempting to send email via SendGrid API (Railway compatible)...")
        logger.info(f"From: {GMAIL_ADDRESS} To: {BROTHER_PRINTER_EMAIL}")
        
        # Try SendGrid API first (recommended for Railway)
        if SENDGRID_API_KEY:
            try:
                logger.info("Using SendGrid API...")
                
                # Read and encode the file
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    encoded_file = base64.b64encode(file_data).decode()
                
                # Create SendGrid message
                message = Mail(
                    from_email=GMAIL_ADDRESS,
                    to_emails=BROTHER_PRINTER_EMAIL,
                    subject='Print',
                    html_content='Print request from Telegram Bot'
                )
                
                # Add attachment
                attachment = Attachment(
                    FileContent(encoded_file),
                    FileName(filename),
                    FileType('application/octet-stream'),
                    Disposition('attachment')
                )
                message.attachment = attachment
                
                # Send via SendGrid
                sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)
                response = sg.send(message)
                
                logger.info(f"SendGrid response status: {response.status_code}")
                if response.status_code == 202:
                    logger.info("Email sent successfully via SendGrid! ✅")
                    return True
                else:
                    logger.error(f"SendGrid failed with status: {response.status_code}")
                    
            except Exception as sendgrid_error:
                logger.error(f"SendGrid failed: {sendgrid_error}")
        
        # Fallback to direct HTTP email service
        logger.info("Trying direct HTTP email service...")
        try:
            # Use a simple email API service
            email_data = {
                "from": GMAIL_ADDRESS,
                "to": BROTHER_PRINTER_EMAIL,
                "subject": "Print",
                "text": "Print request from Telegram Bot",
                "filename": filename
            }
            
            # Try EmailJS or similar service
            response = requests.post(
                "https://api.emailjs.com/api/v1.0/email/send",
                json=email_data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("Email sent successfully via HTTP service! ✅")
                return True
            else:
                logger.warning(f"HTTP email service failed: {response.status_code}")
                
        except Exception as http_error:
            logger.error(f"HTTP email service failed: {http_error}")
        
        # Final fallback: Manual email notification
        logger.error("All email methods failed. Railway blocks SMTP and no API key configured.")
        logger.error("SOLUTION: Set up SendGrid API key in Railway environment variables")
        logger.error(f"File to print: {filename}")
        logger.error(f"Printer email: {BROTHER_PRINTER_EMAIL}")
        
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
            await update.message.reply_text("❌ Failed to send photo. Railway blocks SMTP. Need SendGrid API key.")
        
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
            await update.message.reply_text("❌ Failed to send document. Railway blocks SMTP. Need SendGrid API key.")
        
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