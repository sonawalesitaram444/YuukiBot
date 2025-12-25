import logging
import random
from datetime import datetime
from tinydb import TinyDB, Query
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = "8520734510:AAFuqA-MlB59vfnI_zUQiGiRQKEJScaUyFs"
OWNER_IDS = {5773908061}

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= DATABASE =================
db = TinyDB("greed_island.json")
players = db.table("players")
Player = Query()

# ================= AUTO YUUKI FONT =================
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

def create_player(user):
    data = {
        "user_id": user.id,
        "username": user.username or user.first_name,
        "hp": 100,
        "nen": 10,
        "strength": 10,
        "kills": 0,
        "milla": 0,
        "location": "Outside GI",
        "alive": True,
        "created_at": str(datetime.utcnow())
    }
    players.insert(data)
    return data

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_player(user.id)

    if not player:
        create_player(user)
        msg = "Welcome to the Hunter World\nUse /stats to view your profile"
    else:
        msg = "You are already registered"

    await update.message.reply_text(yuuki(msg))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player = get_player(update.effective_user.id)

    if not player:
        return await update.message.reply_text(yuuki("Use /start first"))

    hp_bar = "█" * (player["hp"] // 10) + "░" * (10 - player["hp"] // 10)

    text = (
        f"Name: {player['username']}\n"
        f"HP: {hp_bar} ({player['hp']})\n"
        f"Nen: {player['nen']}\n"
        f"Strength: {player['strength']}\n"
        f"Kills: {player['kills']}\n"
        f"Milla: {player['milla']}\n"
        f"Location: {player['location']}\n"
        f"Status: {'Alive' if player['alive'] else 'Dead'}"
    )

    await update.message.reply_text(yuuki(text))

# ================= FIGHT SYSTEM =================
async def fight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = get_player(update.effective_user.id)

    if not attacker:
        return await update.message.reply_text(yuuki("Use /start first"))

    if not update.message.reply_to_message:
        return await update.message.reply_text(
            yuuki("Reply to a player message to fight")
        )

    target_user = update.message.reply_to_message.from_user
    defender = get_player(target_user.id)

    if not defender:
        return await update.message.reply_text(yuuki("Target not registered"))

    if not attacker["alive"]:
        return await update.message.reply_text(yuuki("You are dead"))

    if not defender["alive"]:
        return await update.message.reply_text(yuuki("Target already dead"))

    atk_damage = random.randint(attacker["strength"] // 2, attacker["strength"])
    def_damage = random.randint(defender["strength"] // 3, defender["strength"] // 2)

    attacker["hp"] -= def_damage
    defender["hp"] -= atk_damage

    result = (
        f"Fight Result\n\n"
        f"{attacker['username']} dealt {atk_damage} damage\n"
        f"{defender['username']} dealt {def_damage} damage"
    )

    if defender["hp"] <= 0:
        defender["alive"] = False
        attacker["kills"] += 1
        attacker["milla"] += 50
        result += f"\n\n{defender['username']} is DEAD"

    if attacker["hp"] <= 0:
        attacker["alive"] = False
        result += f"\n\n{attacker['username']} is DEAD"

    players.update(attacker, Player.user_id == attacker["user_id"])
    players.update(defender, Player.user_id == defender["user_id"])

    await update.message.reply_text(yuuki(result))

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return await update.message.reply_text(yuuki("Access denied"))

    if not context.args:
        return await update.message.reply_text(yuuki("Usage: /broadcast message"))

    msg = " ".join(context.args)

    for p in players.all():
        try:
            await context.bot.send_message(p["user_id"], yuuki(msg))
        except:
            pass

    await update.message.reply_text(yuuki("Broadcast sent"))

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("fight", fight))
    app.add_handler(CommandHandler("broadcast", broadcast))

    logger.info("Greed Island core running...")
    app.run_polling()

if __name__ == "__main__":
    main()