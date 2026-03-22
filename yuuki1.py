#!/usr/bin/env python3

import os
import re
import logging
import random
import pytz
import base64
import io
from io import BytesIO

import requests
import httpx
from telegram.constants import ParseMode
from fastapi import FastAPI, Request  # <--- Added for Webhooks
from pymongo import MongoClient

from telegram import InputSticker, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from motor.motor_asyncio import AsyncIOMotorClient

from datetime import datetime, timezone

# ================= WEBHOOK SETUP =================
app = FastAPI() # <--- This is your "Web Server"
BOT_START_TIME = datetime.now(timezone.utc)

# ================= TERMUX +srv FIX =================
import dns.resolver

# ======Resolver======
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1']

# ================= ALL_CONFIGS =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = "yuuri"
OWNER_ID = int(os.getenv("OWNER_ID"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
#--

OWNER_ID = 7139383373
OWNER_IDS = 5773908061

# ================= MONGODB =================
# Use AsyncIOMotorClient for everything so 'await' works
async_client = AsyncIOMotorClient(MONGO_URI)
db = async_client["yuuri_db"]

# All these now support 'await'
users = db["users"]
guilds = db["guilds"]
sticker_packs = db["sticker_packs"]
heists = db["heists"]
redeem_col = db["redeem_codes"]

# Management Db Collection
admins_db = db["admins"] 
torture_db = db["torture_registry"]
allowed_collection = db["allowed_users"] 
groups_collection = db["saved_groups"]

# ================= LOG =================
logging.basicConfig(level=logging.INFO)

#===========Systems========
#--
# ================= MONGODB (SYNC FIX) =================
# We switch back to MongoClient so 'await' is NOT required
from pymongo import MongoClient

client = MongoClient(MONGO_URI)
db = client["yuuri_db"]

# Collections
users = db["users"]
guilds = db["guilds"]
sticker_packs = db["sticker_packs"]
heists = db["heists"]
redeem_col = db["redeem_codes"]
admins_db = db["admins"] 
torture_db = db["torture_registry"]
allowed_collection = db["allowed_users"] 
groups_collection = db["saved_groups"]

# ================= USER SYSTEM (SYNC FIX) =================
def get_user(user):
    # No 'await' here. Returns a dictionary immediately.
    data = users.find_one({"id": user.id})

    default_data = {
        "id": user.id,
        "name": user.first_name,
        "coins": 100,
        "xp": 0,
        "level": 1,
        "kills": 0,
        "guild": None,
        "dead": False,
        "inventory": [],
        "referred_by": None,
        "blocked": False,
        "premium": False
    }

    if not data:
        users.insert_one(default_data)
        return default_data

    updated_fields = {}
    if data.get("name") != user.first_name:
        data["name"] = user.first_name
        updated_fields["name"] = user.first_name

    for key, value in default_data.items():
        if key not in data:
            data[key] = value
            updated_fields[key] = value

    if updated_fields:
        users.update_one({"id": user.id}, {"$set": updated_fields})

    return data

def save_user(data):
    # No 'await' here.
    users.update_one({"id": data["id"]}, {"$set": data}, upsert=True)

# ======Broadcast_System======
import asyncio
import time
from telegram import Update
from telegram.ext import ContextTypes

# Broadcast control dictionary
broadcast_control = {"running": False, "cancel": False}

# ========== UPDATED LEVEL SYSTEM ========
# Updated Leveling Config
def add_xp(user_data, amount):
    user_data["xp"] += amount
    leveled_up = False

    # Use a 'while' loop instead of 'if' 
    # This catches users who gain 1000 XP at once!
    while True:
        need = int(100 * (1.5 ** (user_data["level"] - 1)))
        if user_data["xp"] >= need:
            user_data["xp"] -= need # Subtract the 'cost' of the level
            user_data["level"] += 1
            leveled_up = True
        else:
            break # User doesn't have enough XP for the next level

    save_user(user_data)
    return leveled_up

# Re-balanced Ranks (Harder to reach "Immortal")
RANKS = [
    {"name": "Nᴏᴏʙ", "lvl": 1},
    {"name": "Bᴇɢɪɴɴᴇʀ", "lvl": 5},
    {"name": "Fɪɢʜᴛᴇʀ", "lvl": 10},
    {"name": "Wᴀʀʀɪᴏʀ", "lvl": 20},
    {"name": "Eʟɪᴛᴇ", "lvl": 35},
    {"name": "Mᴀsᴛᴇʀ", "lvl": 55},
    {"name": "Lᴇɢᴇɴᴅ", "lvl": 80},
    {"name": "Mʏᴛʜɪᴄ", "lvl": 110},
    {"name": "Iᴍᴍᴏʀᴛᴀʟ", "lvl": 150},
]

def get_rank_data(level):
    """Finds rank based on current Level instead of total XP"""
    current_rank = RANKS[0]
    next_rank = None

    for i, rank in enumerate(RANKS):
        if level >= rank["lvl"]:
            current_rank = rank
            if i + 1 < len(RANKS):
                next_rank = RANKS[i + 1]
        else:
            break
    return current_rank, next_rank

# ====== PROGRESS BAR =======
def create_progress_bar(percent):
    bars = 10
    # Ensure percent doesn't break the bar if it's over 100
    percent = min(max(percent, 0), 100)
    filled = int(bars * percent / 100)
    empty = bars - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {percent}%"

#=========The_Important_System========
#--
# ======= AUTO SAVE CHATS =======
async def save_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat:
        return

    # Upsert chat document
    db["chats"].update_one(
        {"id": chat.id},
        {"$set": {
            "id": chat.id,
            "type": chat.type,  # "private", "group", "supergroup"
            "title": getattr(chat, "title", None)
        }},
        upsert=True
    )

def increment_warns(user_id):
    # Increments warning count and returns the new total
    res = users_collection.find_one_and_update(
        {"user_id": user_id},
        {"$inc": {"warns": 1}},
        upsert=True,
        return_document=True
    )
    return res.get("warns", 0)

def is_allowed(user_id):
    # Checks if user is in the whitelist
    user = allowed_collection.find_one({"user_id": user_id})
    return True if user else False


#========fonts-command========
# Small Caps and Bold Mappings
SMALL_CAPS = {"a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ꜰ", "g": "ɢ", "h": "ʜ", "i": "ɪ", "j": "ᴊ", "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ", "o": "ᴏ", "p": "ᴘ", "q": "ǫ", "r": "ʀ", "s": "ꜱ", "t": "ᴛ", "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ", "z": "ᴢ"}

BOLD_SERIF = {
    "a": "𝐚", "b": "𝐛", "c": "𝐜", "d": "𝐝", "e": "𝐞", "f": "𝐟", "g": "𝐠", "h": "𝐡", "i": "𝐢", "j": "𝐣", "k": "𝐤", "l": "𝐥", "m": "𝐦", "n": "𝐧", "o": "𝐨", "p": "𝐩", "q": "𝐪", "r": "𝐫", "s": "𝐬", "t": "𝐭", "u": "𝐮", "v": "𝐯", "w": "𝐰", "x": "𝐱", "y": "𝐲", "z": "𝐳",
    "A": "𝐀", "B": "𝐁", "C": "𝐂", "D": "𝐃", "E": "𝐄", "F": "𝐅", "G": "𝐆", "H": "𝐇", "I": "𝐈", "J": "𝐉", "K": "𝐊", "L": "𝐋", "M": "𝐌", "N": "𝐍", "O": "𝐎", "P": "𝐏", "Q": "𝐐", "R": "𝐑", "S": "𝐒", "T": "𝐓", "U": "𝐔", "V": "𝐕", "W": "𝐖", "X": "𝐗", "Y": "𝐘", "Z": "𝐙"
}

def get_fancy_text(text, font_type):
    words = text.split(" ")
    final_output = []

    for word in words:
        if not word:
            final_output.append("")
            continue

        new_word = ""
        for i, char in enumerate(word):
            low_char = char.lower()

            if font_type == "1":
                # ALL SMALL CAPS: ɴɪᴄᴇ ꜱᴇᴛᴜᴘ
                new_word += SMALL_CAPS.get(low_char, char)

            elif font_type == "2":
                # FIRST LETTER CAPS + REST SMALL CAPS: Nɪᴄᴇ Sᴇᴛᴜᴘ
                if i == 0:
                    new_word += char.upper()
                else:
                    new_word += SMALL_CAPS.get(low_char, char)

            elif font_type == "3":
                # FIRST LETTER BOLD + REST SMALL CAPS: 𝐧ɪ𝐜ᴇ 𝐬ᴇ𝐭𝐮𝐩
                if i == 0:
                    new_word += BOLD_SERIF.get(low_char, char)
                else:
                    new_word += SMALL_CAPS.get(low_char, char)
            else:
                new_word += char

        final_output.append(new_word)

    return " ".join(final_output)

# Helper functions for MongoDB
def is_tortured(user_id, torture_type):
    """Checks if a user is currently targeted in DB"""
    return torture_db.find_one({"id": user_id, "type": torture_type}) is not None

def toggle_torture(user_id, torture_type):
    """Adds to DB if missing, removes if exists. Returns True if added."""
    query = {"id": user_id, "type": torture_type}
    existing = torture_db.find_one(query)
    if existing:
        torture_db.delete_one(query)
        return False
    else:
        torture_db.insert_one(query)
        return True

def clear_all_torture():
    """Wipes the entire torture registry"""
    torture_db.delete_many({})

#============ Side_Features ========
#--
# ================= REDEEM SYSTEM =================
async def create_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/create <code> <limit> <type:value> - Owner Only"""
    if update.effective_user.id != OWNER_IDS:
        return

    if len(context.args) < 3:
        usage = (
            "📑 𝗖𝗿𝗲𝗮𝘁𝗲 𝗥𝗲𝗱𝗲𝗲𝗺 𝗖𝗼𝗱𝗲\n\n"
            "Usage: `/create <code> <limit> <type:value>`\n"
            "Types: `coins` or `item`\n\n"
            "Examples:\n"
            "• `/create GIFT10 5 coins:5000`\n"
            "• `/create TEDDY 1 item:Teddy 🧸`"
        )
        return await update.message.reply_text(usage, parse_mode="Markdown")

    code = context.args[0].upper()
    try:
        limit = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("❌ Lɪᴍɪᴛ ᴍᴜsᴛ ʙᴇ ᴀ ɴᴜᴍʙᴇʀ!")

    reward_raw = context.args[2]
    if ":" not in reward_raw:
        return await update.message.reply_text("❌ Fᴏʀᴍᴀᴛ ᴍᴜsᴛ ʙᴇ `type:value` (e.g., `coins:100`)!")

    # Save to MongoDB
    redeem_col.update_one(
        {"code": code},
        {"$set": {
            "code": code,
            "limit": limit,
            "used_by": [],
            "reward": reward_raw,
            "created_at": datetime.now()
        }},
        upsert=True
    )

    await update.message.reply_text(
        f"✅ 𝗥𝗲𝗱𝗲𝗲𝗺 𝗖𝗼𝗱𝗲 𝗖𝗿𝗲𝗮𝘁𝗲𝗱\n\n"
        f"🎫 Cᴏᴅᴇ : `{code}`\n"
        f"👥 Lɪᴍɪᴛ : `{limit}`\n"
        f"🎁 Rᴇᴡᴀʀᴅ : `{reward_raw}`",
        parse_mode="Markdown"
    )

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/redeem <code> - For Users"""
    user = update.effective_user
    msg = update.effective_message

    # 1. FIXED USAGE: Correct check for empty arguments
    if not context.args:
        usage = (
            "🎫 <b>𝗥𝗲𝗱𝗲𝗲𝗺 𝗖𝗼𝗱𝗲</b>\n\n"
            "Uꜱᴀɢᴇ: <code>/redeem <code></code>\n\n"
            "Exᴀᴍᴘʟᴇ:\n"
            "• <code>/redeem GIFT10</code>"
        )
        return await msg.reply_text(usage, parse_mode="HTML")

    code_input = context.args[0].upper()

    # 2. ATOMIC CHECK AND UPDATE
    # This finds the code ONLY if the user hasn't used it AND the limit isn't reached
    result = redeem_col.find_one_and_update(
        {
            "code": code_input,
            "used_by": {"$ne": user.id},  # User hasn't used it
            "$expr": {"$lt": [{"$size": "$used_by"}, "$limit"]} # Current uses < limit
        },
        {"$push": {"used_by": user.id}}
    )

    # 3. IF NO RESULT: Determine why it failed
    if not result:
        # Check if the code exists at all
        data = redeem_col.find_one({"code": code_input})
        if not data:
            return await msg.reply_text("🚫 Tʜᴀᴛ ᴄᴏᴅᴇ ɪs ɪɴᴠᴀʟɪᴅ ᴏʀ ᴇxᴘɪʀᴇᴅ!")

        if user.id in data.get("used_by", []):
            return await msg.reply_text("⚠️ Yᴏᴜ ʜᴀᴠᴇ ᴀʟʀᴇᴀᴅʏ ᴄʟᴀɪᴍᴇᴅ ᴛʜɪs ᴄᴏᴅᴇ!")

        if len(data.get("used_by", [])) >= data["limit"]:
            return await msg.reply_text("😔 Sᴏʀʀʏ! Tʜɪs ᴄᴏᴅᴇ ʜᴀs ʀᴇᴀᴄʜᴇᴅ ɪᴛs ᴜsᴀɢᴇ ʟɪᴍɪᴛ.")

        return await msg.reply_text("❌ Sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ. Tʀʏ ᴀɢᴀɪɴ.")

    # 4. PROCESS REWARD (Using 'result' which is the data before the push)
    reward_type, reward_val = result["reward"].split(":", 1)
    user_data = get_user(user) # Assuming this fetches user from DB
    level_msg = ""
    display_reward = ""

    try:
        if reward_type == "coins":
            val = int(reward_val)
            user_data["coins"] = user_data.get("coins", 0) + val
            display_reward = f"💰 <code>{val:,} Cᴏɪɴs</code>"

        elif reward_type == "xp":
            val = int(reward_val)
            leveled_up = add_xp(user_data, val) # Assuming this modifies user_data
            display_reward = f"✨ <code>{val:,} XP</code>"
            if leveled_up:
                level_msg = f"\n\n🎊 <b>Lᴇᴠᴇʟ Uᴘ!</b> Yᴏᴜ ᴀʀᴇ ɴᴏᴡ Lᴇᴠᴇʟ <code>{user_data['level']}</code>!"

        elif reward_type == "item":
            if "inventory" not in user_data:
                user_data["inventory"] = []
            user_data["inventory"].append(reward_val)
            display_reward = f"🎁 <code>{reward_val}</code>"

        else:
            return await msg.reply_text("❌ Uɴᴋɴᴏᴡɴ ʀᴇᴡᴀʀᴅ ᴛʏᴘᴇ!")

        # CRITICAL: Save user data after any reward type
        save_user(user_data)

    except (ValueError, IndexError):
        return await msg.reply_text("❌ Error processing reward value.")

    # 5. Final Output
    response_text = (
        f"🎉 <b>𝗖𝗼𝗻𝗴𝗿𝗮𝘁𝘂𝗹𝗮𝘁𝗶𝗼𝗻𝘀 {user.first_name}!</b>\n\n"
        f"Yᴏᴜ sᴜᴄᴄᴇssғᴜʟʟʏ ʀᴇᴅᴇᴇᴍᴇᴅ: {display_reward}"
        f"{level_msg}\n\n"
        "Cʜᴇᴄᴋ ʏᴏᴜʀ /status ᴛᴏ sᴇᴇ ʏᴏᴜʀ ɢʀᴏᴡᴛʜ! 🚀"
    )

    await msg.reply_text(response_text, parse_mode="HTML")

#=== Quote_transformer =======
import httpx
import base64
from io import BytesIO

# Real Telegram Dark Theme Colors
COLOR_MAP = {
    "red": "#FF595A", "blue": "#3E885B", "green": "#008000",
    "yellow": "#FFD700", "pink": "#FFC0CB", "purple": "#800080",
    "dark": "#1b1429", "black": "#000000"
}

async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.reply_to_message:
        return await msg.reply_text("❌ Rᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴄʀᴇᴀᴛᴇ Qᴜᴏᴛᴇ.")

    # 1. Parse Args (Color and Multi-mode)
    bg_color = "#1b1429" 
    is_multi = False

    if context.args:
        args_str = [a.lower() for a in context.args]
        if "r" in args_str or "reply" in args_str:
            is_multi = True
        for name, hex_val in COLOR_MAP.items():
            if name in args_str:
                bg_color = hex_val

    target_msg = msg.reply_to_message
    messages_list = []

    # 2. Build High-Quality Conversation List
    # We add both messages to the list to get the "Stacked Bubbles" look

    # Message A (The one being replied to)
    if is_multi and target_msg.reply_to_message:
        parent = target_msg.reply_to_message
        messages_list.append({
            "entities": [],
            "avatar": True,
            "from": {
                "id": parent.from_user.id,
                "name": parent.from_user.full_name,
                "photo": True
            },
            "text": parent.text or parent.caption or "Media"
        })

    # Message B (The main message)
    messages_list.append({
        "entities": [],
        "avatar": True,
        "from": {
            "id": target_msg.from_user.id,
            "name": target_msg.from_user.full_name,
            "photo": True
        },
        "text": target_msg.text or target_msg.caption or ""
    })

    loading = await msg.reply_text("🪄 Gᴇɴᴇʀᴀᴛɪɴɢ HD Qᴜᴏᴛᴇ...")

    # 3. Enhanced HD Payload
    payload = {
        "type": "quote",
        "format": "webp",
        "backgroundColor": bg_color,
        "width": 512,
        "height": 768 if is_multi else 512,
        "scale": 2,  # <--- Increased to 2 for sharp HD text
        "messages": messages_list
    }

    try:
        # Using the faster, high-quality bot.lyo API with optimized settings
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://bot.lyo.su/quote/generate", 
                json=payload, 
                timeout=30.0,
                headers={"Content-Type": "application/json"}
            )

        if res.status_code == 200:
            data = res.json()
            img_data = data.get("result", {}).get("image") or data.get("image")

            # Decode with high precision
            sticker_file = BytesIO(base64.b64decode(img_data))
            sticker_file.name = "quote.webp"

            # Send as Sticker with high priority
            await msg.reply_sticker(sticker=sticker_file)
            await loading.delete()
        else:
            await loading.edit_text(f"❌ API Error: {res.status_code}")
    except Exception as e:
        await loading.edit_text("❌ Fᴀɪʟᴇᴅ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ HD Qᴜᴏᴛᴇ.")

#========== Sticker Create ========
#--
# === Own Sticker Pack Creator ===

BOT_USERNAME = "im_yuuribot"

async def save_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    user_id = user.id

    if not message.reply_to_message or not message.reply_to_message.sticker:
        await message.reply_text("❌ Rᴇᴘʟʏ Tᴏ A Sᴛɪᴄᴋᴇʀ Tᴏ Sᴀᴠᴇ Iᴛ.")
        return

    sticker = message.reply_to_message.sticker

    # 1. API Logic (Must stay plain lowercase)
    if sticker.is_animated:
        st_logic = "animated"
        fancy_type = "Aɴɪᴍᴀᴛᴇᴅ"
        type_desc = "ᴀʟʟ Aɴɪᴍᴀᴛᴇᴅ"
    elif sticker.is_video:
        st_logic = "video"
        fancy_type = "Vɪᴅᴇᴏ"
        type_desc = "ᴀʟʟ Vɪᴅᴇᴏ"
    else:
        st_logic = "static"
        fancy_type = "Sᴛᴀᴛɪᴄ"
        type_desc = "ᴀʟʟ Nᴏɴ-ᴀɴɪᴍᴀᴛᴇᴅ"

    # Fetch bot username
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username

    # Pack name must be lowercase for Telegram
    pack_name = f"user_{user_id}_{st_logic}_by_{bot_username}".lower()
    pack_title = f"{user.first_name[:15]}'s {fancy_type} Sᴛɪᴄᴋᴇʀs"

    saving_msg = await message.reply_text("🪄 Sᴀᴠɪɴɢ Sᴛɪᴄᴋᴇʀ...")

    try:
        input_sticker = InputSticker(
            sticker=sticker.file_id,
            emoji_list=[sticker.emoji or "🙂"],
            format=st_logic 
        )

        try:
            await context.bot.add_sticker_to_set(
                user_id=user_id,
                name=pack_name,
                sticker=input_sticker
            )
        except Exception as e:
            err = str(e).lower()
            if "stickerset_invalid" in err or "not found" in err:
                await context.bot.create_new_sticker_set(
                    user_id=user_id,
                    name=pack_name,
                    title=pack_title,
                    stickers=[input_sticker],
                    sticker_format=st_logic
                )
            else:
                raise e

        # 2. Fancy Description Style
        description = (
            f"🔰 ꜱᴛɪᴄᴋᴇʀ Sᴀᴠᴇᴅ Tᴏ Yᴏᴜʀ {fancy_type} Pᴀᴄᴋ\n\n"
            f"{type_desc}\n"
            f"ʟɪᴍɪᴛ: 120 Sᴛɪᴄᴋᴇʀꜱ\n\n"
            f"🤖 Tᴀᴋᴇꜱ 2-3 Mɪɴᴜᴛᴇꜱ Tᴏ Sʜᴏᴡ Tʜᴇ Sᴛɪᴄᴋᴇʀ Iɴ Yᴏᴜʀ Pᴀᴄᴋ 🪄"
        )

        await saving_msg.edit_text(
            text=description,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("👀 Oᴘᴇɴ Pᴀᴄᴋ", url=f"https://t.me/addstickers/{pack_name}")
            ]])
        )

    except Exception as e:
        logging.error(f"Sticker Error: {e}")
        error_msg = str(e)
        if "Peer_id_invalid" in error_msg:
            await saving_msg.edit_text("⚠️ Sᴛᴀʀᴛ ᴍᴇ ɪɴ Private Chat (PM) ꜰɪʀꜱᴛ!")
        else:
            await saving_msg.edit_text(f"❌ Cᴀɴ'ᴛ Sᴀᴠᴇ: {error_msg[:50]}")

from telegram.ext import ApplicationHandlerStop

# --- BLOCK/UNBLOCK LOGIC ---
async def block_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Security check: Only Owner can use this command
    if update.effective_user.id != OWNER_IDS:
        return await update.message.reply_text("Oᴏᴘꜱ! Tʜɪꜱ Cᴏᴍᴍᴀɴᴅ Iꜱ Fᴏʀ Mʏ Oᴡɴᴇʀ Oɴʟʏ 😊")

    target_id = None
    target_name = "Uꜱᴇʀ" # Default fallback name

    # 2. Extract ID and Name
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target_id = target_user.id
        target_name = target_user.first_name
    elif context.args:
        try:
            target_id = int(context.args[0])
            # Optional: Try to find their name in your database since we only have an ID
            user_data = users.find_one({"id": target_id})
            if user_data:
                target_name = user_data.get("name", f"Uꜱᴇʀ ({target_id})")
            else:
                target_name = f"Uꜱᴇʀ ({target_id})"
        except ValueError:
            return await update.message.reply_text("❌ Pʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ Uꜱᴇʀ ID.")

    # 3. THE PROTECTOR GUARD 🛑
    bot_id = context.bot.id

    if target_id == OWNER_IDS:
        return await update.message.reply_text("Yᴏᴜ ᴄᴀɴ'ᴛ ʙʟᴏᴄᴋ ʏᴏᴜʀsᴇʟғ, Bᴏss! Tʜᴀᴛ's ᴀ ᴛʀᴀᴘ. ⛔")

    if target_id == bot_id:
        return await update.message.reply_text("Eʜ? Yᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʙʟᴏᴄᴋ ᴍᴇ? I'ᴍ Yᴜᴜʀɪ! I ᴄᴀɴ'ᴛ ʙʟᴏᴄᴋ ᴍʏsᴇʟғ! 🌸")

    # 4. Proceed with blocking
    if target_id:
        users.update_one({"id": target_id}, {"$set": {"blocked": True}}, upsert=True)
        # Using the specific font style for the success message
        await update.message.reply_text(f"{target_name} Bʟᴏᴄᴋᴇᴅ Sᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ✅")

async def unblock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("Oᴏᴘꜱ! Tʜɪꜱ Cᴏᴍᴍᴀɴᴅ Iꜱ Fᴏʀ Mʏ Oᴡɴᴇʀ Oɴʟʏ 😊")

    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        first_name = update.message.reply_to_message.from_user.first_name
    elif context.args:
        try:
            target_id = int(context.args[0])
            first_name = f"Uꜱᴇʀ ({target_id})"
        except ValueError:
            return await update.message.reply_text("❌ Pʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ Uꜱᴇʀ ID.")

    if target_id:
        users.update_one({"id": target_id}, {"$set": {"blocked": False}}, upsert=True)
        await update.message.reply_text(f"{first_name} Uɴʙʟᴏᴄᴋᴇᴅ Sᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ✅")

#==========welcome_message======
import random
from telegram import Update
from telegram.ext import ContextTypes

WELCOME_STYLES = [

"🤗 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 {user} 🧸✨",
"🤗 𝙒𝙚𝙡𝙘𝙤𝙢𝙚 {user} 🧸✨",
"🤗 𝑾𝒆𝒍𝒄𝒐𝒎𝒆 {user} 🧸✨",
"🤗 𝒲𝑒𝓁𝒸𝑜𝓂𝑒 {user} 🧸✨",
"🤗 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 {user} 🧸✨",
"🤗 𝘞𝘦𝘭𝘤𝘰𝘮𝘦 {user} 🧸✨",
"🤗 𝚆𝚎𝚕𝚌𝚘𝚖𝚎 {user} 🧸✨",
"🤗 𝕎𝕖𝕝𝕔𝕠𝕞𝕖 {user} 🧸✨",
"🤗 𝓦𝓮𝓵𝓬𝓸𝓶𝓮 {user} 🧸✨"

]

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):

    for member in update.message.new_chat_members:

        user = member.mention_html()

        text = random.choice(WELCOME_STYLES).format(user=user)

        await update.message.reply_html(text)

# ===== Fun Interaction Commands =====

import random
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

# ===============================
# GIF DATABASE
# ===============================

KISS_GIFS = [
    "CgACAgQAAxkBAAFEqUpps88XuvzJ7gKt9RgT8r3_MgpGhwACgAcAAvwpjFMTm9An_6_McToE",
    "CgACAgQAAxkBAAFEqThps851iVq2fmWNXo3sq1HTx8qP4QACggMAAp897VKT2Ktemaxp2joE",
    "CgACAgQAAxkBAAFEqUxps89ecJSnnN0UOSk13Y6xp7ZI3QACvgQAAp-RzVId4q-39NiNDjoE"
]

HUG_GIFS = [
    "CgACAgQAAxkBAAFEqVVps9AQMt85jqkHjtSeCzgLLfaFngAC7QUAAkWIzFF_W-zVNIr6QjoE",
    "CgACAgQAAxkBAAFEqVZps9AQUhBv94fq6VuPvtMeifMetQACpwgAAsq9fFK5IuJw0Q6KazoE",
    "CgACAgQAAxkBAAFEqVRps9AQLzL3MSq0ciO-AAEzsh47bOEAAq4FAAIL_z1TzpL3e-CUa0I6BA"
]

BITE_GIFS = [
    "CgACAgQAAxkBAAFEqXhps9F32LDcpcXH9NOS-ktnVDG-HgACOwMAAqV6RFELerv_D_rO8joE",
    "CgACAgQAAxkBAAFEqXlps9F3rRMKmv4PISyGVOxXs4v4EAACJQMAAudMBVPQtxclFSEtgDoE",
    "CgACAgQAAxkBAAFEqXdps9F3CUDP_uXjN4HWcMBiacvatQACBQMAAsV7BVM4j4JdPptQDzoE"
]

SLAP_GIFS = [
    "CgACAgQAAxkBAAFEqaJps9JRC5Mfb5jNr5XgAm6RMWovEAACyQUAApZrVVAar3BemvEERjoE",
    "CgACAgQAAxkBAAFEqaNps9JRkv0XbMCeGvsQFLaGGUyuwAACbAMAAvp45FPnsYLcLNShDToE",
    "CgACAgQAAxkBAAFEqaRps9JRPuXBNf7aa9v_whuwU2nLEgACPQMAAhreBFPkfVHAxMcKpjoE"
]

KICK_GIFS = [
    "CgACAgQAAxkBAAFEq3Zps-hFW0CEBmL6u7njUYLGr22q3AAC0gYAAog2jFBmFZXucvqURjoE",
    "CgACAgQAAxkBAAFEq3Vps-hF0AJg7zywn9El8BJUA3DzEwAC8wIAAnvgBFMZAV2MHSAZlzoE",
    "CgACAgQAAxkBAAFEq3dps-hFNX4ZQ4rdT5s32Wnn3NhVAAPIBwACgbe1UVl5Z4WkKnrHOgQ"
]

PUNCH_GIFS = [
    "CgACAgQAAxkBAAFEq4pps-jh2SYq4RCb0d3QXA1ano0ihgACmQYAAmNlfVBPu8eB0yXiOzoE",
    "CgACAgQAAxkBAAFEq4tps-jh9BFfmDjK6XNDKL15Pjzn9wAC8wIAAoSnLVNyqAKuMP98wjoE",
    "CgACAgQAAxkBAAFEq4xps-jh_GtyKDOrEQABr0ParkF7kpEAAsMCAAInZQ1THZgTJK0G2bA6BA"
]

MURDER_GIFS = [
    "CgACAgQAAxkBAAFEq5tps-nhOiSq-vuyjmk13zm30l7R5gAC8AIAAvmANVPbgt6AF05WbzoE",
    "CgACAgQAAxkBAAFEq5xps-nhBH8Ml1UEBCjctbNpBmH1jwACLQMAAuLJDFMgyege_IFM2ToE",
    "CgACAgQAAxkBAAFEq51ps-nhCb0TEIbTPAIBrY2fjxF4cgACQQMAAhQTJVOQ4cLMXsbquToE"
]

WARNING_TEXT = "Cʜᴜᴘᴘ!! Wᴀʀɴᴀ Yᴜᴜᴋɪ Kᴏ Bᴛᴀ Dᴜɴɢɪ 😒"


# ===============================
# CHECK FUNCTION
# ===============================

async def check_target(update: Update, context: ContextTypes.DEFAULT_TYPE, action):
    if not update.message.reply_to_message:
        await update.message.reply_text("ʀᴇᴘʟʏ ᴛᴏ sᴏᴍᴇᴏɴᴇ ғɪʀsᴛ")
        return None

    sender = update.effective_user
    target = update.message.reply_to_message.from_user
    bot_id = context.bot.id

    if sender.id == target.id:
        await update.message.reply_text(f"ʏᴏᴜ ᴄᴀɴ'ᴛ {action} ʏᴏᴜʀsᴇʟғ")
        return None

    if target.id == bot_id:
        await update.message.reply_text(WARNING_TEXT)
        return None

    return sender, target


# ===============================
# COMMANDS
# ===============================

async def kiss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await check_target(update, context, "ᴋɪss")
    if not data: return
    sender, target = data
    gif = random.choice(KISS_GIFS)
    await update.message.reply_animation(
        gif,
        caption=f"{sender.mention_html()} Kɪꜱꜱᴇᴅ {target.mention_html()}",
        parse_mode="HTML"
    )

async def hug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await check_target(update, context, "ʜᴜɢ")
    if not data: return
    sender, target = data
    gif = random.choice(HUG_GIFS)
    await update.message.reply_animation(
        gif,
        caption=f"{sender.mention_html()} Hᴜɢɢᴇᴅ {target.mention_html()}",
        parse_mode="HTML"
    )

async def bite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await check_target(update, context, "ʙɪᴛᴇ")
    if not data: return
    sender, target = data
    gif = random.choice(BITE_GIFS)
    await update.message.reply_animation(
        gif,
        caption=f"{sender.mention_html()} Bɪᴛ {target.mention_html()}",
        parse_mode="HTML"
    )

async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await check_target(update, context, "sʟᴀᴘ")
    if not data: return
    sender, target = data
    gif = random.choice(SLAP_GIFS)
    await update.message.reply_animation(
        gif,
        caption=f"{sender.mention_html()} Sʟᴀᴘᴘᴇᴅ {target.mention_html()}",
        parse_mode="HTML"
    )

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await check_target(update, context, "ᴋɪᴄᴋ")
    if not data: return
    sender, target = data
    gif = random.choice(KICK_GIFS)
    await update.message.reply_animation(
        gif,
        caption=f"{sender.mention_html()} Kɪᴄᴋᴇᴅ {target.mention_html()}",
        parse_mode="HTML"
    )

async def punch(update: Update, context: Update):
    data = await check_target(update, context, "ᴘᴜɴᴄʜ")
    if not data: return
    sender, target = data
    gif = random.choice(PUNCH_GIFS)
    await update.message.reply_animation(
        gif,
        caption=f"{sender.mention_html()} Pᴜɴᴄʜᴇᴅ {target.mention_html()}",
        parse_mode="HTML"
    )

async def murder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await check_target(update, context, "ᴍᴜʀᴅᴇʀ")
    if not data: return
    sender, target = data
    gif = random.choice(MURDER_GIFS)
    await update.message.reply_animation(
        gif,
        caption=f"{sender.mention_html()} Mᴜʀᴅᴇʀᴇᴅ {target.mention_html()}",
        parse_mode="HTML"
    )

#=========sticker sender=======
import random
import logging
import asyncio # Added for the simulation delay
from telegram import Update, constants
from telegram.ext import ContextTypes

MY_PACKS = [
    "YUUKI321",
    "Slaybie_by_fStikBot",
    "Bocchi_the_Rock_Part_1_by_Fix_x_Fox"
]

async def reply_with_random_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Basic safety check
    if not update.message or not update.message.sticker:
        return

    # 2. Identify the chat type (Private vs Group)
    chat_type = update.effective_chat.type

    # 3. Logic: Trigger if it's a Private chat OR if it's a reply to the bot in a group
    # If you want her to reply to EVERY sticker in groups too, just remove this 'if' block.
    is_reply_to_bot = (
        update.message.reply_to_message and 
        update.message.reply_to_message.from_user.id == context.bot.id
    )

    # Trigger on any sticker in Private, or a reply-trigger in Groups
    if chat_type == constants.ChatType.PRIVATE or is_reply_to_bot:

        chosen_pack = random.choice(MY_PACKS)

        try:
            # --- SIMULATION START ---
            # This shows "Yuuri is choosing a sticker..." status
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, 
                action=constants.ChatAction.CHOOSE_STICKER
            )
            # A tiny 1-second delay makes the "choosing" look real
            await asyncio.sleep(1) 
            # --- SIMULATION END ---

            # Fetch the pack
            sticker_set = await context.bot.get_sticker_set(name=chosen_pack)

            if sticker_set and sticker_set.stickers:
                random_sticker = random.choice(sticker_set.stickers)

                # Always reply directly to the user's sticker
                await update.message.reply_sticker(sticker=random_sticker.file_id)

        except Exception as e:
            logging.error(f"Sticker Pack {chosen_pack} error: {e}")

#========Font-command======
async def font_converter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Updated usage message to show both ways
    usage_msg = (
        "❌ **Uꜱᴀɢᴇ:**\n"
        "1️⃣ `/font 1 Hello` (Direct text)\n"
        "2️⃣ Reply to a message with `/font 1`"
    )

    # 1. Check for the font choice (1, 2, or 3)
    if not context.args:
        await update.message.reply_text(usage_msg, parse_mode="Markdown")
        return

    font_choice = context.args[0]
    if font_choice not in ["1", "2", "3"]:
        await update.message.reply_text(usage_msg, parse_mode="Markdown")
        return

    target_text = ""

    # 2. Check if text was provided DIRECTLY: /font 1 My Text
    if len(context.args) > 1:
        target_text = " ".join(context.args[1:])

    # 3. If no direct text, check if it's a REPLY
    elif update.message.reply_to_message:
        replied = update.message.reply_to_message
        # This handles both plain text and photo captions
        target_text = replied.text or replied.caption

    # 4. If still no text found, give up
    if not target_text:
        await update.message.reply_text("❌ Nᴏ ᴛᴇxᴛ ꜰᴏᴜɴᴅ ᴛᴏ ᴄᴏɴᴠᴇʀᴛ!")
        return

    # 5. Process and send
    converted_text = get_fancy_text(target_text, font_choice)
    await update.message.reply_text(converted_text)

# ================= OWNER COMMANDS =================

async def leave_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /leave - Yuri leaves with sass 💥"""
    if update.effective_user.id != OWNER_IDS:
        return

    chat = update.effective_chat
    # If used in Private Chat (DM)
    if chat.type == "private":
        await update.message.reply_text("Aᴡᴡᴡ Sᴡᴇᴇᴛʏ Sɪʟʟʏ Uꜱᴇ Tʜɪꜱ Iɴ Gʀᴏᴜᴘꜱ ☺️")
        return

    group_name = chat.title
    await update.message.reply_text(f"🚪 Lᴇᴀᴠɪɴɢ {group_name} ... Bʏᴇ! 💥")
    await context.bot.leave_chat(chat_id=chat.id)

async def send_personal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /personal <userid> [reply|message] - Send anything anywhere"""
    if update.effective_user.id != OWNER_ID:
        return

    # Check for basic usage
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Uꜱᴀɢᴇ: /ᴘᴇʀꜱᴏɴᴀʟ <ᴜꜱᴇʀɪᴅ> [ʀᴇᴘʟʏ|ᴍᴇꜱꜱᴀɢᴇ]\n"
            "ᴏʙᴊᴇᴄᴛ Cᴀɴ Bᴇ Sᴇɴᴛ 📤\n"
            "1. ꜱᴛɪᴄᴋᴇʀ ( Rᴇᴘʟʏ )\n"
            "2. ᴍᴇꜱꜱᴀɢᴇ ( Rᴇᴘʟʏ|ɪɴ-ᴄᴏᴍᴍᴀɴᴅ )\n"
            "3. ᴇᴍᴏᴊɪ ( Rᴇᴘʟʏ|ɪɴ-ᴄᴏᴍᴍᴀɴᴅ )"
        )
        return

    try:
        target_id = context.args[0]
    except IndexError:
        await update.message.reply_text("⚠️ Boss, I need a UserID first!")
        return

    try:
        # OPTION A: If you are replying to a message/sticker/GIF
        if update.message.reply_to_message:
            reply = update.message.reply_to_message

            # Use copy_message to preserve the exact object (Sticker, GIF, Video, Photo)
            await context.bot.copy_message(
                chat_id=target_id, 
                from_chat_id=update.effective_chat.id, 
                message_id=reply.message_id
            )

        # OPTION B: If you typed a message after the ID
        elif len(context.args) > 1:
            text_to_send = " ".join(context.args[1:])
            await context.bot.send_message(chat_id=target_id, text=text_to_send)

        else:
            await update.message.reply_text("❓ Nothing to send. Reply to something or type text.")
            return

        await update.message.reply_text(f"✅ Oʙᴊᴇᴄᴛ Sᴇɴᴛ Tᴏ `{target_id}` 🚀")

    except Exception as e:
        await update.message.reply_text(f"❌ Fᴀɪʟᴇᴅ Tᴏ Dᴇʟɪᴠᴇʀ: {e}")

# ================= BOT STATS =================
import psutil
import os
from datetime import datetime, timezone

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Security check
    if update.effective_user.id != OWNER_IDS:
        return

    # 2. Calculate Uptime
    now = datetime.now(timezone.utc)
    uptime_delta = now - BOT_START_TIME
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}ʜ {minutes}ᴍ {seconds}ꜱ"

    # 3. Calculate REAL RAM (Bot only)
    process = psutil.Process(os.getpid())
    ram_mb = round(process.memory_info().rss / (1024 ** 2), 1)

    # Getting system percentage for the look, but using Real MB for the value
    sys_ram = psutil.virtual_memory()
    ram_str = f"{sys_ram.percent}% ({ram_mb} MB)"

    # 4. Database Queries
    chats_col = db["chats"]
    groups = chats_col.count_documents({"type": {"$in": ["group", "supergroup"]}})
    private = chats_col.count_documents({"type": "private"})
    blocked = users.count_documents({"blocked": True})
    total_users = users.count_documents({})

    # 5. UI - Compact & Fixed
    text = (
        "📊 **𝗬𝘂𝘂𝗿𝗶 𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝘀**\n\n"
        f"👥 Gʀᴏᴜᴘꜱ : `{groups}`\n"
        f"💬 Cʜᴀᴛꜱ : `{private}`\n"
        f"🧑‍💻 Tᴏᴛᴀʟ Uꜱᴇʀꜱ : `{total_users}`\n"
        f"⏱ Uᴘᴛɪᴍᴇ : `{uptime_str}`\n"
        f"💾 Rᴀᴍ : `{ram_str}`\n\n"
        f"🚫 Bʟᴏᴄᴋᴇᴅ Uꜱᴇʀꜱ : `{blocked}`"
    )

    await update.message.reply_text(text, parse_mode="Markdown")

#=========ping=========
import time
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    # Send initial message in fancy font
    message = await update.message.reply_text("📡 Pɪɴɢɪɴɢ...")

    end_time = time.time()
    latency = round((end_time - start_time) * 1000)

    # Edit with the result
    await message.edit_text(
        f"<b>Pᴏɴɢ!</b> 🏓\n📡 Lᴀᴛᴇɴᴄʏ: <code>{latency}ms</code>", 
        parse_mode='HTML'
    )

#============cmd_command=========
async def owner_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != OWNER_IDS:
        # Using the "Invalid Code" style font for the error
        await update.message.reply_text("Yᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ.")
        return

    help_text = (
        "👑 <b>Oᴡɴᴇʀ Hɪᴅᴅᴇɴ Cᴏᴍᴍᴀɴᴅs</b> 👑\n\n"
        "📡 <code>/ping</code> - Cʜᴇᴄᴋ ʙᴏᴛ ʟᴀᴛᴇɴᴄʏ\n"
        "📊 <code>/stats</code> - (Fᴜᴛᴜʀᴇ) Vɪᴇᴡ ʙᴏᴛ ᴜsᴀɢᴇ\n\n"
        "<b>Aᴅᴍɪɴ Tᴏᴏʟs:</b>\n"
        "👤 <code>/personal [reply] &lt;user-id&gt;</code>\n"
        "🔡 <code>/font 1|2|3</code>\n"
        "🎟 <code>/create &lt;code&gt; &lt;limit&gt; &lt;item|coins|xp:amount&gt;</code>"
    )

    await update.message.reply_text(help_text, parse_mode='HTML')

#==================Main StartUp Of Yuuri==================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user = msg.from_user
    first_name = user.first_name or "User"
    args = context.args

    # Video File ID provided
    START_VIDEO = "VID_20260316_083355_613"

    # --- REFERRAL LOGIC ---
    user_data = get_user(user)

    if user_data.get("referred_by") is None and args:
        ref = args[0]
        if ref.startswith("ref_"):
            try:
                referrer_id = int(ref.split("_")[1])
                if referrer_id != user.id:
                    # Update New User
                    users.update_one(
                        {"id": user.id},
                        {"$set": {"referred_by": referrer_id}}
                    )
                    # Reward Referrer
                    users.update_one(
                        {"id": referrer_id},
                        {"$inc": {"coins": 1000}}
                    )
                    # Notify Referrer
                    try:
                        await context.bot.send_message(
                            referrer_id,
                            f"🎉 {first_name} joined using your referral!\n💰 You earned 1000 coins!"
                        )
                    except Exception:
                        pass
            except (ValueError, IndexError):
                pass

    # --- BUTTONS & CAPTION ---
    bot = await context.bot.get_me()

    keyboard = [
        [
            InlineKeyboardButton("📰 Uᴘᴅᴀᴛᴇs", url="https://t.me/yuuriXupdates"),
            InlineKeyboardButton("💬 Sᴜᴘᴘᴏʀᴛ", url="https://t.me/DreamSpaceZ")
        ],
        [
            InlineKeyboardButton("🤖 Sᴇᴄᴏɴᴅ ʙᴏᴛ", url="https://t.me/Im_yuukibot")
        ],
        [
            InlineKeyboardButton(
                "➕ Aᴅᴅ Mᴇ Tᴏ Gʀᴏᴜᴘ",
                url=f"https://t.me/{bot.username}?startgroup=true"
            )
        ]
    ]

    caption = f"""
✨ 𝗛ᴇʟʟᴏ {first_name} ✨🧸

💥 𝗪ᴇʟᴄᴏᴍᴇ 𝘁𝗼 𝗬𝘂𝘂𝗿𝗶 𝗕𝗼𝘁 🧸✨

🎮 Pʟᴀʏ Gᴀᴍᴇꜱ
💰 Eᴀʀɴ Cᴏɪɴꜱ
🏦 Jᴏɪɴ Hᴇɪꜱᴛꜱ 
🎁 Iɴᴠɪᴛᴇ Fʀɪᴇɴᴅꜱ 

👥 Uꜱᴇ: /referral 
      Tᴏ Iɴᴠɪᴛᴇ Fʀɪᴇɴᴅꜱ 
💰 Eᴀʀɴ 1000 Cᴏɪɴꜱ Pᴇʀ Iɴᴠɪᴛᴇ
"""

    # --- SEND VIDEO MESSAGE ---
    try:
        sent_msg = await msg.reply_video(
            video=START_VIDEO,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML" # Using HTML to support your bold styling
        )
    except Exception as e:
        # Fallback to text if video fails (e.g. invalid File ID)
        sent_msg = await msg.reply_text(
            caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    context.chat_data["start_message_id"] = sent_msg.message_id

# =======Daily=======
from datetime import datetime
import random

async def daily(update, context):
    user_id = update.effective_user.id
    u = users.find_one({"id": user_id})

    # create user if not exist
    if not u:
        u = {
            "id": user_id,
            "name": update.effective_user.first_name,
            "coins": 0,
            "xp": 0,
            "level": 1,
            "inventory": []
        }
        users.insert_one(u)

    today = datetime.now().date()

    if "last_daily" in u:
        last_claim = datetime.strptime(u["last_daily"], "%Y-%m-%d").date()
        if last_claim == today:
            return await update.message.reply_text(
                "⛔ Yᴏᴜ ᴀʟʀᴇᴀᴅʏ Cʟᴀɪᴍᴇᴅ Yᴏᴜʀ Dᴀɪʟʏ Rᴇᴡᴀʀᴅ Tᴏᴅᴀʏ."
            )

    # Give reward
    reward = random.randint(50, 120)
    u["coins"] += reward
    u["last_daily"] = today.strftime("%Y-%m-%d")

    # Save user
    users.update_one({"id": user_id}, {"$set": u})

    await update.message.reply_text(
        f"🎁 Dᴀɪʟʏ Rᴇᴡᴀʀᴅ: +{reward} Cᴏɪɴs"
    )

#====economy commands=======
#--
# ======== PROFILE =======
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return

    target_user = msg.reply_to_message.from_user if msg.reply_to_message else update.effective_user
    data = get_user(target_user) 

    # --- ✨ AUTO-FIX LOGIC ---
    # This checks if the user is "overdue" for a level up
    updated = False
    while True:
        need = int(100 * (1.5 ** (data["level"] - 1)))
        if data["xp"] >= need:
            data["xp"] -= need
            data["level"] += 1
            updated = True
        else:
            break

    if updated:
        save_user(data) # Sync the fix back to MongoDB
    # -------------------------

    xp = data.get("xp", 0)
    lvl = data.get("level", 1)
    coins = data.get("coins", 0)
    premium = data.get("premium", False)

    current_rank_data, _ = get_rank_data(lvl)
    rank_title = current_rank_data["name"]

    need = int(100 * (1.5 ** (lvl - 1)))
    percent = int((xp / need) * 100) if need > 0 else 0
    bar = create_progress_bar(min(percent, 100))

    # Calculate Global Ranks (Excluding the bot)
    # Note: Make sure context.bot.id is correct here
    higher_lvl = users.count_documents({"id": {"$ne": context.bot.id}, "level": {"$gt": lvl}})
    same_lvl_more_xp = users.count_documents({"id": {"$ne": context.bot.id}, "level": lvl, "xp": {"$gt": xp}})
    xp_rank = 1 + higher_lvl + same_lvl_more_xp

    richer_people = users.count_documents({"id": {"$ne": context.bot.id}, "coins": {"$gt": coins}})
    wealth_rank = 1 + richer_people

    inv = data.get("inventory", [])
    inventory_str = ", ".join(inv) if inv else "Eᴍᴘᴛʏ"
    status = "💀 Dᴇᴀᴅ" if data.get("dead") else "❤️ Aʟɪᴠᴇ"
    icon = "💓" if premium else "👤"

    text = (
        f"{icon} Nᴀᴍᴇ: {data.get('name', target_user.first_name)}\n"
        f"🛡️ Tɪᴛʟᴇ: {rank_title}\n"
        f"🏅 Lᴇᴠᴇʟ: {lvl}\n"
        f"💰 Cᴏɪɴꜱ: {coins:,}\n"
        f"🎒 Iɴᴠᴇɴᴛᴏʀʏ: {inventory_str}\n"
        f"🎯 Sᴛᴀᴛᴜꜱ: {status}\n\n"
        f"📊 Pʀᴏɢʀᴇꜱꜱ: {xp:,} / {need:,} XP\n"
        f"{bar} ({percent}%)\n\n"
        f"🌐 Gʟᴏʙᴀʟ Rᴀɴᴋ (XP): {xp_rank}\n"
        f"💸 Wᴇᴀʟᴛʜ Rᴀɴᴋ: {wealth_rank}\n"
        f"🏰 Gᴜɪʟᴅ: {data.get('guild') or 'Nᴏɴᴇ'}"
    )

    await msg.reply_text(text)

# ======== ROB SYSTEM ========
from datetime import datetime

BOT_ID = None

MAX_ROB_PER_ATTEMPT = 10000

async def robe(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    msg = update.message
    robber_user = update.effective_user

    # ❌ Block in private
    if update.effective_chat.type == "private":
        return await msg.reply_text("❌ Tʜɪs Cᴏᴍᴍᴀɴᴅ Cᴀɴ Oɴʟʏ Bᴇ Usᴇᴅ Iɴ Gʀᴏᴜᴘs.")

    # ❌ Must reply
    if not msg.reply_to_message:
        return await msg.reply_text("⚠️ Rᴇᴘʟʏ Tᴏ Sᴏᴍᴇᴏɴᴇ Yᴏᴜ Wᴀɴᴛ Tᴏ Rᴏʙ.")

    target_user = msg.reply_to_message.from_user

    # ❌ Cannot rob bot
    if target_user.id == BOT_ID or target_user.is_bot:
        return await msg.reply_text("🤖 Yᴏᴜ Cᴀɴɴᴏᴛ Rᴏʙ A Bᴏᴛ.")

    # ❌ Cannot rob yourself
    if target_user.id == robber_user.id:
        return await msg.reply_text("❌ Yᴏᴜ Cᴀɴ'ᴛ Rᴏʙ Yᴏᴜʀsᴇʟғ.")

    # 👑 Owner protection
    if target_user.id == OWNER_ID:
        return await msg.reply_text("👑 Yᴏᴜ Cᴀɴ'ᴛ Rᴏʙ Mʏ Dᴇᴀʀᴇsᴛ Oᴡɴᴇʀ 😒")

    # ❌ Need amount
    if not context.args:
        return await msg.reply_text("⚠️ Uꜱᴀɢᴇ: /rob <amount>")

    try:
        amount = int(context.args[0])
    except:
        return await msg.reply_text("❌ Iɴᴠᴀʟɪᴅ Aᴍᴏᴜɴᴛ.")

    robber = get_user(robber_user)
    target = get_user(target_user)

    # 🛡️ Protection check
    if target.get("protect_until"):
        expire = datetime.strptime(target["protect_until"], "%Y-%m-%d %H:%M:%S")
        if expire > datetime.utcnow():
            return await msg.reply_text(
                "🛡️ Tʜɪꜱ Uꜱᴇʀ Iꜱ Pʀᴏᴛᴇᴄᴛᴇᴅ.\n"
                "🔒 Yᴏᴜ Cᴀɴɴᴏᴛ Rᴏʙ Tʜᴇᴍ."
            )

    # 💰 Minimum coins check
    if robber["coins"] < 50:
        return await msg.reply_text(
            "💰 Yᴏᴜ Nᴇᴇᴅ Aᴛ Lᴇᴀsᴛ 50 Cᴏɪɴs Tᴏ Rᴏʙ Sᴏᴍᴇᴏɴᴇ."
        )

    steal = min(amount, target["coins"], MAX_ROB_PER_ATTEMPT)

    if steal <= 0:
        return await msg.reply_text(
            f"💸 {target_user.first_name} Hᴀs Nᴏ Cᴏɪɴs."
        )

    # ✅ Always success
    robber["coins"] += steal
    target["coins"] -= steal

    save_user(robber)
    save_user(target)

    await msg.reply_text(
        f"🕵️ {robber_user.first_name} Sᴜᴄᴄᴇssғᴜʟʟʏ Rᴏʙʙᴇᴅ {target_user.first_name}\n"
        f"💰 Sᴛᴏʟᴇɴ: {steal} Cᴏɪɴs"
    )

#======Give======
async def givee(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.effective_message
    sender = update.effective_user
    reply = msg.reply_to_message

    if not reply:
        return await msg.reply_text("⚠️ Rᴇᴘʟʏ Tᴏ A Pʟᴀʏᴇʀ Tᴏ Gɪᴠᴇ Cᴏɪɴs")

    target = reply.from_user

    if not target:
        return await msg.reply_text("❌ Pʟᴀʏᴇʀ Nᴏᴛ Fᴏᴜɴᴅ")

    if target.is_bot:
        return await msg.reply_text("🤖 Yᴏᴜ Cᴀɴ'ᴛ Gɪᴠᴇ Cᴏɪɴs Tᴏ Bᴏᴛs")

    if not context.args:
        return await msg.reply_text("⚠️ Usᴀɢᴇ: /givee <amount>")

    try:
        amount = int(context.args[0])
    except:
        return await msg.reply_text("❌ Iɴᴠᴀʟɪᴅ Aᴍᴏᴜɴᴛ")

    if amount <= 0:
        return await msg.reply_text("❌ Aᴍᴏᴜɴᴛ Mᴜsᴛ Bᴇ Pᴏsɪᴛɪᴠᴇ")

    if target.id == sender.id:
        return await msg.reply_text("⚠️ Yᴏᴜ Cᴀɴ'ᴛ Gɪᴠᴇ Cᴏɪɴs Tᴏ Yᴏᴜʀsᴇʟғ")

    # 🚫 block giving coins to owner
    if target.id == OWNER_ID:
        return await msg.reply_text("🧸 Nᴏᴛ Nᴇᴇᴅ Tᴏ Gɪᴠᴇ Mʏ Oᴡɴᴇʀ 🧸✨")

    sender_data = get_user(sender)
    receiver_data = get_user(target)

    if sender_data.get("coins", 0) < amount:
        return await msg.reply_text("💰 Yᴏᴜ Dᴏɴ'ᴛ Hᴀᴠᴇ Eɴᴏᴜɢʜ Cᴏɪɴs")

    # ===== TAX =====
    tax = int(amount * 0.10)
    received = amount - tax

    # ===== XP DEDUCTION =====
    xp_loss = max(1, min(amount // 30, 50))

    # ===== ANIMATION =====
    anim = await msg.reply_text("💸 Tʀᴀɴsғᴇʀ Iɴɪᴛɪᴀᴛᴇᴅ...")
    await asyncio.sleep(1.2)

    await anim.edit_text("💰 Cᴀʟᴄᴜʟᴀᴛɪɴɢ Tᴀx...")
    await asyncio.sleep(1.2)

    # deduct sender
    users.update_one(
        {"id": sender.id},
        {"$inc": {"coins": -amount, "xp": -xp_loss}}
    )

    # give receiver
    users.update_one(
        {"id": target.id},
        {"$inc": {"coins": received}}
    )

    # tax to owner
    users.update_one(
        {"id": OWNER_ID},
        {"$inc": {"coins": tax}}
    )

    await anim.edit_text(
f"""
✅ Tʀᴀɴsᴀᴄᴛɪᴏɴ Cᴏᴍᴘʟᴇᴛᴇᴅ

👤 Sᴇɴᴅᴇʀ: {sender.first_name}
🎁 Rᴇᴄᴇɪᴠᴇʀ: {target.first_name}

✅ {target.first_name} Rᴇᴄᴇɪᴠᴇᴅ ${received}
💸 Tᴀx: ${tax} (10%)
⚡ Xᴘ Dᴇᴅᴜᴄᴛᴇᴅ: -{xp_loss}
"""
    )

#========Kill=======
import random
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

BOT_ID = None

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_ID

    if BOT_ID is None:
        BOT_ID = context.bot.id

    if not update.message:
        return

    msg = update.message
    user = update.effective_user

    # ❌ Block in private
    if update.effective_chat.type == "private":
        return await msg.reply_text("❌ Tʜɪs Cᴏᴍᴍᴀɴᴅ Cᴀɴ Oɴʟʏ Bᴇ Usᴇᴅ Iɴ Gʀᴏᴜᴘs.")

    # ❌ Must reply
    if not msg.reply_to_message:
        return await msg.reply_text("⚠️ Rᴇᴘʟʏ Tᴏ Sᴏᴍᴇᴏɴᴇ Yᴏᴜ Wᴀɴᴛ Tᴏ Kɪʟʟ.")

    target_user = msg.reply_to_message.from_user

    # ❌ Invalid target
    if not target_user:
        return await msg.reply_text("❌ Iɴᴠᴀʟɪᴅ Tᴀʀɢᴇᴛ.")

    # ❌ Cannot kill any bot (including other bots in the group)
    if target_user.is_bot:
        if target_user.id == BOT_ID:
            return await msg.reply_text("😂 Nɪᴄᴇ Tʀʏ Oɴ Mᴇ!")
        return await msg.reply_text("🤖 Yᴏᴜ Cᴀɴ'ᴛ Kɪʟʟ Bᴏᴛs, Tʜᴇʏ Hᴀᴠᴇ Nᴏ Sᴏᴜʟ.")

    # ❌ Cannot kill bot owner
    if target_user.id == OWNER_ID:
        return await msg.reply_text("😒 Yᴏᴜ Cᴀɴ'ᴛ Kɪʟʟ Mʏ Dᴇᴀʀᴇsᴛ Oᴡɴᴇʀ.")

    # ❌ Cannot kill yourself
    if target_user.id == user.id:
        return await msg.reply_text("❌ Yᴏᴜ Cᴀɴ'ᴛ Kɪʟʟ Yᴏᴜʀsᴇʟғ.")

    # ✅ Get MongoDB data
    killer = get_user(user)
    victim = get_user(target_user)

    # 🛡️ Protection check
    if victim.get("protect_until"):
        # Use try/except or safe get for date parsing
        try:
            expire = datetime.strptime(victim["protect_until"], "%Y-%m-%d %H:%M:%S")
            if expire > datetime.utcnow():
                return await msg.reply_text(
                    "🛡️ Tʜɪꜱ Uꜱᴇʀ Iꜱ Pʀᴏᴛᴇᴄᴛᴇᴅ.\n"
                    "🔒 Cʜᴇᴄᴋ Pʀᴏᴛᴇᴄᴛɪᴏɴ Tɪᴍᴇ → Cᴏᴍɪɴɢ Sᴏᴏɴ 🔜"
                )
        except (ValueError, TypeError):
            pass

    # ❌ Check if already dead
    if victim.get("dead", False):
        return await msg.reply_text(f"💀 {target_user.first_name} ɪꜱ ᴀʟʀᴇᴀᴅʏ ᴅᴇᴀᴅ!")

    # 🎲 Random rewards
    reward = random.randint(50, 299)
    xp_gain = random.randint(1, 19)

    killer["coins"] = killer.get("coins", 0) + reward
    killer["xp"] = killer.get("xp", 0) + xp_gain
    killer["kills"] = killer.get("kills", 0) + 1

    # 🏰 Guild XP logic (ensure add_guild_xp is defined)
    guild_name = killer.get("guild")
    if guild_name:
        try:
            await add_guild_xp(guild_name, context)
        except NameError:
            pass

    # 🎯 Bounty reward
    bounty_reward = victim.get("bounty", 0)
    if bounty_reward > 0:
        killer["coins"] += bounty_reward
        victim["bounty"] = 0

    # 💀 Mark victim dead
    victim["dead"] = True

    # 💾 Save MongoDB
    save_user(killer)
    save_user(victim)

    # 📢 Kill message
    await msg.reply_text(
        f"👤 {user.first_name} Kɪʟʟᴇᴅ {target_user.first_name}\n"
        f"💰 Eᴀʀɴᴇᴅ: {reward} Cᴏɪɴs\n"
        f"⭐ Gᴀɪɴᴇᴅ: +{xp_gain} Xᴘ"
    )

    # 🎯 Bounty message
    if bounty_reward > 0:
        await msg.reply_text(
            f"🎯 Bᴏᴜɴᴛʏ Cʟᴀɪᴍᴇᴅ!\n"
            f"💰 Eᴀʀɴᴇᴅ ᴇxᴛʀᴀ: {bounty_reward} Cᴏɪɴs!"
        )

# ========== BOUNTY =========
async def bounty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to someone to place bounty.")

    if not context.args:
        return await update.message.reply_text("Use: /bounty <amount>")

    try:
        amount = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Aᴍᴏᴜɴᴛ ᴍᴜsᴛ ʙᴇ ᴀ ɴᴜᴍʙᴇʀ.")

    sender = get_user(update.effective_user)
    target_user = update.message.reply_to_message.from_user
    target = get_user(target_user)

    if sender["coins"] < amount:
        return await update.message.reply_text("❌ Nᴏᴛ ᴇɴᴏᴜɢʜ Cᴏɪɴs.")

    if target_user.id == update.effective_user.id:
        return await update.message.reply_text("❌ Yᴏᴜ ᴄᴀɴ'ᴛ ᴘʟᴀᴄᴇ ʙᴏᴜɴᴛʏ ᴏɴ ʏᴏᴜʀsᴇʟғ.")

    # Deduct coins from sender
    sender["coins"] -= amount
    # Add bounty to target
    target["bounty"] = target.get("bounty", 0) + amount

    # Save to MongoDB
    save_user(sender)
    save_user(target)

    # Fancy reply
    await update.message.reply_text(
            f"🎯 Bᴏᴜɴᴛʏ Pʟᴀᴄᴇᴅ!\n\n"
            f"👤 Tᴀʀɢᴇᴛ: {target_user.first_name}\n"
            f"💰 Rᴇᴡᴀʀᴅ: {amount} Cᴏɪɴs\n\n"
            f"⚔️ Kɪʟʟ ᴛʜᴇᴍ Tᴏ Cʟᴀɪᴍ!"
        )

#========Revive========
async def revive(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    msg = update.effective_message
    reply = msg.reply_to_message

    # target player
    if reply:
        target = reply.from_user
    else:
        target = user

    data = users.find_one({"id": target.id})

    if not data:
        return await msg.reply_text("❌ Pʟᴀʏᴇʀ Nᴏᴛ Fᴏᴜɴᴅ")

    # check if already alive
    if not data.get("dead", False):
        return await msg.reply_text("⚠️ Tʜɪs Pʟᴀʏᴇʀ ɪs Aʟʀᴇᴀᴅʏ Aʟɪᴠᴇ")

    # self revive cost
    if target.id == user.id:

        coins = data.get("coins", 0)

        if coins < 400:
            return await msg.reply_text(
                "💰 Yᴏᴜ Nᴇᴇᴅ 400 Cᴏɪɴs Tᴏ Rᴇᴠɪᴠᴇ Yᴏᴜʀsᴇʟғ"
            )

        users.update_one(
            {"id": user.id},
            {"$inc": {"coins": -400}}
        )

    # revive player
    users.update_one(
        {"id": target.id},
        {"$set": {"dead": False}}
    )

    await msg.reply_text(
f"""
✨ Rᴇᴠɪᴠᴇ Sᴜᴄᴄᴇssғᴜʟ

👤 Nᴀᴍᴇ : {target.first_name}
🆔 Iᴅ : {target.id}
❤️ Sᴛᴀᴛᴜs : Aʟɪᴠᴇ

⚔️ Rᴇᴀᴅʏ Aɢᴀɪɴ
"""
    )

# ======= PROTECT SYSTEM =======
from datetime import datetime, timedelta

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return await update.message.reply_text(
            "🛡️ Pʀᴏᴛᴇᴄᴛɪᴏɴ Sʏsᴛᴇᴍ\n\n"
            "💰 Cᴏsᴛs:\n"
            "1ᴅ → 200$\n"
            "2ᴅ → 400$\n"
            "3ᴅ → 600$\n\n"
            "Uꜱᴀɢᴇ: /protect 1d|2d|3d"
        )

    arg = context.args[0].lower()

    durations = {
        "1d": (1, 200),
        "2d": (2, 400),
        "3d": (3, 600)
    }

    if arg not in durations:
        return await update.message.reply_text(
            "🛡️ Iɴᴠᴀʟɪᴅ Pʀᴏᴛᴇᴄᴛɪᴏɴ Tɪᴍᴇ.\n\n"
            "💰 Aᴛ Lᴇᴀꜱᴛ 200$ Nᴇᴇᴅᴇᴅ Fᴏʀ 1ᴅ Pʀᴏᴛᴇᴄᴛɪᴏɴ.\n"
            "Uꜱᴀɢᴇ: /protect 1d|2d|3d"
        )

    days, price = durations[arg]

    user = get_user(update.effective_user)

    # 💰 Check coins
    if user["coins"] < price:
        return await update.message.reply_text(
            "💰 Nᴏᴛ Eɴᴏᴜɢʜ Cᴏɪɴs.\n"
            f"🛡️ {arg} Pʀᴏᴛᴇᴄᴛɪᴏɴ Cᴏsᴛꜱ {price}$."
        )

    now = datetime.utcnow()

    protect_until = user.get("protect_until")
    if protect_until:
        expire = datetime.strptime(protect_until, "%Y-%m-%d %H:%M:%S")
        if expire > now:
            remaining = expire - now
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)

            return await update.message.reply_text(
                "🛡️ Yᴏᴜ Aʀᴇ Aʟʀᴇᴀᴅʏ Pʀᴏᴛᴇᴄᴛᴇᴅ.\n"
                f"⏳ Tɪᴍᴇ Lᴇꜰᴛ: {hours}ʜ {minutes}ᴍ\n"
                f"🔒 Uɴᴛɪʟ: {protect_until}"
            )

    # 💰 Deduct coins
    user["coins"] -= price

    expire_time = now + timedelta(days=days)
    user["protect_until"] = expire_time.strftime("%Y-%m-%d %H:%M:%S")

    save_user(user)

    # ☠️ If dead
    if user.get("dead", False):
        return await update.message.reply_text(
            f"🛡️ Yᴏᴜ Aʀᴇ Nᴏᴡ Pʀᴏᴛᴇᴄᴛᴇᴅ Fᴏʀ {arg}.\n"
            "🔄 Bᴜᴛ Yᴏᴜʀ Sᴛᴀᴛᴜꜱ Iꜱ Sᴛɪʟʟ Dᴇᴀᴅ Uɴᴛɪʟ Rᴇᴠɪᴠᴇ."
        )

    # ✅ Normal message
    await update.message.reply_text(
        f"🛡️ Yᴏᴜ Aʀᴇ Nᴏᴡ Pʀᴏᴛᴇᴄᴛᴇᴅ Fᴏʀ {arg}."
    )

#========= REGISTER ========
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only allow in private chat
    if update.effective_chat.type != "private":
        return await update.message.reply_text(
            "❌ Tʜɪs Cᴏᴍᴍᴀɴᴅ Cᴀɴ Oɴʟʏ Bᴇ Usᴇᴅ Iɴ Dᴍ."
        )

    user = update.effective_user
    user_data = users.find_one({"id": user.id})

    # If user doesn't exist, create new
    if not user_data:
        user_data = {
            "id": user.id,
            "name": user.first_name,
            "coins": 0,
            "xp": 0,
            "level": 1,
            "inventory": [],
            "registered": False
        }
        users.insert_one(user_data)

    # Already registered?
    if user_data.get("registered", False):
        return await update.message.reply_text(
            "⚠️ Yᴏᴜ Aʟʀᴇᴀᴅʏ Rᴇɢɪsᴛᴇʀᴇᴅ."
        )

    # Update user: give coins & mark registered
    users.update_one(
        {"id": user.id},
        {"$set": {"registered": True}, "$inc": {"coins": 1000}}
    )

    await update.message.reply_text(
        "🎉 Rᴇɢɪsᴛʀᴀᴛɪᴏɴ Sᴜᴄᴄᴇssғᴜʟ!\n"
        "💰 Rᴇᴄᴇɪᴠᴇᴅ: $1000\n"
        "✨ Wᴇʟᴄᴏᴍᴇ Tᴏ Yᴜᴜʀɪ!"
    )

# ======= SHOP ========
SHOP_ITEMS = {
    "rose": (500, "🌹"),
    "chocolate": (800, "🍫"),
    "ring": (2000, "💍"),
    "teddy": (1500, "🧸"),
    "pizza": (600, "🍕"),
    "box": (2500, "🎁"),
    "puppy": (3000, "🐶"),
    "cake": (1000, "🍰"),
    "letter": (400, "💌"),
    "cat": (2500, "🐱"),
    "hepikute": (1500, "💖")
}

# Pre-styled font helper (optional, you can style directly)
def font_text(text: str) -> str:
    # Replace only letters/numbers you want in font style
    font_map = {
        "A":"ᴬ","B":"ᴮ","C":"ᶜ","D":"ᴰ","E":"ᴱ","F":"ᶠ","G":"ᴳ","H":"ᴴ","I":"ᴵ","J":"ᴶ",
        "K":"ᴷ","L":"ᴸ","M":"ᴹ","N":"ᴺ","O":"ᴼ","P":"ᴾ","Q":"ᵠ","R":"ᴿ","S":"ˢ","T":"ᵀ",
        "U":"ᵁ","V":"ⱽ","W":"ᵂ","X":"ˣ","Y":"ʸ","Z":"ᶻ",
        "a":"ᵃ","b":"ᵇ","c":"ᶜ","d":"ᵈ","e":"ᵉ","f":"ᶠ","g":"ᵍ","h":"ʰ","i":"ᶦ","j":"ʲ",
        "k":"ᵏ","l":"ˡ","m":"ᵐ","n":"ⁿ","o":"ᵒ","p":"ᵖ","q":"ᵠ","r":"ʳ","s":"ˢ","t":"ᵗ",
        "u":"ᵘ","v":"ᵛ","w":"ʷ","x":"ˣ","y":"ʸ","z":"ᶻ",
        "0":"0","1":"1","2":"2","3":"3","4":"4","5":"5","6":"6","7":"7","8":"8","9":"9",
        " ":" "
    }
    return "".join(font_map.get(c, c) for c in text)

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🎁 Aᴠᴀɪʟᴀʙʟᴇ Gɪꜰᴛs:\n\n"
    for k, (v, emoji) in SHOP_ITEMS.items():
        msg += f"{emoji} {font_text(k.capitalize())} — {font_text(str(v))} ᴄᴏɪɴs\n"

    await update.message.reply_text(msg)


# ======= PURCHASE ========
async def purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Uꜱᴀɢᴇ: /purchase item")

    item = context.args[0].lower()

    if item not in SHOP_ITEMS:
        return await update.message.reply_text("Iᴛᴇᴍ ɴᴏᴛ ꜰᴏᴜɴᴅ")

    u = get_user(update.effective_user)
    price, emoji = SHOP_ITEMS[item]

    if u["coins"] < price:
        return await update.message.reply_text("ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴄᴏɪɴs")

    u["coins"] -= price
    u["inventory"].append(item)
    save_user(u)

    await update.message.reply_text(f"✅ {emoji} Yᴏᴜ ʙᴏᴜɢʜᴛ {font_text(item.capitalize())}")


#===================top_players_command=================
#--
#=====Top_rhichest=====
async def richest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sort by coins (descending)
    top_list = users.find({"id": {"$ne": context.bot.id}}).sort("coins", -1).limit(10)

    text = "🏆 Tᴏᴘ 10 Rɪᴄʜᴇꜱᴛ Uꜱᴇʀꜱ:\n\n"

    for i, user in enumerate(top_list, start=1):
        name = user.get("name", "Uɴᴋɴᴏᴡɴ")
        coins = user.get("coins", 0)
        # Use 💓 for premium, 👤 for normal
        icon = "💓" if user.get("premium") else "👤"

        # Display: Icon Index. Name: $Amount
        text += f"{icon} {i}. {name}: ${coins:,}\n"

    text += "\n💓 = Pʀᴇᴍɪᴜᴍ • 👤 = Nᴏʀᴍᴀʟ\n\n"
    text += "✅ Uᴘɢʀᴀᴅᴇ Tᴏ Pʀᴇᴍɪᴜᴍ : ᴄᴏᴍɪɴɢ ꜱᴏᴏɴ 🔜"

    await update.message.reply_text(text)

#=====rankers====
async def rankers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sort by Level first, then XP tie-breaker
    top_list = users.find({"id": {"$ne": context.bot.id}}).sort([("level", -1), ("xp", -1)]).limit(10)

    text = "🎖️ Tᴏᴘ 10 Gʟᴏʙᴀʟ Rᴀɴᴋᴇʀꜱ:\n\n"

    for i, user in enumerate(top_list, start=1):
        name = user.get("name", "Uɴᴋɴᴏᴡɴ")
        lvl = user.get("level", 1)
        xp = user.get("xp", 0)
        icon = "💓" if user.get("premium") else "👤"

        # Display: Icon Index. Name: Lᴠʟ 10 (500 XP)
        text += f"{icon} {i}. {name}: Lᴠʟ {lvl} ({xp:,} XP)\n"

    text += "\n💓 = Pʀᴇᴍɪᴜᴍ • 👤 = Nᴏʀᴍᴀʟ\n\n"
    text += "🏆 Kᴇᴇᴘ Gʀɪɴᴅɪɴɢ Tᴏ Rᴇᴀᴄʜ Tʜᴇ Tᴏᴘ!"

    await update.message.reply_text(text)

#=======mini_games_topplayers=======
#--
#======rullrank-the Russian rullate rank=====
async def rullrank(update: Update, context: ContextTypes.DEFAULT_TYPE):

    top_users = users.find().sort("roulette_won", -1).limit(10)

    text = (
        "🏆 Rᴜssɪᴀɴ Rᴜʟʟᴇᴛᴇ Lᴇᴀᴅᴇʀʙᴏᴀʀᴅ\n\n"
    )

    rank = 1

    for user in top_users:

        name = user.get("name", "Pʟᴀʏᴇʀ")
        amount = user.get("roulette_won", 0)

        medals = {
            1: "🥇",
            2: "🥈",
            3: "🥉"
        }

        medal = medals.get(rank, "🔹")

        text += f"{medal} {rank}. {name} — `{amount}` Wɪɴꜱ\n"

        rank += 1

    if rank == 1:
        text += "Nᴏ Rᴏᴜʟᴇᴛᴛᴇ Wɪɴɴᴇʀs Yᴇᴛ."

    text += "\n\n🎰 Kᴇᴇᴘ Pʟᴀʏɪɴɢ & Wɪɴ Tʜᴇ Pᴏᴛ 🍯"

    await update.message.reply_text(
        text,
        parse_mode="Markdown"
    )

#=======broadcasting======
#--
# ======= PRIVATE BROADCAST ========
async def broad_c(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_IDS:
        return await update.message.reply_text("❌ Uɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ")

    if broadcast_control["running"]:
        return await update.message.reply_text("⚠️ Aɴᴏᴛʜᴇʀ ʙʀᴏᴀᴅᴄᴀsᴛ ʀᴜɴɴɪɴɢ!")

    # Get message preserving all spaces
    if update.message.reply_to_message:
        msg = update.message.reply_to_message.text or update.message.reply_to_message.caption
    else:
        if not context.args:
            return await update.message.reply_text("Rᴇᴘʟʏ ᴏʀ ᴜsᴇ /broad_c message")
        msg = update.message.text.split(" ", 1)[1]

    all_chats = list(db["chats"].find({"type": "private"}))
    total = len(all_chats)