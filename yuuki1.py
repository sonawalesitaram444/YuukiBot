import os
import random
import time
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# ---------------- CONFIG ----------------
TOKEN = "8520734510:AAFuqA-MlB59vfnI_zUQiGiRQKEJScaUyFs"
MONGO_URL = "mongodb+srv://sonawalesitaram444_db_user:xqAwRv0ZdKMI6dDa@anixgrabber.a2tdbiy.mongodb.net/?appName=anixgrabber"
GROQ_API_KEY = "GROQ_API_KEY"

client = MongoClient(MONGO_URL)
db = client["greed_island"]
players = db["players"]
cities = db["cities"]
quests = db["quests"]

# ---------------- FONT ----------------
font_map = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ',
    'f': 'ꜰ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ',
    'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ',
    'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ',
    'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ',
    'F': 'ꜰ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ',
    'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ',
    'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ',
    'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
    '0':'0','1':'1','2':'2','3':'3','4':'4','5':'5',
    '6':'6','7':'7','8':'8','9':'9',
    ' ':' '
}
def yuuki(text): return ''.join(font_map.get(c, c) for c in text)

# ---------------- HELPER ----------------
def init_player(user_id, username):
    if not players.find_one({"user_id": user_id}):
        players.insert_one({
            "user_id": user_id,
            "username": username,
            "hp": 100,
            "nen": 10,
            "strength": random.randint(100, 1000),
            "kills": 0,
            "alive": True,
            "location": "HxH World",
            "special_skill": "Ren Burst",
            "console": True,
            "book": [],
            "party": None,
            "cooldowns": {}
        })

async def groq_talk(prompt):
    url = "https://api.groq.com/v1/generate"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    data = {"prompt": prompt, "max_output_tokens": 100}
    res = requests.post(url, json=data, headers=headers).json()
    return res.get("text","I cannot answer that.")

# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_player(update.effective_user.id, update.effective_user.username)
    await update.message.reply_text(yuuki("ʜᴇʟʟᴏ ᴀɴᴅ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ɢʀᴇᴇᴅ ɪsʟᴀɴᴅ ʙᴏᴛ!"))

# ---------------- CONSOLE ----------------
async def console(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = players.find_one({"user_id": update.effective_user.id})
    if not user:
        await update.message.reply_text(yuuki("ᴘʟᴇᴀsᴇ ᴜsᴇ /start ғɪʀsᴛ"))
        return
    text = f"""🖥️ ᴄᴏɴsᴏʟᴇ
📍 ʟᴏᴄᴀᴛɪᴏɴ: {user['location']}
💖 ʜᴘ: {user['hp']}
🌀 ɴᴇɴ: {user['nen']}
💪 sᴛʀᴇɴɢᴛʜ: {user['strength']}
⚔️ ᴋɪʟʟs: {user['kills']}
✨ sᴘᴇᴄɪᴀʟ sᴋɪʟʟ: {user['special_skill']}
"""
    buttons = [
        [InlineKeyboardButton(yuuki("💥 Fɪɢʜᴛ"), callback_data="fight")],
        [InlineKeyboardButton(yuuki("🎯 Qᴜᴇsᴛ"), callback_data="quest")],
        [InlineKeyboardButton(yuuki("🗺️ Tʀᴀᴠᴇʟ"), callback_data="travel")],
        [InlineKeyboardButton(yuuki("💬 Tᴀʟᴋ"), callback_data="talk")]
    ]
    await update.message.reply_text(yuuki(text), reply_markup=InlineKeyboardMarkup(buttons))

# ---------------- FIGHT SYSTEM ----------------
async def fight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(yuuki("ғɪɢʜᴛ ᴄᴏᴍɪɴɢ sᴏᴏɴ... ʙᴜɪʟᴅɪɴɢ ʙᴀsɪᴄ ᴘᴠᴘ"))

# ---------------- QUEST SYSTEM ----------------
async def quest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    quest_list = ["ᴋɪʟʟ 5 ᴘʟᴀʏᴇʀs", "ʀᴏʙ 3 ᴘʟᴀʏᴇʀs", "ᴛʀᴀɪɴ ɴᴇɴ", "ᴄᴏʟʟᴇᴄᴛ ʀᴇᴡᴀʀᴅs"]
    buttons = [[InlineKeyboardButton(yuuki(q), callback_data=f"start_{i}")] for i,q in enumerate(quest_list)]
    await query.message.reply_text(yuuki("🎯 ʀᴀɴᴅᴏᴍ ǫᴜᴇsᴛs:"), reply_markup=InlineKeyboardMarkup(buttons))

# ---------------- TALKING SYSTEM ----------------
async def talk_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    answer = await groq_talk("Hello! Pretend you are Yuuki Bot.")
    await query.message.reply_text(yuuki(answer))

# ---------------- CALLBACK ----------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "fight": await fight_handler(update, context)
    elif data == "quest": await quest_handler(update, context)
    elif data == "talk": await talk_handler(update, context)
    elif data == "travel": await query.message.reply_text(yuuki("ʀᴀᴠᴇʟ sʏsᴛᴇᴍ ᴄᴏᴍɪɴɢ sᴏᴏɴ"))

# ---------------- MAIN ----------------
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("console", console))
app.add_handler(CallbackQueryHandler(button_callback))

print("ʏᴜᴜᴋɪ ɢʀᴇᴇᴅ ɪsʟᴀɴᴅ ʙᴏᴛ ʀᴜɴɴɪɴɢ...")
app.run_polling()