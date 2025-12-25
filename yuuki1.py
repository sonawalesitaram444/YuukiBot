import logging
import random
from datetime import datetime, timedelta

from pymongo import MongoClient
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters

# ================= CONFIG =================
BOT_TOKEN = "8520734510:AAFuqA-MlB59vfnI_zUQiGiRQKEJScaUyFs"
MONGO_URI = "mongodb+srv://sonawalesitaram444_db_user:xqAwRv0ZdKMI6dDa@anixgrabber.a2tdbiy.mongodb.net/?appName=anixgrabber"
OWNER_IDS = {5773908061}

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= MONGODB =================
mongo = MongoClient(MONGO_URI)
db = mongo.greed_island

players = db.players
cards = db.cards
groups = db.groups
lands = db.lands
settings = db.settings

if not settings.find_one({"key": "global"}):
    settings.insert_one({"key": "global", "open": True})

# ================= FONT =================
FONT = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"
    "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"
)

def yuuki(t): 
    return t.translate(FONT)

# ================= UTIL =================
def get_player(uid):
    return players.find_one({"user_id": uid})

def ensure_player(user):
    if not get_player(user.id):
        players.insert_one({
            "user_id": user.id,
            "name": user.first_name,
            "hp": 100,
            "nen": 10,
            "strength": 10,
            "wins": 0,
            "kills": 0,
            "greed_coins": 50,
            "cards": [],
            "land": "Outside",
            "last_daily": None
        })

def land_active(name):
    land = lands.find_one({"name": name})
    if not land:
        lands.insert_one({"name": name, "active": True})
        return True
    return land["active"]

def group_enabled(chat_id):
    g = groups.find_one({"chat_id": chat_id})
    return g is None or g["enabled"]

# ================= GROUP ENABLE / DISABLE =================
async def y(update: Update, ctx):
    if update.effective_user.id not in OWNER_IDS and not update.effective_user.id:
        return
    groups.update_one(
        {"chat_id": update.effective_chat.id},
        {"$set": {"enabled": True}},
        upsert=True
    )
    await update.message.reply_text("✅ Game enabled in this group")

async def n(update: Update, ctx):
    if update.effective_user.id not in OWNER_IDS:
        return
    groups.update_one(
        {"chat_id": update.effective_chat.id},
        {"$set": {"enabled": False}},
        upsert=True
    )
    await update.message.reply_text("❌ Game disabled in this group")

# ================= START =================
async def start(update: Update, ctx):
    ensure_player(update.effective_user)
    await update.message.reply_text(yuuki("Welcome to Greed Island 🌍"))

# ================= STATS =================
async def stats(update: Update, ctx):
    p = get_player(update.effective_user.id)
    await update.message.reply_text(yuuki(
        f"👤 {p['name']}\n"
        f"❤️ HP: {p['hp']}\n"
        f"✨ Nen: {p['nen']}\n"
        f"💪 Strength: {p['strength']}\n"
        f"🏆 Wins: {p['wins']}\n"
        f"☠️ Kills: {p['kills']}\n"
        f"💰 Coins: {p['greed_coins']}\n"
        f"🌍 Land: {p['land']}"
    ))

# ================= TRAIN =================
async def train(update: Update, ctx):
    players.update_one(
        {"user_id": update.effective_user.id},
        {"$inc": {"nen": 18, "strength": 30, "hp": -2}}
    )
    await update.message.reply_text(yuuki("Training complete 💪"))

# ================= FIGHT =================
async def fight(update: Update, ctx):
    if not update.message.reply_to_message:
        return
    a = get_player(update.effective_user.id)
    d = get_player(update.message.reply_to_message.from_user.id)
    if not d:
        return

    if random.randint(1, a["strength"]) > random.randint(1, d["strength"]):
        players.update_one(
            {"user_id": a["user_id"]},
            {"$inc": {"wins": 1, "kills": 1, "greed_coins": 40}}
        )
        players.update_one(
            {"user_id": d["user_id"]},
            {"$inc": {"hp": -25}}
        )
        await update.message.reply_text(yuuki("You won ⚔️"))
    else:
        players.update_one(
            {"user_id": a["user_id"]},
            {"$inc": {"hp": -15}}
        )
        await update.message.reply_text(yuuki("You lost 💀"))

# ================= WORK / DAILY / QUEST =================
async def work(update: Update, ctx):
    earn = random.randint(20, 50)
    players.update_one({"user_id": update.effective_user.id}, {"$inc": {"greed_coins": earn}})
    await update.message.reply_text(yuuki(f"+{earn} coins 💰"))

async def daily(update: Update, ctx):
    p = get_player(update.effective_user.id)
    now = datetime.utcnow()
    if p["last_daily"] and now - p["last_daily"] < timedelta(hours=24):
        return await update.message.reply_text("⏳ Already claimed")
    players.update_one(
        {"user_id": p["user_id"]},
        {"$set": {"last_daily": now}, "$inc": {"greed_coins": 100}}
    )
    await update.message.reply_text("🎁 Daily claimed")

async def quest(update: Update, ctx):
    reward = random.randint(80, 150)
    players.update_one({"user_id": update.effective_user.id}, {"$inc": {"greed_coins": reward}})
    await update.message.reply_text(yuuki(f"Quest complete +{reward}"))

# ================= LAND =================
async def enter(update: Update, ctx):
    land = ctx.args[0]
    if not land_active(land):
        return await update.message.reply_text("🔒 This land is shutdown")
    players.update_one({"user_id": update.effective_user.id}, {"$set": {"land": land}})
    await update.message.reply_text(yuuki(f"Entered {land} 🌍"))

async def shutdown(update: Update, ctx):
    if update.effective_user.id not in OWNER_IDS:
        return
    lands.update_one({"name": ctx.args[0]}, {"$set": {"active": False}}, upsert=True)
    await update.message.reply_text("🔒 Land shutdown")

async def active(update: Update, ctx):
    if update.effective_user.id not in OWNER_IDS:
        return
    lands.update_one({"name": ctx.args[0]}, {"$set": {"active": True}}, upsert=True)
    await update.message.reply_text("✅ Land activated")

# ================= CARDS =================
SHOP = {
    "accompany": 500,
    "angelbreath": 350,
    "sword": 200,
    "heal": 150
}

async def upload(update: Update, ctx):
    if update.effective_user.id not in OWNER_IDS:
        return
    name, cid, rank, work = ctx.args
    cards.insert_one({
        "name": name.lower(),
        "id": cid,
        "rank": rank,
        "work": work.lower()
    })
    await update.message.reply_text("🃏 Card uploaded")

async def cardshop(update: Update, ctx):
    text = "🛒 Card Shop\n\n"
    for c, p in SHOP.items():
        text += f"{c} — {p} coins\n"
    await update.message.reply_text(text)

async def buy(update: Update, ctx):
    card = ctx.args[0].lower()
    price = SHOP.get(card)
    p = get_player(update.effective_user.id)
    if not price or p["greed_coins"] < price:
        return
    players.update_one(
        {"user_id": p["user_id"]},
        {"$inc": {"greed_coins": -price}, "$push": {"cards": card}}
    )
    await update.message.reply_text("Purchased 🃏")

async def use(update: Update, ctx):
    card = ctx.args[0].lower()
    p = get_player(update.effective_user.id)
    if card not in p["cards"]:
        return
    if card == "accompany":
        players.update_one({"user_id": p["user_id"]}, {"$set": {"land": "GreedIsland"}})
    elif card == "heal":
        players.update_one({"user_id": p["user_id"]}, {"$inc": {"hp": 30}})
    await update.message.reply_text(yuuki(f"{card} used 🌀"))

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    for cmd, func in {
        "start": start, "stats": stats, "train": train, "fight": fight,
        "work": work, "daily": daily, "quest": quest,
        "enter": enter, "shutdown": shutdown, "active": active,
        "upload": upload, "cardshop": cardshop, "buy": buy, "use": use,
        "y": y, "n": n
    }.items():
        app.add_handler(CommandHandler(cmd, func))

    logger.info("Greed Island FULL SYSTEM running 🔥")
    app.run_polling()

if __name__ == "__main__":
    main()