import logging
import random
from pymongo import MongoClient
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= CONFIG =================
BOT_TOKEN = "8520734510:AAFuqA-MlB59vfnI_zUQiGiRQKEJScaUyFs"
MONGO_URI = "mongodb+srv://sonawalesitaram444_db_user:xqAwRv0ZdKMI6dDa@anixgrabber.a2tdbiy.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "greed_island"
# ========================================

# ---------- LOGGING ----------
logging.basicConfig(level=logging.INFO)

# ---------- DATABASE ----------
mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
users = db.users
fights = db.fights

# ---------- HELPERS ----------
def get_user(user):
    data = users.find_one({"user_id": user.id})
    if not data:
        data = {
            "user_id": user.id,
            "name": user.first_name,
            "hp": 1000,
            "max_hp": 1000,
            "nen": 0,
            "strength": 1000,
            "jenny": 500,
            "in_gi": False
        }
        users.insert_one(data)
    return data

def hp_bar(hp, max_hp):
    filled = int(20 * hp / max_hp)
    return "█" * filled + "░" * (20 - filled)

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user)
    await update.message.reply_text(
        "🌍 *Greed Island Initialized*\n\n"
        "/profile – View stats\n"
        "/fight (reply) – Fight player",
        parse_mode="Markdown"
    )

# ---------- PROFILE ----------
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user)
    await update.message.reply_text(
        f"👤 *{u['name']}*\n\n"
        f"❤️ HP\n`{hp_bar(u['hp'], u['max_hp'])}` {u['hp']}/{u['max_hp']}\n\n"
        f"⚡ Nen: `{u['nen']}`\n"
        f"💪 Strength: `{u['strength']}`\n"
        f"💴 Jenny: `{u['jenny']}`\n"
        f"🎮 GI Status: `{ 'Inside' if u['in_gi'] else 'Outside' }`",
        parse_mode="Markdown"
    )

# ---------- FIGHT ----------
async def fight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message:
        return await msg.reply_text("❌ Reply to a user to fight.")

    attacker = msg.from_user
    defender = msg.reply_to_message.from_user

    if attacker.id == defender.id:
        return await msg.reply_text("❌ You can’t fight yourself.")

    get_user(attacker)
    get_user(defender)

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"accept:{attacker.id}"),
            InlineKeyboardButton("❌ Decline", callback_data="decline")
        ]
    ])

    await msg.reply_text(
        f"⚔️ *Fight Request*\n\n"
        f"{defender.first_name}, do you accept?",
        parse_mode="Markdown",
        reply_markup=kb
    )

# ---------- CALLBACK ----------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat.id
    user = q.from_user

    if q.data == "decline":
        fights.delete_one({"chat_id": chat_id})
        return await q.edit_message_text("❌ Fight declined.")

    if q.data.startswith("accept:"):
        attacker_id = int(q.data.split(":")[1])
        if user.id == attacker_id:
            return await q.answer("❌ You can’t accept your own fight.", show_alert=True)

        fights.replace_one(
            {"chat_id": chat_id},
            {
                "chat_id": chat_id,
                "p1": attacker_id,
                "p2": user.id,
                "turn": attacker_id
            },
            upsert=True
        )

        p1 = users.find_one({"user_id": attacker_id})
        p2 = users.find_one({"user_id": user.id})

        return await q.edit_message_text(
            f"⚔️ *FIGHT STARTED*\n\n"
            f"{p1['name']} vs {p2['name']}\n\n"
            f"▶ Turn: {p1['name']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Attack", callback_data="attack")]
            ])
        )

    if q.data == "attack":
        fight = fights.find_one({"chat_id": chat_id})
        if not fight or fight["turn"] != user.id:
            return await q.answer("❌ Not your turn.", show_alert=True)

        attacker = users.find_one({"user_id": user.id})
        defender_id = fight["p2"] if fight["p1"] == user.id else fight["p1"]
        defender = users.find_one({"user_id": defender_id})

        dmg = random.randint(80, 150) + attacker["strength"] // 30
        defender["hp"] -= dmg

        if defender["hp"] <= 0:
            users.update_one(
                {"user_id": defender_id},
                {"$set": {"hp": defender["max_hp"]}}
            )
            fights.delete_one({"chat_id": chat_id})

            return await q.edit_message_text(
                f"🏆 *{attacker['name']} WON!*\n"
                f"💥 Damage: `{dmg}`",
                parse_mode="Markdown"
            )

        users.update_one(
            {"user_id": defender_id},
            {"$set": {"hp": defender["hp"]}}
        )
        fights.update_one(
            {"chat_id": chat_id},
            {"$set": {"turn": defender_id}}
        )

        await q.edit_message_text(
            f"⚔️ *Battle Ongoing*\n\n"
            f"{attacker['name']} dealt `{dmg}` damage\n\n"
            f"{attacker['name']} HP: `{attacker['hp']}`\n"
            f"{defender['name']} HP: `{defender['hp']}`\n\n"
            f"▶ Turn: {defender['name']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Attack", callback_data="attack")]
            ])
        )

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("fight", fight))
    app.add_handler(CallbackQueryHandler(callbacks))

    print("✅ Greed Island MongoDB Bot Running")
    app.run_polling()

if __name__ == "__main__":
    main()