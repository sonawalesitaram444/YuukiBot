# ===============================
#  ELITEXHOSTER — ALL IN ONE BOT
# ===============================

import os, random, time, asyncio, datetime, requests
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from tinydb import TinyDB, Query

# ================= CONFIG =================
BOT_TOKEN = os.getenv("YOUR_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

OWNER_IDS = [5773908061]

BOT_NAME = "˹ 𝐄𝐥𝐢𝐭𝐞 ✘ 𝐇ᴏꜱᴛᴇʀ ˼"
SUPPORT = "https://t.me/team_bright_lightX"
UPDATES = "https://t.me/+dsCkYEVHJBRiMjI9"
ADD_ME = "https://t.me/EliteXHosterBot?startgroup=true"

DB = TinyDB("users.json")
Users = Query()

# ================= USER =================
def get_user(uid, name):
    u = DB.get(Users.id == uid)
    if not u:
        u = {
            "id": uid,
            "name": name,
            "coins": 100,
            "kills": 0,
            "alive": True,
            "inventory": [],
            "protected_until": 0,
            "dice_used": 0,
            "dice_day": str(datetime.date.today())
        }
        DB.insert(u)
    return u

def save_user(u):
    DB.update(u, Users.id == u["id"])

# ================= SHOP =================
SHOP = {
    "teddy": ("🧸", 50),
    "rose": ("🌹", 30),
    "knife": ("🔪", 100),
    "console": ("🎮", 200),
    "premium": ("💎", 500)
}

# ================= UI =================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ɢʀᴏᴜᴘ", url=ADD_ME)],
        [
            InlineKeyboardButton("🎮 ɢᴀᴍᴇs", callback_data="games"),
            InlineKeyboardButton("📜 ʜᴇʟᴘ", callback_data="help")
        ],
        [
            InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇs", url=UPDATES),
            InlineKeyboardButton("🆘 sᴜᴘᴘᴏʀᴛ", url=SUPPORT)
        ]
    ])

START_TEXT = f"""
✨ **WELCOME TO {BOT_NAME}**

🎯 Talking + Mini Games Bot  
💰 Economy • 🔪 Kill • 🏃 Rob  
🧠 Math • 🎲 Dice • 🛒 Shop  

⚡ Use buttons below to explore
"""

HELP_TEXT = """
🎮 **PLAYER COMMANDS**

/dice  
/bal  
/rob <amount> (reply)
/kill (reply)
/protect 1d | 2d  
/revive (reply optional)
/shop  
/buy <item>  
/inventory  
/gift <item> (reply)
/toprichest  
/topkillers  

👑 **OWNER**
/announce  
/broadcast
"""

# ================= CALLBACK =================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "help":
        await q.message.edit_text(HELP_TEXT)
    if q.data == "games":
        await q.message.edit_text(
            "🎮 Dice • Math • Rob • Kill\nUse /dice to start!"
        )

# ================= AI CHAT =================
async def elite_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    msg = update.message.text.lower()
    if BOT_NAME.lower() not in msg:
        return

    payload = {
        "model": "moonshotai/kimi-k2-instruct-0905",
        "messages": [
            {"role": "system",
             "content": "Act human. Hinglish. Sad vibe 😔. Max 20 words. Never say bot."},
            {"role": "user", "content": msg}
        ]
    }

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json=payload,
            timeout=15
        )
        reply = r.json()["choices"][0]["message"]["content"]
    except:
        reply = "Aaj thoda broken feel ho raha 😔"

    await update.message.reply_text(reply)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        START_TEXT,
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

async def bal(update: Update, context):
    u = get_user(update.effective_user.id, update.effective_user.first_name)
    await update.message.reply_text(
        f"👤 {u['name']}\n💰 Coins: {u['coins']}\n❤️ {'Alive' if u['alive'] else 'Dead'}"
    )

async def dice(update: Update, context):
    u = get_user(update.effective_user.id, update.effective_user.first_name)
    today = str(datetime.date.today())
    if u["dice_day"] != today:
        u["dice_used"] = 0
        u["dice_day"] = today

    if u["dice_used"] >= 10:
        return await update.message.reply_text("🎲 Daily limit reached")

    m = await update.message.reply_dice()
    await asyncio.sleep(2)
    coins = m.dice.value * random.randint(5, 15)
    u["coins"] += coins
    u["dice_used"] += 1
    save_user(u)
    await m.edit_text(f"🎲 You won {coins} coins 💰")

async def rob(update: Update, context):
    if not update.message.reply_to_message:
        return
    thief = get_user(update.effective_user.id, update.effective_user.first_name)
    target = get_user(
        update.message.reply_to_message.from_user.id,
        update.message.reply_to_message.from_user.first_name
    )
    amt = int(context.args[0])
    if target["coins"] >= amt:
        target["coins"] -= amt
        thief["coins"] += amt
        save_user(thief); save_user(target)
        await update.message.reply_text("💰 Rob successful!")
    else:
        await update.message.reply_text("❌ Rob failed")

async def kill(update: Update, context):
    if not update.message.reply_to_message:
        return
    killer = get_user(update.effective_user.id, update.effective_user.first_name)
    victim = get_user(
        update.message.reply_to_message.from_user.id,
        update.message.reply_to_message.from_user.first_name
    )

    if time.time() < victim["protected_until"]:
        return await update.message.reply_text("🛡️ Target protected")

    if not victim["alive"]:
        return

    reward = random.randint(150, 350)
    victim["alive"] = False
    killer["kills"] += 1
    killer["coins"] += reward
    save_user(victim); save_user(killer)

    await update.message.reply_text(
        f"💀 {killer['name']} killed {victim['name']} (+{reward} 💰)"
    )

async def shop(update: Update, context):
    txt = "🛒 **SHOP**\n\n"
    for i,(e,p) in SHOP.items():
        txt += f"{e} {i} — {p} 💰\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def buy(update: Update, context):
    u = get_user(update.effective_user.id, update.effective_user.first_name)
    item = context.args[0].lower()
    if item not in SHOP:
        return
    emoji, price = SHOP[item]
    if u["coins"] < price:
        return await update.message.reply_text("❌ Not enough coins")
    u["coins"] -= price
    u["inventory"].append(item)
    save_user(u)
    await update.message.reply_text(f"✅ Bought {emoji} {item}")

async def inventory(update: Update, context):
    u = get_user(update.effective_user.id, update.effective_user.first_name)
    await update.message.reply_text(
        "🎒 Inventory:\n" + (", ".join(u["inventory"]) or "Empty")
    )

async def announce(update: Update, context):
    if update.effective_user.id not in OWNER_IDS:
        return
    msg = update.message.text.split(maxsplit=1)[1]
    for u in DB.all():
        try:
            await context.bot.send_message(u["id"], f"📢 {msg}")
        except:
            pass

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", lambda u,c: u.message.reply_text(HELP_TEXT)))
app.add_handler(CommandHandler("bal", bal))
app.add_handler(CommandHandler("dice", dice))
app.add_handler(CommandHandler("rob", rob))
app.add_handler(CommandHandler("kill", kill))
app.add_handler(CommandHandler("shop", shop))
app.add_handler(CommandHandler("buy", buy))
app.add_handler(CommandHandler("inventory", inventory))
app.add_handler(CommandHandler("announce", announce))

app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, elite_chat))

print("🔥 EliteXHoster running...")
app.run_polling()