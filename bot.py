#!/usr/bin/env python3
"""
Telegram to Printer Bot
Receives photos via Telegram and emails them to a Brother printer via Gmail SMTP
"""

import logging
import smtplib
import os
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Load environment variables from .env file (local development only)
load_dotenv()

# Credentials loaded from environment variables - never hardcoded
TELEGRAM_TOKEN      = os.getenv("TELEGRAM_TOKEN")
GMAIL_ADDRESS       = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD  = os.getenv("GMAIL_APP_PASSWORD")
PRINTER_EMAIL       = os.getenv("PRINTER_EMAIL")

# Validate all required env vars are present
missing = [k for k, v in {
    "TELEGRAM_TOKEN":     TELEGRAM_TOKEN,
    "GMAIL_ADDRESS":      GMAIL_ADDRESS,
    "GMAIL_APP_PASSWORD": GMAIL_APP_PASSWORD,
    "PRINTER_EMAIL":      PRINTER_EMAIL,
}.items() if not v]

if missing:
    print(f"ERROR: Missing environment variables: {', '.join(missing)}")
    print("Set them in .env file (local) or Render dashboard (production)")
    sys.exit(1)

# Thread pool - runs SMTP in background so it never blocks Telegram
executor = ThreadPoolExecutor(max_workers=2)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def send_email_sync(file_path: str, filename: str) -> tuple:
    """Synchronous email sending - runs in thread pool"""
    try:
        logger.info("Starting email send process...")
        logger.info(f"From: {GMAIL_ADDRESS}  To: {PRINTER_EMAIL}")

        # Build email with only the photo attachment (no body = no extra printed page)
        msg = MIMEMultipart()
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = PRINTER_EMAIL
        msg["Subject"] = "Print"

        with open(file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)

        # Send via Gmail SMTP port 587 + STARTTLS
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            logger.info("Gmail login successful!")
            server.sendmail(GMAIL_ADDRESS, PRINTER_EMAIL, msg.as_string())
            logger.info("Email sent successfully!")

        return True, "Email sent successfully!"

    except smtplib.SMTPAuthenticationError:
        logger.error("Gmail authentication failed - check App Password")
        return False, "Gmail authentication failed. Check App Password."
    except smtplib.SMTPConnectError:
        logger.error("Cannot connect to Gmail SMTP")
        return False, "Cannot connect to Gmail SMTP."
    except TimeoutError:
        logger.error("SMTP connection timed out")
        return False, "Connection timed out. SMTP may be blocked."
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return False, f"Error: {str(e)[:100]}"


async def send_email_with_attachment(file_path: str, filename: str) -> tuple:
    """Run email sending in thread pool to avoid blocking Telegram"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, send_email_sync, file_path, filename)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photo messages"""
    try:
        logger.info("Photo received from Telegram")

        photo = update.message.photo[-1]  # highest quality
        file  = await context.bot.get_file(photo.file_id)

        # Use /tmp on Linux (Render) and current dir on Windows
        tmp_dir = "/tmp" if os.name != "nt" else os.getcwd()
        file_path = os.path.join(tmp_dir, f"photo_{photo.file_id}.jpg")
        await file.download_to_drive(file_path)

        await update.message.reply_text("Photo received! Sending to printer...")

        success, message = await send_email_with_attachment(file_path, "photo.jpg")

        if success:
            await update.message.reply_text("Photo sent to printer! It should print shortly.")
        else:
            await update.message.reply_text(f"Failed: {message}")

        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        logger.exception(f"Error handling photo: {e}")
        await update.message.reply_text(f"Error: {str(e)[:100]}")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "Telegram Printer Bot\n\n"
        "Send me a photo and I will print it on your Brother printer!\n\n"
        "Just send a photo to get started."
    )


def main():
    """Start the bot"""
    logger.info("Starting Telegram Printer Bot...")
    logger.info(f"Gmail: {GMAIL_ADDRESS}")
    logger.info(f"Printer: {PRINTER_EMAIL}")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND, handle_start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Bot is running! Send photos to print.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
