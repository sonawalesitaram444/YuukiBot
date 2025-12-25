import logging
import random
from datetime import datetime, timedelta

from tinydb import TinyDB, Query
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

# ================= CONFIG =================
BOT_TOKEN = "YOUR_BOT_TOKEN"
OWNER_IDS = {5773908061}

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= DATABASE =================
db = TinyDB("greed_island.json")
players = db.table("players")
Player = Query()

# ================= FONT (LETTERS ONLY) =================
FONT_MAP = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"
)

def yuuki(text: str) -> str:
    return text.translate(FONT_MAP)

# ================= UTIL =================
def is_owner(uid: int) -> bool:
    return uid in OWNER_IDS

def get_player(uid: int):
    return players.get(Player.user_id == uid)

def clickable(user_id: int, name: str) -> str:
    return f"[{name}](tg://user?id={user_id})"

def create_player(user):
    data = {
        "user_id": user.id,
        "name": user.first_name,
        "hp": 100,
        "nen": 10,
        "strength": 10,
        "wins": 0,
        "kills": 0,
        "greed_coins": 0,
        "alive": True,
        "last_daily": None,
        "created_at": str(datetime.utcnow())
    }
    players.insert(data)
    return data

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_player(user.id)

    if not player:
        create_player(user)
        text = (
            "Welcome to the Hunter World 🌍\n\n"
            "Train your Nen, fight players, earn Milla,\n"
            "and prepare yourself for Greed Island.\n\n"
            "Use /stats to view your profile."
        )
    else:
        text = "You are already registered in this world."

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Support", url="https://t.me/team_bright_lightX")],
        [InlineKeyboardButton("Updates", url="https://t.me/YUUKIUPDATES")],
        [InlineKeyboardButton("Add me to Group", url=f"https://t.me/{context.bot.username}?startgroup=true")]
    ])

    await update.message.reply_text(
        yuuki(text),
        reply_markup=keyboard
    )

# ================= STATS =================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not p:
        return await update.message.reply_text(yuuki("Use /start first."))

    hp_bar = "█" * (p["hp"] // 10) + "░" * (10 - p["hp"] // 10)

    text = (
        f"Name: {p['name']}\n"
        f"HP: {hp_bar} ({p['hp']})\n"
        f"Nen: {p['nen']}\n"
        f"Strength: {p['strength']}\n"
        f"Wins: {p['wins']}\n"
        f"Kills: {p['kills']}\n"
        f"greed_coins: {p['milla']}"
    )

    await update.message.reply_text(yuuki(text))

# ================= FIGHT =================
async def fight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = get_player(update.effective_user.id)
    if not attacker:
        return await update.message.reply_text(yuuki("Use /start first."))

    if not update.message.reply_to_message:
        return await update.message.reply_text(yuuki("Reply to a player to fight."))

    target = update.message.reply_to_message.from_user
    defender = get_player(target.id)

    if not defender:
        return await update.message.reply_text(yuuki("Target not registered."))

    atk = random.randint(attacker["strength"], attacker["strength"] + 20)
    dfs = random.randint(defender["strength"], defender["strength"] + 20)

    if atk > dfs:
        attacker["wins"] += 1
        attacker["kills"] += 1
        attacker["Greed_Coins"] += 60
        defender["hp"] -= 25
        result = (
            f"{clickable(attacker['user_id'], attacker['name'])} WON\n\n"
            f"Defeated {clickable(defender['user_id'], defender['name'])}\n"
            f"Total Wins: {attacker['wins']}\n"
            f"+60 Greed coins"
        )
    else:
        attacker["hp"] -= 15
        result = (
            f"{clickable(defender['user_id'], defender['name'])} WON\n\n"
            f"{clickable(attacker['user_id'], attacker['name'])} was defeated"
        )

    players.update(attacker, Player.user_id == attacker["user_id"])
    players.update(defender, Player.user_id == defender["user_id"])

    await update.message.reply_text(
        yuuki(result),
        parse_mode="Markdown"
    )

# ================= TRAIN =================
async def train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not p:
        return await update.message.reply_text(yuuki("Use /start first."))

    p["nen"] += 18
    p["strength"] += 30
    p["hp"] -= 2

    players.update(p, Player.user_id == p["user_id"])

    text = (
        "Training Complete\n\n"
        "Nen: +18\n"
        "Strength: +30\n"
        "HP: -2"
    )

    await update.message.reply_text(yuuki(text))

# ================= WORK =================
async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    earn = random.randint(20, 50)
    p["greed_coins"] += earn
    players.update(p, Player.user_id == p["user_id"])
    await update.message.reply_text(yuuki(f"You earned {earn} greed coins."))

# ================= DAILY =================
async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    now = datetime.utcnow()

    if p["last_daily"]:
        last = datetime.fromisoformat(p["last_daily"])
        if now - last < timedelta(hours=24):
            return await update.message.reply_text(yuuki("Daily already claimed."))

    p["last_daily"] = now.isoformat()
    p["Greed coins"] += 100
    players.update(p, Player.user_id == p["user_id"])
    await update.message.reply_text(yuuki("Daily reward claimed: +100 Greed Coins"))

# ================= QUEST =================
async def quest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    reward = random.randint(80, 150)
    p["greed_coins"] += reward
    players.update(p, Player.user_id == p["user_id"])
    await update.message.reply_text(yuuki(f"Quest completed\n+{reward} Greed coins"))

# ================= LEADERBOARDS =================
async def tkill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = sorted(players.all(), key=lambda x: x["kills"], reverse=True)[:10]
    text = "Top Kills\n\n"
    for i, p in enumerate(top, 1):
        text += f"{i}. {clickable(p['user_id'], p['name'])} — {p['kills']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def trich(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = sorted(players.all(), key=lambda x: x["greed_coins"], reverse=True)[:10]
    text = "Top Rich\n\n"
    for i, p in enumerate(top, 1):
        text += f"{i}. {clickable(p['user_id'], p['name'])} — {p['greed_coins']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("fight", fight))
    app.add_handler(CommandHandler("train", train))
    app.add_handler(CommandHandler("work", work))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("quest", quest))
    app.add_handler(CommandHandler("tkill", tkill))
    app.add_handler(CommandHandler("trich", trich))

    logger.info("Greed Island core running...")
    app.run_polling()

if __name__ == "__main__":
    main()