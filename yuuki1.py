import os
import random
import time
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from tinydb import TinyDB, Query

# ================= CONFIG =================
BOT_TOKEN = os.getenv("YOUR_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

OWNER_IDS = [5773908061]
BOT_NAME_DISPLAY = "˹ 𝐄𝐥𝐢𝐭𝐞 ✘ 𝐇ᴏꜱᴛᴇʀ ˼"

SUPPORT_LINK = "https://t.me/team_bright_lightX"
CHANNEL_LINK = "https://t.me/+dsCkYEVHJBRiMjI9"

DB = TinyDB("users.json")

# ================= STATE =================
group_message_count = {}
math_interval = {}
math_level = {}
math_answers = {}
user_points = {}

# ================= SHOP =================
SHOP_ITEMS = {
    "teddy": {"emoji": "🧸", "price": 50},
    "rose": {"emoji": "🌹", "price": 30},
    "toy": {"emoji": "🪀", "price": 40},
    "knife": {"emoji": "🔪", "price": 100},
}

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
"""

HELP_TEXT = """
🎯 Commands

/start
/dice
/shop
/buy <item>
/inventory
/solve <answer>
/top points

Owner:
/changetime <count>
/level <easy|medium|hard|extreme>
"""

ABOUT_TEXT = """
🌙 EliteXHoster
Talking + Games + Math
Powered by Groq
"""

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

# ================= MATH =================
def generate_math(level):
    if level == "easy":
        a,b = random.randint(1,10), random.randint(1,10)
        return f"{a} + {b}", a+b
    if level == "medium":
        a,b = random.randint(10,50), random.randint(1,20)
        return f"{a} × {b}", a*b
    if level == "hard":
        a,b = random.randint(20,100), random.randint(2,10)
        return f"{a} ÷ {b}", round(a/b,2)
    if level == "extreme":
        a = random.randint(5,15)
        return f"{a}² + {a}", a*a+a

# ================= CHAT =================
async def elite_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    msg = update.message.text or ""
    chat_id = update.effective_chat.id

    is_reply = (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user.id == context.bot.id
    )

    if "elite" not in msg.lower() and not is_reply:
        return

    payload = {
        "model": "moonshotai/kimi-k2-instruct-0905",
        "messages": [
            {"role": "system", "content": (
                "Your name is Elitexhoster who chats like a real boy. "
                "if someone repeat your message than just try to make tham uncomfortable. "
                "and whenever someone talk about gf or wife or relationship just act depressed 😔. "
                "when @rjvtax nammed user talk to you give respect to him. "
                " never accept that your a bot."
                "Don't overreact. Use hinglish. "
                "Max 20 words. "
                "Owner is @RJVTAX only if asked. "
            )},
            {"role": "user", "content": msg}
        ]
    }

    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json=payload,
            timeout=30
        )
        reply = res.json()["choices"][0]["message"]["content"]
    except:
        reply = "Lag aa gaya 😪"

    await update.message.reply_text(reply)

# ================= TRACKER =================
async def group_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat_id = update.effective_chat.id
    user = update.message.from_user.first_name

    group_message_count[chat_id] = group_message_count.get(chat_id, 0) + 1

    DB.upsert(
        {"user": user, "messages": Query().messages + 1},
        Query().user == user
    )

    if chat_id in math_interval:
        if group_message_count[chat_id] % math_interval[chat_id] == 0:
            lvl = math_level.get(chat_id, "easy")
            q,a = generate_math(lvl)
            math_answers[chat_id] = a

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🧠 Math ({lvl.upper()})\n\n{q}\n\nUse /solve <answer>"
            )

# ================= COMMANDS =================
async def solve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in math_answers:
        return await update.message.reply_text("❌ No active math")

    try:
        ans = float(context.args[0])
    except:
        return await update.message.reply_text("Use /solve <answer>")

    if ans == math_answers[chat_id]:
        pts = random.randint(1,80)
        user = update.effective_user.first_name
        user_points[user] = user_points.get(user,0) + pts
        del math_answers[chat_id]
        await update.message.reply_text(f"✅ Correct! +{pts} pts")
    else:
        await update.message.reply_text("❌ Wrong")

async def dice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_dice("🎲")
    await asyncio.sleep(2)
    val = msg.dice.value
    pts = val * 2
    user = update.effective_user.first_name
    user_points[user] = user_points.get(user,0) + pts
    await msg.edit_text(f"🎲 Dice: {val}\n+{pts} points")

async def shop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🛒 Elite Shop\n\n"
    for i,v in SHOP_ITEMS.items():
        text += f"{v['emoji']} {i} → {v['price']} pts\n"
    await update.message.reply_text(text)

async def buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    if not context.args:
        return await update.message.reply_text("Use /buy <item>")
    item = context.args[0].lower()
    if item not in SHOP_ITEMS:
        return await update.message.reply_text("Item not found")
    price = SHOP_ITEMS[item]["price"]
    if user_points.get(user,0) < price:
        return await update.message.reply_text("Not enough points")
    user_points[user] -= price
    DB.insert({"user": user, "item": item})
    await update.message.reply_text(f"Bought {SHOP_ITEMS[item]['emoji']} {item}")

async def inventory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    items = DB.search(Query().user == user)
    if not items:
        return await update.message.reply_text("Inventory empty")
    msg = "🎒 Inventory\n"
    for i in items:
        if "item" in i:
            msg += f"{SHOP_ITEMS[i['item']]['emoji']} {i['item']}\n"
    await update.message.reply_text(msg)

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = sorted(user_points.items(), key=lambda x:x[1], reverse=True)
    msg = "🏆 Top Points\n\n"
    for i,(u,p) in enumerate(top[:10]):
        msg += f"{i+1}. {u} → {p}\n"
    await update.message.reply_text(msg)

async def changetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    math_interval[update.effective_chat.id] = int(context.args[0])
    await update.message.reply_text("Math timer set")

async def level_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    math_level[update.effective_chat.id] = context.args[0]
    await update.message.reply_text("Level set")

# ================= CALLBACK =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "games":
        await q.message.edit_text("🎮 Mini Games", reply_markup=games_keyboard())
    elif q.data == "dice":
        await q.message.reply_text("Use /dice")
    elif q.data == "back":
        await q.message.edit_text(START_TEXT, reply_markup=main_keyboard())
    elif q.data == "help":
        await q.message.edit_text(HELP_TEXT, reply_markup=main_keyboard())
    elif q.data == "about":
        await q.message.edit_text(ABOUT_TEXT, reply_markup=main_keyboard())

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text(START_TEXT, reply_markup=main_keyboard())))
app.add_handler(CommandHandler("help", lambda u,c: u.message.reply_text(HELP_TEXT)))
app.add_handler(CommandHandler("about", lambda u,c: u.message.reply_text(ABOUT_TEXT)))
app.add_handler(CommandHandler("dice", dice_cmd))
app.add_handler(CommandHandler("shop", shop_cmd))
app.add_handler(CommandHandler("buy", buy_cmd))
app.add_handler(CommandHandler("inventory", inventory_cmd))
app.add_handler(CommandHandler("solve", solve_cmd))
app.add_handler(CommandHandler("top", top_cmd))
app.add_handler(CommandHandler("changetime", changetime))
app.add_handler(CommandHandler("level", level_cmd))

app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, elite_chat))
app.add_handler(MessageHandler(filters.ALL, group_tracker))

print("🤖 EliteXHoster running...")
app.run_polling()