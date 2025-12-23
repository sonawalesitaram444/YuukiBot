#!/usr/bin/env python3
# =========================================
# GREED ISLAND – NORMAL WORLD (FIXED CORE)
# =========================================

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

# ---------- CONFIG ----------
BOT_TOKEN = "8520734510:AAFuqA-MlB59vfnI_zUQiGiRQKEJScaUyFs"
MONGO_URI = "mongodb+srv://sonawalesitaram444_db_user:xqAwRv0ZdKMI6dDa@anixgrabber.a2tdbiy.mongodb.net/?appName=anixgrabber"

# ---------- LOGGING ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- DATABASE ----------
mongo = MongoClient(MONGO_URI)
db = mongo["greed_island"]
users = db["users"]

# ---------- MEMORY ----------
ACTIVE_FIGHTS = {}

# ---------- HELPERS ----------
def hp_bar(cur, max_hp, size=20):
    filled = int(size * cur / max_hp)
    return "█" * filled + "░" * (size - filled)

def get_user(user, chat):
    data = users.find_one({"user_id": user.id})
    if not data:
        data = {
            "user_id": user.id,
            "name": user.first_name,
            "hp": 1000,
            "max_hp": 1000,
            "nen": 0,
            "strength": 1000,
            "money": 600,
            "gi_money": None,
            "in_gi": False
        }
        users.insert_one(data)
    return data

def save(uid, data):
    users.update_one({"user_id": uid}, {"$set": data})

# ---------- START ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user, update.effective_chat)
    await update.message.reply_text(
        "🌍 Welcome to the World.\n\n"
        "Use /profile to see your stats.\n"
        "Use /fight (reply) to battle."
    )

# ---------- PROFILE ----------
async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user, update.effective_chat)

    text = (
        f"👤 **{u['name']}**\n\n"
        f"❤️ HP\n`{hp_bar(u['hp'], u['max_hp'])}` {u['hp']}/{u['max_hp']}\n\n"
        f"⚡ Nen : `{u['nen']}`\n"
        f"💪 Strength : `{u['strength']}`\n"
        f"💴 Jenny : `{u['money']}`\n"
        f"🎮 GI Money : `{u['gi_money'] or 'None'}`"
    )

    await update.message.reply_text(text, parse_mode="Markdown")

# ---------- FIGHT ----------
async def fight_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message:
        return await msg.reply_text("❌ Reply to someone to fight.")

    challenger = msg.from_user
    target = msg.reply_to_message.from_user

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"accept:{challenger.id}"),
            InlineKeyboardButton("❌ Decline", callback_data="decline")
        ]
    ])

    await msg.reply_text(
        f"⚔️ **Fight Request**\n\n"
        f"{target.first_name}, {challenger.first_name} wants to fight!",
        parse_mode="Markdown",
        reply_markup=kb
    )

# ---------- CALLBACK HANDLER (FIXED) ----------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    chat_id = q.message.chat.id
    user = q.from_user

    # DECLINE
    if q.data == "decline":
        return await q.edit_message_text("❌ Fight declined.")

    # ACCEPT
    if q.data.startswith("accept:"):
        attacker_id = int(q.data.split(":")[1])
        defender_id = user.id

        p1 = users.find_one({"user_id": attacker_id})
        p2 = users.find_one({"user_id": defender_id})

        ACTIVE_FIGHTS[chat_id] = {
            "p1": attacker_id,
            "p2": defender_id,
            "turn": attacker_id
        }

        return await show_fight(q, p1, p2)

    # ATTACK
    if q.data == "attack":
        fight = ACTIVE_FIGHTS.get(chat_id)
        if not fight or fight["turn"] != user.id:
            return

        atk = users.find_one({"user_id": user.id})
        def_id = fight["p2"] if fight["p1"] == user.id else fight["p1"]
        dfd = users.find_one({"user_id": def_id})

        dmg = random.randint(80, 150) + atk["strength"] // 20
        dfd["hp"] -= dmg

        if dfd["hp"] <= 0:
            dfd["hp"] = dfd["max_hp"]
            save(def_id, dfd)
            save(atk["user_id"], atk)
            del ACTIVE_FIGHTS[chat_id]
            return await q.edit_message_text(
                f"🏆 **{atk['name']} WON!**\n\n"
                f"💥 Damage: `{dmg}`",
                parse_mode="Markdown"
            )

        save(def_id, dfd)
        fight["turn"] = def_id

        return await q.edit_message_text(
            f"⚔️ **Fight Ongoing**\n\n"
            f"{atk['name']} hit `{dmg}` damage!\n\n"
            f"{atk['name']} HP: {atk['hp']}\n"
            f"{dfd['name']} HP: {dfd['hp']}\n\n"
            f"▶ Turn: {dfd['name']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Attack", callback_data="attack")]
            ])
        )

# ---------- SHOW FIGHT ----------
async def show_fight(q, p1, p2):
    await q.edit_message_text(
        f"⚔️ **FIGHT STARTED**\n\n"
        f"{p1['name']} vs {p2['name']}\n\n"
        f"▶ Turn: {p1['name']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Attack", callback_data="attack")]
        ])
    )

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CommandHandler("fight", fight_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("✅ Greed Island Core Running")
    app.run_polling()

if __name__ == "__main__":
    main()