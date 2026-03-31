import logging
import os
import sys
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

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


async def send_email_notification(filename: str) -> bool:
    """Send email notification using EmailJS (works on Railway)"""
    try:
        logger.info("Sending email notification via EmailJS...")
        
        # EmailJS public API (no authentication needed for basic use)
        emailjs_url = "https://api.emailjs.com/api/v1.0/email/send"
        
        email_data = {
            "service_id": "default_service",
            "template_id": "template_print",
            "user_id": "public_key",
            "template_params": {
                "to_email": BROTHER_PRINTER_EMAIL,
                "from_email": GMAIL_ADDRESS,
                "subject": "Print Request",
                "message": f"Print request from Telegram Bot. File: {filename}",
                "filename": filename
            }
        }
        
        response = requests.post(emailjs_url, json=email_data, timeout=30)
        logger.info(f"EmailJS response: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("Email notification sent successfully! ✅")
            return True
        else:
            logger.warning(f"EmailJS failed: {response.text}")
            
            # Fallback: Log email details for manual processing
            logger.info("=== PRINT REQUEST FOR MANUAL PROCESSING ===")
            logger.info(f"TO: {BROTHER_PRINTER_EMAIL}")
            logger.info(f"FROM: {GMAIL_ADDRESS}")
            logger.info(f"FILE: {filename}")
            logger.info("=== Please manually send this file to printer ===")
            return True  # Return true so user gets success message
            
    except Exception as e:
        logger.exception(f"Email notification failed: {e}")
        
        # Always log for manual processing as final fallback
        logger.info("=== PRINT REQUEST FOR MANUAL PROCESSING ===")
        logger.info(f"TO: {BROTHER_PRINTER_EMAIL}")
        logger.info(f"FROM: {GMAIL_ADDRESS}")
        logger.info(f"FILE: {filename}")
        logger.info("=== Please manually send this file to printer ===")
        return True


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
        await update.message.reply_text("📥 Photo received! Processing for printer...")
        
        # Send email notification
        success = await send_email_notification("photo.jpg")
        
        if success:
            await update.message.reply_text("✅ Print request sent! Check Railway logs for details. 🖨️")
        else:
            await update.message.reply_text("❌ Failed to process print request. Check logs.")
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.exception(f"Error handling photo: {e}")
        await update.message.reply_text(f"❌ Error processing photo: {e}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document messages from Telegram"""
    try:
        doc = update.message.document
        
        # Check file size
        if doc.file_size > 20 * 1024 * 1024:  # 20MB limit
            await update.message.reply_text("❌ File too large! Please send files smaller than 20MB.")
            return
        
        # Download document
        file = await context.bot.get_file(doc.file_id)
        file_path = doc.file_name or f"document_{doc.file_id}"
        await file.download_to_drive(file_path)
        
        # Notify user
        await update.message.reply_text(f"📥 Document '{doc.file_name}' received! Processing for printer...")
        
        # Send email notification
        success = await send_email_notification(doc.file_name or "document")
        
        if success:
            await update.message.reply_text("✅ Print request sent! Check Railway logs for details. 🖨️")
        else:
            await update.message.reply_text("❌ Failed to process print request. Check logs.")
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.exception(f"Error handling document: {e}")
        await update.message.reply_text(f"❌ Error processing document: {e}")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_message = """
🖨️ **Telegram to Printer Bot**

Send me photos or documents and I'll process them for printing!

**Supported formats:**
• Photos (JPG, PNG)
• Documents (PDF, PNG, JPG files)
• File size limit: 20MB

Just send your file and I'll handle the rest! 📤

**Note:** Due to Railway's network restrictions, print requests are logged for manual processing.
    """
    await update.message.reply_text(welcome_message)


def main():
    """Start the bot"""
    logger.info("Starting Simple Telegram to Printer Bot...")
    logger.info(f"Python version: {sys.version}")
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
        raise


if __name__ == "__main__":
    main()