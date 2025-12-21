#!/usr/bin/env python3
import random
import logging
import asyncio
import httpx  # Faster than 'requests' for bots
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
GROQ_API_KEY = "YOUR_GROQ_KEY" # Add your key here

# -------------------- MONGODB --------------------
client = MongoClient("mongodb+srv://sonawalesitaram444_db_user:xqAwRv0ZdKMI6dDa@anixgrabber.a2tdbiy.mongodb.net/?appName=anixgrabber")
db = client["greed_island_ultra"]
users = db["users"]
cards = db["cards"]

# -------------------- HELPERS --------------------
def get_user(user):
    data = users.find_one({"user_id": user.id})
    if not data:
        data = {"user_id": user.id, "name": user.first_name, "hp": 100, "aura": 100, "location": "Antokiba", "inventory": [], "coins": 1000}
        users.insert_one(data)
    return data

# -------------------- SPEED FIX: ASYNC AI CHAT --------------------
async def yuuki_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text
    chat = update.effective_chat
    
    # Only reply if DM or Mentioned
    if chat.type != "private":
        if "yuuki" not in text.lower() and not (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id):
            return

    await context.bot.send_chat_action(chat_id=chat.id, action="typing")
    
    # Using Async client so the bot doesn't "freeze"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "moonshotai/kimi-k2-instruct-0905",
                    "messages": [{"role": "system", "content": "You are Yuuki. Reply in Hinglish. Max 20 words. Friendly and cool."}, {"role": "user", "content": text}],
                },
                timeout=5.0
            )
            reply = response.json()["choices"][0]["message"]["content"]
        except:
            reply = "Network issue hai shayad! 😪"
    
    await update.message.reply_text(reply)

# -------------------- CORE GAME COMMANDS --------------------

async def book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user)
    await send_card_page(update, context, 0, user_data)

async def send_card_page(update, context, index, user_data, edit=False):
    card_id_str = f"{index:03}"
    card_info = cards.find_one({"card_id": card_id_str})
    owned = card_id_str in user_data['inventory']
    
    if not card_info:
        display = f"🎴 *Card #{card_id_str}*\n\nNot uploaded yet."
        photo = "https://via.placeholder.com/300x400?text=No+Data"
    elif not owned:
        display = f"🎴 *Card #{card_id_str}*\n\nSlot Khali Hai!"
        photo = card_info['file_id']
    else:
        display = (f"🃏 *[{card_info['name']}]*\n\n*ID:* {card_id_str}\n*Rank:* {card_info['rank']}\n*About:* {card_info['desc']}")
        photo = card_info['file_id']

    kb = [[
        InlineKeyboardButton("⬅️ Pre", callback_data=f"page_{index-1}"),
        InlineKeyboardButton(f"{index}/100", callback_data="none"),
        InlineKeyboardButton("Next ➡️", callback_data=f"page_{index+1}")
    ]]
    
    if edit:
        await update.callback_query.edit_message_media(InputMediaPhoto(photo, caption=display, parse_mode="Markdown"), reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_photo(photo, caption=display, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# -------------------- STEAL SYSTEM (BATTLE) --------------------
async def steal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user)
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to a player to steal from them!")
    
    victim = get_user(update.message.reply_to_message.from_user)
    if not victim['inventory']:
        return await update.message.reply_text("❌ This player has no cards to steal!")

    # 30% success rate
    if random.random() < 0.3:
        stolen_card = random.choice(victim['inventory'])
        users.update_one({"user_id": victim['user_id']}, {"$pull": {"inventory": stolen_card}})
        users.update_one({"user_id": user['user_id']}, {"$addToSet": {"inventory": stolen_card}})
        await update.message.reply_text(f"⚔️ *SUCCESS!* You stole Card #{stolen_card} from {victim['name']}!")
    else:
        await update.message.reply_text("🛡️ *FAILED!* The player defended their binder.")

# -------------------- MAIN --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎮 *Welcome to Greed Island!*\nUse /book to open your binder and /collect to find cards.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Game Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("book", book))
    app.add_handler(CommandHandler("steal", steal))
    app.add_handler(CommandHandler("collect", book)) # Placeholder for collect logic
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_callbacks)) # Reuse handle_callbacks logic
    
    # AI Chat
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), yuuki_chat))

    app.run_polling()

if __name__ == "__main__":
    main()
