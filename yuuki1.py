import os
import logging
from datetime import datetime
from pymongo import MongoClient
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("YOUR_BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

OWNER_IDS = {5773908061}

# ================= LOGGING =================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= DATABASE =================
mongo = MongoClient(MONGO_URL)
db = mongo["greed_island"]
players = db["players"]

# ================= FONT =================
def yuuki(text: str) -> str:
    return f"Tʜɪs ʏᴜᴜᴋɪ\n\n{text}"

# ================= UTIL =================
def is_owner(uid: int) -> bool:
    return uid in OWNER_IDS

def get_player(uid: int):
    return players.find_one({"user_id": uid})

def create_player(user):
    data = {
        "user_id": user.id,
        "username": user.username or user.first_name,
        "hp": 100,
        "nen": 10,
        "nen_type": "Unawakened",
        "strength": 10,
        "kills": 0,
        "milla": 0,
        "location": "HxH World",
        "alive": True,
        "console": False,
        "binder": [],
        "inventory": [],
        "party": None,
        "created_at": datetime.utcnow()
    }
    players.insert_one(data)
    return data

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_player(user.id)

    if not player:
        create_player(user)
        msg = "Welcome to the HxH world.\nUse /stats to view your profile."
    else:
        msg = "You are already registered."

    await update.message.reply_text(yuuki(msg))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_player(user.id)

    if not player:
        return await update.message.reply_text(
            yuuki("You are not registered. Use /start.")
        )

    hp_bar = "█" * (player["hp"] // 10) + "░" * (10 - player["hp"] // 10)

    text = (
        f"Name: {player['username']}\n"
        f"HP: {hp_bar} ({player['hp']})\n"
        f"Nen: {player['nen']}\n"
        f"Strength: {player['strength']}\n"
        f"Kills: {player['kills']}\n"
        f"Milla: {player['milla']}\n"
        f"Location: {player['location']}\n"
        f"Console: {'Yes' if player['console'] else 'No'}"
    )

    await update.message.reply_text(yuuki(text))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return await update.message.reply_text(yuuki("Access denied."))

    if not context.args:
        return await update.message.reply_text(yuuki("Usage: /broadcast <msg>"))

    msg = " ".join(context.args)

    for p in players.find():
        try:
            await context.bot.send_message(p["user_id"], yuuki(msg))
        except:
            pass

    await update.message.reply_text(yuuki("Broadcast sent."))

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))

    logger.info("Greed Island core running...")
    app.run_polling()

if __name__ == "__main__":
    main()