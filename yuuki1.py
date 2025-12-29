import os
import random
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from tinydb import TinyDB, Query

# ================= CONFIG =================
BOT_TOKEN = os.getenv("YOUR_BOT_TOKEN")  # Railway env
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

OWNER_IDS = [5773908061]
BOT_NAME_DISPLAY = "˹ 𝐄𝐥𝐢𝐭𝐞 ✘ 𝐇ᴏꜱᴛᴇʀ ˼"
SUPPORT_LINK = "https://t.me/team_bright_lightX"
CHANNEL_LINK = "https://t.me/+dsCkYEVHJBRiMjI9"

# Persistent DB
DB_PLAYERS = TinyDB("users.json")

# Sticker and Riddles
ELITE_STICKERS = [
    "CAACAgIAAxkBAAEBGZJhV6Hx6ZpQo5Vh1gZr6K9p0bcQbgACfwIAAnuXhUh2C0xV1h6sPiQE",
    "CAACAgIAAxkBAAEBGZNhV6I6O8f02fsTQ8VvMIGwD9l0ZwACGgIAAnuXhUhJ9UfiwJ6HHiQE"
]

RIDDLES = [
    ("What has keys but can't open locks?", "keyboard"),
    ("I speak without a mouth and hear without ears. What am I?", "echo"),
    ("What gets wetter the more it dries?", "towel")
]

# ================= STATE =================
group_message_count = {}
math_interval = {}
math_level = {}
math_answers = {}
user_points = {}

# ================= UI =================
START_TEXT = f"""
[🌀 LOGO 🌀]

┌────── ɪɴғᴏʀᴍᴀᴛɪᴏɴ ★
┆◍ ʜᴇʏ, ɪ ᴀᴍ : {BOT_NAME_DISPLAY}
┆● ɴɪᴄᴇ ᴛᴏ ᴍᴇᴇᴛ ʏᴏᴜ !
└─────────────────────•
❖ ᴀ ᴛᴀʟᴋɪɴɢ + ᴍɪɴɪ ɢᴀᴍᴇs ʙᴏᴛ
❖ ᴍᴀᴅᴇ ғᴏʀ ғᴜɴ & ɪɴᴛᴇʀᴀᴄᴛɪᴏɴ
•─────────────────────•
❖ ʙʏ : <a href='https://t.me/RJVTAX'>RJ</a>
"""

HELP_TEXT = """
ʜᴇʟᴘ ᴍᴇɴᴜ 🎯
/start - Start Bot
/help - Open Help
/about - About Bot
/dice - Roll a Dice
/changetime <num> - Owner Only
/level <easy|medium|hard|extreme> - Owner Only
/top - Top Players
"""

ABOUT_TEXT = f"""
ᴀʙᴏᴜᴛ ʙᴏᴛ 🌙
Made for chatting, mini-games & math fun.
Powered by Groq API & Python
"""

# ================= KEYBOARDS =================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 ᴍɪɴɪ ɢᴀᴍᴇs 🎮", callback_data="games")],
        [InlineKeyboardButton("📜 ɢᴜɪᴅᴇ", callback_data="help"),
         InlineKeyboardButton("🎶 ᴀʙᴏᴜᴛ", callback_data="about")],
        [InlineKeyboardButton("⚡ ᴜᴘᴅᴀᴛᴇs", url=CHANNEL_LINK),
         InlineKeyboardButton("🌨️ sᴜᴘᴘᴏʀᴛ", url=SUPPORT_LINK)]
    ])

def games_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 ᴅɪᴄᴇ", callback_data="dice")],
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back")]
    ])

# ================= GROQ TALK =================
async def elite_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_msg = update.message.text or ""
    chat_id = update.effective_chat.id
    try:
        is_reply_to_bot = (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user.id == context.bot.id
        )
    except: is_reply_to_bot = False

    if "elitexhoster" not in user_msg.lower() and not is_reply_to_bot:
        return

    if "riddle" in user_msg.lower():
        q = random.choice(RIDDLES)
        await update.message.reply_text(f"Riddle 🤨: {q[0]}")
        return

    if "bruh" in user_msg.lower():
        await update.message.reply_text("Mera owner @RJVTAX hai 😎⚡ kya hua?")
        return

    if "history" not in context.chat_data:
        context.chat_data["history"] = []

    context.chat_data["history"].append({"role": "user", "content": user_msg})
    context.chat_data["history"] = context.chat_data["history"][-10:]

    # Original prompt restored
    payload = {
        "model": "moonshotai/kimi-k2-instruct-0905",
        "messages": [
            {"role": "system", "content": (
                "Your name is Elitexhoster who chats on telegram like a real boy. "
                "Don't overreact, don't be dramatic. "
                "Always reply in hinglish. "
                "If someone specially asks about your owner, reply @RJVTAX. "
                "Maximum words: 20."
            )}
        ] + context.chat_data["history"]
    }

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    for attempt in range(3):
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            bot_reply = res.json()["choices"][0]["message"]["content"]
            break
        except:
            bot_reply = "Lag aa gaya 😪"

    context.chat_data["history"].append({"role": "assistant", "content": bot_reply})
    context.chat_data["history"] = context.chat_data["history"][-10:]

    if random.randint(1,7) == 4:
        await update.message.reply_sticker(random.choice(ELITE_STICKERS))

    await update.message.reply_text(bot_reply)

# ================= MINI-GAMES =================
async def dice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    roll = random.randint(1,6)
    await update.message.reply_text(f"🎲 You rolled: {roll}")

# ================= MATH TRACKER =================
def generate_math(level):
    if level=="easy": a,b=random.randint(1,10),random.randint(1,10); return f"{a}+{b}",a+b
    if level=="medium": a,b=random.randint(10,50),random.randint(1,20); return f"{a}×{b}",a*b
    if level=="hard": a,b=random.randint(50,100),random.randint(10,30); return f"{a}÷{b}",round(a/b,2)
    if level=="extreme": a=random.randint(5,12); return f"{a}²+{a}",a*a+a

async def group_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.message.from_user.first_name
    group_message_count[chat_id] = group_message_count.get(chat_id,0)+1

    if chat_id in math_interval:
        if group_message_count[chat_id] % math_interval[chat_id] == 0:
            lvl = math_level.get(chat_id,"easy")
            q,a = generate_math(lvl)
            math_answers[chat_id] = a
            await update.message.reply_text(f"🧠 Math ({lvl}): {q}")

    if chat_id in math_answers:
        try:
            if float(update.message.text.strip())==math_answers[chat_id]:
                pts=random.randint(1,80)
                user_points[user] = user_points.get(user,0)+pts
                await update.message.reply_text(f"✅ Correct! +{pts} pts")
                del math_answers[chat_id]
        except: pass

# ================= OWNER COMMANDS =================
async def changetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS: return
    count = int(context.args[0])
    math_interval[update.effective_chat.id] = count
    await update.message.reply_text(f"⏱ Math every {count} messages")

async def level_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS: return
    lvl = context.args[0].lower()
    math_level[update.effective_chat.id] = lvl
    await update.message.reply_text(f"🧠 Math level set: {lvl}")

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_points: await update.message.reply_text("No points yet!"); return
    top = sorted(user_points.items(), key=lambda x:x[1], reverse=True)
    msg = "🏆 Top Players:\n" + "\n".join(f"{i+1}. {u} - {p} pts" for i,(u,p) in enumerate(top[:10]))
    await update.message.reply_text(msg)

# ================= CALLBACKS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data=="games": await q.message.edit_text("🎮 Mini Games",reply_markup=games_keyboard())
    elif q.data=="dice": await q.message.reply_text(f"🎲 You rolled {random.randint(1,6)}")
    elif q.data=="back": await q.message.edit_text(START_TEXT, reply_markup=main_keyboard())
    elif q.data=="help": await q.message.edit_text(HELP_TEXT, reply_markup=main_keyboard())
    elif q.data=="about": await q.message.edit_text(ABOUT_TEXT, reply_markup=main_keyboard())

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text(START_TEXT, reply_markup=main_keyboard())))
app.add_handler(CommandHandler("help", lambda u,c: u.message.reply_text(HELP_TEXT)))
app.add_handler(CommandHandler("about", lambda u,c: u.message.reply_text(ABOUT_TEXT)))
app.add_handler(CommandHandler("dice", dice_cmd))
app.add_handler(CommandHandler("changetime", changetime))
app.add_handler(CommandHandler("level", level_cmd))
app.add_handler(CommandHandler("top", top_cmd))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, elite_chat))
app.add_handler(MessageHandler(filters.ALL, group_tracker))

print("🤖 EliteXHoster Bot running...")
app.run_polling()