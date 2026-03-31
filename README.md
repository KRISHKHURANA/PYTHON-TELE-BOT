# Telegram to Printer Bot 🖨️

A Python Telegram bot that receives photos and documents from users and automatically emails them to a Brother printer for printing.

## How It Works

1. **You** send a photo or document to the Telegram bot
2. **Bot** downloads the file and emails it via Gmail SMTP
3. **Brother printer** receives the email and prints automatically
4. **You** get confirmation messages throughout the process

## Setup Instructions

### 1. Get Your Telegram Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the instructions
3. Copy your bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Set Up Gmail App Password

**Important:** You cannot use your regular Gmail password. You need an App Password.

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Click **Security** → **2-Step Verification** (enable it if not already)
3. Click **Security** → **App passwords**
4. Select **Mail** and generate a password
5. Copy the 16-character password (no spaces)

### 3. Get Your Brother Printer Email Address

1. Install **Brother iPrint&Scan** on your PC/Mac
2. Go to **Machine Settings** → **Online Functions** → **Online Functions Settings**
3. Click **"I accept the terms and conditions"**
4. Your printer will print an instruction sheet with its unique email address
5. The email looks like: `your_printer@print.brother.com`

### 4. Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual values:
   ```
   TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   GMAIL_ADDRESS=your_gmail@gmail.com
   GMAIL_APP_PASSWORD=abcdabcdabcdabcd
   BROTHER_PRINTER_EMAIL=your_printer@print.brother.com
   ```

## Local Testing

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the bot:
   ```bash
   python bot.py
   ```

3. Send a photo or document to your bot on Telegram!

## Deploy to Railway (Free)

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/telegram-printer-bot.git
   git push -u origin main
   ```

2. **Deploy on Railway:**
   - Go to [railway.app](https://railway.app) and sign up
   - Click **"New Project"** → **"Deploy from GitHub repo"**
   - Connect your GitHub repository
   - Railway will automatically detect the Python app

3. **Add Environment Variables:**
   In Railway dashboard, go to **Variables** tab and add:
   ```
   TELEGRAM_TOKEN=8729755193:AAHeo-9XjpWgnG05xE5nRVdhgFVaDKqqfmY
   GMAIL_ADDRESS=brotherprintermmk@gmail.com
   GMAIL_APP_PASSWORD=ugvjtxkboucnerre
   BROTHER_PRINTER_EMAIL=44653980797@print.brother.com
   ```

4. **Deploy:**
   - Railway will automatically build and deploy
   - Check the **Deployments** tab for logs
   - Your bot is now running 24/7!

## Troubleshooting Railway Deployment

If the bot crashes on Railway:

1. **Check the logs** in Railway dashboard → Deployments → View Logs
2. **Common issues:**
   - Missing environment variables
   - Wrong Procfile configuration
   - Network connectivity issues

3. **Restart the deployment** if needed

## Supported File Types

- **Photos:** JPG, PNG (sent as Telegram photos)
- **Documents:** PDF, PNG, JPG, DOC, DOCX (sent as Telegram files)
- **File size limit:** 20MB (Brother printer limitation)

## Troubleshooting

### Bot doesn't respond
- Check your `TELEGRAM_TOKEN` is correct
- Make sure the bot is running (check Render logs)

### "Failed to send to printer"
- Verify your `GMAIL_APP_PASSWORD` (not your regular password!)
- Check your `BROTHER_PRINTER_EMAIL` is correct
- Ensure your Gmail account has 2-Step Verification enabled

### Printer doesn't print
- Check if your Brother printer is connected to WiFi
- Verify the printer's email feature is enabled
- Try sending a test email manually to the printer's email address

### File too large error
- Brother printers typically have a 20MB email attachment limit
- Compress large files or split them into smaller parts

## Commands

- `/start` - Show welcome message and instructions

## Security Notes

- Never commit your `.env` file to version control
- Use Gmail App Passwords, not your real password
- The bot only accepts files from users who message it directly

## License

MIT License - feel free to modify and use for your own projects!