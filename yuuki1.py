import os
import random
import time
import asyncio
import datetime
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
Users = Query()

# ================= STATE =================
group_message_count = {}
math_interval = {}
math_level = {}
math_answers = {}

# ================= ECONOMY =================
def get_user(uid, name):
    u = DB.get(Users.id == uid)
    if not u:
        u = {
            "id": uid,
            "name": name,
            "coins": 0,
            "kills": 0,
            "alive": True,
            "dice_used": 0,
            "dice_day": str(datetime.date.today()),
            "inventory": [],
            "protected_until": 0
        }
        DB.insert(u)
    return u

def save_user(u):
    DB.update(u, Users.id == u["id"])

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
/bal
/steal <amount> (reply)
/murder (reply)
/protect 1d|2d
/revive (reply optional)
/shop
/buy <item>
/inventory
/gift <item> (reply)
/solve <answer>
/toprichest
/topmurderers

Owner:
/changetime <count>
/level <easy|medium|hard|extreme>
/announce
/broadcast
"""

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

    if "elite" not in msg.lower():
        return

    payload = {
        "model": "moonshotai/kimi-k2-instruct-0905",
        "messages": [
            {"role": "system", "content":
             "You are Elitexhoster. Act human. Use hinglish. "
             "Relationship talk = depressed 😔. Max 20 words. "
             "Never say you are a bot."
            },
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
        reply = "Lag aa gaya 😪"

    await update.message.reply_text(reply)

# ================= GROUP TRACKER =================
async def group_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.from_user.is_bot:
        return

    cid = update.effective_chat.id
    group_message_count[cid] = group_message_count.get(cid, 0) + 1

    if cid in math_interval:
        if group_message_count[cid] % math_interval[cid] == 0:
            lvl = math_level.get(cid, "easy")
            q, a = generate_math(lvl)
            math_answers[cid] = a
            await context.bot.send_message(
                cid, f"🧠 𝐌𝐚𝐭𝐡 ({lvl.upper()})\n\n{q}\n\n/solve <answer>"
            )

# ================= COMMANDS =================
async def solve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid not in math_answers:
        return

    try:
        ans = float(context.args[0])
    except:
        return

    if ans == math_answers[cid]:
        pts = random.randint(1,80)
        u = get_user(update.effective_user.id, update.effective_user.first_name)
        u["coins"] += pts
        save_user(u)
        del math_answers[cid]
        await update.message.reply_text(f"✅ Correct +{pts} 💰")
    else:
        await update.message.reply_text("❌ Wrong")

async def dice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id, update.effective_user.first_name)
    today = str(datetime.date.today())
    if u["dice_day"] != today:
        u["dice_used"] = 0
        u["dice_day"] = today

    if u["dice_used"] >= 10:
        return await update.message.reply_text("Dice limit reached 🎲")

    msg = await update.message.reply_dice()
    await asyncio.sleep(2)
    coins = msg.dice.value * random.randint(5,15)
    u["coins"] += coins
    u["dice_used"] += 1
    save_user(u)
    await msg.edit_text(f"🎲 +{coins} 💰")

async def bal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id, update.effective_user.first_name)
    await update.message.reply_text(
        f"👤 {u['name']}\n💰 {u['coins']}\n❤️ {'Alive' if u['alive'] else 'Dead'}"
    )

async def steal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return
    thief = get_user(update.effective_user.id, update.effective_user.first_name)
    target = get_user(update.message.reply_to_message.from_user.id,
                      update.message.reply_to_message.from_user.first_name)
    amt = int(context.args[0])
    if target["coins"] >= amt:
        target["coins"] -= amt
        thief["coins"] += amt
        save_user(thief); save_user(target)
        await update.message.reply_text("Rob success 🎯")
    else:
        await update.message.reply_text("Rob failed 😔")

async def murder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return
    killer = get_user(update.effective_user.id, update.effective_user.first_name)
    victim = get_user(update.message.reply_to_message.from_user.id,
                      update.message.reply_to_message.from_user.first_name)

    if time.time() < victim.get("protected_until", 0):
        return await update.message.reply_text("Target is protected 🛡️")

    if not victim["alive"]:
        return

    reward = random.randint(100,300)
    victim["alive"] = False
    killer["kills"] += 1
    killer["coins"] += reward
    save_user(victim); save_user(killer)

    await update.message.reply_text(f"{killer['name']} murdered {victim['name']} 💀")

async def protect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id, update.effective_user.first_name)
    now = time.time()

    if u["protected_until"] > now:
        rem = int((u["protected_until"]-now)/3600)
        return await update.message.reply_text(f"Already protected {rem}h")

    if context.args[0] == "1d":
        cost, sec = 200, 86400
    elif context.args[0] == "2d":
        cost, sec = 400, 172800
    else:
        return

    if u["coins"] < cost:
        return

    u["coins"] -= cost
    u["protected_until"] = now + sec
    save_user(u)
    await update.message.reply_text("Protection enabled 🪀")

async def revive_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reviver = get_user(update.effective_user.id, update.effective_user.first_name)
    if update.message.reply_to_message:
        target = get_user(update.message.reply_to_message.from_user.id,
                          update.message.reply_to_message.from_user.first_name)
        cost = 450
    else:
        target = reviver
        cost = 500

    if reviver["coins"] < cost:
        return

    target["alive"] = True
    reviver["coins"] -= cost
    save_user(target); save_user(reviver)

    await update.message.reply_text("Revive successful ✅")

async def shop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = "🛒 Shop\n\n"
    for k,v in SHOP_ITEMS.items():
        txt += f"{v['emoji']} {k} - {v['price']} 💰\n"
    await update.message.reply_text(txt)

async def buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id, update.effective_user.first_name)
    item = context.args[0].lower()
    if u["coins"] < SHOP_ITEMS[item]["price"]:
        return
    u["coins"] -= SHOP_ITEMS[item]["price"]
    u["inventory"].append(item)
    save_user(u)
    await update.message.reply_text("Purchased ✅")

async def inventory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id, update.effective_user.first_name)
    await update.message.reply_text("🎒 " + ", ".join(u["inventory"]))

async def gift_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return
    giver = get_user(update.effective_user.id, update.effective_user.first_name)
    rec = get_user(update.message.reply_to_message.from_user.id,
                   update.message.reply_to_message.from_user.first_name)
    item = context.args[0]
    if item not in giver["inventory"]:
        return
    giver["inventory"].remove(item)
    rec["inventory"].append(item)
    save_user(giver); save_user(rec)
    await update.message.reply_text("Gift sent 🎁")

async def toprichest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = sorted(DB.all(), key=lambda x:x["coins"], reverse=True)[:10]
    msg = "🏆 Top Richest\n\n"
    for i,u in enumerate(top):
        msg += f"{i+1}. [{u['name']}](tg://user?id={u['id']}) - {u['coins']} 💰\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def topmurderers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = sorted(DB.all(), key=lambda x:x["kills"], reverse=True)[:10]
    msg = "💀 Top Murderers\n\n"
    for i,u in enumerate(top):
        msg += f"{i+1}. {u['name']} - {u['kills']}\n"
    await update.message.reply_text(msg)

async def changetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in OWNER_IDS:
        math_interval[update.effective_chat.id] = int(context.args[0])
        group_message_count[update.effective_chat.id] = 0
        await update.message.reply_text("Math timer set")

async def level_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in OWNER_IDS:
        math_level[update.effective_chat.id] = context.args[0]

async def announce_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    msg = update.message.text.split(maxsplit=1)[1]
    for u in DB.all():
        try:
            await context.bot.send_message(u["id"], f"📢 {msg}")
        except:
            pass

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    msg = update.message.text.split(maxsplit=1)[1]
    for u in DB.all():
        try:
            await context.bot.send_message(u["id"], f"📡 {msg}")
        except:
            pass

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text(START_TEXT)))
app.add_handler(CommandHandler("help", lambda u,c: u.message.reply_text(HELP_TEXT)))
app.add_handler(CommandHandler("dice", dice_cmd))
app.add_handler(CommandHandler("bal", bal_cmd))
app.add_handler(CommandHandler("steal", steal_cmd))
app.add_handler(CommandHandler("murder", murder_cmd))
app.add_handler(CommandHandler("protect", protect_cmd))
app.add_handler(CommandHandler("revive", revive_cmd))
app.add_handler(CommandHandler("shop", shop_cmd))
app.add_handler(CommandHandler("buy", buy_cmd))
app.add_handler(CommandHandler("inventory", inventory_cmd))
app.add_handler(CommandHandler("gift", gift_cmd))
app.add_handler(CommandHandler("solve", solve_cmd))
app.add_handler(CommandHandler("toprichest", toprichest))
app.add_handler(CommandHandler("topmurderers", topmurderers))
app.add_handler(CommandHandler("changetime", changetime))
app.add_handler(CommandHandler("level", level_cmd))
app.add_handler(CommandHandler("announce", announce_cmd))
app.add_handler(CommandHandler("broadcast", broadcast_cmd))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, elite_chat))
app.add_handler(MessageHandler(filters.ALL, group_tracker))

print("🤖 EliteXHoster running...")
app.run_polling()