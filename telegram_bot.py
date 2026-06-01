# telegram_bot.py - SID Telegram Bot (CHAOS + PURE CARE MODE)
import os
import logging
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, time
from collections import defaultdict

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from dotenv import load_dotenv
import pytz

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
# AUTO GREETING SYSTEM (AI-Generated - NO HARDCODING)
# ============================================================

TIMEZONE = pytz.timezone("Asia/Kolkata")
greeted_today = set()

async def send_dynamic_greeting(bot, greeting_type):
    """Send AI-generated greeting to all users - NO HARDCODING"""
    all_users = list(sid_agent._sessions.keys())
    
    if not all_users:
        print("⚠️ No users found")
        return
    
    for user_id in all_users:
        if user_id in greeted_today:
            continue
        
        try:
            # Get user's mode (chaos or care)
            mode = user_modes.get(user_id, "chaos")
            
            # Get user's recent chat history (last 3 exchanges)
            user_history = sid_agent._sessions.get(user_id, [])
            recent_msgs = []
            for msg in user_history[-6:]:  # Last 3 exchanges
                recent_msgs.append(f"{msg['role']}: {msg['content']}")
            history_text = "\n".join(recent_msgs) if recent_msgs else "New user, no history yet."
            
            # Let SID generate a personalized greeting
            if greeting_type == "morning":
                prompt = f"Generate a sarcastic GOOD MORNING message for this user. Their mode is {mode}. Their recent chat: {history_text[:200]}. Be savage but loving. 2-3 lines with emojis. Never say 'slipper shot' as words, use 🩴 emoji."
            else:
                prompt = f"Generate a sarcastic GOOD NIGHT message for this user. Their mode is {mode}. Their recent chat: {history_text[:200]}. Be funny, roast them gently, wish them good night. 2-3 lines with emojis. Never say 'slipper shot' as words, use 🩴 emoji."
            
            # Use SID's AI to generate the greeting
            greeting = sid_agent.chat(user_id, prompt, mode)
            
            # Clean up the greeting
            greeting = greeting.replace("SID:", "").strip()
            
            if greeting_type == "morning":
                await bot.send_message(chat_id=user_id, text=f"🌅 *GOOD MORNING*\n\n{greeting}", parse_mode='Markdown')
            else:
                await bot.send_message(chat_id=user_id, text=f"🌙 *GOOD NIGHT*\n\n{greeting}", parse_mode='Markdown')
            
            greeted_today.add(user_id)
            print(f"✅ {greeting_type} AI greeting sent to {user_id}")
            await asyncio.sleep(1)  # Rate limit to avoid blocking
        except Exception as e:
            print(f"❌ Failed to send to {user_id}: {e}")

async def greeting_scheduler():
    """Background task that sends AI-generated greetings at 7:00 AM and 12:00 AM"""
    print("⏰ AI Greeting scheduler started (7:00 AM & 12:00 AM IST)")
    morning_sent = False
    night_sent = False
    
    while True:
        now = datetime.now(TIMEZONE)
        current_time = now.time()
        
        # Morning: 7:00 AM - 7:05 AM
        if time(7, 0) <= current_time <= time(7, 5):
            if not morning_sent and hasattr(greeting_scheduler, 'bot'):
                print(f"🌅 Sending AI-generated morning greetings at {current_time}...")
                await send_dynamic_greeting(greeting_scheduler.bot, "morning")
                morning_sent = True
        
        # Night: 12:00 AM - 12:05 AM
        if time(0, 0) <= current_time <= time(0, 5):
            if not night_sent and hasattr(greeting_scheduler, 'bot'):
                print(f"🌙 Sending AI-generated night greetings at {current_time}...")
                await send_dynamic_greeting(greeting_scheduler.bot, "night")
                night_sent = True
        
        # Reset flags after time window passes
        if current_time > time(7, 10):
            morning_sent = False
        if current_time > time(0, 10):
            night_sent = False
            greeted_today.clear()
            print("🔄 Reset greeting flags for new day")
        
        await asyncio.sleep(30)  # Check every 30 seconds

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
    total_users = len(sid_agent._sessions.keys())
    total_msgs = sum(len(v) for v in sid_agent._sessions.values())
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

    # Start AI greeting scheduler
    greeting_scheduler.bot = app.bot
    loop = asyncio.get_event_loop()
    loop.create_task(greeting_scheduler())
    print("\n✅ AI Greeting Scheduler Started!")
    print("⏰ Morning: 7:00 AM IST | Night: 12:00 AM IST")
    print("✨ Greetings are AI-generated uniquely for each user")

    print("\n✅ Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()