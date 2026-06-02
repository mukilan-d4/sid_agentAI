# telegram_bot.py - SID Telegram Bot (CHAOS + PURE CARE MODE)
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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

CARE_WELCOME = """
🤗 *CARE MODE ACTIVATED* 🤗

No sarcasm. No jokes. Just pure support.
I'm here to listen and help.

Type /chaos to go back to savage mode 🔥
"""

CHAOS_WELCOME = """
🔥 *CHAOS MODE ACTIVATED* 🔥

Savage roasts. Dark humor. No mercy.
Ready to get destroyed? 💀

Type /care for support mode 🤗
"""

# ============================================================
# HEALTH CHECK SERVER (Required for Render)
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run_health_server():
    ports = [int(os.getenv("PORT", 10000)), 8080, 8000]
    for port in ports:
        try:
            server = HTTPServer(("0.0.0.0", port), HealthHandler)
            print(f"✅ Health server running on port {port}")
            server.serve_forever()
            break
        except OSError:
            print(f"⚠️ Port {port} in use, trying next...")
            continue

health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()
print("✅ Health server thread started")

# ============================================================
# BOT COMMANDS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT, parse_mode='Markdown')

async def chaos_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_modes[user_id] = "chaos"
    await update.message.reply_text(CHAOS_WELCOME, parse_mode='Markdown')

async def care_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_modes[user_id] = "care"
    await update.message.reply_text(CARE_WELCOME, parse_mode='Markdown')

async def check_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    mode = user_modes[user_id]
    if mode == "chaos":
        await update.message.reply_text("🔥 *CHAOS MODE* - Savage roasts active 🔥", parse_mode='Markdown')
    else:
        await update.message.reply_text("🤗 *CARE MODE* - Pure support active 🤗", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("🤖 Talk to me in private chat for best experience!")
        return

    user_id = str(update.effective_user.id)
    user_message = update.message.text

    now = datetime.now()
    if user_id in user_last_message:
        time_diff = (now - user_last_message[user_id]).total_seconds()
        if time_diff < 1:
            await update.message.reply_text("Slow down... 🔥")
            return

    user_last_message[user_id] = now
    await update.message.chat.send_action(action="typing")

    try:
        mode = user_modes[user_id]
        response = sid_agent.chat(user_id, user_message, mode)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Something went wrong. Try again. 💀")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("Error occurred. Try again. 💀")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    mode = user_modes[user_id]
    session_count = len(sid_agent._sessions.get(user_id, [])) // 2
    stats_text = f"""
📊 *Your Stats*

Mode: {mode.upper()}
Messages: {session_count}
Status: Active 🔥

Keep talking - I remember everything!
    """
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def adminstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin stats - total users and messages"""
    total_users = len(sid_agent.memory.memories)
    total_msgs = sum(len(v) for v in sid_agent.memory.memories.values())
    await update.message.reply_text(
        f"👥 Total Users: {total_users}\n"
        f"💬 Total Messages: {total_msgs}\n"
        f"🔥 Active Sessions: {len(sid_agent._sessions)}"
    )

# ============================================================
# MAIN FUNCTION
# ============================================================

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found!")
        return

    if not config.GROQ_API_KEY:
        print("❌ GROQ_API_KEY not found!")
        return

    print("=" * 50)
    print("🤖 SID TELEGRAM BOT STARTING...")
    print("=" * 50)

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chaos", chaos_mode))
    app.add_handler(CommandHandler("care", care_mode))
    app.add_handler(CommandHandler("mode", check_mode))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("adminstats", adminstats))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_message
    ))

    app.add_error_handler(error_handler)

    print("\n✅ Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main() 