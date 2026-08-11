import os
import uuid
import sqlite3
from dotenv import load_dotenv
import telebot
from telebot import types

from converter import extract_and_format_custom_emojis, generate_code_snippet

# Environment variables load
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in .env file!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Temp directory verify/create
os.makedirs("temp", exist_ok=True)

# Cache for temporarily storing generated HTML snippets
CACHE = {}

# --- Database Setup ---
DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def register_user(user: types.User):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (user.id, user.username, user.first_name))
    conn.commit()
    conn.close()

def get_total_users() -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count


# --- Handlers ---

@bot.message_handler(commands=['start'])
def start_handler(message: types.Message):
    register_user(message.from_user)
    welcome_msg = (
        "👋 <b>Welcome to Custom Emoji Code Generator Bot!</b>\n\n"
        "Send or forward any message containing Telegram Premium custom emojis "
        "(Text, Photo, Video, Animation, or Document with caption) to get instant copyable code snippets."
    )
    bot.reply_to(message, welcome_msg)


@bot.message_handler(commands=['stats'])
def stats_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total_users = get_total_users()
    bot.reply_to(message, f"📊 <b>Bot Statistics</b>\n\nTotal Users: <code>{total_users}</code>")


@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'animation'])
def emoji_detector_handler(message: types.Message):
    register_user(message.from_user)

    # Determine input text & entities based on message type
    if message.content_type == 'text':
        text = message.text
        entities = message.entities
    else:
        text = message.caption
        entities = message.caption_entities

    if not text or not entities:
        bot.reply_to(message, "⚠️ No custom emojis detected. Send a message containing Telegram Premium custom emojis.")
        return

    html_text, has_custom_emoji = extract_and_format_custom_emojis(text, entities)

    if not has_custom_emoji:
        bot.reply_to(message, "⚠️ No custom emojis detected in this message.")
        return

    # Cache result temporarily with a short UUID
    cache_id = str(uuid.uuid4())[:8]
    CACHE[cache_id] = html_text

    # Build 4 format buttons
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_php = types.InlineKeyboardButton("PHP", callback_data=f"fmt:php:{cache_id}")
    btn_python = types.InlineKeyboardButton("Python", callback_data=f"fmt:python:{cache_id}")
    btn_md = types.InlineKeyboardButton("Markdown", callback_data=f"fmt:markdown:{cache_id}")
    btn_aiogram = types.InlineKeyboardButton("aiogram", callback_data=f"fmt:aiogram:{cache_id}")
    markup.add(btn_php, btn_python, btn_md, btn_aiogram)

    response = (
        "✅ <b>Custom Emojis Detected!</b>\n\n"
        "Select your preferred language/framework code format below:"
    )
    bot.reply_to(message, response, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('fmt:'))
def callback_format_handler(call: types.CallbackQuery):
    try:
        _, format_type, cache_id = call.data.split(":")
        
        html_text = CACHE.get(cache_id)
        if not html_text:
            bot.answer_callback_query(call.id, "❌ Session expired! Please resend your message.", show_alert=True)
            return

        code_snippet = generate_code_snippet(html_text, format_type)
        
        bot.answer_callback_query(call.id)
        
        bot.send_message(
            chat_id=call.message.chat.id,
            text=f"<code>{format_type.upper()} Code Snippet:</code>\n\n{code_snippet}",
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}", show_alert=True)


if __name__ == '__main__':
    init_db()
    print("🤖 Bot started successfully...")
    bot.infinity_polling(skip_pending=True)