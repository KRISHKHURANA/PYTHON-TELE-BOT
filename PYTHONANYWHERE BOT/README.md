# Telegram to Printer Bot - PythonAnywhere Version

A Python Telegram bot optimized for PythonAnywhere hosting that sends photos and documents to a Brother printer via Gmail.

## 🌟 PythonAnywhere Advantages

- ✅ **Full SMTP Support** - Unlike Railway, PythonAnywhere allows Gmail SMTP connections
- ✅ **Always-On Free Tier** - Bot runs 24/7 without sleeping
- ✅ **File System Access** - Proper temporary file handling
- ✅ **Detailed Logging** - Logs saved to `/home/MASTERMINDKRISH/telegram_bot.log`

## 🚀 PythonAnywhere Deployment Steps

### 1. Upload Files
1. **Go to PythonAnywhere Dashboard** → **Files**
2. **Navigate to** `/home/MASTERMINDKRISH/`
3. **Upload these files:**
   - `bot.py`
   - `requirements.txt` 
   - `.env`

### 2. Install Dependencies
1. **Open a Bash console** on PythonAnywhere
2. **Run:**
   ```bash
   cd /home/MASTERMINDKRISH/
   pip3.10 install --user -r requirements.txt
   ```

### 3. Test the Bot
1. **In the Bash console, run:**
   ```bash
   python3.10 bot.py
   ```
2. **Send a photo** to your Telegram bot
3. **Check logs** for detailed SMTP process

### 4. Run as Always-On Task (Paid Feature)
If you have a paid PythonAnywhere account:
1. **Go to Dashboard** → **Tasks**
2. **Create new task:**
   - **Command:** `python3.10 /home/MASTERMINDKRISH/bot.py`
   - **Hour:** `*` (runs always)

### 5. Alternative: Keep Console Open (Free)
For free accounts:
1. **Keep the Bash console open** with the bot running
2. **PythonAnywhere allows one always-on console** for free users

## 📊 Monitoring

### Check Logs
```bash
tail -f /home/MASTERMINDKRISH/telegram_bot.log
```

### Check Bot Status
```bash
ps aux | grep bot.py
```

## 🔧 Configuration

All settings are in the `.env` file:
- `TELEGRAM_TOKEN` - Your bot token from @BotFather
- `GMAIL_ADDRESS` - Gmail account for sending emails
- `GMAIL_APP_PASSWORD` - Gmail App Password (not regular password)
- `BROTHER_PRINTER_EMAIL` - Your Brother printer's email address

## 🖨️ How It Works

1. **User sends photo/document** to Telegram bot
2. **Bot downloads file** to `/tmp/` directory
3. **Bot creates email** with file attachment
4. **Bot sends via Gmail SMTP** (port 587 + STARTTLS)
5. **Brother printer receives email** and prints automatically
6. **User gets confirmation** message

## 🐛 Troubleshooting

### Bot Not Responding
- Check if bot process is running: `ps aux | grep bot.py`
- Check logs: `tail /home/MASTERMINDKRISH/telegram_bot.log`
- Restart bot: `python3.10 bot.py`

### Email Not Sending
- Verify Gmail App Password is correct
- Check Gmail 2-Step Verification is enabled
- Check logs for SMTP error details

### File Upload Issues
- Ensure `/tmp/` directory is writable
- Check file size limits (20MB max)
- Verify file permissions

## 🔒 Security

- ✅ Environment variables stored in `.env` file
- ✅ Gmail App Password (not regular password)
- ✅ Temporary files automatically cleaned up
- ✅ Detailed logging for debugging

## 📞 Support

Check the logs first:
```bash
tail -20 /home/MASTERMINDKRISH/telegram_bot.log
```

The logs show detailed information about each step of the email sending process.