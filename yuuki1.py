#!/usr/bin/env python3
import random
import logging
import asyncio
import httpx 
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

def owner_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in OWNER_IDS:
            return await update.message.reply_text("❌ GM Access Only.")
        return await func(update, context)
    return wrapper

# -------------------- AI CHAT --------------------
async def yuuki_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text
    if update.effective_chat.type != "private":
        if "yuuki" not in text.lower() and not (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id):
            return

    async with httpx.AsyncClient() as client_ai:
        try:
            response = await client_ai.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "moonshotai/kimi-k2-instruct-0905",
                    "messages": [{"role": "system", "content": "You are Yuuki. Reply in Hinglish. Friendly. Max 20 words."}, {"role": "user", "content": text}],
                },
                timeout=5.0
            )
            reply = response.json()["choices"][0]["message"]["content"]
            await update.message.reply_text(reply)
        except:
            pass # Silent fail to prevent crash

# -------------------- BINDER LOGIC --------------------
async def send_card_page(update, context, index, user_data, edit=False):
    if index < 0: index = 99
    if index > 99: index = 0
    
    card_id_str = f"{index:03}"
    card_info = cards.find_one({"card_id": card_id_str})
    owned = card_id_str in user_data['inventory']
    
    if not card_info:
        display = f"🎴 *Card #{card_id_str}*\n\nGM has not uploaded this card yet."
        photo = "https://via.placeholder.com/300x400?text=Locked+Slot"
    elif not owned:
        display = f"🎴 *Card #{card_id_str}*\n\nSlot Khali Hai! Search or Steal to get this."
        photo = card_info['file_id']
    else:
        display = (f"🃏 *[{card_info['name']}]*\n\n*ID:* {card_id_str}\n*Rank:* {card_info['rank']}\n*About:* {card_info['desc']}")
        photo = card_info['file_id']

    kb = [[
        InlineKeyboardButton("⬅️ Pre", callback_data=f"page_{index-1}"),
        InlineKeyboardButton(f"{index}/100", callback_data="none"),
        InlineKeyboardButton("Next ➡️", callback_data=f"page_{index+1}")
    ]]
    
    try:
        if edit:
            await update.callback_query.edit_message_media(InputMediaPhoto(photo, caption=display, parse_mode="Markdown"), reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_photo(photo, caption=display, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logging.error(f"Binder Error: {e}")

# -------------------- COMMANDS --------------------
async def book_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user)
    await send_card_page(update, context, 0, user_data)

async def collect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    all_cards = list(cards.find())
    if not all_cards:
        return await update.message.reply_text("❌ No cards available in the game yet!")
    
    found = random.choice(all_cards)
    users.update_one({"user_id": user.id}, {"$addToSet": {"inventory": found['card_id']}})
    await update.message.reply_text(f"✨ *GAIN!* You found Card #{found['card_id']}: {found['name']}!")

@owner_only
async def upload_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        return await msg.reply_text("❌ Reply to a photo with: `/upload 001 SS Name | Description`")
    try:
        raw = " ".join(context.args).split("|")
        head = raw[0].strip().split(" ", 2)
        cards.update_one({"card_id": head[0]}, {"$set": {"rank": head[1], "name": head[2], "desc": raw[1].strip(), "file_id": msg.reply_to_message.photo[-1].file_id}}, upsert=True)
        await msg.reply_text(f"✅ Card {head[0]} uploaded!")
    except:
        await msg.reply_text("❌ Use: `/upload 000 SS Name | Description`")

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_data = get_user(query.from_user)
    if query.data.startswith("page_"):
        idx = int(query.data.split("_")[1])
        await send_card_page(update, context, idx, user_data, edit=True)

# -------------------- MAIN --------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", book_cmd))
    app.add_handler(CommandHandler("book", book_cmd))
    app.add_handler(CommandHandler("collect", collect_cmd))
    app.add_handler(CommandHandler("upload", upload_card))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), yuuki_chat))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
