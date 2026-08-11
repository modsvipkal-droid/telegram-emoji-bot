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

# Start command Video Link / Telegram File ID
START_VIDEO = "https://t.me/postkalmoda/8"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in .env file!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Ensure pyTelegramBotAPI always transmits 'style' and 'icon_custom_emoji_id' in JSON payload
orig_to_dict = types.InlineKeyboardButton.to_dict
def patched_to_dict(self):
    d = orig_to_dict(self)
    if hasattr(self, 'style') and self.style:
        d['style'] = self.style
    if hasattr(self, 'icon_custom_emoji_id') and self.icon_custom_emoji_id:
        d['icon_custom_emoji_id'] = self.icon_custom_emoji_id
    return d
types.InlineKeyboardButton.to_dict = patched_to_dict

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
    
    # Premium Emoji Welcome Message (Caption text)
    welcome_msg = (
        '<tg-emoji emoji-id="4963233485356533176">👋</tg-emoji><tg-emoji emoji-id="6053229479944264545">✨</tg-emoji> Welcome to EmojiPackfindBot!\n\n'
        '<tg-emoji emoji-id="6053400522721859262">🗑</tg-emoji> Convert Telegram Premium Custom Emojis into clean, copyable code instantly. <tg-emoji emoji-id="6053229479944264545">✨</tg-emoji>\n\n'
        '<tg-emoji emoji-id="6052991826518873591">📌</tg-emoji> How to use: <tg-emoji emoji-id="6052964261418769099">💬</tg-emoji>\n'
        '<tg-emoji emoji-id="6053193097276298985">✉️</tg-emoji> Send or forward any message containing custom emojis — <tg-emoji emoji-id="6053193097276298985">✉️</tg-emoji> Text • <tg-emoji emoji-id="6053142399482339205">🔔</tg-emoji> Photo • <tg-emoji emoji-id="6023660287968678279">🎬</tg-emoji> Video • <tg-emoji emoji-id="6311831672744580735">💥</tg-emoji> Animation • <tg-emoji emoji-id="5258477770735885832">📄</tg-emoji> Document\n\n'
        '<tg-emoji emoji-id="6312317205912492287">⚡</tg-emoji> Detect → Convert → Copy <tg-emoji emoji-id="5404697694650262981">😣</tg-emoji>\n'
        '<tg-emoji emoji-id="5226639745106330551">🧠</tg-emoji> Get your code instantly!<tg-emoji emoji-id="6312147825287239190">‼️</tg-emoji>\n\n'
        '<tg-emoji emoji-id="4994496741282677708">🖥</tg-emoji> Developer: @kal_mods <tg-emoji emoji-id="6338899694810307622">🗣️</tg-emoji>'
    )
    
    try:
        # Send video with welcome message in Caption
        bot.send_video(
            chat_id=message.chat.id,
            video=START_VIDEO,
            caption=welcome_msg,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Error sending video, falling back to text: {e}")
        bot.send_message(
            chat_id=message.chat.id,
            text=welcome_msg,
            parse_mode="HTML"
        )


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

    # Agar text ya entities nahi hain, silently ignore karo
    if not text or not entities:
        return

    html_text, has_custom_emoji = extract_and_format_custom_emojis(text, entities)

    # Agar message mein custom emoji nahi hai, silently ignore karo
    if not has_custom_emoji:
        return

    # Cache result temporarily with a short UUID
    cache_id = str(uuid.uuid4())[:8]
    CACHE[cache_id] = html_text

    # Buttons with Premium Custom Emojis & Green Style
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_php = types.InlineKeyboardButton(
        "PHP", 
        callback_data=f"fmt:php:{cache_id}", 
        style="success", 
        icon_custom_emoji_id="5774138454896022007"
    )
    btn_python = types.InlineKeyboardButton(
        "Python", 
        callback_data=f"fmt:python:{cache_id}", 
        style="success", 
        icon_custom_emoji_id="4985626654563894116"
    )
    btn_md = types.InlineKeyboardButton(
        "Markdown", 
        callback_data=f"fmt:markdown:{cache_id}", 
        style="success", 
        icon_custom_emoji_id="5893382531037794941"
    )
    btn_aiogram = types.InlineKeyboardButton(
        "aiogram", 
        callback_data=f"fmt:aiogram:{cache_id}", 
        style="success", 
        icon_custom_emoji_id="5893494861612455015"
    )
    
    markup.add(btn_php, btn_python, btn_md, btn_aiogram)

    # Premium Custom Emoji Response Message
    response = (
        '<tg-emoji emoji-id="6052973985224728368">💥</tg-emoji> <b>Custom Emojis Detected!</b> <tg-emoji emoji-id="6053030296540946080">🎉</tg-emoji>\n\n'
        '<tg-emoji emoji-id="6052991826518873591">📌</tg-emoji> Select your preferred language/framework to generate the code. <tg-emoji emoji-id="6339201691140758295">🛍</tg-emoji>\n\n'
        '━━━━━━━━━━━━━━━━━━\n'
        '<tg-emoji emoji-id="6053202116707622090">✔️</tg-emoji> Choose an option below <tg-emoji emoji-id="6338899694810307622">🗣️</tg-emoji>'
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
        
        # Headers with Custom Emojis for each format
        headers = {
            "markdown": (
                '<tg-emoji emoji-id="5256131095094652290">🎯</tg-emoji> Code is Ready! <tg-emoji emoji-id="6181329095750589575">✨</tg-emoji>\n\n'
                '<tg-emoji emoji-id="6314482200142157650">🤖</tg-emoji> MARKDOWN  • Generated Successfully <tg-emoji emoji-id="6269163801178804220">✅</tg-emoji>\n'
                '<tg-emoji emoji-id="5197269100878907942">✍️</tg-emoji> Copy &amp; Use <tg-emoji emoji-id="6053202116707622090">✔️</tg-emoji>'
            ),
            "python": (
                '<tg-emoji emoji-id="5256131095094652290">🎯</tg-emoji> Code is Ready! <tg-emoji emoji-id="6181329095750589575">✨</tg-emoji>\n\n'
                '<tg-emoji emoji-id="6314482200142157650">🤖</tg-emoji> PYTHON • Generated Successfully <tg-emoji emoji-id="6269163801178804220">✅</tg-emoji>\n'
                '<tg-emoji emoji-id="5197269100878907942">✍️</tg-emoji> Copy &amp; Use <tg-emoji emoji-id="6053202116707622090">✔️</tg-emoji>'
            ),
            "php": (
                '<tg-emoji emoji-id="5256131095094652290">🎯</tg-emoji> Code is Ready! <tg-emoji emoji-id="6181329095750589575">✨</tg-emoji>\n\n'
                '<tg-emoji emoji-id="6314482200142157650">🤖</tg-emoji> PHP • Generated Successfully <tg-emoji emoji-id="6269163801178804220">✅</tg-emoji>\n'
                '<tg-emoji emoji-id="5197269100878907942">✍️</tg-emoji> Copy &amp; Use <tg-emoji emoji-id="6053202116707622090">✔️</tg-emoji>'
            ),
            "aiogram": (
                '<tg-emoji emoji-id="5256131095094652290">🎯</tg-emoji> Code is Ready! <tg-emoji emoji-id="6181329095750589575">✨</tg-emoji>\n\n'
                '<tg-emoji emoji-id="6314482200142157650">🤖</tg-emoji> AIOGRAM • Generated Successfully <tg-emoji emoji-id="6269163801178804220">✅</tg-emoji>\n'
                '<tg-emoji emoji-id="5197269100878907942">✍️</tg-emoji> Copy &amp; Use <tg-emoji emoji-id="6053202116707622090">✔️</tg-emoji>'
            )
        }
        
        header = headers.get(format_type, f"<b>{format_type.upper()} Code Snippet:</b>")
        full_message = f"{header}\n\n{code_snippet}"
        
        bot.send_message(
            chat_id=call.message.chat.id,
            text=full_message,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Error in callback: {e}")
        bot.answer_callback_query(call.id, f"Error: {str(e)}", show_alert=True)


if __name__ == '__main__':
    init_db()
    print("🤖 Bot started successfully...")
    bot.infinity_polling(skip_pending=True)
