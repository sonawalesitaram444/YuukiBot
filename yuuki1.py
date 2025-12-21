#!/usr/bin/env python3
import os
import random
import logging
import asyncio
import requests
from datetime import datetime
from functools import wraps
from typing import Dict, Any

from pymongo import MongoClient
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ChatMember
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.error import BadRequest

# -------------------- LOGGING --------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# -------------------- CONFIG --------------------
BOT_TOKEN = "8520734510:AAFuqA-MlB59vfnI_zUQiGiRQKEJScaUyFs"
OWNER_IDS = [5773908061] 
BOT_NAME_DISPLAY = "Yuuki_GI"
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # Ensure this is set in your environment

# -------------------- MONGODB SETUP --------------------
MONGO_URI = "mongodb+srv://sonawalesitaram444_db_user:xqAwRv0ZdKMI6dDa@anixgrabber.a2tdbiy.mongodb.net/?appName=anixgrabber"
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["greed_island_db"]

users_table = mongo_db["users"]
cards_table = mongo_db["cards"] # Stores card info and file_ids
creators_table = mongo_db["approved_creators"]

# -------------------- DECORATORS --------------------
def owner_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id not in OWNER_IDS:
            return await update.message.reply_text("❌ Owner access only.")
        return await func(update, context, *args, **kwargs)
    return wrapper

# -------------------- DATABASE HELPERS --------------------
def ensure_user_record(user) -> Dict[str, Any]:
    rec = users_table.find_one({"user_id": user.id})
    if not rec:
        rec = {
            "user_id": user.id,
            "username": getattr(user, "username", None),
            "display_name": user.first_name,
            "coins": 500,
            "inventory": [], # List of Card IDs
            "registered_at": datetime.utcnow()
        }
        users_table.insert_one(rec)
    return rec

# -------------------- UPLOAD CARD SYSTEM --------------------
@owner_only
async def upload_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /upload <id> <name> <rank> (Reply to a photo)"""
    msg = update.message
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        return await msg.reply_text("❌ Reply to a card photo with: `/upload <id> <name> <rank>`")

    if len(context.args) < 3:
        return await msg.reply_text("❌ Usage: `/upload 001 Path_of_Truth SS` (Use underscores for names)")

    card_id = context.args[0]
    card_name = context.args[1].replace("_", " ")
    rank = context.args[2]
    file_id = msg.reply_to_message.photo[-1].file_id

    cards_table.update_one(
        {"card_id": card_id},
        {"$set": {
            "name": card_name,
            "rank": rank,
            "file_id": file_id
        }},
        upsert=True
    )
    await msg.reply_text(f"✅ Card `{card_id}` ({card_name}) uploaded to Greed Island database!")

# -------------------- BINDER / BOOK SYSTEM --------------------
async def book_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    rec = ensure_user_record(user)
    inventory = rec.get("inventory", [])
    
    text = (
        f"📔 *{user.first_name}'s Binder*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✨ *Specified Slots:* {len(inventory)}/100\n"
        f"💰 *Jenny:* {rec.get('coins', 0)}\n\n"
        "Browse your collection using the buttons below."
    )
    
    keyboard = [
        [InlineKeyboardButton("📖 Specified Slots", callback_data="view_page_0")],
        [InlineKeyboardButton("🔍 Inspect Card", callback_data="inspect_info")]
    ]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_binder_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    rec = users_table.find_one({"user_id": user_id})
    inventory = rec.get("inventory", [])

    if query.data.startswith("view_page_"):
        page = int(query.data.split("_")[-1])
        start_id = page * 9
        
        grid_text = f"📖 *SPECIFIED SLOTS (Page {page + 1})*\n\n"
        for i in range(start_id, start_id + 9):
            if i > 99: break
            cid = f"{i:03}"
            status = "✅" if cid in inventory else "⬜️"
            grid_text += f"`{cid}`: {status}  "
            if (i + 1) % 3 == 0: grid_text += "\n"

        buttons = []
        nav = []
        if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"view_page_{page-1}"))
        if start_id + 9 < 100: nav.append(InlineKeyboardButton("➡️", callback_data=f"view_page_{page+1}"))
        buttons.append(nav)
        buttons.append([InlineKeyboardButton("🔙 Cover", callback_data="open_cover")])

        await query.edit_message_text(grid_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# -------------------- GAIN / COLLECT SYSTEM --------------------
async def gain_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Get all available cards from DB
    all_cards = list(cards_table.find())
    if not all_cards:
        return await update.message.reply_text("❌ No cards have been uploaded to the game yet!")

    chosen = random.choice(all_cards)
    cid = chosen['card_id']
    
    users_table.update_one({"user_id": user.id}, {"$addToSet": {"inventory": cid}})
    
    caption = f"✨ *GAIN!*\n\nCard #{cid}: *{chosen['name']}*\nRank: {chosen['rank']}"
    await context.bot.send_photo(update.effective_chat.id, chosen['file_id'], caption=caption, parse_mode="Markdown")

# -------------------- YUUKI CHAT LOGIC --------------------
async def yuuki_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    user_msg = update.message.text
    chat = update.effective_chat
    
    # Simple check for reply or mention if in group
    if chat.type != "private":
        if "yuuki" not in user_msg.lower() and not (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id):
            return

    await context.bot.send_chat_action(chat_id=chat.id, action="typing")
    
    # Placeholder for AI API call
    # In a real scenario, use the GROQ logic from your previous snippet here
    bot_reply = f"Kya hua bhai? Main abhi Greed Island khel raha hoon. 🃏"
    await update.message.reply_text(bot_reply)

# -------------------- MAIN APP --------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", book_cmd))
    app.add_handler(CommandHandler("book", book_cmd))
    app.add_handler(CommandHandler("gain", gain_cmd))
    app.add_handler(CommandHandler("upload", upload_card))
    
    # Callback Handlers
    app.add_handler(CallbackQueryHandler(handle_binder_pages, pattern="^view_page_"))
    
    # Chat Handler (Filters out commands)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), yuuki_chat))

    print("Greed Island Bot is Online...")
    app.run_polling()

if __name__ == "__main__":
    main()
