# telegram_bot.py - SID Telegram Bot (CHAOS + PURE CARE MODE)
import os
import logging
from datetime import datetime
from collections import defaultdict

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from dotenv import load_dotenv

# Import your SID agent
from sid_agent import SIDAgent, config

load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize SID Agent
sid_agent = SIDAgent()

# Store user modes
user_modes = defaultdict(lambda: "chaos")

# Rate limiting
user_last_message = {}

# Welcome message
WELCOME_TEXT = """
🔥 *WELCOME TO SID - YOUR SAVAGE AI FRIEND* 🔥

I roast you, I mock you, I make you laugh.
No filter. No mercy. Pure entertainment.

*Commands:*
/chaos - Savage mode (default) 🔥
/care - Pure support mode 🤗
/mode - Check current mode
/start - Show this message

*Just talk to me.* I remember everything.
Ready to get roasted? 💀
"""

# Care mode welcome message
CARE_WELCOME = """
🤗 *CARE MODE ACTIVATED* 🤗

No sarcasm. No jokes. Just pure support.
I'm here to listen and help.

Type /chaos to go back to savage mode 🔥
"""

# Chaos mode welcome message
CHAOS_WELCOME = """
🔥 *CHAOS MODE ACTIVATED* 🔥

Savage roasts. Dark humor. No mercy.
Ready to get destroyed? 💀

Type /care for support mode 🤗
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text(WELCOME_TEXT, parse_mode='Markdown')

async def chaos_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch to chaos mode - savage roasts"""
    user_id = str(update.effective_user.id)
    user_modes[user_id] = "chaos"
    await update.message.reply_text(CHAOS_WELCOME, parse_mode='Markdown')

async def care_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch to care mode - pure support, no sarcasm"""
    user_id = str(update.effective_user.id)
    user_modes[user_id] = "care"
    await update.message.reply_text(CARE_WELCOME, parse_mode='Markdown')

async def check_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current mode"""
    user_id = str(update.effective_user.id)
    mode = user_modes[user_id]
    
    if mode == "chaos":
        await update.message.reply_text("🔥 *CHAOS MODE* - Savage roasts active 🔥", parse_mode='Markdown')
    else:
        await update.message.reply_text("🤗 *CARE MODE* - Pure support active 🤗", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages"""
    # Block group chats
    if update.effective_chat.type != "private":
        await update.message.reply_text("🤖 Talk to me in private chat for best experience!")
        return
    
    user_id = str(update.effective_user.id)
    user_message = update.message.text
    
    # Rate limiting (prevent spam)
    now = datetime.now()
    if user_id in user_last_message:
        time_diff = (now - user_last_message[user_id]).total_seconds()
        if time_diff < 1:
            await update.message.reply_text("Slow down... 🔥")
            return
    
    user_last_message[user_id] = now
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    try:
        # Get user's mode
        mode = user_modes[user_id]
        
        # Get response from SID
        response = sid_agent.chat(user_id, user_message, mode)
        
        # Send response
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Something went wrong. Try again. 💀")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("Error occurred. Try again. 💀")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user stats (optional feature)"""
    user_id = str(update.effective_user.id)
    mode = user_modes[user_id]
    
    # Get rough message count from sessions
    session_count = len(sid_agent._sessions.get(user_id, [])) // 2
    
    stats_text = f"""
📊 *Your Stats*

Mode: {mode.upper()}
Messages: {session_count}
Status: Active 🔥

Keep talking - I remember everything!
    """
    await update.message.reply_text(stats_text, parse_mode='Markdown')

def main():
    """Start the bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("=" * 50)
        print("❌ TELEGRAM_BOT_TOKEN not found!")
        print("=" * 50)
        print("\nCreate .env file with:")
        print("TELEGRAM_BOT_TOKEN=your_token_here")
        print("GROQ_API_KEY=your_key_here")
        print("\nGet token from @BotFather on Telegram")
        return
    
    if not config.GROQ_API_KEY:
        print("=" * 50)
        print("❌ GROQ_API_KEY not found!")
        print("=" * 50)
        print("\nAdd to .env file:")
        print("GROQ_API_KEY=your_groq_key_here")
        return
    
    print("=" * 50)
    print("🤖 SID TELEGRAM BOT STARTING...")
    print("=" * 50)
    print(f"🔥 CHAOS MODE: Savage roasts")
    print(f"🤗 CARE MODE: Pure support")
    print(f"📝 Logging: sid.log")
    print("=" * 50)
    
    # Create application
    app = Application.builder().token(token).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chaos", chaos_mode))
    app.add_handler(CommandHandler("care", care_mode))
    app.add_handler(CommandHandler("mode", check_mode))
    app.add_handler(CommandHandler("stats", stats))
    
    # Add message handler (only for private chats)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, 
        handle_message
    ))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Start the bot
    print("\n✅ Bot is running!")
    print("📱 Open Telegram and search for your bot")
    print("🛑 Press Ctrl+C to stop\n")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass

def run_health():
    HTTPServer(("0.0.0.0", int(os.getenv("PORT", 8080))), Handler).serve_forever()

threading.Thread(target=run_health, daemon=True).start()

if __name__ == "__main__":
    main()