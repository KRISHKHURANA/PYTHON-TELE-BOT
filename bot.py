#!/usr/bin/env python3
"""
Telegram to Printer Bot
Receives photos via Telegram, asks for print mode (Color / B&W),
then emails the image to a Brother printer via Gmail SMTP.
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
from PIL import Image
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ── Environment variables ─────────────────────────────────────────────────────
load_dotenv()

TELEGRAM_TOKEN     = os.getenv("TELEGRAM_TOKEN")
GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
PRINTER_EMAIL      = os.getenv("PRINTER_EMAIL")

# Validate all required env vars are present
missing = [k for k, v in {
    "TELEGRAM_TOKEN":     TELEGRAM_TOKEN,
    "GMAIL_ADDRESS":      GMAIL_ADDRESS,
    "GMAIL_APP_PASSWORD": GMAIL_APP_PASSWORD,
    "PRINTER_EMAIL":      PRINTER_EMAIL,
}.items() if not v]

if missing:
    print(f"ERROR: Missing environment variables: {', '.join(missing)}")
    print("Set them in .env (local) or Render/EC2 environment (production)")
    sys.exit(1)

# ── Thread pool ───────────────────────────────────────────────────────────────
# Runs blocking SMTP code in background so it never blocks the Telegram loop
executor = ThreadPoolExecutor(max_workers=2)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Callback data constants ───────────────────────────────────────────────────
CB_COLOR = "print_color"
CB_BW    = "print_bw"


# ── SMTP helper ───────────────────────────────────────────────────────────────
def send_email_sync(file_path: str, filename: str) -> tuple:
    """
    Blocking SMTP send - called via ThreadPoolExecutor.
    Returns (success: bool, message: str).
    """
    try:
        logger.info("Starting email send process...")
        logger.info(f"From: {GMAIL_ADDRESS}  To: {PRINTER_EMAIL}")

        # Build email - attachment only, no body text (avoids extra printed page)
        msg = MIMEMultipart()
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = PRINTER_EMAIL
        msg["Subject"] = "Print"

        with open(file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{filename}"',
            )
            msg.attach(part)

        # Gmail SMTP - port 587 + STARTTLS
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
    """Async wrapper - runs SMTP in thread pool to avoid blocking Telegram."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, send_email_sync, file_path, filename)


# ── Temp file path helper ─────────────────────────────────────────────────────
def get_tmp_path(filename: str) -> str:
    """Returns a temp path that works on both Windows and Linux (Render/EC2)."""
    tmp_dir = "/tmp" if os.name != "nt" else os.getcwd()
    return os.path.join(tmp_dir, filename)


# ── Cleanup helper ────────────────────────────────────────────────────────────
def cleanup(file_path: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deletes the temp file and clears stored user data."""
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"Deleted temp file: {file_path}")
    context.user_data.clear()


# ── Handlers ──────────────────────────────────────────────────────────────────
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start command handler."""
    await update.message.reply_text(
        "Telegram Printer Bot\n\n"
        "Send me a photo and I will ask how you want to print it.\n\n"
        "Supported modes:\n"
        "  Color - prints the original photo\n"
        "  Black & White - converts to grayscale before printing"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Receives a photo, downloads it, stores the path in user_data,
    then presents the print-mode selection keyboard.
    """
    try:
        logger.info(f"Photo received from user {update.effective_user.id}")

        # Download the highest-quality version
        photo     = update.message.photo[-1]
        file      = await context.bot.get_file(photo.file_id)
        file_path = get_tmp_path(f"photo_{update.effective_user.id}.jpg")
        await file.download_to_drive(file_path)
        logger.info(f"Photo saved to: {file_path}")

        # Store path so the callback handler can find it
        context.user_data["photo_path"] = file_path

        # Build inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("🌈 Color",         callback_data=CB_COLOR),
                InlineKeyboardButton("🖤 Black & White", callback_data=CB_BW),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🖨️ Select Print Mode",
            reply_markup=reply_markup,
        )

    except Exception as e:
        logger.exception(f"Error handling photo: {e}")
        await update.message.reply_text(f"Error processing photo: {str(e)[:100]}")


async def handle_print_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handles the Color / Black & White button press.
    Converts image if needed, sends via email, then cleans up.
    """
    query = update.callback_query
    await query.answer()  # removes the loading spinner on the button

    # Retrieve the stored photo path
    photo_path: str = context.user_data.get("photo_path")

    if not photo_path or not os.path.exists(photo_path):
        await query.edit_message_text(
            "No photo found. Please send another photo."
        )
        return

    mode = query.data  # CB_COLOR or CB_BW

    try:
        if mode == CB_BW:
            # ── Black & White conversion (high quality) ───────────────────
            logger.info("Converting image to high-quality grayscale...")
            await query.edit_message_text("Converting to Black & White...")

            from PIL import ImageEnhance, ImageFilter
            import numpy as np

            img = Image.open(photo_path).convert("RGB")

            # Use luminosity weights (human eye perception) for best B&W
            # This is how professional photo editors convert to B&W
            r, g, b = img.split()
            r_arr = np.array(r, dtype=np.float32)
            g_arr = np.array(g, dtype=np.float32)
            b_arr = np.array(b, dtype=np.float32)

            # ITU-R BT.709 luma coefficients (best for natural B&W)
            gray = 0.2126 * r_arr + 0.7152 * g_arr + 0.0722 * b_arr
            img = Image.fromarray(np.clip(gray, 0, 255).astype(np.uint8), mode="L")

            # Unsharp mask for crisp detail (like printer driver does)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=2))

            # Save as lossless PNG - no compression artifacts
            png_path = photo_path.replace(".jpg", ".png")
            img.save(png_path, "PNG")

            # Replace photo_path with PNG path
            os.remove(photo_path)
            photo_path = png_path
            context.user_data["photo_path"] = png_path
            logger.info("High-quality lossless B&W conversion complete.")

        else:
            # ── Color (lossless PNG for max quality) ─────────────────────
            logger.info("Converting color image to lossless PNG...")
            await query.edit_message_text("Sending color photo to printer...")

            png_path = photo_path.replace(".jpg", ".png")
            img = Image.open(photo_path).convert("RGB")
            img.save(png_path, "PNG")
            os.remove(photo_path)
            photo_path = png_path
            context.user_data["photo_path"] = png_path
            logger.info("Color image saved as lossless PNG.")

        # ── Send via Gmail SMTP ───────────────────────────────────────────
        filename = "photo_bw.png" if mode == CB_BW else "photo.png"
        success, message = await send_email_with_attachment(photo_path, filename)

        if success:
            mode_label = "Black & White" if mode == CB_BW else "Color"
            await query.edit_message_text(
                f"✅ Photo sent to printer! ({mode_label})\nIt should print shortly."
            )
        else:
            await query.edit_message_text(f"❌ Failed: {message}")

    except Exception as e:
        logger.exception(f"Error in print callback: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)[:100]}")

    finally:
        # Always clean up temp file and user data
        cleanup(photo_path, context)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    """Builds and starts the bot."""
    logger.info("Starting Telegram Printer Bot...")
    logger.info(f"Gmail:   {GMAIL_ADDRESS}")
    logger.info(f"Printer: {PRINTER_EMAIL}")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_print_callback, pattern=f"^({CB_COLOR}|{CB_BW})$"))

    logger.info("Bot is running! Send photos to print.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
