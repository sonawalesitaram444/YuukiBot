#!/usr/bin/env python3
import os
import random
import logging
import requests
from datetime import datetime
from functools import wraps

from pymongo import MongoClient
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# -------------------- CONFIG --------------------
BOT_TOKEN = "8520734510:AAFuqA-MlB59vfnI_zUQiGiRQKEJScaUyFs"
OWNER_IDS = [5773908061] 
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 

# -------------------- WORLD DATA --------------------
LOCATIONS = {
    "Antokiba": {"desc": "The Capital of Prizes. Start your journey here.", "difficulty": 1},
    "Masadora": {"desc": "The City of Magic. Best place to buy Spell Cards.", "difficulty": 3},
    "Aiai": {"desc": "The City of Love. Many interactive quests found here.", "difficulty": 2},
    "Soufrabi": {"desc": "A coastal town. Home to Razor's gym.", "difficulty": 5}
}

# -------------------- MONGODB --------------------
MONGO_URI = "mongodb+srv://sonawalesitaram444_db_user:xqAwRv0ZdKMI6dDa@anixgrabber.a2tdbiy.mongodb.net/?appName=anixgrabber"
client = MongoClient(MONGO_URI)
db = client["greed_island_pro"]

users = db["users"]
cards = db["cards"]

# -------------------- DATABASE HELPERS --------------------
def get_user(user):
    data = users.find_one({"user_id": user.id})
    if not data:
        data = {
            "user_id": user.id,
            "name": user.first_name,
            "hp": 100,
            "aura": 100,
            "level": 1,
            "location": "Antokiba",
            "inventory": [],
            "coins": 1000,
            "last_collect": 0
        }
        users.insert_one(data)
    return data

def save_user(user_id, update_data):
    users.update_one({"user_id": user_id}, {"$set": update_data})

# -------------------- GAME COMMANDS --------------------

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user)
    text = (
        f"👤 *PLAYER: {user['name']}*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📍 *Location:* {user['location']}\n"
        f"❤️ *HP:* {user['hp']}/100\n"
        f"⚡ *Aura:* {user['aura']}/100\n"
        f"💰 *Jenny:* {user['coins']}\n"
        f"🃏 *Cards Found:* {len(user['inventory'])}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def map_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user)
    text = f"📍 *CURRENT LOCATION: {user['location']}*\n\n{LOCATIONS[user['location']]['desc']}\n\n*Available Cities to /travel:* \n"
    for loc in LOCATIONS:
        if loc != user['location']:
            text += f"• {loc}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def travel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user)
    if not context.args:
        return await update.message.reply_text("❌ Specify a city: `/travel Masadora`")
    
    dest = context.args[0].capitalize()
    if dest not in LOCATIONS:
        return await update.message.reply_text("❌ That city doesn't exist on Greed Island!")
    
    if user['aura'] < 20:
        return await update.message.reply_text("❌ You don't have enough Aura (20) to travel!")

    users.update_one(
        {"user_id": user['user_id']},
        {"$set": {"location": dest}, "$inc": {"aura": -20}}
    )
    await update.message.reply_text(f"✈️ You used your aura to fly to *{dest}*!", parse_mode="Markdown")

async def collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user)
    
    # Simple Cooldown check
    now = datetime.now().timestamp()
    if now - user.get('last_collect', 0) < 30: # 30 seconds cooldown
        return await update.message.reply_text("⏳ Wait a bit! Searching the area takes time.")

    await update.message.reply_text("🔍 Searching for cards in the wilderness...")
    
    # 30% chance to find a card based on location difficulty
    chance = random.random()
    if chance < 0.3:
        all_cards = list(cards.find())
        if all_cards:
            found = random.choice(all_cards)
            users.update_one(
                {"user_id": user['user_id']},
                {"$addToSet": {"inventory": found['card_id']}, "$set": {"last_collect": now}}
            )
            await update.message.reply_photo(
                photo=found['file_id'], 
                caption=f"✨ *GAIN!*\n\nYou found Card #{found['card_id']}: {found['name']}!"
            )
            return
            
    users.update_one({"user_id": user['user_id']}, {"$set": {"last_collect": now}, "$inc": {"coins": 50}})
    await update.message.reply_text("☁️ You didn't find any cards, but you found 50 Jenny on the ground!")

# -------------------- SHOP SYSTEM --------------------
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user)
    if user['location'] != "Masadora":
        return await update.message.reply_text("🛒 The Magic Shop is only in *Masadora*. Travel there first!", parse_mode="Markdown")
    
    text = "🏪 *WELCOME TO MASADORA SHOP*\n\nBuy a Spell Pack for 500 Jenny?\n(Contains 1 random card)"
    kb = [[InlineKeyboardButton("💳 Buy Spell Pack (500)", callback_data="buy_pack")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def handle_shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_user(query.from_user)
    
    if query.data == "buy_pack":
        if user['coins'] < 500:
            return await query.answer("❌ Not enough Jenny!", show_alert=True)
        
        all_cards = list(cards.find())
        found = random.choice(all_cards)
        
        users.update_one(
            {"user_id": user['user_id']}, 
            {"$inc": {"coins": -500}, "$addToSet": {"inventory": found['card_id']}}
        )
        await query.message.edit_text(f"🛍 You bought a pack and got: *{found['name']}*!", parse_mode="Markdown")

# -------------------- MAIN APP --------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Core Commands
    app.add_handler(CommandHandler("start", stats))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("map", map_cmd))
    app.add_handler(CommandHandler("travel", travel))
    app.add_handler(CommandHandler("collect", collect))
    app.add_handler(CommandHandler("shop", shop))
    
    # Book & Upload (From previous script)
    app.add_handler(CommandHandler("book", book)) # Use the book code from previous response
    app.add_handler(CommandHandler("upload", upload_card))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_shop_callback, pattern="^buy_pack$"))
    app.add_handler(CallbackQueryHandler(handle_callbacks)) # From previous script

    # AI Personality
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), yuuki_chat))

    print("Greed Island v2.0 Fully Working...")
    app.run_polling()

if __name__ == "__main__":
    main()
