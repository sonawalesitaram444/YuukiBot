#!/usr/bin/env python3
import random
import logging
import httpx
from functools import wraps
from pymongo import MongoClient
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================== CONFIG ==================
BOT_TOKEN = "8520734510:AAFuqA-MlB59vfnI_zUQiGiRQKEJScaUyFs"
GROQ_API_KEY = "YOUR_GROQ_KEY"
OWNER_IDS = [5773908061]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ================== MONGODB ==================
client = MongoClient(
    "mongodb+srv://sonawalesitaram444_db_user:xqAwRv0ZdKMI6dDa@anixgrabber.a2tdbiy.mongodb.net/?appName=anixgrabber"
)
db = client["greed_island_ultra"]
users = db["users"]
cards = db["cards"]

# ================== HELPERS ==================
def get_user(user):
    data = users.find_one({"user_id": user.id})
    if not data:
        data = {
            "user_id": user.id,
            "name": user.first_name,
            "hp": 100,
            "aura": 100,
            "coins": 1000,
            "inventory": []
        }
        users.insert_one(data)
    return data


def owner_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in OWNER_IDS:
            await update.message.reply_text("❌ GM Access Only.")
            return
        return await func(update, context)
    return wrapper

# ================== START ==================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏝️ **Greed Island Ultra**\n\n"
        "Commands:\n"
        "/book – Card Binder\n"
        "/collect – Find a card\n\n"
        "Yuuki is online 😎",
        parse_mode="Markdown"
    )

# ================== AI CHAT ==================
async def yuuki_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    chat = update.effective_chat

    # Group filter
    if chat.type != "private":
        if "yuuki" not in text.lower() and not (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user.id == context.bot.id
        ):
            return

    reply_text = "Haan bol 😄 kya scene hai?"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client_ai:
            response = await client_ai.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "moonshotai/kimi-k2-instruct-0905",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are Yuuki. Reply in Hinglish. Friendly. Max 20 words."
                        },
                        {"role": "user", "content": text}
                    ]
                }
            )
            reply_text = response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        logging.error(f"AI Error: {e}")

    await update.message.reply_text(reply_text)

# ================== BINDER ==================
async def send_card_page(update, context, index, user_data, edit=False):
    if index < 0:
        index = 99
    if index > 99:
        index = 0

    card_id = f"{index:03}"
    card = cards.find_one({"card_id": card_id})
    owned = card_id in user_data["inventory"]

    if not card:
        text = f"🎴 *Card #{card_id}*\n\nGM has not uploaded this card yet."
        photo = "https://via.placeholder.com/300x400?text=Locked"
    elif not owned:
        text = f"🎴 *Card #{card_id}*\n\nSlot khali hai!"
        photo = card["file_id"]
    else:
        text = (
            f"🃏 *{card['name']}*\n\n"
            f"*ID:* {card_id}\n"
            f"*Rank:* {card['rank']}\n"
            f"*About:* {card['desc']}"
        )
        photo = card["file_id"]

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️", callback_data=f"page_{index-1}"),
            InlineKeyboardButton(f"{index}/100", callback_data="noop"),
            InlineKeyboardButton("➡️", callback_data=f"page_{index+1}")
        ]
    ])

    if edit:
        await update.callback_query.edit_message_media(
            InputMediaPhoto(photo, caption=text, parse_mode="Markdown"),
            reply_markup=keyboard
        )
    else:
        await update.message.reply_photo(
            photo,
            caption=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

# ================== COMMANDS ==================
async def book_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user)
    await send_card_page(update, context, 0, user)


async def collect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    all_cards = list(cards.find())

    if not all_cards:
        await update.message.reply_text("❌ No cards available.")
        return

    found = random.choice(all_cards)
    users.update_one(
        {"user_id": user.id},
        {"$addToSet": {"inventory": found["card_id"]}}
    )

    await update.message.reply_text(
        f"✨ You found *{found['name']}* (#{found['card_id']})",
        parse_mode="Markdown"
    )

@owner_only
async def upload_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await msg.reply_text("Reply to a photo with:\n/upload 001 SS Name | Description")
        return

    try:
        raw = " ".join(context.args).split("|")
        head = raw[0].strip().split(" ", 2)

        cards.update_one(
            {"card_id": head[0]},
            {
                "$set": {
                    "rank": head[1],
                    "name": head[2],
                    "desc": raw[1].strip(),
                    "file_id": msg.reply_to_message.photo[-1].file_id
                }
            },
            upsert=True
        )

        await msg.reply_text(f"✅ Card {head[0]} uploaded")

    except:
        await msg.reply_text("❌ Format error.")

# ================== CALLBACK ==================
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()
    user = get_user(query.from_user)

    if query.data.startswith("page_"):
        idx = int(query.data.split("_")[1])
        await send_card_page(update, context, idx, user, edit=True)

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("book", book_cmd))
    app.add_handler(CommandHandler("collect", collect_cmd))
    app.add_handler(CommandHandler("upload", upload_card))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, yuuki_chat))

    logging.info("Greed Island Ultra Bot Started")
    app.run_polling()

if __name__ == "__main__":
    main()