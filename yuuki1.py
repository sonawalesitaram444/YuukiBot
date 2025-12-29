import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from groq import Groq

# ================= CONFIG =================
TOKEN = os.getenv("YOUR_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = 8370400225  # change to your Telegram ID

BOTNAME = "˹ 𝐄𝐥𝐢𝐭𝐞 ✘ 𝐇ᴏꜱᴛᴇʀ ˼"
DEVELOPER_USERNAME = "RJVTAX"
CHANNEL = "@YUUKIUPDATES"

client = Groq(api_key=GROQ_API_KEY)

# ================= STATE =================
group_message_count = {}
math_interval = {}
math_level = {}
math_answers = {}
user_points = {}

# ================= TEXT =================
START_TEXT = f"""
[🌀 LOGO 🌀]

┌────── ˹ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ˼ ⏤͟͟͞͞ ★
┆◍ ʜᴇʏ, ɪ ᴀᴍ : {BOTNAME}
┆● ɴɪᴄᴇ ᴛᴏ ᴍᴇᴇᴛ ʏᴏᴜ !
└─────────────────────•
❖ ᴀ ᴛᴀʟᴋɪɴɢ + ᴍɪɴɪ ɢᴀᴍᴇs ʙᴏᴛ
❖ ᴍᴀᴅᴇ ғᴏʀ ғᴜɴ & ɪɴᴛᴇʀᴀᴄᴛɪᴏɴ
•─────────────────────•
❖ ʙʏ : <a href="https://t.me/{DEVELOPER_USERNAME}">『𓋹』 🇷 🇯 『〔☤〕』</a>
"""

ABOUT_TEXT = f"""
ᴀʙᴏᴜᴛ ᴛʜɪꜱ ʙᴏᴛ 🌙

ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴛᴏ ʙᴏᴏsᴛ ʏᴏᴜʀ ɪᴅ ᴡɪᴛʜ ʙᴇᴀᴜᴛɪғᴜʟ ᴀɴɪᴍᴀᴛɪᴏɴ.

◌ ʟᴀɴɢᴜᴀɢᴇ : ᴘʏᴛʜᴏɴ
◌ ᴘᴏᴡᴇʀᴇᴅ ʙʏ : {CHANNEL}
◌ ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href="https://t.me/{DEVELOPER_USERNAME}">RJ</a>
"""

HELP_TEXT = """
ʜᴇʟᴘ ᴍᴇɴᴜ ⚙️
➤ /start - ꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ
➤ /help - ᴏᴘᴇɴ ʜᴇʟᴘ ᴍᴇɴᴜ
➤ /about - ᴀʙᴏᴜᴛ ᴛʜᴇ ʙᴏᴛ
➤ /dice - ʀᴏʟʟ ᴀ ᴅɪᴄᴇ
➤ /changetime <num> - ᴏᴡɴᴇʀ ᴏɴʟʏ
➤ /level <easy|medium|hard|extreme> - ᴏᴡɴᴇʀ ᴏɴʟʏ
➤ /top - ᴛᴏᴘ ᴘʟᴀʏᴇʀs
"""

# ================= KEYBOARDS =================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 ᴍɪɴɪ ɢᴀᴍᴇs 🎮", callback_data="games")],
        [
            InlineKeyboardButton("📜 ɢᴜɪᴅᴇ", callback_data="help"),
            InlineKeyboardButton("🎶 ᴀʙᴏᴜᴛ", callback_data="about")
        ],
        [
            InlineKeyboardButton("⚡ ᴜᴘᴅᴀᴛᴇs", url=f"https://t.me/{CHANNEL[1:]}"),
            InlineKeyboardButton("🌨️ sᴜᴘᴘᴏʀᴛ", url="https://t.me/team_bright_lightX")
        ],
        [InlineKeyboardButton("🌿 ᴅᴇᴠᴇʟᴏᴘᴇʀ 🌿", url=f"https://t.me/{DEVELOPER_USERNAME}")]
    ])

def games_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 ᴅɪᴄᴇ", callback_data="dice")],
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back")]
    ])

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(START_TEXT, reply_markup=main_keyboard(), parse_mode="HTML")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)

async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ABOUT_TEXT, parse_mode="HTML")

async def dice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    roll = random.randint(1, 6)
    await update.message.reply_text(f"🎲 ʏᴏᴜ ʀᴏʟʟᴇᴅ : **{roll}**")

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_points:
        await update.message.reply_text("No points yet!")
        return
    top = sorted(user_points.items(), key=lambda x: x[1], reverse=True)
    msg = "🏆 ᴛᴏᴘ ᴘʟᴀʏᴇʀs:\n"
    for i, (user, pts) in enumerate(top[:10], start=1):
        msg += f"{i}. {user} - {pts} pts\n"
    await update.message.reply_text(msg)

# ================= BUTTON CALLBACKS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "games":
        await q.message.edit_text("🎮 ᴍɪɴɪ ɢᴀᴍᴇs", reply_markup=games_keyboard())
    elif q.data == "dice":
        await q.message.reply_text(f"🎲 ʏᴏᴜ ʀᴏʟʟᴇᴅ : {random.randint(1,6)}")
    elif q.data == "back":
        await q.message.edit_text(START_TEXT, reply_markup=main_keyboard(), parse_mode="HTML")
    elif q.data == "help":
        await q.message.edit_text(HELP_TEXT, reply_markup=main_keyboard())
    elif q.data == "about":
        await q.message.edit_text(ABOUT_TEXT, reply_markup=main_keyboard())

# ================= GROQ TALK =================
async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private" or BOTNAME.lower() in update.message.text.lower():
        try:
            res = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": update.message.text}]
            )
            await update.message.reply_text(res.choices[0].message.content)
        except Exception:
            pass

# ================= GROUP MATH =================
def generate_math(level):
    if level == "easy":
        a,b = random.randint(1,10), random.randint(1,10)
        return f"{a} + {b}", a+b
    if level == "medium":
        a,b = random.randint(10,50), random.randint(1,20)
        return f"{a} × {b}", a*b
    if level == "hard":
        a,b = random.randint(50,100), random.randint(10,30)
        return f"{a} ÷ {b}", round(a/b,2)
    if level == "extreme":
        a = random.randint(5,12)
        return f"{a}² + {a}", a*a + a

async def group_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user = update.message.from_user.first_name
    group_message_count[chat_id] = group_message_count.get(chat_id,0)+1

    # check math interval
    if chat_id in math_interval:
        if group_message_count[chat_id] % math_interval[chat_id] == 0:
            lvl = math_level.get(chat_id,"easy")
            q,a = generate_math(lvl)
            math_answers[chat_id] = a
            await update.message.reply_text(f"🧠 ᴍᴀᴛʜ ᴛɪᴍᴇ ({lvl})\n❓ {q}")

    # check if message is answer
    if chat_id in math_answers:
        try:
            if float(update.message.text.strip()) == math_answers[chat_id]:
                pts = random.randint(1,80)
                user_points[user] = user_points.get(user,0)+pts
                await update.message.reply_text(f"✅ ᴄᴏʀʀᴇᴄᴛ! +{pts} pts")
                del math_answers[chat_id]
        except:
            pass

# ================= OWNER =================
async def changetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    count = int(context.args[0])
    math_interval[update.message.chat_id] = count
    await update.message.reply_text(f"⏱ ᴍᴀᴛʜ ᴇᴠᴇʀʏ {count} ᴍᴇssᴀɢᴇs")

async def level_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    lvl = context.args[0].lower()
    math_level[update.message.chat_id] = lvl
    await update.message.reply_text(f"🧠 ᴍᴀᴛʜ ʟᴇᴠᴇʟ sᴇᴛ : {lvl}")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("about", about_cmd))
app.add_handler(CommandHandler("dice", dice_cmd))
app.add_handler(CommandHandler("changetime", changetime))
app.add_handler(CommandHandler("level", level_cmd))
app.add_handler(CommandHandler("top", top_cmd))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, talk))
app.add_handler(MessageHandler(filters.ALL, group_tracker))

print("🤖 Bot running...")
app.run_polling()