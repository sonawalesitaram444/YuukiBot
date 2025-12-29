import os
import random
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from groq import Groq

# ================= CONFIG =================
TOKEN = os.getenv("8160955111:AAH4rSihP8JQdt-AcXYGapebuuT2F-BglxA")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = 5773908061  # change if needed

BOTNAME = "˹ 𝐄𝐥𝐢𝐭𝐞 ✘ 𝐇ᴏꜱᴛᴇʀ ˼"
DEVELOPER_USERNAME = "RJVTAX"

client = Groq(api_key=GROQ_API_KEY)

# ================= STATE =================
group_message_count = {}
math_interval = {}
math_level = {}

# ================= TEXT =================
START_TEXT = f"""
┌────── ˹ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ˼ ⏤͟͟͞͞ ★
┆◍ ʜᴇʏ, ɪ ᴀᴍ : {BOTNAME}
┆● ɴɪᴄᴇ ᴛᴏ ᴍᴇᴇᴛ ʏᴏᴜ !
└─────────────────────•
❖ ᴀ ᴛᴀʟᴋɪɴɢ + ᴍɪɴɪ ɢᴀᴍᴇs ʙᴏᴛ
❖ ᴍᴀᴅᴇ ғᴏʀ ғᴜɴ & ɪɴᴛᴇʀᴀᴄᴛɪᴏɴ
•─────────────────────•
❖ ʙʏ : <a href="https://t.me/{DEVELOPER_USERNAME}">RJ</a>
"""

# ================= KEYBOARD =================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 ᴍɪɴɪ ɢᴀᴍᴇs 🎮", callback_data="games")],
        [InlineKeyboardButton("🌿 ᴅᴇᴠᴇʟᴏᴘᴇʀ 🌿", url=f"https://t.me/{DEVELOPER_USERNAME}")]
    ])

def games_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 ᴅɪᴄᴇ", callback_data="dice")],
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back")]
    ])

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        START_TEXT,
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

async def dice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    roll = random.randint(1, 6)
    await update.message.reply_text(f"🎲 ʏᴏᴜ ʀᴏʟʟᴇᴅ : **{roll}**")

# ================= BUTTONS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "games":
        await q.message.edit_text("🎮 ᴍɪɴɪ ɢᴀᴍᴇs", reply_markup=games_keyboard())
    elif q.data == "dice":
        await q.message.reply_text(f"🎲 ʏᴏᴜ ʀᴏʟʟᴇᴅ : {random.randint(1,6)}")
    elif q.data == "back":
        await q.message.edit_text(START_TEXT, reply_markup=main_keyboard(), parse_mode="HTML")

# ================= GROQ TALKING =================
async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private" or BOTNAME.lower() in update.message.text.lower():
        res = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": update.message.text}]
        )
        await update.message.reply_text(res.choices[0].message.content)

# ================= GROUP MATH =================
def generate_math(level):
    if level == "easy":
        a, b = random.randint(1,10), random.randint(1,10)
        return f"{a} + {b}", a+b
    if level == "medium":
        a, b = random.randint(10,50), random.randint(1,20)
        return f"{a} × {b}", a*b
    if level == "hard":
        a, b = random.randint(50,100), random.randint(10,30)
        return f"{a} ÷ {b}", round(a/b, 2)
    if level == "extreme":
        a = random.randint(5,12)
        return f"{a}² + {a}", a*a + a

async def group_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    group_message_count[chat_id] = group_message_count.get(chat_id, 0) + 1

    if chat_id in math_interval:
        if group_message_count[chat_id] % math_interval[chat_id] == 0:
            level = math_level.get(chat_id, "easy")
            q, ans = generate_math(level)
            await update.message.reply_text(f"🧠 ᴍᴀᴛʜ ᴛɪᴍᴇ ({level})\n❓ {q}")

# ================= OWNER COMMANDS =================
async def changetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    count = int(context.args[0])
    math_interval[update.message.chat_id] = count
    await update.message.reply_text(f"⏱ ᴍᴀᴛʜ ᴇᴠᴇʀʏ {count} ᴍᴇssᴀɢᴇs")

async def level_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    lvl = context.args[0]
    math_level[update.message.chat_id] = lvl
    await update.message.reply_text(f"🧠 ᴍᴀᴛʜ ʟᴇᴠᴇʟ sᴇᴛ : {lvl}")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("dice", dice_cmd))
app.add_handler(CommandHandler("changetime", changetime))
app.add_handler(CommandHandler("level", level_cmd))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, talk))
app.add_handler(MessageHandler(filters.ALL, group_tracker))

print("🤖 Bot running...")
app.run_polling()