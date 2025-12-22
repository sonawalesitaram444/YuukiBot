#!/usr/bin/env python3
# ===============================
# GREED ISLAND – NORMAL WORLD CORE
# ===============================

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
    ContextTypes,
    filters
)

# ---------------- CONFIG ----------------
BOT_TOKEN = "8312215148:AAEYp1kZGcWn6pgWSxp8qgA_MR4i9HkfvWo"
OWNER_IDS = [5773908061]

MONGO_URI = "mongodb+srv://sonawalesitaram444_db_user:xqAwRv0ZdKMI6dDa@anixgrabber.a2tdbiy.mongodb.net/?appName=anixgrabber"

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- DATABASE ----------------
mongo = MongoClient(MONGO_URI)
db = mongo["greed_island"]
users = db["users"]

# ---------------- MEMORY ----------------
ACTIVE_FIGHTS = {}

# ---------------- HELPERS ----------------
def hp_bar(current, max_hp, size=20):
    filled = int(size * current / max_hp)
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
            "defence": 200,
            "money": 600,
            "gi_money": None,
            "special_skill": None,
            "in_gi": False,
            "location": chat.title if chat else "Private"
        }
        users.insert_one(data)
    return data

def save_user(user_id, data):
    users.update_one({"user_id": user_id}, {"$set": data})

# ---------------- START ----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    get_user(user, chat)
    await update.message.reply_text(
        "🌍 Welcome to the World.\n\n"
        "This is the NORMAL WORLD.\n"
        "Greed Island awaits those worthy."
    )

# ---------------- PROFILE ----------------
async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    data = get_user(user, chat)

    hp_text = hp_bar(data["hp"], data["max_hp"])

    text = (
        f"👤 **{data['name']}**\n\n"
        f"❤️ HP\n"
        f"`{hp_text}` {data['hp']}/{data['max_hp']}\n\n"
        f"⚡ Nen : `{data['nen']}`\n"
        f"💪 Strength : `{data['strength']}`\n"
        f"💴 Jenny : `{data['money']}`\n"
        f"🎮 GI Money : `{data['gi_money'] or 'None'}`\n"
        f"🌀 Special Skill : `{data['special_skill'] or 'None'}`\n"
        f"📍 Location : `{chat.title if chat else 'Private'}`"
    )

    await update.message.reply_text(text, parse_mode="Markdown")

# ---------------- FIGHT REQUEST ----------------
async def fight_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = msg.from_user

    if not msg.reply_to_message:
        return await msg.reply_text("❌ Reply to someone to fight.")

    target = msg.reply_to_message.from_user
    if target.id == user.id:
        return await msg.reply_text("❌ You can’t fight yourself.")

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"fight_accept:{user.id}"),
            InlineKeyboardButton("❌ Decline", callback_data="fight_decline")
        ]
    ])

    await msg.reply_text(
        f"⚔️ Fight Request!\n\n"
        f"{target.first_name}, you got a fight request from {user.first_name}",
        reply_markup=kb
    )

# ---------------- FIGHT CALLBACK ----------------
async def fight_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat.id
    await query.answer()

    if query.data == "fight_decline":
        return await query.edit_message_text("❌ Fight declined.")

    if query.data.startswith("fight_accept"):
        attacker_id = int(query.data.split(":")[1])

        p1 = users.find_one({"user_id": attacker_id})
        p2 = users.find_one({"user_id": user.id})

        if not p1 or not p2:
            return await query.edit_message_text("❌ Player data missing.")

        ACTIVE_FIGHTS[chat_id] = {
            "p1": attacker_id,
            "p2": user.id,
            "turn": attacker_id
        }

        await show_fight_ui(query, p1, p2)

# ---------------- FIGHT UI ----------------
async def show_fight_ui(query, p1, p2):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Attack", callback_data="fight_attack"),
            InlineKeyboardButton("🛡 Defend", callback_data="fight_defend")
        ]
    ])

    await query.edit_message_text(
        f"⚔️ **FIGHT STARTED**\n\n"
        f"{p1['name']} vs {p2['name']}\n\n"
        f"{p1['name']} HP: {p1['hp']}/{p1['max_hp']}\n"
        f"{p2['name']} HP: {p2['hp']}/{p2['max_hp']}\n\n"
        f"▶ Turn: {p1['name']}",
        parse_mode="Markdown",
        reply_markup=kb
    )

# ---------------- FIGHT ACTION ----------------
async def fight_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat.id
    await query.answer()

    if chat_id not in ACTIVE_FIGHTS:
        return

    fight = ACTIVE_FIGHTS[chat_id]
    if fight["turn"] != user.id:
        return await query.answer("Not your turn!", show_alert=True)

    attacker = users.find_one({"user_id": user.id})
    defender_id = fight["p2"] if fight["p1"] == user.id else fight["p1"]
    defender = users.find_one({"user_id": defender_id})

    dmg = max(50, attacker["strength"] // 10)
    defender["hp"] -= dmg

    if defender["hp"] <= 0:
        await end_fight(query, attacker, defender)
        return

    save_user(defender_id, defender)
    fight["turn"] = defender_id

    await query.edit_message_text(
        f"⚔️ Fight Ongoing\n\n"
        f"{attacker['name']} dealt `{dmg}` damage!\n\n"
        f"{attacker['name']} HP: {attacker['hp']}\n"
        f"{defender['name']} HP: {defender['hp']}\n\n"
        f"▶ Turn: {defender['name']}",
        parse_mode="Markdown",
        reply_markup=query.message.reply_markup
    )

# ---------------- END FIGHT ----------------
async def end_fight(query, winner, loser):
    text = f"🏆 **{winner['name']} WON!**\n\n"

    if loser.get("in_gi"):
        loser["in_gi"] = False
        loser["gi_money"] = None
        text += "☠️ You died in Greed Island.\nAll progress lost.\n"

    loser["hp"] = loser["max_hp"]
    winner["money"] += 200

    save_user(loser["user_id"], loser)
    save_user(winner["user_id"], winner)

    del ACTIVE_FIGHTS[query.message.chat.id]

    await query.edit_message_text(text, parse_mode="Markdown")

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CommandHandler("fight", fight_cmd))

    app.add_handler(CallbackQueryHandler(fight_action, pattern="fight_"))
    app.add_handler(CallbackQueryHandler(fight_callback))

    print("Greed Island Core running...")
    app.run_polling()

if __name__ == "__main__":
    main()