import logging
from pymongo import MongoClient
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

# ================= CONFIG =================
BOT_TOKEN = "8520734510:AAFuqA-MlB59vfnI_zUQiGiRQKEJScaUyFs"
MONGO_URL = "MONGO_URI"

OWNER_IDS = {5773908061}  # <-- PUT OWNER ID(s)

DB_NAME = "greed_island"
COLLECTION = "players"

# ================= LOGGING =================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================= DATABASE =================
client = MongoClient(MONGO_URL)
db = client[DB_NAME]
players = db[COLLECTION]

# ================= FONT SYSTEM =================
def yuuki(text: str) -> str:
    return f"Tʜɪs ʏᴜᴜᴋɪ\n\n{text}"

# ================= PLAYER HELPERS =================
def get_player(user):
    return players.find_one({"user_id": user.id})

def create_player(user):
    data = {
        "user_id": user.id,
        "username": user.username,
        "name": user.first_name,
        "hp": 100,
        "max_hp": 100,
        "nen": 10,
        "nen_type": None,
        "strength": 10,
        "kills": 0,
        "alive": True,
        "location": "HxH World",
        "console": False,
        "binder": [],
        "inventory": [],
        "milla": 0,
        "party": None,
        "is_owner": user.id in OWNER_IDS
    }
    players.insert_one(data)
    return data

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_player(user)

    if not player:
        player = create_player(user)
        await update.message.reply_text(
            yuuki(
                f"Welcome {user.first_name}\n"
                f"You have entered the world of Greed Island.\n\n"
                f"Status: Registered\n"
                f"Location: HxH World"
            )
        )
    else:
        await update.message.reply_text(
            yuuki(
                f"Welcome back {user.first_name}\n"
                f"Location: {player['location']}\n"
                f"HP: {player['hp']}/{player['max_hp']}\n"
                f"Nen: {player['nen']}"
            )
        )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_player(user)

    if not player:
        await update.message.reply_text(
            yuuki("You are not registered. Use /start")
        )
        return

    text = (
        f"Name: {player['name']}\n"
        f"HP: {player['hp']}/{player['max_hp']}\n"
        f"Nen: {player['nen']}\n"
        f"Strength: {player['strength']}\n"
        f"Kills: {player['kills']}\n"
        f"Location: {player['location']}\n"
        f"Console: {'Yes' if player['console'] else 'No'}"
    )

    if player["is_owner"]:
        text += "\nRole: OWNER"

    await update.message.reply_text(yuuki(text))

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()