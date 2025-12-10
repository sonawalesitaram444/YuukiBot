	#!/usr/bin/env python3
"""
	.Yuuki — Economy / Game / Sticker bot (single-file, improved)

Set BOT_TOKEN and OWNER_IDS below, then:
  pip install python-telegram-bot==20.3 tinydb pillow
  python3 yuuki_bot.py
"""
import logging
import os
import re
import random
import shutil
import subprocess
from telegram import ChatAdministratorRights
from datetime import datetime
from functools import wraps
from io import BytesIO
from typing import Dict, Any, Optional, Tuple

from functools import wraps
from telegram import ChatMember

def admin_only(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat

        # Allow bot creator always
        if user.id in OWNER_IDS:
            return await func(update, context, *args, **kwargs)

        # If private chat → only creator can use
        if chat.type == "private":
            return await update.message.reply_text("❌ You are not allowed to use this command in private.")

        # Check admin status in the group
        member = await chat.get_member(user.id)
        if member.status not in [ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
            return await update.message.reply_text("⛔ Only group admins can use this command.")

        return await func(update, context, *args, **kwargs)
    
    return wrapped

from tinydb import TinyDB, Query
from PIL import Image, ImageDraw, ImageFont

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

async def safe_reply(msg, text, **kwargs):
    for _ in range(3):
        try:
            return await msg.reply_text(text, **kwargs)
        except:
            await asyncio.sleep(1)
    return None

# Add this ↓↓↓
from telegram.helpers import escape_markdown

from functools import wraps

# -----------------------
# Safe Reply Function
# -----------------------
import asyncio
from telegram.error import BadRequest

async def safe_reply(msg, text, **kwargs):
    # Telegram Markdown errors → fallback to plain text
    for _ in range(3):
        try:
            return await msg.reply_text(text, **kwargs)
        except BadRequest as e:
            # Fix for "can't parse entities"
            if "can't parse entities" in str(e):
                return await msg.reply_text(text, parse_mode=None)
            await asyncio.sleep(1)
        except Exception:
            await asyncio.sleep(1)
    return None

# ------------------ YUUKI PING TEXT DETECTOR ------------------
import time

def escape_md(text):
    chars = r"\_[]()~`>#+-=|{}.!"
    for c in chars:
        text = text.replace(c, f"\\{c}")
    return text

async def text_message_handler(update, context):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()

    # Detect reply to bot
    try:
        is_reply_to_bot = (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user.id == context.bot.id
        )
    except:
        is_reply_to_bot = False

    # Trigger on "yuuki" or reply
    if "yuuki" in text or is_reply_to_bot:
        start = time.time()
        msg = await update.message.reply_text("Calculating ping… ⏳")
        end = time.time()

        ping = int((end - start) * 1000)

        await msg.edit_text(
            f"Yes, I'm here and running smoothly 💨\n"
            f"**Ping:** `{ping} ms`\n"
            f"System Stable • Response Optimized ⚡",
            parse_mode="Markdown"
        )
        return

# ---------------- CONFIG ----------------
BOT_TOKEN = "8520734510:AAFuqA-MlB59vfnI_zUQiGiRQKEJScaUyFs"
OWNER_IDS = [5773908061, 7139383373]
BOT_NAME_DISPLAY = "Yuuki_"
SUPPORT_LINK = "https://t.me/team_bright_lightX"
CHANNEL_LINK = "https://t.me/+dsCkYEVHJBRiMjI9"
DB_PLAYERS = TinyDB("users.json")
# ----------------------------------------
import os
import random
import time
import requests
from telegram import Update
from telegram.ext import ContextTypes

# API from Railway env
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

YUUKI_STICKERS = [
    "CAACAgIAAxkBAAEBGZJhV6Hx6ZpQo5Vh1gZr6K9p0bcQbgACfwIAAnuXhUh2C0xV1h6sPiQE",
    "CAACAgIAAxkBAAEBGZNhV6I6O8f02fsTQ8VvMIGwD9l0ZwACGgIAAnuXhUhJ9UfiwJ6HHiQE"
]

RIDDLES = [
    ("What has keys but can't open locks?", "keyboard"),
    ("I speak without a mouth and hear without ears. What am I?", "echo"),
    ("What gets wetter the more it dries?", "towel")
]

async def yuuki_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    text = (update.message.text or "").lower()

    # Check if user is replying to Yuuki
    try:
        is_reply_to_bot = (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user.id == context.bot.id
        )
    except:
        is_reply_to_bot = False

    # ❌ Yuuki should NOT react to stickers unless replied to
    if update.message.sticker and not is_reply_to_bot:
        return

    # ❌ Only respond if user mentions yuuki or replies to him
    if "yuuki" not in text and not is_reply_to_bot:
        return

    user_msg = update.message.text or ""

    # Owner response
    owner_keywords = [
        "owner", "who made you", "kisne banaya",
        "creator", "maker", "tumhara owner"
    ]
    if any(word in user_msg.lower() for word in owner_keywords):
        await update.message.reply_text("Mera owner @RJVTAX hai 😎⚡ kya hua?")
        return

    # Riddles
    for q, a in RIDDLES:
        if a in user_msg.lower():
            await update.message.reply_text(f"Correct 😎 — {a}")
            return
        elif "riddle" in user_msg.lower():
            riddle = random.choice(RIDDLES)
            await update.message.reply_text(f"Riddle time 🤨: {riddle[0]}")
            return

    # Memory
    if "history" not in context.chat_data:
        context.chat_data["history"] = []

    context.chat_data["history"].append({"role": "user", "content": user_msg})
    context.chat_data["history"] = context.chat_data["history"][-10:]

    # System message — no actions, no AI reveal
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Yuuki, a real human boy. "
                    "You talk in short Hinglish sentences with attitude, fun and sarcasm. "
                    "Never reveal you are AI or bot. "
                    "No *actions* like *laughs* or *smiles*. "
                    "Reply like a normal teenager: short, real, casual."
                ),
            }
        ] + context.chat_data["history"],
    }

    # Show typing…
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # API CALL with retry
    for attempt in range(3):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=40
            )

            bot_reply = response.json()["choices"][0]["message"]["content"]
            break
        except:
            if attempt < 2:
                time.sleep(2)
                continue
            bot_reply = "Lag aa gaya yaar 😪"

    # Save to memory
    context.chat_data["history"].append({"role": "assistant", "content": bot_reply})
    context.chat_data["history"] = context.chat_data["history"][-10:]

    # Small chance of sticker
    if random.randint(1, 7) == 4:
        await update.message.reply_sticker(random.choice(YUUKI_STICKERS))

    await update.message.reply_text(bot_reply)
import os
import shutil
from tinydb import TinyDB, Query

# Prefer persistent volume path if Railway mounted it at /app/yuuki_data
REPO_DATA_DIR = os.path.join(os.getcwd(), "yuuki_data")
PERSISTENT_DATA_DIR = "/app/yuuki_data"

# Choose DATA_DIR
if os.path.isdir(PERSISTENT_DATA_DIR):
    DATA_DIR = PERSISTENT_DATA_DIR
else:
    DATA_DIR = REPO_DATA_DIR

os.makedirs(DATA_DIR, exist_ok=True)

TEMP_DIR = os.path.join(DATA_DIR, "tmp")
os.makedirs(TEMP_DIR, exist_ok=True)

# Copy repo data → persistent volume (only first deploy)
try:
    if DATA_DIR == PERSISTENT_DATA_DIR:
        if not any(name.endswith(".json") for name in os.listdir(DATA_DIR)):
            if os.path.isdir(REPO_DATA_DIR):
                shutil.copytree(REPO_DATA_DIR, DATA_DIR, dirs_exist_ok=True)
except Exception:
    pass

DB_PATH = os.path.join(DATA_DIR, "db.json")
USERS_PATH = os.path.join(DATA_DIR, "users.json")
APPROVE_PATH = os.path.join(DATA_DIR, "approve_db.json")

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Initialize TinyDBs
db = TinyDB(DB_PATH)
users_db = TinyDB(USERS_PATH)
db_approve = TinyDB(APPROVE_PATH)

# Tables
users_table = users_db.table("users")
groups_table = db.table("groups")
packs_table = db.table("packs")
sessions_table = db.table("sessions")
banks_table = db.table("banks")
creators_table = db.table("bank_creators")
ApproveTable = db_approve.table("approved_creators")

# Queries
UserQ = Query()
GroupQ = Query()
PackQ = Query()
SessQ = Query()

# ---------- SHOP STATE ----------
# Tracks the weekly Moneybag cooldown
SHOP_STATE = {}

# ---------- HELPER FUNCTIONS ----------
def ensure_user_record(user):
    """Return user record from DB; create if doesn't exist."""
    rec = users_table.get(UserQ.user_id == user.id)
    if not rec:
        rec = {
            "user_id": user.id,
            "coins": 0,
            "inventory": {},
            "registered": False,
            "display_name": user.first_name
        }
        users_table.insert(rec)
    return rec

def save_user(user):
    """Save or update user record in DB."""
    users_table.upsert(user, UserQ.user_id == user["user_id"])

def stylize_name(name):
    """Optional formatting for display names."""
    return name

# -------------------- BANK HELPERS --------------------
def pretty_name_from_rec(rec):
    uname = rec.get("username")
    if uname:
        return f"@{uname}"
    return rec.get("display_name") or f"User{rec.get('user_id','???')}"

def pretty_name_from_user(user):
    if getattr(user, "username", None):
        return f"@{user.username}"
    return getattr(user, "full_name", None) or getattr(user, "first_name", None) or f"User{getattr(user,'id','???')}"

def find_bank(name):
    """Find a bank by name (case-insensitive)"""
    if not name:
        return None
    name = name.strip().lower()
    for b in banks_table.all():
        if b.get("name","").lower() == name:
            return b
    return None

def save_bank(bank):
    """Upsert bank by name"""
    try:
        Q = Query()
        banks_table.upsert(bank, Q.name == bank["name"])
    except Exception:
        # fallback: remove and insert
        for b in banks_table.all():
            if b.get("name","").lower() == bank["name"].lower():
                banks_table.remove(doc_ids=[b.doc_id])
        banks_table.insert(bank)

# ECONOMY SETTINGS
START_COINS = 100
DAILY_MIN, DAILY_MAX = 100, 400
REVIVE_COST = 500
PROTECT_COST = {"1d": 200, "2d": 400}
KILL_MIN_REWARD, KILL_MAX_REWARD = 100, 500
GIFT_FEE_RATIO = 0.10

# shop items
SHOP_ITEMS = {
    "rose": {"display": "🌹 [rose]", "price": 200},
    "heart": {"display": "❤️ [heart]", "price": 150},
    "moneybag": {"display": "💰 [moneybag]", "price": 1000},
    "sword": {"display": "⚔️ [sword]", "price": 800},
    "shield": {"display": "🛡️ [shield]", "price": 700},
    "potion": {"display": "🧪 [potion]", "price": 120},
    "apple": {"display": "🍎 [apple]", "price": 50},
    "ticket": {"display": "🎫 [ticket]", "price": 300},
    "gem": {"display": "💎 [gem]", "price": 1500},
    "pet": {"display": "🐶 [pet]", "price": 1200},
}

# simple GIF placeholders
PUNCH_GIFS = ["https://media.tenor.com/jQpYtU3n6nEAAAAC/anime-punch.gif"]
SLAP_GIFS = ["https://media.tenor.com/ZQjJz1Kkb04AAAAC/anime-slap.gif"]
HUG_GIFS = ["https://media.tenor.com/IKXDsOYe6YsAAAAC/anime-hug.gif"]
KISS_GIFS = ["https://media.tenor.com/k7u_8srrcFUAAAAC/anime-kiss.gif"]

async def wish_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text(
        f"🌟 | Your wish has been recorded, {user.first_name}! ✨"
    )

# -----------------------------
# BANK + ECONOMY FIXES & NEW
# -----------------------------
# Paste this section to replace/augment your existing bank/economy code.
# Requires: telegram.ext Application instance in variable `app`.
# Uses TinyDB tables: users_table, banks_table, creators_table, sessions_table, groups_table.
# If they don't exist, fallback TinyDB files will be created.

import random
import time
from typing import Optional, Dict, Any

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters

# --- CONFIG: tweak if needed ---
OWNER_IDS = globals().get("OWNER_IDS") or globals().get("OWNER_ID") or [5773908061]
if isinstance(OWNER_IDS, int):
    OWNER_IDS = [OWNER_IDS]

# --- TinyDB fallbacks (if your main code already defines these they'll be reused) ---
try:
    users_table
except NameError:
    from tinydb import TinyDB, Query
    users_table = TinyDB("data/users.json").table("users")
    UserQ = Query()
else:
    from tinydb import Query
    UserQ = Query()

try:
    banks_table
except NameError:
    from tinydb import TinyDB
    banks_table = TinyDB("data/banks.json").table("banks")

try:
    creators_table
except NameError:
    from tinydb import TinyDB
    creators_table = TinyDB("data/banks.json").table("bank_creators")

try:
    sessions_table
except NameError:
    from tinydb import TinyDB
    sessions_table = TinyDB("data/sessions.json").table("sessions")

# reuse existing helpers if available, otherwise implement safe fallback
ensure_user_record = globals().get("ensure_user_record")
save_user = globals().get("save_user")
now_ts = globals().get("now_ts")
stylize_name = globals().get("stylize_name", lambda x: x)
check_group_open = globals().get("check_group_open", lambda cid: True)

if not ensure_user_record:
    def ensure_user_record(user) -> Dict[str, Any]:
        uid = int(user.id)
        rec = users_table.get(UserQ.user_id == uid)
        if rec:
            return rec
        rec = {"user_id": uid, "username": getattr(user, "username", None), "display_name": user.first_name, "coins": 0}
        users_table.insert(rec)
        return rec

if not save_user:
    def save_user(rec: Dict[str, Any]):
        users_table.upsert(rec, UserQ.user_id == rec["user_id"])

if not now_ts:
    def now_ts():
        return time.time()

# -----------------------
# Helper util functions
# -----------------------
def pretty_name_from_user(user):
    if getattr(user, "username", None):
        return f"@{user.username}"
    if getattr(user, "full_name", None):
        return user.full_name
    return user.first_name or f"User{user.id}"

def find_bank(name: str):
    if not name:
        return None
    name = name.strip()
    try:
        from tinydb import Query
        Q = Query()
        res = banks_table.search(Q.name == name)
        return res[0] if res else None
    except Exception:
        for b in banks_table.all():
            if b.get("name","").lower() == name.lower():
                return b
    return None

def save_bank(bank: Dict[str, Any]):
    try:
        from tinydb import Query
        Q = Query()
        banks_table.upsert(bank, Q.name == bank["name"])
    except Exception:
        # fallback
        allb = banks_table.all()
        for b in allb:
            if b.get("name","").lower() == bank["name"].lower():
                banks_table.remove(doc_ids=[b.doc_id])
        banks_table.insert(bank)

def owner_only_check(uid:int) -> bool:
    return uid in OWNER_IDS

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from tinydb import TinyDB, Query
import os
import time
from functools import wraps

# --------------------
# DB Setup
# --------------------
DATA_DIR = "yuuki_data"
os.makedirs(DATA_DIR, exist_ok=True)

db = TinyDB(os.path.join(DATA_DIR, "db.json"))
users_table = db.table("users")
creators_table = db.table("approved_creators")  # approved users for creating banks
banks_table = db.table("banks")
sessions_table = db.table("sessions")

# --------------------
# Helpers
# --------------------
def find_bank(name):
    Q = Query()
    return banks_table.get(Q.name == name)

def save_bank(bank):
    Q = Query()
    banks_table.upsert(bank, Q.name == bank["name"])

def now_ts():
    return int(time.time())

from datetime import datetime, timedelta

def check_auto_revive(user):
    """Automatically revive a user if their revive timer expired."""
    if user.get("dead") and user.get("dead_until"):
        now = datetime.utcnow().timestamp()
        if now >= user["dead_until"]:
            user["dead"] = False
            user["dead_until"] = None
            save_user(user)
    return user

def pretty_name_from_user(user):
    if getattr(user, "username", None):
        return f"@{user.username}"
    return user.first_name

def owner_only(func):
    @wraps(func)
    def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        OWNER_IDS = [5773908061]  # <-- set your bot owner ids
        if user_id not in OWNER_IDS:
            return update.message.reply_text("❌ You are not authorized to use this command.")
        return func(update, context, *args, **kwargs)
    return wrapper

# ========================
# /approve <reply/username/userid>
# ========================
@owner_only
def approve_cmd(update, context):
    msg = update.message
    if not msg or not context.args:
        return msg.reply_text("Usage: /approve <reply/username/userid>")

    user = None
    if msg.reply_to_message:
        user = msg.reply_to_message.from_user
    else:
        arg = context.args[0]
        if arg.isdigit():
            user_id = int(arg)
            user = type('User', (), {'id': user_id, 'first_name': arg})()
        elif arg.startswith("@"):
            user = type('User', (), {'id': None, 'first_name': arg, 'username': arg[1:]})()
    if not user:
        return msg.reply_text("Could not determine the user.")

    Q = Query()
    creators_table.upsert({"user_id": user.id, "approved_at": now_ts()}, Q.user_id == user.id)
    msg.reply_text(f"✅ User {pretty_name_from_user(user)} is now approved to create banks.")

# -----------------------
# /unapprove <reply/username/userid>
# -----------------------
@owner_only
def unapprove_cmd(update, context):
    msg = update.message
    if not msg or not context.args:
        return msg.reply_text("Usage: /unapprove <reply/username/userid>")

    user = None
    if msg.reply_to_message:
        user = msg.reply_to_message.from_user
    else:
        arg = context.args[0]
        if arg.isdigit():
            user_id = int(arg)
            user = type('User', (), {'id': user_id, 'first_name': arg})()
        elif arg.startswith("@"):
            user = type('User', (), {'id': None, 'first_name': arg, 'username': arg[1:]})()
    if not user:
        return msg.reply_text("Could not determine the user.")

    Q = Query()
    creators_table.remove(Q.user_id == user.id)
    msg.reply_text(f"❌ User {pretty_name_from_user(user)} is no longer approved to create banks.")

# -----------------------
# /approvelist — show approved creators
# -----------------------
def approvelist_cmd(update, context):
    msg = update.message
    users = creators_table.all()
    if not users:
        return msg.reply_text("No users are approved yet.")
    lines = ["✅ *Approved Creators:*"]
    for u in users:
        uid = u.get("user_id")
        lines.append(f"• UserID: {uid}")
    msg.reply_text("\n".join(lines), parse_mode="Markdown")

# -----------------------
# /addbank <name> — join a bank
# -----------------------
async def addbank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    if not context.args:
        return await safe_reply(msg, "Usage: /addbank <bank_name>\nUse /banklist to see available banks.")

    bank_name = " ".join(context.args).strip()
    bank = find_bank(bank_name)

    if not bank:
        return await safe_reply(msg, "That bank does not exist. Use /banklist to view available banks.")

    user = msg.from_user

    # Already member?
    if user.id in bank.get("members", []):
        return await safe_reply(msg, "You are already a member of this bank.")

    # Add user to member list
    bank.setdefault("members", []).append(user.id)
    save_bank(bank)

    await safe_reply(
        msg,
        f"✅ You have joined the bank *{bank_name}*.",
        parse_mode="Markdown"
    )

# -----------------------
# /createbank — DM only, approved creators
# -----------------------
async def createbank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    if msg.chat.type != "private":
        return await msg.reply_text("Please DM me to create a bank. Use /createbank <bank_name>.")

    user = msg.from_user
    Q = Query()
    approved = creators_table.get(Q.user_id == user.id)
    if not approved:
        return await msg.reply_text("❌ You are not approved to create a bank. Ask the bot owner to /approve you first.")

    if not context.args:
        return await msg.reply_text("Usage: /createbank <bank_name> — after this, send the bank logo photo.")

    bank_name = " ".join(context.args).strip()
    if find_bank(bank_name):
        return await msg.reply_text("A bank with that name already exists. Choose another name.")

    sessions_table.upsert({"user_id": user.id, "action": "create_bank", "bank_name": bank_name}, lambda r: r.get("user_id") == user.id)
    await msg.reply_text(f"✅ '{bank_name}' reserved. Now send the photo for the bank logo.")

# -----------------------
# Handle bank logo photo DM
# -----------------------
async def handle_photos_for_banks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat.type != "private" or not msg.photo:
        return
    user = msg.from_user
    Q = Query()
    sess = sessions_table.get(Q.user_id == user.id)
    if not sess or sess.get("action") != "create_bank":
        return

    file_id = msg.photo[-1].file_id
    bank_name = sess.get("bank_name")
    bank = {
        "name": bank_name,
        "creator_id": user.id,
        "creator_username": getattr(user, "username", None),
        "logo_file_id": file_id,
        "created_at": now_ts(),
        "members": [],
        "deposits": {},
        "budget": 0
    }
    save_bank(bank)
    sessions_table.remove(Q.user_id == user.id)

    caption = f"🏦 *{bank_name}*\nOwner: {pretty_name_from_user(user)}\nMembers: 0\nTotal deposits: 0\n\nBank created successfully! Use /banklist or /addbank {bank_name} to join."
    try:
        await context.bot.send_photo(user.id, file_id, caption=caption, parse_mode="Markdown")
    except Exception:
        await msg.reply_text(caption)

# /banklist — show all banks
async def banklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    banks = banks_table.all()

    if not banks:
        return await msg.reply_text("No banks have been created yet.")

    lines = ["🏦 Available Banks:"]
    for b in banks:
        owner = b.get("creator_username") or f"User{b.get('creator_id')}"
        members = len(b.get("members", []))
        name = b.get("name")
        lines.append(f"• {name} — Owner: {owner} — Members: {members}")

    lines.append("\nTo join a bank: /addbank <bank_name>")

    # Use simple reply_text
    await msg.reply_text("\n".join(lines))

# -----------------------
# /deposit <amount> — DM only (add to user's deposit in their bank)
# -----------------------
async def deposit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    if msg.chat.type != "private":
        return await msg.reply_text("Deposits must be done in DM with the bot. Use /deposit <amount> in a private chat.")
    user = msg.from_user
    if not context.args:
        return await msg.reply_text("Usage: /deposit <amount>")

    try:
        amt = int(context.args[0])
        if amt <= 0:
            return await msg.reply_text("Amount must be positive.")
    except:
        return await msg.reply_text("Invalid amount.")

    # find the bank where user is a member
    user_bank = None
    for b in banks_table.all():
        if user.id in b.get("members", []):
            user_bank = b; break
    if not user_bank:
        return await msg.reply_text("You are not a member of any bank. Use /addbank <bank_name> to join a bank.")

    # ensure user has enough coins in global balance
    rec = ensure_user_record(user)
    if rec.get("coins", 0) < amt:
        return await msg.reply_text("Insufficient coins in your balance to deposit.")

    rec["coins"] = rec.get("coins", 0) - amt
    save_user(rec)

    deposits = user_bank.get("deposits", {})
    deposits[str(user.id)] = deposits.get(str(user.id), 0) + amt
    user_bank["deposits"] = deposits
    save_bank(user_bank)

    await msg.reply_text(f"✅ Deposited ${amt} into *{user_bank['name']}*.", parse_mode="Markdown")

# -----------------------
# /withdraw <amount> — works anywhere (checks deposit)
# -----------------------
async def withdraw_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    if not context.args:
        return await msg.reply_text("Usage: /withdraw <amount>")

    try:
        amt = int(context.args[0])
        if amt <= 0:
            return await msg.reply_text("Amount must be positive.")
    except:
        return await msg.reply_text("Invalid amount.")

    user = msg.from_user
    user_bank = None
    for b in banks_table.all():
        if user.id in b.get("members", []):
            user_bank = b; break
    if not user_bank:
        return await msg.reply_text("You are not a member of any bank. Use /addbank <bank_name> to join one.")

    deposits = user_bank.get("deposits", {})
    user_amt = deposits.get(str(user.id), 0)
    if user_amt < amt:
        return await msg.reply_text("You haven't deposited this much — withdraw failed.")

    deposits[str(user.id)] = user_amt - amt
    user_bank["deposits"] = deposits
    save_bank(user_bank)

    rec = ensure_user_record(user)
    rec["coins"] = rec.get("coins", 0) + amt
    save_user(rec)

    await msg.reply_text(f"✅ Withdrawn ${amt} from *{user_bank['name']}*.", parse_mode="Markdown")

import re

def esc(text: str) -> str:
    """Escape MarkdownV2 for Telegram."""
    if not text:
        return ""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))


# -----------------------
# /bank — view bank profile
# -----------------------
async def bank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    name = " ".join(context.args).strip() if context.args else None

    bank = find_bank(name) if name else None

    # auto-detect bank of user if no name
    if not bank:
        user = msg.from_user
        for b in banks_table.all():
            if user.id in b.get("members", []):
                bank = b
                break

    if not bank:
        return await msg.reply_text(
            "No bank found. Use /banklist to see all banks or /bank <bank_name>.",
        )

    owner_name = bank.get("creator_username") or f"User{bank.get('creator_id')}"
    total_deposits = sum(bank.get("deposits", {}).values()) if bank.get("deposits") else 0
    members = bank.get("members", [])

    # Escape text for MarkdownV2
    text = (
        f"🏦 *{esc(bank['name'])}*\n"
        f"👤 Owner: {esc(owner_name)}\n"
        f"👥 Members: {len(members)}\n"
        f"💰 Total deposits: ${total_deposits}\n"
        f"📦 Budget: ${bank.get('budget',0)}"
    )

    if bank.get("logo_file_id"):
        try:
            await context.bot.send_photo(
                chat_id=msg.chat.id,
                photo=bank.get("logo_file_id"),
                caption=text,
                parse_mode="MarkdownV2"
            )
            return
        except:
            pass

    await msg.reply_text(text, parse_mode="MarkdownV2")


# -----------------------
# /bankstatus — personal balance
# -----------------------
async def bankstatus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = msg.from_user

    user_bank = None
    for b in banks_table.all():
        if user.id in b.get("members", []):
            user_bank = b
            break

    if not user_bank:
        return await msg.reply_text("You are not a member of any bank.")

    deposit = user_bank.get("deposits", {}).get(str(user.id), 0)

    text = (
        f"🏦 *{esc(user_bank['name'])}* — Your account\n"
        f"👤 Owner: {esc(user_bank.get('creator_username') or 'User' + str(user_bank.get('creator_id')))}\n"
        f"💵 Your deposit: ${deposit}\n"
        f"📦 Bank budget: ${user_bank.get('budget',0)}"
    )

    await msg.reply_text(text, parse_mode="MarkdownV2")

# -----------------------
# /budget <bankname> <amount> — owner requests budget assignment to bank
# Owner receives a prompt to set budget via /budget_set <bankname> <amount>
# -----------------------
async def budget_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    if len(context.args) < 2:
        return await msg.reply_text("Usage: /budget <bank_name> <amount>  — this notifies the bot owner to allocate funds to that bank.")
    bank_name = context.args[0]
    try:
        amount = int(context.args[1])
    except:
        return await msg.reply_text("Invalid amount.")
    bank = find_bank(bank_name)
    if not bank:
        return await msg.reply_text("Bank not found.")
    # notify bot owner(s)
    owner_ids = OWNER_IDS
    notified = 0
    for oid in owner_ids:
        try:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Set budget", callback_data=f"budget_set|{bank_name}|{amount}|{bank.get('creator_id')}")]])
            await context.bot.send_message(oid, f"📣 Bank budget request:\nBank: *{bank_name}*\nRequested amount: ${amount}\nCreator: {pretty_name_from_user(type('u',(),{'id':bank.get('creator_id'),'username':bank.get('creator_username')}))}", parse_mode="Markdown", reply_markup=kb)
            notified += 1
        except Exception:
            pass
    await msg.reply_text(f"✅ Your budget request was sent to the bot owner(s) ({notified} notified). They can approve using the inline button or use /budget_set <bankname> <amount>.")

# Callback to handle budget_set inline action by owner
async def callback_budget_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    parts = q.data.split("|")
    if len(parts) < 4:
        return await q.edit_message_text("Invalid data.")
    _, bank_name, amount_s, creator_id_s = parts[:4]
    try:
        amount = int(amount_s)
    except:
        return await q.edit_message_text("Invalid amount.")
    bank = find_bank(bank_name)
    if not bank:
        return await q.edit_message_text("Bank not found.")
    # only owners can set via this button
    if q.from_user.id not in OWNER_IDS:
        return await q.edit_message_text("Only bot owner can set budgets.")
    bank["budget"] = amount
    save_bank(bank)
    # notify bank creator
    try:
        await context.bot.send_message(int(creator_id_s), f"📣 Your bank *{bank_name}* has been allocated a budget of ${amount} by the bot owner.", parse_mode="Markdown")
    except:
        pass
    await q.edit_message_text(f"✅ Budget ${amount} set for bank *{bank_name}*.", parse_mode="Markdown")

# -----------------------
# /lottery — owner-only run lottery distribution
# Behavior: choose one jackpot winner who gets 30000, others (sampled up to 100000 users) get random 1000-9000
# -----------------------
async def lottery_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    uid = msg.from_user.id
    if uid not in OWNER_IDS:
        return await msg.reply_text("Only bot owner can run the lottery.")
    # gather users
    all_users = users_table.all()
    if not all_users:
        return await msg.reply_text("No users in database to run a lottery.")
    # cap to 100000 to prevent huge loops
    cap = 100000
    if len(all_users) > cap:
        sampled = random.sample(all_users, cap)
    else:
        sampled = all_users
    # compute wallet updates
    jackpot_winner = random.choice(sampled)
    jackpot_uid = int(jackpot_winner.get("user_id"))
    JACKPOT = 30000
    winners_sent = 0
    failures = 0
    for rec in sampled:
        try:
            uid_t = int(rec.get("user_id"))
            rec_db = users_table.get(UserQ.user_id == uid_t) or rec
            if uid_t == jackpot_uid:
                recdb = users_table.get(UserQ.user_id == uid_t) or rec
            if uid_t == jackpot_uid:
                rec_db["coins"] = rec_db.get("coins", 0) + JACKPOT
                note = f"🎉 Lottery jackpot! You won ${JACKPOT}!"
            else:
                gain = random.randint(1000, 9000)
                rec_db["coins"] = rec_db.get("coins", 0) + gain
                note = f"🎟️ You won ${gain} in the lottery!"
            users_table.upsert(rec_db, UserQ.user_id == uid_t)
            # try DM (best-effort)
            try:
                await context.bot.send_message(uid_t, note)
                winners_sent += 1
            except:
                failures += 1
        except Exception:
            failures += 1
    await msg.reply_text(f"Lottery distributed to {len(sampled)} users. DMs sent: {winners_sent}; failures: {failures}. Jackpot winner: User{jackpot_uid}")

# -----------------------
# /leavebank <bank_name>
# -----------------------
async def leavebank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    if not context.args:
        return await safe_reply(msg, "Usage: /leavebank <bank_name>")

    bank_name = " ".join(context.args).strip()
    bank = find_bank(bank_name)

    if not bank:
        return await safe_reply(msg, "That bank does not exist.")

    user = msg.from_user

    if user.id not in bank.get("members", []):
        return await safe_reply(msg, "You are not a member of this bank.")

    # Remove user
    bank["members"].remove(user.id)
    save_bank(bank)

    await safe_reply(msg, f"👋 You have left the bank *{bank_name}*.", parse_mode="Markdown")

# -----------------------
# /all <message> — mention all admins (safer than mentioning everyone)
# -----------------------
async def all_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    text = " ".join(context.args).strip()
    if not text:
        return await msg.reply_text("Usage: /all <message> — mentions all admins.")
    chat = msg.chat
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
    except Exception:
        return await msg.reply_text("Failed to fetch admins.")
    mentions = []
    for a in admins:
        u = a.user
        if getattr(u, "username", None):
            mentions.append(f"@{u.username}")
        else:
            mentions.append(f"[{u.first_name}](tg://user?id={u.id})")
    mention_text = " ".join(mentions)
    out = f"{text}\n\n{mention_text}"
    await msg.reply_markdown(out)

# ============================
# /getloan <amount>
# Request a loan from your bank (must be approved)
# ============================
async def getloan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user = msg.from_user
    uid = user.id

    # amount validation
    if not context.args:
        return await msg.reply_text("Usage: /getloan <amount>")
    try:
        amount = int(context.args[0])
        if amount <= 0:
            return await msg.reply_text("Loan amount must be positive.")
    except:
        return await msg.reply_text("Invalid amount. Use numbers only.")

    # get bank record
    bank = banks_table.get(BankQ.name == bank_name)
    if not bank:
        return await msg.reply_text("Error: Your bank no longer exists.")

    creator_id = bank.get("creator_id")
    budget = bank.get("budget", 0)

    if amount > budget:
        return await msg.reply_text(f"Your bank does not have enough budget for this loan.\nAvailable: {budget}")

    # Notify bank creator for approval
    text = (
        f"📨 Loan Request\n"
        f"User: {user.first_name} ({uid})\n"
        f"Bank: {bank_name}\n"
        f"Amount: {amount}\n\n"
        f"Approve loan?"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Approve", callback_data=f"loan_ok|{uid}|{amount}|{bank_name}"),
            InlineKeyboardButton("Reject", callback_data=f"loan_no|{uid}|{amount}|{bank_name}")
        ]
    ])

    try:
        await context.bot.send_message(creator_id, text, reply_markup=keyboard)
        await msg.reply_text("Your loan request was sent to the bank creator!")
    except:
        await msg.reply_text("Bank creator cannot be contacted. Try again later.")

# =============================
# Loan approval callback
# =============================
async def loan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    action, uid, amount, bankname = data
    uid = int(uid)
    amount = int(amount)

    bank = banks_table.get(BankQ.name == bankname)
    if not bank:
        return await query.edit_message_text("Bank not found.")

    # bank creator check
    if query.from_user.id != bank.get("creator_id"):
        return await query.answer("Only bank creator can approve.", show_alert=True)

    # approve loan
    if action == "loan_ok":
        user_rec = ensure_user_record({"id": uid})
        user_rec["coins"] = user_rec.get("coins", 0) + amount
        save_user(user_rec)

        bank["budget"] -= amount
        banks_table.update(bank, BankQ.name == bankname)

        await context.bot.send_message(
            uid,
            f"🎉 Your loan request of {amount} was approved!"
        )
        await query.edit_message_text("Loan approved successfully.")

    else:
        await context.bot.send_message(uid, "❌ Your loan request was rejected.")
        await query.edit_message_text("Loan rejected.")

# -----------------------
# /deletebank <bank_name>
# -----------------------
async def deletebank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    if not context.args:
        return await safe_reply(msg, "Usage: /deletebank <bank_name>")

    bank_name = " ".join(context.args).strip()
    bank = find_bank(bank_name)

    if not bank:
        return await safe_reply(msg, "That bank does not exist.")

    user = msg.from_user

    # Check creator
    if bank.get("creator_id") != user.id:
        return await safe_reply(msg, "❌ Only the bank creator can delete this bank.")

    # Delete bank
    Q = Query()
    banks_table.remove(Q.name == bank_name)

    await safe_reply(msg, f"🗑️ Bank *{bank_name}* has been deleted.", parse_mode="Markdown")

# End of bank+economy module

# ===============================
# 🔰 BANK CALLBACKS (FULL CODE)
# ===============================

# -------- JOIN REQUEST ACCEPT / DECLINE --------
async def callback_bank_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data or ""
    parts = data.split("|")
    if len(parts) != 3:
        return await query.edit_message_text("Invalid data.")

    action, bank_name, user_id = parts[0], parts[1], int(parts[2])

    bank = find_bank(bank_name)
    if not bank:
        return await query.edit_message_text("This bank no longer exists.")

    # Only bank owner can accept / decline
    if query.from_user.id != bank.get("creator_id"):
        return await query.edit_message_text("Only the bank owner can respond to join requests.")

    # Approve join
    if action == "bank_join":
        if user_id in bank.get("members", []):
            return await query.edit_message_text("User already a member.")

        bank.setdefault("members", []).append(user_id)
        save_bank(bank)

        try:
            await context.bot.send_message(
                user_id,
                f"✅ You have been approved to join *{bank_name}* by {query.from_user.mention_html()}!",
                parse_mode="HTML"
            )
        except:
            pass

        return await query.edit_message_text("User approved and notified.")

    # Decline join
    else:
        try:
            await context.bot.send_message(
                user_id,
                f"❌ Your request to join *{bank_name}* was declined.",
            )
        except:
            pass

        return await query.edit_message_text("Declined and user notified.")


# -------- JOIN CANCELLED BY USER --------
async def callback_bank_join_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ You cancelled joining the bank.")


# ===============================
# 🔰 LEAVE BANK CALLBACKS
# ===============================

# -------- USER CONFIRMS LEAVING BANK --------
async def callback_leavebank_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    parts = data.split("|")

    if len(parts) != 3:
        return await query.edit_message_text("Invalid leavebank data.")

    _, bank_name, user_id = parts
    user_id = int(user_id)

    bank = find_bank(bank_name)
    if not bank:
        return await query.edit_message_text("This bank no longer exists.")

    # Only the user himself can confirm
    if query.from_user.id != user_id:
        return await query.edit_message_text("❌ You cannot confirm on behalf of another user.")

    # Check membership
    if user_id not in bank.get("members", []):
        return await query.edit_message_text("❌ You are not a member of this bank.")

    # Remove user
    bank["members"].remove(user_id)
    save_bank(bank)

    await query.edit_message_text(
        f"👋 You have left *{bank_name}*.",
        parse_mode="Markdown"
    )


# -------- USER CANCELS LEAVE BANK --------
async def callback_leavebank_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Cancelled leaving the bank.")


# ===============================
# 🔰 DELETE BANK CALLBACKS
# ===============================

# -------- BANK OWNER CONFIRMS DELETE --------
async def callback_deletebank_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    parts = data.split("|")

    if len(parts) != 3:
        return await query.edit_message_text("Invalid deletebank data.")

    _, bank_name, creator_id = parts
    creator_id = int(creator_id)

    bank = find_bank(bank_name)
    if not bank:
        return await query.edit_message_text("Bank does not exist anymore.")

    # Only creator can delete
    if query.from_user.id != creator_id:
        return await query.edit_message_text("❌ Only the bank creator can delete this bank.")

    # Delete bank
    Q = Query()
    banks_table.remove(Q.name == bank_name)

    await query.edit_message_text(
        f"🗑️ Bank *{bank_name}* has been permanently deleted.",
        parse_mode="Markdown"
    )


# -------- CREATOR CANCELS DELETE --------
async def callback_deletebank_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Bank deletion cancelled.")

# ========== FEEDBACK SYSTEM (ONLY /feedback) ==========
from tinydb import TinyDB, Query

feedback_db = TinyDB("feedback.json")
FeedbackQ = Query()

OWNER_IDS = {5773908061}   # <-- replace with your owner id(s)

# /feedback <message>
async def feedback_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user = msg.from_user
    text = " ".join(context.args).strip()

    if not text:
        return await msg.reply_text(
            "✏️ **Usage:** /feedback <your feedback>\n"
            "Please tell me what you want to report or suggest.",
            parse_mode="markdown"
        )

    # Store feedback in DB (optional)
    feedback_rec = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "feedback": text
    }
    feedback_db.insert(feedback_rec)

    # Send to owner(s)
    for owner in OWNER_IDS:
        try:
            await context.bot.send_message(
                owner,
                f"📝 **New Feedback Received**\n"
                f"👤 From: {user.first_name} (@{user.username})\n"
                f"🆔 ID: {user.id}\n\n"
                f"💬 Message:\n{text}",
                parse_mode="markdown"
            )
        except:
            pass

    await msg.reply_text("✅ Thank you! Your feedback has been sent.")

# -------------------- /register --------------------
async def register_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    user = msg.from_user
    rec = ensure_user_record(user)
    if rec.get("registered"):
        return await msg.reply_text("You are already registered.")
    rec["coins"] = rec.get("coins", 0) + 100000
    rec["registered"] = True
    save_user(rec)
    await msg.reply_text("✅ Registered! You received 100000 coins.")

# ====== END: NEW FEATURES ======

async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        try:
            await update.message.reply_text(
                f"Welcome {member.mention_html()} ❤️🤗!",
                parse_mode="HTML"
            )
        except Exception:
            continue

# utilities
def owner_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *a, **kw):
        uid = update.effective_user.id if update.effective_user else None
        if uid in OWNER_IDS:
            return await func(update, context, *a, **kw)
        await update.effective_message.reply_text("❌ Only the owner may use this command.")
    return wrapped

def now_ts() -> float:
    return datetime.utcnow().timestamp()

def ensure_user_record(user) -> Dict[str, Any]:
    uid = int(user.id)
    rec = users_table.get(UserQ.user_id == uid)
    if rec:
        # update username/display_name/is_bot
        rec["username"] = (f"@{user.username}" if getattr(user, "username", None) else rec.get("username"))
        rec["display_name"] = user.first_name or rec.get("display_name")
        rec["is_bot"] = bool(getattr(user, "is_bot", False))
        users_table.upsert(rec, UserQ.user_id == uid)
        return rec
    rec = {
        "user_id": uid,
        "username": (f"@{user.username}" if getattr(user, "username", None) else None),
        "display_name": user.first_name or None,
        "is_bot": bool(getattr(user, "is_bot", False)),
        "coins": START_COINS,
        "kills": 0,
        "dead": False,
        "protected_until": 0.0,
        "last_daily": 0.0,
        "inventory": {},
        # sticker pack record key (internal DB pack_key), created by /newpack or /own first use
        "sticker_pack": None,
    }
    users_table.insert(rec)
    return rec

def save_user(rec: Dict[str, Any]):
    users_table.upsert(rec, UserQ.user_id == rec["user_id"])

def get_user_by_id(uid: int) -> Optional[Dict[str, Any]]:
    return users_table.get(UserQ.user_id == int(uid))

def set_group_open(chat_id: int, val: bool):
    groups_table.upsert({"chat_id": int(chat_id), "economy_enabled": bool(val)}, GroupQ.chat_id == int(chat_id))

def check_group_open(chat_id: int) -> bool:
    rec = groups_table.get(GroupQ.chat_id == int(chat_id))
    return bool(rec and rec.get("economy_enabled", False))

def mention_clickable(rec: Dict[str, Any]) -> str:
    if rec.get("username"):
        return rec["username"]
    name = rec.get("display_name") or f"User{rec['user_id']}"
    return f"[{name}](tg://user?id={rec['user_id']})"

def stylize_name(name: str) -> str:
    return name

def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None

FFMPEG = ffmpeg_available()
logger.info("ffmpeg available: %s", FFMPEG)

# ---------- Sticker packs DB helpers ----------
# packs_table records: { 'owner_id': int, 'pack_key': str, 'title': str, 'created': bool }
def pack_key_for_user_name(raw_name: str, bot_username: str) -> str:
    s = re.sub(r'[^A-Za-z0-9_]', '_', raw_name).strip('_')
    s = re.sub(r'_+', '_', s)[:30]
    botname = re.sub(r'[^A-Za-z0-9_]', '', bot_username or "bot")
    full = f"{s}_{botname}"
    return full[:64]

def save_pack_record(owner_id: int, pack_key: str, title: str, created: bool=False):
    packs_table.upsert({'owner_id': int(owner_id), 'pack_key': pack_key, 'title': title, 'created': bool(created)},
                       (PackQ.owner_id == int(owner_id)) & (PackQ.pack_key == pack_key))

def list_user_packs(owner_id: int):
    return packs_table.search(PackQ.owner_id == int(owner_id))

def get_pack(owner_id: int, pack_key: str):
    return packs_table.get((PackQ.owner_id == int(owner_id)) & (PackQ.pack_key == pack_key))

def remove_pack_record(owner_id: int, pack_key: str):
    packs_table.remove((PackQ.owner_id == int(owner_id)) & (PackQ.pack_key == pack_key))

# sessions_table used to store temporary state: {user_id, awaiting_newpack_name, awaiting_own_name, last_action}
def save_session(user_id: int, data: Dict[str, Any]):
    sessions_table.upsert({'user_id': int(user_id), **data}, SessQ.user_id == int(user_id))

def load_session(user_id: int) -> Optional[Dict[str, Any]]:
    res = sessions_table.get(SessQ.user_id == int(user_id))
    return res

def clear_session(user_id: int):
    sessions_table.remove(SessQ.user_id == int(user_id))

# ---------- UI Keyboards & START/HELP MENU (replacement) ----------
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

# ---------- IMPORTS ----------
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

BOT_OWNER = "RJVTAX"
OWNER_URL = f"https://t.me/{BOT_OWNER}"
SUPPORT_LINK = "https://t.me/team_bright_lightX"
CHANNEL_LINK = "https://t.me/YUUKIUPDATES"

# ---------- INLINE KEYBOARDS ----------
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎭 Economy", callback_data="menu:economy"),
            InlineKeyboardButton("🥳 Fun", callback_data="menu:fun")
        ],
        [
            InlineKeyboardButton("🎮 Game", callback_data="menu:game"),
            InlineKeyboardButton("👥 Group Help", callback_data="menu:grouphelp")
        ],
        [
            InlineKeyboardButton("👑 Owner 👑", url=OWNER_URL)
        ]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Back", callback_data="menu:main")
        ],
        [
            InlineKeyboardButton("👑 Owner 👑", url=OWNER_URL)
        ]
    ])

def start_keyboard(addme_url):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💬 Support Chat", SUPPORT_URL),
            InlineKeyboardButton("✅ Updates Channel", CHANNEL_URL)
        ],
        [
            InlineKeyboardButton("✨ Add Me To Your Group ✨", url=addme_url)
        ],
        [
            InlineKeyboardButton("👑 Owner 👑", url=OWNER_URL)
        ]
    ])

# ---------- START COMMAND ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    # Prepare Add-Me link
    try:
        me = await context.bot.get_me()
        addme_url = f"https://t.me/{me.username}?startgroup=true"
    except:
        addme_url = "https://t.me/Im_yuukiBot?startgroup=true"

    text = (
        "✨ 𝑾𝒆𝒍𝒄𝒐𝒎𝒆 𝒕𝒐 𝒀𝒖𝒖𝒌𝒊_ ✨\n\n"
        "⚡ 𝒀𝒐𝒖𝒓 𝒖𝒍𝒕𝒊𝒎𝒂𝒕𝒆 𝒈𝒓𝒐𝒖𝒑 𝒂𝒔𝒔𝒊𝒔𝒕𝒂𝒏𝒕\n"
        "💰 𝑬𝒄𝒐𝒏𝒐𝒎𝒚 • 🎮 𝑮𝒂𝒎𝒆𝒔 • 🥳 𝑭𝒖𝒏 • 🛡 𝑴𝒐𝒅𝒆𝒓𝒂𝒕𝒊𝒐𝒏\n"
        "🔧 𝑨𝒅𝒗𝒂𝒏𝒄𝒆𝒅 𝒈𝒄 𝒕𝒐𝒐𝒍𝒔 & 𝒔𝒎𝒂𝒓𝒕 𝒂𝒖𝒕𝒐-𝒓𝒆𝒑𝒍𝒚\n\n"
        "❤️ 𝑴𝒂𝒅𝒆 𝒃𝒚 @{BOT_OWNER}"
    )

    await msg.reply_text(
        text,
        reply_markup=start_keyboard(addme_url),
        parse_mode="Markdown"
    )

# ---------- HELP COMMAND ----------
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ 𝒀𝒖𝒖𝒌𝒊_ — 𝑯𝒆𝒍𝒑 𝑴𝒆𝒏𝒖\n𝑪𝒉𝒐𝒐𝒔𝒆 𝒂 𝒄𝒂𝒕𝒆𝒈𝒐𝒓𝒚 👇",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

# ---------- CALLBACK HANDLER ----------
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    section = q.data.split(":", 1)[1]

    # MAIN MENU
    if section == "main":
        await q.edit_message_text(
            "✨ 𝒀𝒖𝒖𝒌𝒊_ — 𝑯𝒆𝒍𝒑 𝑴𝒆𝒏𝒖\n𝑺𝒆𝒍𝒆𝒄𝒕 𝒂 𝒄𝒂𝒕𝒆𝒈𝒐𝒓𝒚 👇",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    # ECONOMY
    if section == "economy":
        txt = (
            "💰 *Yuuki — Economy Commands*\n\n"
            "• /open — Enable economy\n"
            "• /close — Disable\n"
            "• /daily — Daily reward\n"
            "• /bal — Balance\n"
            "• /toprich — Richest users\n"
            "• /topkill — Kill leaderboard\n\n"
            "• /give — Gift coins\n"
            "• /rob — Rob users\n"
            "• /kill — Kill a user\n"
            "• /revive — Revive someone\n"
            "• /protect — Buy protection\n\n"
            "🛍 *Shop*\n/register • /shop • /buy • /gift\n\n"
            "🏦 *Bank*\n/createbank • /deposit • /withdraw\n/bank • /budget • /getloan"
        )
        await q.edit_message_text(txt, reply_markup=back_keyboard(), parse_mode="Markdown")
        return

    # FUN
    if section == "fun":
        txt = (
            "🥳 *Fun Commands*\n"
            "• /punch\n"
            "• /slap\n"
            "• /kiss\n"
            "• /hug\n"
            "• /ping"
        )
        await q.edit_message_text(txt, reply_markup=back_keyboard(), parse_mode="Markdown")
        return

    # GAME
    if section == "game":
        txt = (
            "🎮 *Game Commands*\n"
            "• /kill\n"
            "• /rob\n"
            "• /revive\n"
            "• /protect"
        )
        await q.edit_message_text(txt, reply_markup=back_keyboard(), parse_mode="Markdown")
        return

    # GROUP HELP
    if section == "grouphelp":
        txt = (
            "👥 *Group Help*\n\n"
            "• /promote\n"
            "• /demote\n"
            "• /ban\n"
            "• /mute\n"
            "• /unmute\n"
            "• /warn\n"
            "• /setwelcome\n"
            "• /setrules"
        )
        await q.edit_message_text(txt, reply_markup=back_keyboard(), parse_mode="Markdown")
        return

# ---------- group open/close ----------
async def open_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        return await update.message.reply_text("Use /open in a group.")
    user = update.effective_user
    try:
        member = await chat.get_member(user.id)
        if member.status not in ("administrator", "creator") and user.id not in OWNER_IDS:
            return await update.message.reply_text("Only group admins can open economy.")
    except Exception:
        pass
    set_group_open(chat.id, True)
    await update.message.reply_text("✅ Economy is now OPEN in this group.")

async def close_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        return await update.message.reply_text("Use /close in a group.")
    user = update.effective_user
    try:
        member = await chat.get_member(user.id)
        if member.status not in ("administrator", "creator") and user.id not in OWNER_IDS:
            return await update.message.reply_text("Only group admins can close economy.")
    except Exception:
        pass
    set_group_open(chat.id, False)
    await update.message.reply_text("⛔ Economy is now CLOSED in this group to reopen: /open .")

# ---------- economy/game commands ----------
async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    rec = ensure_user_record(user)
    if now_ts() - rec.get("last_daily", 0.0) < 24*3600:
        return await update.message.reply_text("You already claimed daily in the last 24 hours.")
    bonus = random.randint(DAILY_MIN, DAILY_MAX)
    rec["coins"] += bonus
    rec["last_daily"] = now_ts()
    save_user(rec)
    await update.message.reply_text(f"🎁 Daily: +{bonus} coins")

async def bal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != "private" and not check_group_open(chat.id):
        return await update.message.reply_text("Economy is closed in this group.")
    target_user = update.effective_user
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    rec = ensure_user_record(target_user)

# ---------- balance ----------
async def bal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != "private" and not check_group_open(chat.id):
        return await update.message.reply_text("⛔ Economy commands are disabled in this group to reopen: /open .")

    target_user = update.effective_user
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user

    rec = ensure_user_record(target_user)

    # compute rank excluding bots
    all_users = [u for u in users_table.all() if not u.get("is_bot", False)]
    sorted_u = sorted(all_users, key=lambda r: r.get("coins", 0), reverse=True)
    rank = next((i+1 for i, r in enumerate(sorted_u) if r["user_id"] == rec["user_id"]), len(sorted_u))

    # just normal name, no clickable link
    name_line = f"👤 Name: {stylize_name(rec.get('display_name') or rec.get('username') or f'User{rec['user_id']}')}"

    status = "💀 Dead" if rec.get("dead", False) else "❤️ Alive"

    text = (
        f"{name_line}\n"
        f"💰 Total Balance: {rec.get('coins',0)}\n"
        f"🏆 Global Rank: {rank}\n"
        f"❤️ Status: {status}\n"
        f"⚔️ Kills: {rec.get('kills',0)}"
    )

    await update.message.reply_text(text)

from telegram import Update
from telegram.ext import ContextTypes

def format_user_plain(r):
    """Format user for plain text leaderboard."""
    username = r.get("username")
    display = r.get("display_name") or f"User{r.get('user_id','???')}"

    if username:
        # Show @username clickable
        return f"{username}"
    else:
        # Show display name if no username
        return display

# ---------- top 10 richest ----------
async def toprich_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        print("No update.message in toprich_cmd")
        return
    try:
        all_users = users_table.all()
        users = [u for u in all_users if not u.get("is_bot", False)]
        if not users:
            await update.message.reply_text("No users found.")
            return

        top = sorted(users, key=lambda r: int(r.get("coins", 0)), reverse=True)[:10]
        lines = ["🏆 Top 10 Richest"]

        for i, r in enumerate(top, start=1):
            name = format_user_plain(r)
            coins = int(r.get("coins", 0))
            lines.append(f"{i}. {name} — {coins} 💰")

        lines.append("\n💡 Set @username to make your name clickable!")
        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        print("Error in toprich_cmd:", e)
        await update.message.reply_text("❌ Something went wrong while fetching the top richest list.")


# ---------- top 10 killers ----------
async def topkills_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        print("No update.message in topkills_cmd")
        return
    try:
        all_users = users_table.all()
        users = [u for u in all_users if not u.get("is_bot", False)]
        if not users:
            await update.message.reply_text("No users found.")
            return

        top = sorted(users, key=lambda r: int(r.get("kills", 0)), reverse=True)[:10]
        lines = ["🔪 Top 10 Killers"]

        for i, r in enumerate(top, start=1):
            name = format_user_plain(r)
            kills = int(r.get("kills", 0))
            lines.append(f"{i}. {name} — {kills} 🔪")

        lines.append("\n💡 Set @username to make your name clickable!")
        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        print("Error in topkills_cmd:", e)
        await update.message.reply_text("❌ Something went wrong while fetching the top killers list.")

# give money - reply usage
async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private" and not check_group_open(update.effective_chat.id):
        return await update.message.reply_text("Economy is closed in this group. To reopen: /open.")

    # Must reply
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to the user you want to give coins to.")

    # Self-giving block
    if update.message.reply_to_message.from_user.id == update.effective_user.id:
        return await update.message.reply_text("You cannot give coins to yourself 💀.")

    # Amount check
    try:
        amt = int(context.args[0])
    except Exception:
        return await update.message.reply_text("Usage: /give <amount> (reply)")

    giver = ensure_user_record(update.effective_user)
    receiver = ensure_user_record(update.message.reply_to_message.from_user)

    # Bot block
    if receiver.get("is_bot"):
        return await update.message.reply_text("🤖 Target detected as a bot — action cancelled.")

    # Balance check
    if giver["coins"] < amt:
        return await update.message.reply_text("You don't have enough coins.")

    # Fee logic
    fee = int(amt * GIFT_FEE_RATIO)
    giver["coins"] -= (amt + fee)
    receiver["coins"] += amt

    save_user(giver)
    save_user(receiver)

    gname = stylize_name(giver.get("display_name") or giver.get("username"))
    rname = stylize_name(receiver.get("display_name") or receiver.get("username"))

    await update.message.reply_text(
        f"💸 {gname} gave ${amt} to {rname}!\n"
        f"Tax fee: ${fee}"
    )

# ---------- rob command ----------
async def rob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != "private" and not check_group_open(chat.id):
        return await update.message.reply_text("⛔ Economy commands are disabled in this group to reopen: /open .")

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to the user you want to rob.")

    try:
        amt = int(context.args[0])
    except Exception:
        return await update.message.reply_text("Usage: /rob <amount> (reply)")
    if amt <= 0:
        return await update.message.reply_text("❌ Invalid amount.")

    thief = ensure_user_record(update.effective_user)
    target = ensure_user_record(update.message.reply_to_message.from_user)

    if target.get("is_bot"):
        return await update.message.reply_text("🤖 Target detected as bot — robbery cancelled.")

    # Check protection
    now = now_ts()
    if target.get("protected_until", 0) > now:
        remaining = int(target["protected_until"] - now)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        return await update.message.reply_text(
            f"🛡️ {stylize_name(target.get('display_name') or target.get('username'))} is protected, Robbery failed!"
        )

    if target["coins"] <= 0:
        return await update.message.reply_text(
            f"{stylize_name(target.get('display_name') or target.get('username'))} has no coins to be robbed."
        )

    stolen = min(amt, target["coins"])
    target["coins"] -= stolen
    thief["coins"] += stolen
    save_user(target)
    save_user(thief)

    txt = f"💰 {stylize_name(thief.get('display_name') or thief.get('username'))} robbed ${stolen} from {stylize_name(target.get('display_name') or target.get('username'))}!"
    await update.message.reply_text(txt)


# ---------- kill command ----------
async def kill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type != "private" and not check_group_open(chat.id):
        return await update.message.reply_text("⛔ Economy commands are disabled in this group. To reopen: /open.")

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to the user you want to kill.")

    killer = ensure_user_record(update.effective_user)
    victim = ensure_user_record(update.message.reply_to_message.from_user)

    # Auto-revive check
    victim = check_auto_revive(victim)
    killer = check_auto_revive(killer)

    if killer.get("dead"):
        return await update.message.reply_text("💀 dead users can’t kill anyone!")

    if victim.get("is_bot"):
        return await update.message.reply_text("🤖 Cannot kill a bot.")

    now = now_ts()
    if victim.get("protected_until", 0) > now:
        return await update.message.reply_text("🛡️ That user is protected, kill failed.")

    if victim.get("dead"):
        return await update.message.reply_text("⚰️ Target is already dead!")

    # reward
    reward = random.randint(KILL_MIN_REWARD, KILL_MAX_REWARD)
    killer["coins"] += reward
    killer["kills"] = killer.get("kills", 0) + 1

    # kill + 6 hr revive timer
    victim["dead"] = True
    victim["dead_until"] = (datetime.utcnow() + timedelta(hours=6)).timestamp()

    save_user(killer)
    save_user(victim)

    txt = (
        f"💀 {stylize_name(killer.get('display_name') or killer.get('username'))} "
        f"killed {stylize_name(victim.get('display_name') or victim.get('username'))}!\n"
        f"💰 Reward: +${reward}\n"
        f"⏳ They will revive automatically in 6 hours."
    )

    await update.message.reply_text(txt)

# ---------- revive command ----------
async def revive_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type != "private" and not check_group_open(chat.id):
        return await update.message.reply_text("⛔ Economy commands are disabled in this group. To reopen: /open.")

    caller = ensure_user_record(update.effective_user)

    # Check reply target
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    else:
        target_user = update.effective_user

    target = ensure_user_record(target_user)

    # Auto revive check (important)
    target = check_auto_revive(target)

    # If already alive
    if not target.get("dead"):
        return await update.message.reply_text("Target is already alive.")

    # Not enough coins
    if caller["coins"] < REVIVE_COST:
        return await update.message.reply_text(f"💸 You need ${REVIVE_COST} to revive.")

    # Manual revive
    caller["coins"] -= REVIVE_COST
    target["dead"] = False
    target["dead_until"] = None
    save_user(caller)
    save_user(target)

    await update.message.reply_text(
        f"🔁 {stylize_name(target.get('display_name') or target.get('username'))} revived —{REVIVE_COST} coins"
    )

# ---------- protect command ----------
async def protect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != "private" and not check_group_open(chat.id):
        return await update.message.reply_text("⛔ Economy commands are disabled in this group.")

    user = ensure_user_record(update.effective_user)
    if not context.args:
        return await update.message.reply_text("Usage: /protect 1d|2d")

    key = context.args[0].lower()
    if key not in PROTECT_COST:
        return await update.message.reply_text("Invalid option. Use 1d or 2d.")

    now = now_ts()
    remaining = user.get("protected_until", 0) - now
    if remaining > 0:
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        return await update.message.reply_text(
            f"🛡️ You are already protected for another {hours}h {minutes}m."
        )

    cost = PROTECT_COST[key]
    if user["coins"] < cost:
        return await update.message.reply_text(f"💸 Not enough coins to buy {key} protection.")

    user["coins"] -= cost
    days = 1 if key == "1d" else 2
    user["protected_until"] = now + days * 86400
    save_user(user)

    await update.message.reply_text(f"✅ Protection purchased for {days} day(s). -{cost} coins")

# revive - if reply -> revive that user, caller pays; if no reply -> revive self (caller pays)
async def revive_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private" and not check_group_open(update.effective_chat.id):
        return await update.message.reply_text("Economy is closed in this group.")
    caller = ensure_user_record(update.effective_user)
    target = None
    if update.message.reply_to_message:
        target = ensure_user_record(update.message.reply_to_message.from_user)
    else:
        target = caller
    if caller["coins"] < REVIVE_COST:
        return await update.message.reply_text(f"You need ${REVIVE_COST} to revive.")
    if not target.get("dead"):
        return await update.message.reply_text("Target is not dead.")
    caller["coins"] -= REVIVE_COST
    target["dead"] = False
    save_user(caller); save_user(target)
    await update.message.reply_text(
        f"🔁 {stylize_name(target.get('display_name') or target.get('username'))} revived -{REVIVE_COST} coins"
)

# transfer for owner
@owner_only
async def transfer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        return await update.message.reply_text("Usage: /transfer <add|remove> <amount> <@user/id>")
    mode = context.args[0]
    try:
        amount = int(context.args[1])
    except:
        return await update.message.reply_text("Invalid amount.")
    target = context.args[2]
    # get id or @username -> naive: try id first
    target_id = None
    if target.startswith("@"):
        # find in DB
        rec = users_table.get(UserQ.username == target)
        if rec:
            target_id = rec["user_id"]
    else:
        try:
            target_id = int(target)
        except:
            pass
    if not target_id:
        return await update.message.reply_text("Could not find target user in DB by username or id.")
    rec = get_user_by_id(target_id)
    if not rec:
        return await update.message.reply_text("Target user not found.")
    if mode == "add":
        rec["coins"] = rec.get("coins", 0) + amount
    elif mode == "remove":
        rec["coins"] = max(0, rec.get("coins", 0) - amount)
    else:
        return await update.message.reply_text("Mode must be add or remove.")
    save_user(rec)
    await update.message.reply_text(f"✅ Transfer done for {rec.get('username') or rec.get('display_name')}")

# ---------- reset single player ----------
@owner_only
async def resetplayer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    target_user = None

    # 1) If command is a reply → use that user
    if msg.reply_to_message:
        target_user = msg.reply_to_message.from_user

    # 2) If argument is provided → check ID or username
    elif context.args:
        arg = context.args[0]

        # Numeric ID
        if arg.isdigit():
            try:
                target_user = await context.bot.get_chat(int(arg))
            except Exception:
                return await msg.reply_text("❌ Invalid user ID.")

        # Username starting with @
        elif arg.startswith("@"):
            try:
                target_user = await context.bot.get_chat(arg)
            except Exception:
                return await msg.reply_text("❌ Invalid username.")
        else:
            return await msg.reply_text("❌ Invalid argument, provide a user ID or @username.")

    # 3) No reply & no args → reset self
    else:
        target_user = msg.from_user

    # Ensure the user record exists
    rec = ensure_user_record(target_user)

    # Reset all relevant fields
    rec["coins"] = START_COINS
    rec["kills"] = 0
    rec["dead"] = False
    rec["dead_until"] = None
    rec["protected_until"] = 0
    rec["inventory"] = {}
    rec["sticker_pack"] = None
    save_user(rec)

    await msg.reply_text(
        f"🔄 Reset data for **{stylize_name(rec.get('display_name') or getattr(target_user, 'username', 'Unknown'))}**.",
        parse_mode="Markdown"
    )

# ---------- reset all players ----------
@owner_only
async def resetall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    # Truncate all relevant tables
    users_table.truncate()
    banks_table.truncate()
    sessions_table.truncate()

    await msg.reply_text("⚠️ All players' data has been whiped out completely.", parse_mode="Markdown")

# ---------- kill command ----------
async def kill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != "private" and not check_group_open(chat.id):
        return await update.message.reply_text("⛔ Economy commands are disabled in this group to reopen: /open .")

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to the user you want to kill.")

    killer = ensure_user_record(update.effective_user)
    victim = ensure_user_record(update.message.reply_to_message.from_user)

    if killer.get("dead"):
        return await update.message.reply_text("💀 You are dead, you can’t kill anyone!")

    if victim.get("is_bot"):
        return await update.message.reply_text("🤖 Target detected as bot — action cancelled.")

    now = now_ts()
    if victim.get("protected_until", 0) > now:
        remaining = int(victim["protected_until"] - now)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        return await update.message.reply_text(
            f"🛡️ {stylize_name(victim.get('display_name') or victim.get('username'))} is protected, Kill failed!"
        )

    if victim.get("dead"):
        return await update.message.reply_text("⚰️ Target is already dead!")

    # Kill success
    reward = random.randint(KILL_MIN_REWARD, KILL_MAX_REWARD)
    killer["kills"] = killer.get("kills", 0) + 1
    killer["coins"] += reward
    victim["dead"] = True
    victim["dead_until"] = (datetime.utcnow() + timedelta(hours=6)).timestamp()  # auto revive in 6h
    save_user(killer)
    save_user(victim)

    txt = (
        f"💀 {stylize_name(killer.get('display_name') or killer.get('username'))} "
        f"killed {stylize_name(victim.get('display_name') or victim.get('username'))}!\n"
        f"💰 Reward: +${reward}\n"
        f"⏳ They will revive automatically in 6 hours."
    )
    await update.message.reply_text(txt)

import random
import time
from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

# ---------- SHOP STATE ----------
# Tracks the weekly Moneybag cooldown
SHOP_STATE = {}

# ---------- CONFIG ----------
SHOP_ITEMS = {
    "rose": {"display": "Rose", "price": 200, "emoji": "🌹", "type": "gift"},
    "moneybag": {"display": "Moneybag", "price": 1000, "emoji": "💰", "type": "money"},
    # Add more gifts here if needed
}

MONEYBAG_COOLDOWN = 7 * 24 * 3600  # 1 week in seconds
REGISTER_AMOUNT = 5000

# ---------- REGISTER ----------
async def register_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return await update.message.reply_text("❗ Use /register in DM for claiming $100000.")

    user = ensure_user_record(update.effective_user)
    if user.get("registered", False):
        return await update.message.reply_text("✅ You have already registered before.")

    user["registered"] = True
    user["coins"] = user.get("coins", 0) + REGISTER_AMOUNT
    save_user(user)
    await update.message.reply_text(f"🎉 Registration successful! You received ${REGISTER_AMOUNT}.")

# ---------- SHOP ----------
async def shop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != "private" and not check_group_open(chat.id):
        return await update.message.reply_text("⛔ Economy commands are disabled in this group.")

    lines = ["🛒 *Shop Items:*"]
    now = time.time()
    moneybag_last = SHOP_STATE.get("moneybag_last", 0)
    for key, item in SHOP_ITEMS.items():
        name = escape_markdown(item['display'], version=2)
        if key == "moneybag":
            if now - moneybag_last < MONEYBAG_COOLDOWN:
                status = "⚠️ Sold out"
            else:
                status = f"{item['price']} 💰"
            lines.append(f"{item['emoji']} [{name}] \\- {status}  (`{key}`)")
        else:
            lines.append(f"{item['emoji']} [{name}] \\- {item['price']} 💰  (`{key}`)")

    lines.append("\nUse: /buy <item_key> <amount>  |  /gift <item_key> <amount> (reply to user)")
    lines.append("⚠️ Set @username to make gifting possible.")
    await update.message.reply_markdown_v2("\n".join(lines))

# ---------- BUY ----------
async def buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user_record(update.effective_user)
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /buy <item_key> <amount>")

    key = context.args[0].lower()
    amt = 1
    if len(context.args) >= 2:
        try:
            amt = int(context.args[1])
        except:
            return await update.message.reply_text("Invalid amount.")
    if amt <= 0:
        return await update.message.reply_text("Amount must be positive.")

    if key not in SHOP_ITEMS:
        return await update.message.reply_text("Item not found.")

    price = SHOP_ITEMS[key]['price'] * amt
    if user["coins"] < price:
        return await update.message.reply_text("Not enough coins.")

    # MONEYBAG SPECIAL RULE
    if key == "moneybag":
        now = time.time()
        last_time = SHOP_STATE.get("moneybag_last", 0)
        if now - last_time < MONEYBAG_COOLDOWN:
            return await update.message.reply_text("⚠️ Moneybag already sold this week! Come back later.")
        SHOP_STATE["moneybag_last"] = now
        gained = random.randint(1000, 10000)
        user["coins"] += gained
        save_user(user)
        await update.message.reply_text(f"💰 You bought Moneybag for {price} 💰 and got {gained} coins!")
        return

    # normal purchase
    user["coins"] -= price
    inv = user.get("inventory", {})
    inv[key] = inv.get(key, 0) + amt
    user["inventory"] = inv
    save_user(user)
    await update.message.reply_text(f"✅ Purchased {amt}x {SHOP_ITEMS[key]['display']} for {price} 💰")

# ---------- INVENTORY ----------
async def inventory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user_record(update.effective_user)
    inv = user.get("inventory", {})
    if not inv:
        return await update.message.reply_text("🎒 Your inventory is empty.")

    lines = ["🎒 *Your Inventory:*"]
    for key, qty in inv.items():
        if key in SHOP_ITEMS:
            item = SHOP_ITEMS[key]
            name = escape_markdown(item['display'], version=2)
            lines.append(f"{item['emoji']} [{name}] \\- {qty}")
    await update.message.reply_markdown_v2("\n".join(lines))

# ---------- GIFT ----------
async def gift_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != "private" and not check_group_open(chat.id):
        return await update.message.reply_text("⛔ Economy commands are disabled in this group.")

    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /gift <item_key> <amount> (reply to user)")

    key = context.args[0].lower()
    try:
        amt = int(context.args[1])
    except:
        return await update.message.reply_text("Invalid amount.")

    if amt <= 0:
        return await update.message.reply_text("Amount must be positive.")

    if key not in SHOP_ITEMS:
        return await update.message.reply_text("Item not found.")

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to the user you want to gift.")

    target_user = update.message.reply_to_message.from_user
    if target_user.id == update.effective_user.id:
        return await update.message.reply_text("You cannot gift items to yourself.")

    sender = ensure_user_record(update.effective_user)
    target = ensure_user_record(target_user)

    inv = sender.get("inventory", {})
    if inv.get(key, 0) < amt:
        return await update.message.reply_text("You don’t have enough of that item.")

    # Remove from sender
    inv[key] -= amt
    if inv[key] == 0:
        del inv[key]
    sender["inventory"] = inv
    save_user(sender)

    # Add to receiver
    recv_inv = target.get("inventory", {})
    recv_inv[key] = recv_inv.get(key, 0) + amt
    target["inventory"] = recv_inv
    save_user(target)

    await update.message.reply_text(
        f"🎁 You gifted {amt}x {SHOP_ITEMS[key]['display']} to {stylize_name(target.get('display_name') or target.get('username'))}!"
    )

# --------------------------
# Membership / Premium / Infinity System + Fun commands
# Paste AFTER your DB & users_table & sessions_table are defined.
# --------------------------

from datetime import datetime, timedelta
import random
import time

# Constants (tweak as needed)
CREDIT_COST_COINS = 100_0000   # you said earlier change, keep high default if you want
# But per your request to reduce costs:
CREDIT_COST_COINS = 1_000_000  # 1 credit = 1,000,000 coins (change if you want)
MEMBERSHIP_COST_CREDITS = 1    # credits
PREMIUM_COST_CREDITS = 5
INFINITY_COST_CREDITS = 2
MEMBERSHIP_DAYS = 30

# Rewards / limits
PDAYLY_REWARD_MEMBER = 5000
PDAYLY_REWARD_PREMIUM = 10000
GMUTE_SECONDS = 5 * 60
GMUTE_DAILY_LIMIT = 2
CHECK_COST_COINS = 5_000
FREE_PERCENT = 0.20
PROB_TAKE_RATIO = 0.30

# infinity effects
INFINITY_BOOST = 0.30           # 30% boost (stats/effects)
INFINITY_REVIVE_REDUCE_HOURS = 5
INFINITY_GRACE_REVIVE_SECONDS = 3600  # if you die, you'll auto-revive within 1 hour (logic described)

# TinyDB Query object — try to reuse existing
try:
    Query  # if Query is already imported
except NameError:
    from tinydb import Query
    Query = Query

UserQ = Query()

# -------------------------
# ensure/save helpers (safe: wont overwrite existing)
# -------------------------
def ensure_user_record(user):
    """Return user record from TinyDB; create defaults if missing.
    Accepts telegram.User or synthetic object."""
    if not user:
        return None
    uid = getattr(user, "id", None)
    if uid is None:
        return {"user_id": None}
    rec = users_table.get(UserQ.user_id == uid)
    if not rec:
        rec = {
            "user_id": uid,
            "username": getattr(user, "username", None),
            "display_name": getattr(user, "first_name", "User"),
            "coins": 0,
            "credits": 0,
            "membership_until": 0,
            "premium_until": 0,
            "infinity_until": 0,
            "last_pdaily": 0,
            "last_daily": 0,
            "claim_available": False,
            "free_available": False,
            "gmute_uses_date": 0,
            "gmute_uses_today": 0,
            "gmute_until": 0,
            "protected_until": 0,
            "dead": False,
            "dead_until": 0,
            "profile_image_file_id": None,
            "last_infinity": 0,
        }
        users_table.insert(rec)
    else:
        # migration: ensure fields exist
        changed = False
        defaults = {
            "credits": 0, "membership_until": 0, "premium_until": 0, "infinity_until": 0,
            "last_pdaily": 0, "claim_available": False, "free_available": False,
            "gmute_uses_date": 0, "gmute_uses_today": 0, "gmute_until": 0,
            "protected_until": 0, "dead": False, "dead_until": 0, "profile_image_file_id": None,
        }
        for k, v in defaults.items():
            if k not in rec:
                rec[k] = v
                changed = True
        if changed:
            users_table.upsert(rec, UserQ.user_id == uid)
    return rec

def save_user(rec):
    if not rec or "user_id" not in rec:
        return
    users_table.upsert(rec, UserQ.user_id == rec["user_id"])

def now_ts():
    return int(time.time())

def is_member(rec):
    return rec.get("membership_until", 0) > now_ts()

def is_premium(rec):
    return rec.get("premium_until", 0) > now_ts()

def is_infinity(rec):
    return rec.get("infinity_until", 0) > now_ts()

def format_ts(ts):
    try:
        return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M UTC")
    except:
        return "N/A"

def reset_member_one_time_flags_on_buy(rec):
    rec["claim_available"] = True
    rec["free_available"] = True
    rec["gmute_uses_today"] = 0
    rec["gmute_uses_date"] = int(datetime.utcnow().strftime("%Y%m%d"))

# -------------------------
# Auto-revive checker
# call this early in commands that inspect dead state (revive/kill/etc.)
# -------------------------
def check_auto_revive(rec):
    """Auto-revive if dead_until expired OR if infinity gives grace revive within its rule."""
    if not rec:
        return rec
    now = now_ts()
    # normal expiry-based revive
    if rec.get("dead") and rec.get("dead_until") and now >= rec.get("dead_until"):
        rec["dead"] = False
        rec["dead_until"] = 0
        save_user(rec)
        return rec
    # if user has infinity and was dead less than INFINITY_GRACE_REVIVE_SECONDS ago, allow revive
    if rec.get("dead") and is_infinity(rec):
        # if they have dead_until timestamp (set by kill logic), and the duration until now is <= INFINITY_GRACE_REVIVE_SECONDS
        # we won't auto-apply here because kill may set dead_until to now + X; the kill logic should set dead_until appropriately.
        # Still, if dead_until exists and now >= dead_until (or other conditions) we can revive:
        if rec.get("dead_until") and now >= rec.get("dead_until"):
            rec["dead"] = False
            rec["dead_until"] = 0
            save_user(rec)
    return rec

# -------------------------
# Small helper to apply Infinity effects at kill-time
# CALL this from your kill logic after you set victim["dead"] = True and victim["dead_until"].
# It will:
#  - shorten dead_until by INFINITY_REVIVE_REDUCE_HOURS if victim has infinity
#  - if victim has infinity, ensure they will auto-revive within 1 hour (set dead_until accordingly)
#  - apply boost bookkeeping if needed
# -------------------------
def apply_infinity_effects_on_kill(killer_rec, victim_rec):
    """Call right after your kill sets victim dead state. This adjusts dead_until and optionally
       prevents reward if you requested (we do not change killer reward here)."""
    now = now_ts()
    if not victim_rec:
        return
    # If victim has infinity active, reduce revive time
    if is_infinity(victim_rec):
        # If victim.dead_until exists, reduce it by INFINITY_REVIVE_REDUCE_HOURS
        if victim_rec.get("dead_until", 0):
            reduced = victim_rec["dead_until"] - INFINITY_REVIVE_REDUCE_HOURS * 3600
            # But ensure they will revive no later than now + grace (1 hour)
            max_auto = now + INFINITY_GRACE_REVIVE_SECONDS
            victim_rec["dead_until"] = min(max_auto, max(reduced, now + 1))
        else:
            # if not set, set to now + 1 hour to allow quick auto revive
            victim_rec["dead_until"] = now + INFINITY_GRACE_REVIVE_SECONDS
        save_user(victim_rec)

# -----------------------------
# /credits - shows coins & credits & status
# -----------------------------
async def credits_cmd(update, context):
    msg = update.message
    if not msg:
        return
    rec = ensure_user_record(msg.from_user)
    await msg.reply_text(
        f"💳 Credits: {rec.get('credits',0)}\n"
        f"💰 Coins: {rec.get('coins',0)}\n"
        f"👑 Membership: {format_ts(rec.get('membership_until',0)) if is_member(rec) else 'No'}\n"
        f"💎 Premium: {format_ts(rec.get('premium_until',0)) if is_premium(rec) else 'No'}\n"
        f"♾️ Infinity: {format_ts(rec.get('infinity_until',0)) if is_infinity(rec) else 'No'}"
    )

# -----------------------------
# /buycredit <n>
# -----------------------------
async def buycredit_cmd(update, context):
    msg = update.message
    if not msg:
        return
    rec = ensure_user_record(msg.from_user)
    if not context.args:
        return await msg.reply_text(f"Usage: /buycredit <amount>\n1 credit = {CREDIT_COST_COINS} coins.")
    try:
        n = int(context.args[0])
        if n <= 0:
            raise ValueError()
    except:
        return await msg.reply_text("Invalid number.")
    cost = n * CREDIT_COST_COINS
    if rec.get("coins",0) < cost:
        return await msg.reply_text(f"💸 Not enough coins. Need {cost} coins to buy {n} credits.")
    rec["coins"] -= cost
    rec["credits"] = rec.get("credits",0) + n
    save_user(rec)
    await msg.reply_text(f"✅ Purchased {n} credits for {cost} coins. You now have {rec['credits']} credits.")

# -----------------------------
# /creditshop
# -----------------------------
async def creditshop_cmd(update, context):
    msg = update.message
    if not msg:
        return
    text = (
        "🛒 *Credit Shop*\n\n"
        f"• Membership (30 days) — {MEMBERSHIP_COST_CREDITS} credit\n"
        f"• Premium (30 days) — {PREMIUM_COST_CREDITS} credits\n"
        f"• Infinity (30 days effect) — {INFINITY_COST_CREDITS} credits\n\n"
        "Commands:\n"
        "/buy membership\n"
        "/buy premium\n"
        "/buy infinity\n"
        "/buycredit <n>\n"
    )
    await msg.reply_text(text, parse_mode="Markdown")

# -----------------------------
# /buy membership | premium | infinity
# -----------------------------
async def buy_cmd(update, context):
    msg = update.message
    if not msg:
        return
    rec = ensure_user_record(msg.from_user)
    if not context.args:
        return await msg.reply_text("Usage: /buy membership|premium|infinity")
    opt = context.args[0].lower()

    now = now_ts()
    if opt == "membership":
        if rec.get("credits",0) < MEMBERSHIP_COST_CREDITS:
            return await msg.reply_text("❌ Not enough credits for membership.")
        rec["credits"] -= MEMBERSHIP_COST_CREDITS
        start = max(now, rec.get("membership_until",0))
        rec["membership_until"] = start + MEMBERSHIP_DAYS * 86400
        reset_member_one_time_flags_on_buy(rec)
        save_user(rec)
        return await msg.reply_text(f"✅ Membership purchased until {format_ts(rec['membership_until'])}. Use /pdaily for members reward.")
    elif opt == "premium":
        if rec.get("credits",0) < PREMIUM_COST_CREDITS:
            return await msg.reply_text("❌ Not enough credits for premium.")
        rec["credits"] -= PREMIUM_COST_CREDITS
        start = max(now, rec.get("premium_until",0))
        rec["premium_until"] = start + MEMBERSHIP_DAYS * 86400
        save_user(rec)
        return await msg.reply_text(f"💎 Premium purchased until {format_ts(rec['premium_until'])}.")
    elif opt == "infinity":
        if rec.get("credits",0) < INFINITY_COST_CREDITS:
            return await msg.reply_text("❌ Not enough credits for infinity.")
        rec["credits"] -= INFINITY_COST_CREDITS
        start = max(now, rec.get("infinity_until",0))
        rec["infinity_until"] = start + MEMBERSHIP_DAYS * 86400
        # record purchase time
        rec["last_infinity"] = now
        save_user(rec)
        await msg.reply_text(
            "♾️ Infinity purchased! Your stats are increased by 30% and revive time reductions applied.\n"
            "After you die, you will be eligible for an automatic revive (special grace) for 1 hour.\n"
            f"Active until {format_ts(rec['infinity_until'])}."
        )
    else:
        return await msg.reply_text("Unknown item. Use /creditshop to see items.")

# -----------------------------
# /pdaily (member=5k, premium=10k)
# -----------------------------
async def pdaily_cmd(update, context):
    msg = update.message
    if not msg:
        return
    rec = ensure_user_record(msg.from_user)
    now = now_ts()
    if now - rec.get("last_pdaily",0) < 24*3600:
        remaining = 24*3600 - (now - rec.get("last_pdaily",0))
        hours = remaining//3600
        minutes = (remaining%3600)//60
        return await msg.reply_text(f"⏳ Already claimed. Try again in {hours}h {minutes}m.")
    # premium -> 10k, member -> 5k, else -> not allowed
    if is_premium(rec):
        amount = PDAYLY_REWARD_PREMIUM
    elif is_member(rec):
        amount = PDAYLY_REWARD_MEMBER
    else:
        return await msg.reply_text("❌ /pdaily is for Members or Premium only. Use /buy membership or /buy premium.")
    rec["coins"] = rec.get("coins",0) + amount
    rec["last_pdaily"] = now
    save_user(rec)
    await msg.reply_text(f"✅ You received {amount} coins.")

# -----------------------------
# /claim (members once, 0-9000)
# -----------------------------
async def claim_cmd(update, context):
    msg = update.message
    if not msg:
        return
    rec = ensure_user_record(msg.from_user)
    if not is_member(rec):
        return await msg.reply_text("❌ /claim is for Members only.")
    if not rec.get("claim_available", False):
        return await msg.reply_text("❌ You already used /claim for this membership period.")
    amt = random.randint(0,9000)
    rec["coins"] = rec.get("coins",0) + amt
    rec["claim_available"] = False
    save_user(rec)
    await msg.reply_text(f"🎁 You claimed {amt} coins!")

# -----------------------------
# /bet <amt> (members only)  -- unchanged behaviour (50/50 *2)
# -----------------------------
async def bet_cmd(update, context):
    msg = update.message
    if not msg: return
    rec = ensure_user_record(msg.from_user)
    if not is_member(rec):
        return await msg.reply_text("❌ /bet is for Members only.")
    if not context.args:
        return await msg.reply_text("Usage: /bet <amount>")
    try:
        amt = int(context.args[0])
    except:
        return await msg.reply_text("Invalid amount.")
    if amt<=0 or rec.get("coins",0) < amt:
        return await msg.reply_text("Insufficient coins.")
    rec["coins"] -= amt
    win = random.choice([True, False])
    if win:
        gain = amt * 2
        rec["coins"] += gain
        save_user(rec)
        await msg.reply_text(f"🎉 You won! You got {gain} coins.")
    else:
        save_user(rec)
        await msg.reply_text(f"💔 You lost {amt} coins. Better luck next time.")

# -----------------------------
# /editname <text> (members only)
# -----------------------------
async def editname_cmd(update, context):
    msg = update.message
    if not msg: return
    rec = ensure_user_record(msg.from_user)
    if not is_member(rec) and not is_premium(rec):
        return await msg.reply_text("❌ /editname is for Members/Premium only.")
    if not context.args:
        return await msg.reply_text("Usage: /editname <new display name>")
    newname = " ".join(context.args).strip()
    rec["display_name"] = newname[:64]
    save_user(rec)
    await msg.reply_text(f"✅ Display name updated to: {rec['display_name']}")

# -----------------------------
# /protect extended (1-4d; non-member up to 2d)
# -----------------------------
async def protect_cmd_extended(update, context):
    msg = update.message
    if not msg:
        return
    rec = ensure_user_record(msg.from_user)
    if not context.args:
        return await msg.reply_text("Usage: /protect 1d|2d|3d|4d")
    key = context.args[0].lower()
    mapping = {"1d":1,"2d":2,"3d":3,"4d":4}
    if key not in mapping:
        return await msg.reply_text("Invalid option.")
    days = mapping[key]
    if not is_member(rec) and days > 2:
        return await msg.reply_text("Non-members can buy max 2d protection. Become a member for longer protection.")
    cost_per_day = 200
    total_cost = cost_per_day * days
    if rec.get("coins",0) < total_cost:
        return await msg.reply_text(f"💸 Not enough coins. Cost: {total_cost}.")
    rec["coins"] -= total_cost
    rec["protected_until"] = now_ts() + days * 86400
    save_user(rec)
    await msg.reply_text(f"✅ Protection purchased for {days} day(s). -{total_cost} coins")

# -----------------------------
# /prob <reply> (premium only steals 30%)
# -----------------------------
async def prob_cmd(update, context):
    msg = update.message
    if not msg or not msg.reply_to_message:
        return await msg.reply_text("Reply to a user to use /prob.")
    caller = ensure_user_record(msg.from_user)
    target_user = msg.reply_to_message.from_user
    target = ensure_user_record(target_user)
    if not is_premium(caller):
        return await msg.reply_text("❌ /prob is for Premium users only.")
    if target.get("protected_until",0) > now_ts():
        return await msg.reply_text("Target is protected. Action failed.")
    take = int(target.get("coins",0) * PROB_TAKE_RATIO)
    if take <= 0:
        return await msg.reply_text("Target has no coins to take.")
    target["coins"] = max(0, target.get("coins",0) - take)
    caller["coins"] = caller.get("coins",0) + take
    save_user(target); save_user(caller)
    await msg.reply_text(f"🔱 You took {take} coins from {pretty_name_from_user(target_user)}!")

# -----------------------------
# /peditbal (private photo session)
# -----------------------------
async def peditbal_cmd(update, context):
    msg = update.message
    if not msg: return
    if msg.chat.type != "private":
        return await msg.reply_text("Please use /peditbal in a private chat with the bot.")
    rec = ensure_user_record(msg.from_user)
    if not is_member(rec) and not is_premium(rec):
        return await msg.reply_text("Only members/premium can use /peditbal.")
    # set session for user
    sessions_table.upsert({"user_id": rec["user_id"], "action": "peditbal"}, Query().user_id == rec["user_id"])
    await msg.reply_text("👑 Send me the image you want to save on your balance status. (Send a photo now)")

async def handle_private_photo_sessions(update, context):
    """A message handler for private photos — store file_id into profile_image_file_id."""
    msg = update.message
    if not msg or msg.chat.type != "private" or not msg.photo:
        return
    uid = msg.from_user.id
    sess = sessions_table.get(Query().user_id == uid)
    if not sess:
        return
    action = sess.get("action")
    if action == "peditbal":
        file_id = msg.photo[-1].file_id
        rec = ensure_user_record(msg.from_user)
        rec["profile_image_file_id"] = file_id
        save_user(rec)
        sessions_table.remove(Query().user_id == uid)
        return await msg.reply_text("✅ Done! Profile image saved. Use /bal to view.")

# -----------------------------
# /gmute <reply> (members: 2 uses/day)
# -----------------------------
async def gmute_cmd(update, context):
    msg = update.message
    if not msg or not msg.reply_to_message:
        return await msg.reply_text("Reply to a user to use /gmute.")
    rec = ensure_user_record(msg.from_user)
    if not is_member(rec):
        return await msg.reply_text("❌ /gmute is for Members only.")
    today = int(datetime.utcnow().strftime("%Y%m%d"))
    if rec.get("gmute_uses_date",0) != today:
        rec["gmute_uses_date"] = today
        rec["gmute_uses_today"] = 0
    if rec.get("gmute_uses_today",0) >= GMUTE_DAILY_LIMIT:
        return await msg.reply_text("You used your /gmute limit for today.")
    target = ensure_user_record(msg.reply_to_message.from_user)
    target["gmute_until"] = now_ts() + GMUTE_SECONDS
    save_user(target)
    rec["gmute_uses_today"] = rec.get("gmute_uses_today",0) + 1
    save_user(rec)
    await msg.reply_text(f"✅ {pretty_name_from_user(msg.reply_to_message.from_user)} will be blocked from economy commands for 5 minutes.")

# -----------------------------
# /check <reply> (premium costs CHECK_COST_COINS)
# -----------------------------
async def check_cmd(update, context):
    msg = update.message
    if not msg or not msg.reply_to_message:
        return await msg.reply_text("Reply to a user to use /check.")
    rec = ensure_user_record(msg.from_user)
    if not is_premium(rec):
        return await msg.reply_text("❌ /check is for Premium users only.")
    if rec.get("coins",0) < CHECK_COST_COINS:
        return await msg.reply_text(f"💸 You need {CHECK_COST_COINS} coins to use /check.")
    rec["coins"] -= CHECK_COST_COINS
    save_user(rec)
    target = ensure_user_record(msg.reply_to_message.from_user)
    p_until = target.get("protected_until",0)
    await msg.reply_text(f"🔎 {pretty_name_from_user(msg.reply_to_message.from_user)} protected until: {format_ts(p_until) if p_until>0 else 'No'}")

# -----------------------------
# /free <reply> (member one-time)
# -----------------------------
async def free_cmd(update, context):
    msg = update.message
    if not msg or not msg.reply_to_message:
        return await msg.reply_text("Reply to a user to use /free.")
    rec = ensure_user_record(msg.from_user)
    if not is_member(rec):
        return await msg.reply_text("❌ /free is for Members only.")
    if not rec.get("free_available", False):
        return await msg.reply_text("❌ You already used your free perk.")
    target = ensure_user_record(msg.reply_to_message.from_user)
    amt = int(target.get("coins",0) * FREE_PERCENT)
    if amt <= 0:
        return await msg.reply_text("Target has no coins.")
    target["coins"] = max(0, target.get("coins",0) - amt)
    rec["coins"] = rec.get("coins",0) + amt
    rec["free_available"] = False
    save_user(target); save_user(rec)
    await msg.reply_text(f"🎁 You received {amt} coins from {pretty_name_from_user(msg.reply_to_message.from_user)}!")

# -----------------------------
# Gift commands for gifting membership/premium to others (use credits)
# /giftmembership <@user>  - spend 1 credit to gift membership (30d)
# /giftpremium <@user>     - spend 5 credits to gift premium (30d)
# -----------------------------
async def giftmembership_cmd(update, context):
    msg = update.message
    if not msg: return
    if not context.args and not msg.reply_to_message:
        return await msg.reply_text("Usage: /giftmembership @user or reply to user.")
    giver = ensure_user_record(msg.from_user)
    if giver.get("credits",0) < MEMBERSHIP_COST_CREDITS:
        return await msg.reply_text("❌ Not enough credits.")
    # target
    if msg.reply_to_message:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = None
        arg = context.args[0]
        if arg.startswith("@"):
            # try to get by username from DB (simple)
            target_rec = users_table.get(UserQ.username == arg[1:])
            if target_rec:
                target_user = type("X",(object,),{"id": target_rec["user_id"], "username": target_rec.get("username")})
    if not target_user:
        return await msg.reply_text("❌ Could not find target. Reply or use @username of a user present in DB.")
    rec_t = ensure_user_record(target_user)
    giver["credits"] -= MEMBERSHIP_COST_CREDITS
    start = max(now_ts(), rec_t.get("membership_until",0))
    rec_t["membership_until"] = start + MEMBERSHIP_DAYS*86400
    reset_member_one_time_flags_on_buy(rec_t)
    save_user(giver); save_user(rec_t)
    await msg.reply_text(f"✅ Gifted membership to {pretty_name_from_user(target_user)} until {format_ts(rec_t['membership_until'])}.")

async def giftpremium_cmd(update, context):
    msg = update.message
    if not msg: return
    if not context.args and not msg.reply_to_message:
        return await msg.reply_text("Usage: /giftpremium @user or reply to user.")
    giver = ensure_user_record(msg.from_user)
    if giver.get("credits",0) < PREMIUM_COST_CREDITS:
        return await msg.reply_text("❌ Not enough credits.")
    # target
    if msg.reply_to_message:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = None
        arg = context.args[0]
        if arg.startswith("@"):
            target_rec = users_table.get(UserQ.username == arg[1:])
            if target_rec:
                target_user = type("X",(object,),{"id": target_rec["user_id"], "username": target_rec.get("username")})
    if not target_user:
        return await msg.reply_text("❌ Could not find target. Reply or use @username of a user present in DB.")
    rec_t = ensure_user_record(target_user)
    giver["credits"] -= PREMIUM_COST_CREDITS
    start = max(now_ts(), rec_t.get("premium_until",0))
    rec_t["premium_until"] = start + MEMBERSHIP_DAYS*86400
    save_user(giver); save_user(rec_t)
    await msg.reply_text(f"✅ Gifted premium to {pretty_name_from_user(target_user)} until {format_ts(rec_t['premium_until'])}.")

# -----------------------------
# Fun commands (open to everyone) — reply_animation with gif URL
# -----------------------------
PUNCH_GIFS = ["https://media.tenor.com/jQpYtU3n6nEAAAAC/anime-punch.gif"]
SLAP_GIFS  = ["https://media.tenor.com/ZQjJz1Kkb04AAAAC/anime-slap.gif"]
HUG_GIFS   = ["https://media.tenor.com/IKXDsOYe6YsAAAAC/anime-hug.gif"]
KISS_GIFS  = ["https://media.tenor.com/k7u_8srrcFUAAAAC/anime-kiss.gif"]
BONK_GIFS  = ["https://media.tenor.com/2pQ6r5eI1t8AAAAC/bonk.gif"]
THROW_GIFS = ["https://media.tenor.com/5q7_a0w1n3MAAAAC/throw.gif"]
RUB_GIFS   = ["https://media.tenor.com/4l-2_xkG0NwAAAAC/rub.gif"]

async def _fun_send_random_gif(msg, urls):
    try:
        await msg.reply_animation(random.choice(urls))
    except Exception:
        # fallback to text
        await msg.reply_text("(gif)")

async def punch_cmd(update, context): await _fun_send_random_gif(update.message, PUNCH_GIFS)
async def slap_cmd(update, context):  await _fun_send_random_gif(update.message, SLAP_GIFS)
async def hug_cmd(update, context):   await _fun_send_random_gif(update.message, HUG_GIFS)
async def kiss_cmd(update, context):  await _fun_send_random_gif(update.message, KISS_GIFS)
async def bonk_cmd(update, context):  await _fun_send_random_gif(update.message, BONK_GIFS)
async def throw_cmd(update, context): await _fun_send_random_gif(update.message, THROW_GIFS)
async def rub_cmd(update, context):   await _fun_send_random_gif(update.message, RUB_GIFS)

# -----------------------------
# Migration helper - safe to run once to add missing fields for all users
# -----------------------------
def membership_migration():
    for rec in users_table.all():
        changed = False
        defaults = {
            "credits": 0, "membership_until": 0, "premium_until": 0, "infinity_until": 0,
            "last_pdaily": 0, "claim_available": False, "free_available": False,
            "gmute_uses_date": 0, "gmute_uses_today": 0, "gmute_until": 0,
            "protected_until": 0, "dead": False, "dead_until": 0, "profile_image_file_id": None
        }
        for k,v in defaults.items():
            if k not in rec:
                rec[k] = v
                changed = True
        if changed:
            users_table.upsert(rec, UserQ.user_id == rec["user_id"])

# Optional: Uncomment the following line to run migration at bot start (run once)
# membership_migration()


# ---------- Fun commands ----------
async def punch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_animation(random.choice(PUNCH_GIFS))

async def slap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_animation(random.choice(SLAP_GIFS))

async def hug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_animation(random.choice(HUG_GIFS))

async def kiss_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_animation(random.choice(KISS_GIFS))

# ---------- Callbacks general ----------
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # route different callback_data prefixes
    data = update.callback_query.data
    if data.startswith("pickadd:"):
        return await pickadd_callback(update, context)
    if data.startswith("delpack:"):
        return await delpack_callback(update, context)
    if data.startswith("menu:"):
        return await menu_callback(update, context)
    await update.callback_query.answer()

# ---------- Misc ----------
async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("PONG — Yuuki is awake ⚡️")

async def unknown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Use /help.")

# ---------- Message router: ensure group state, handle awaited sessions ----------
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # run when messages arrive; text handler checks for awaiting_newpack_name
    if update.message and update.message.text:
        await text_message_handler(update, context)

# ---------- Startup ----------
def main():
    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        print("Please set BOT_TOKEN in the script before running.")
        return

from tinydb import TinyDB, Query

DB_PLAYERS = TinyDB("users.json")

@owner_only
async def give_all(update, context):
    try:
        table = DB_PLAYERS.table("players")
        players = table.all()

        if not players:
            return await update.message.reply_text("No players found in database.")

        for player in players:
            uid = player.get("user_id")
            coins = player.get("coins", 0)
            table.update({"coins": coins + 10000}, Query().user_id == uid)

        await update.message.reply_text(
            "💸 Successfully added **10,000 coins** to ALL players!"
        )

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
 ============================================================
#                  GROUP MANAGEMENT SYSTEM
# ============================================================

from tinydb import TinyDB, Query
from telegram import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from functools import wraps

db = TinyDB("group_settings.json")
LOCKS = db.table("locks")

OWNER_IDS = [5773908061]  # Add more owner IDs if needed
PREFIX = r"^[\./!?]"

# ---------------- Helper: User Mention ----------------
def mention(user):
    return f"@{user.username}" if user.username else user.first_name

# ---------------- Decorator: Admin Only ----------------
def admin_only(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat

        # Owner bypass
        if user.id in OWNER_IDS:
            return await func(update, context, *args, **kwargs)

        # Only allow in groups
        if chat.type == "private":
            return await update.message.reply_text("❌ This command works only in groups.")

        member = await chat.get_member(user.id)
        if member.status not in ["administrator", "creator"]:
            return await update.message.reply_text("⛔ Only group admins can use this command.")

        return await func(update, context, *args, **kwargs)
    
    return wrapped

# ---------------- Helper: Lock DB ----------------
def set_lock(chat_id, key, value):
    LOCKS.upsert({"chat_id": chat_id, key: value}, Query().chat_id == chat_id)

def get_lock(chat_id, key):
    data = LOCKS.get(Query().chat_id == chat_id)
    return data.get(key, False) if data else False

# ====================================================
# 🔨 BAN (with Unban button)
# ====================================================
@admin_only
async def ban_cmd(update, context):
    msg = update.message
    chat = msg.chat
    bot = context.bot

    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if not target:
        return await msg.reply_text("Reply to a user to ban 🚫")

    me = await bot.get_chat_member(chat.id, bot.id)
    if not me.can_restrict_members:
        return await msg.reply_text("❌ I need Ban permission!")

    await bot.ban_chat_member(chat.id, target.id)

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unban ✅", callback_data=f"unban:{target.id}")]])
    await msg.reply_text(f"{mention(target)} banned! 🚫", reply_markup=kb, parse_mode="Markdown")

@admin_only
async def unban_cmd(update, context):
    msg = update.message
    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if not target:
        return await msg.reply_text("Reply to a banned user to unban.")
    await context.bot.unban_chat_member(msg.chat.id, target.id)
    await msg.reply_text(f"{mention(target)} unbanned! ✅")

async def unban_button(update, context):
    q = update.callback_query
    uid = int(q.data.split(":")[1])
    await context.bot.unban_chat_member(q.message.chat.id, uid)
    await q.edit_message_text("User unbanned! ✅")

# ====================================================
# 🔇 MUTE + UNMUTE
# ====================================================
@admin_only
async def mute_cmd(update, context):
    msg = update.message
    chat = msg.chat
    bot = context.bot

    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if not target:
        return await msg.reply_text("Reply to mute 🔕")

    me = await bot.get_chat_member(chat.id, bot.id)
    if not me.can_restrict_members:
        return await msg.reply_text("❌ I need Mute permission!")

    perms = ChatPermissions(can_send_messages=False)
    await bot.restrict_chat_member(chat.id, target.id, perms)

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unmute 🔔", callback_data=f"unmute:{target.id}")]])
    await msg.reply_text(f"{mention(target)} muted! 🔕", reply_markup=kb, parse_mode="Markdown")

@admin_only
async def unmute_cmd(update, context):
    msg = update.message
    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if not target:
        return await msg.reply_text("Reply to unmute 🔊")

    perms = ChatPermissions(can_send_messages=True)
    await context.bot.restrict_chat_member(msg.chat.id, target.id, perms)
    await msg.reply_text(f"{mention(target)} unmuted! 🔔", parse_mode="Markdown")

async def unmute_button(update, context):
    q = update.callback_query
    uid = int(q.data.split(":")[1])
    perms = ChatPermissions(can_send_messages=True)
    await context.bot.restrict_chat_member(q.message.chat.id, uid, perms)
    await q.edit_message_text("User unmuted! 🔔")

# ====================================================
# 👢 KICK
# ====================================================
@admin_only
async def kick_cmd(update, context):
    msg = update.message
    chat = msg.chat
    bot = context.bot

    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if not target:
        return await msg.reply_text("Reply to kick 👢")

    me = await bot.get_chat_member(chat.id, bot.id)
    if not me.can_restrict_members:
        return await msg.reply_text("❌ I need Kick permission!")

    await bot.ban_chat_member(chat.id, target.id)
    await bot.unban_chat_member(chat.id, target.id)

    await msg.reply_text(f"{mention(target)} kicked! 👢")

# ====================================================
# 📌 PROMOTE LEVEL 1 / 2 / 3
# ====================================================

from telegram import ChatAdministratorRights

@admin_only
async def promote_cmd(update, context):
    msg = update.message
    chat = msg.chat
    bot = context.bot

    args = msg.text.split()
    lvl = 1
    if len(args) > 1:
        try:
            lvl = int(args[1])
        except:
            lvl = 1

    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if not target:
        return await msg.reply_text("Reply to promote")

    me = await bot.get_chat_member(chat.id, bot.id)
    if not me.can_promote_members:
        return await msg.reply_text("❌ I need Promote permission!")

    if lvl == 1:
        rights = ChatAdministratorRights(can_invite_users=True)
        text = "Promoted! Basic permission ⚪ (can't mute/ban/add admin)"
    elif lvl == 2:
        rights = ChatAdministratorRights(
            can_invite_users=True,
            can_restrict_members=True,
            can_delete_messages=True
        )
        text = "Promoted! Can Mute | Ban 🟡"
    else:
        rights = ChatAdministratorRights(
            can_manage_chat=True,
            can_pin_messages=True,
            can_promote_members=True,
            can_restrict_members=True,
            can_delete_messages=True,
            can_invite_users=True
        )
        text = "Promoted! FULL PERMISSIONS 🌟"

    await bot.promote_chat_member(chat.id, target.id, rights)
    await msg.reply_text(f"{mention(target)} {text}", parse_mode="Markdown")

# ====================================================
# 🔽 DEMOTE
# ====================================================
@admin_only
async def demote_cmd(update, context):
    msg = update.message
    chat = msg.chat
    bot = context.bot

    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if not target:
        return await msg.reply_text("Reply to demote")

    # Remove all admin rights
    rights = ChatAdministratorRights()
    await bot.promote_chat_member(chat.id, target.id, rights)
    await msg.reply_text(f"{mention(target)} demoted! ⬇️")

# ====================================================
# 👥 ADMINLIST
# ====================================================
async def adminlist_cmd(update, context):
    chat = update.effective_chat
    admins = await context.bot.get_chat_administrators(chat.id)

    text = "👮 **Admins in this chat:**\n\n"
    for a in admins:
        u = a.user
        text += f"- {mention(u)}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

# ====================================================
# ℹ️ INFO
# ====================================================
async def info_cmd(update, context):
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.message.from_user

    text = f"""
**User Info**
🆔 ID: `{user.id}`
👤 Name: {user.first_name}
🔗 Username: @{user.username if user.username else 'none'}
"""
    await update.message.reply_text(text, parse_mode="Markdown")

# ====================================================
# 🔒 LOCK / UNLOCK SYSTEM (TinyDB)
# ====================================================
@admin_only
async def lock_cmd(update, context):
    msg = update.message
    chat = msg.chat

    if len(msg.text.split()) < 2:
        return await msg.reply_text("Usage: /lock <chat|media|gifs|stickers|photos|all>")

    mode = msg.text.split()[1]
    set_lock(chat.id, mode, True)
    await msg.reply_text(f"{mode} locked 🔒")

@admin_only
async def unlock_cmd(update, context):
    msg = update.message
    chat = msg.chat

    if len(msg.text.split()) < 2:
        return await msg.reply_text("Usage: /unlock <chat|media|gifs|stickers|photos|all>")

    mode = msg.text.split()[1]
    set_lock(chat.id, mode, False)
    await msg.reply_text(f"{mode} unlocked 🔓")

async def help_group(update, context):
    text = (
        "📘 **Group Help Menu**\n\n"
        "Here are all available group commands:\n\n"
        "🔹 `/promote <1|2|3>` — Promote a user\n"
        "🔹 `/demote` — Demote a user\n"
        "🔹 `/adminlist` — Show all admins\n"
        "🔹 `/info` — Show user info\n"
        "🔹 `/lock <mode>` — Lock chat features\n"
        "🔹 `/unlock <mode>` — Unlock chat features\n\n"
        "✨ More features coming soon!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

#===================================================================
#start_message
#===================================================================

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    mention = user.mention_html()

    # ★ YUUKI LOGO (Text Banner)
    logo = (
        "┏━•❃°•°❀°•°❃•━┓\n"
        "   ✨ 𝓨𝑼𝑼𝑲𝑰⚙𝑩𝑶𝑻 ✨\n"
        "┗━•❃°•°❀°•°❃•━┛"
    )

    # ★ Start Text
    text = (
        f"{logo}\n\n"
        f"𝘏𝘦𝘺 {mention} ❤️🥳\n"
        f"𝑾𝒆𝒍𝒄𝒐𝒎𝒆 𝒕𝒐 𝒕𝒉𝒆 𝒀𝒖𝒖𝒌𝒊💀𝑩𝒐𝒕!\n\n"

        "💠 𝘗𝘰𝘸𝘦𝘳𝘧𝘶𝘭 | 𝘍𝘢𝘴𝘵 | 𝘈𝘯𝘪𝘮𝘦 𝘛𝘩𝘦𝘮𝘦𝘥\n"
        "💠 𝘌𝘤𝘰𝘯𝘰𝘮𝘺 • 𝘍𝘶𝘯 • 𝘜𝘵𝘪𝘭𝘪𝘵𝘺 • 𝘗𝘳𝘰𝘵𝘦𝘤𝘵𝘪𝘰𝘯\n\n"

        "✨ 𝙐𝙨𝙚 𝙩𝙝𝙚 𝙗𝙪𝙩𝙩𝙤𝙣𝙨 𝙗𝙚𝙡𝙤𝙬 𝙩𝙤 𝙣𝙖𝙫𝙞𝙜𝙖𝙩𝙚:"
    )

    keyboard = [
        [
            InlineKeyboardButton("💬 𝙎𝙪𝙥𝙥𝙤𝙧𝙩 𝘾𝙝𝙖𝙩", url="https://t.me/team_bright_lightX"),
            InlineKeyboardButton("📢 𝙐𝙥𝙙𝙖𝙩𝙚𝙨", url="https://t.me/YUUKIUPDATES"),
        ],
        [
            InlineKeyboardButton("➕ 𝘼𝙙𝙙 𝙈𝙚 𝙏𝙤 𝙂𝙧𝙤𝙪𝙥", url=f"https://t.me/{context.bot.username}?startgroup=true"),
        ],
        [
            InlineKeyboardButton("🤖 𝙎𝙚𝙘𝙤𝙣𝙙 𝘽𝙤𝙩", url="https://t.me/im_yuukianimefile_bot"),
        ]
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

def is_approved(user_id: int) -> bool:
    return ApproveTable.contains(Query().user_id == user_id)

def add_approval(user_id: int):
    if not is_approved(user_id):
        ApproveTable.insert({"user_id": user_id})

def remove_approval(user_id: int):
    ApproveTable.remove(Query().user_id == user_id)

def list_approved_users():
    return ApproveTable.all()

from functools import wraps

def owner_only(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != 5773908061:
            return await update.message.reply_text("❌ You are not the owner of this bot.")
        return await func(update, context, *args, **kwargs)
    return wrapper

# ========= CREATE BOT =========
app = ApplicationBuilder().token(BOT_TOKEN).build()
# ----------------------------------

# ========= REGISTER HANDLERS =========

async def skip_old_updates(app):
    print("Skipping old updates...")
    try:
        updates = await app.bot.get_updates(offset=-1)
        print(f"Skipped {len(updates)} old updates.")
    except Exception as e:
        print("Error skipping updates:", e)

# ----- Management -----
management_handlers = [
    MessageHandler(filters.Regex(r"^\.promote(\s[1-3])?$"), promote_cmd),
    MessageHandler(filters.Regex(r"^\.demote$"), demote_cmd),
    MessageHandler(filters.Regex(r"^\.mute$"), mute_cmd),
    MessageHandler(filters.Regex(r"^\.unmute$"), unmute_cmd),
    MessageHandler(filters.Regex(r"^\.ban$"), ban_cmd),
    MessageHandler(filters.Regex(r"^\.unban$"), unban_cmd),
    MessageHandler(filters.Regex(r"^\.kick$"), kick_cmd),
    MessageHandler(filters.Regex(r"^\.lockchat$"), lock_cmd),
    MessageHandler(filters.Regex(r"^\.unlockchat$"), unlock_cmd),
    MessageHandler(filters.Regex(r"^\.info$"), info_cmd),
    MessageHandler(filters.Regex(r"^\.adminlist$"), adminlist_cmd),
    CommandHandler("grouphelp", help_group),
]

# ----- START + HELP -----
start_help_handlers = [
    CommandHandler("start", start_cmd),
    CommandHandler("help", help_cmd),
    CallbackQueryHandler(menu_callback, pattern=r"^menu:"),
]

# ----- Economy -----
economy_handlers = [
    CommandHandler("open", open_cmd),
    CommandHandler("close", close_cmd),
    CommandHandler("daily", daily_cmd),
    CommandHandler("bal", bal_cmd),
    CommandHandler("toprich", toprich_cmd),
    CommandHandler("topkill", topkills_cmd),
    CommandHandler("give", give_cmd),
    CommandHandler("rob", rob_cmd),
    CommandHandler("kill", kill_cmd),
    CommandHandler("revive", revive_cmd),
    CommandHandler("protect", protect_cmd),
    CommandHandler("transfer", transfer_cmd),
    CommandHandler("resetplayer", resetplayer_cmd),
    CommandHandler("resetall", resetall_cmd),
    CommandHandler("lottery", lottery_cmd),
    CommandHandler("all", all_cmd),
]

# ----- Shop -----
shop_handlers = [
    CommandHandler("register", register_cmd),
    CommandHandler("shop", shop_cmd),
    CommandHandler("inventory", inventory_cmd),
    CommandHandler("gift", gift_cmd),
    CommandHandler("buy", buy_cmd),
]

# ----- Fun -----
fun_handlers = [
    CommandHandler("punch", punch_cmd),
    CommandHandler("slap", slap_cmd),
    CommandHandler("hug", hug_cmd),
    CommandHandler("kiss", kiss_cmd),
    CommandHandler("ping", ping_cmd),
]

# ----- Banking -----
bank_handlers = [

    # Commands
    CommandHandler("createbank", createbank_cmd),
    CommandHandler("banklist", banklist_cmd),
    CommandHandler("addbank", addbank_cmd),
    CommandHandler("deposit", deposit_cmd),
    CommandHandler("withdraw", withdraw_cmd),
    CommandHandler("bank", bank_cmd),
    CommandHandler("bankstatus", bankstatus_cmd),
    CommandHandler("budget", budget_cmd),
    CommandHandler("getloan", getloan_cmd),
    CommandHandler("leavebank", leavebank_cmd),
    CommandHandler("deletebank", deletebank_cmd),

    # Callbacks
    CallbackQueryHandler(callback_bank_join, pattern=r"^bank_join"),
    CallbackQueryHandler(callback_bank_join_no, pattern=r"^bank_join_no"),

    CallbackQueryHandler(callback_leavebank_yes, pattern=r"^leavebank_yes"),
    CallbackQueryHandler(callback_leavebank_no, pattern=r"^leavebank_no"),

    CallbackQueryHandler(callback_deletebank_yes, pattern=r"^deletebank_yes"),
    CallbackQueryHandler(callback_deletebank_no, pattern=r"^deletebank_no"),

    CallbackQueryHandler(callback_budget_set, pattern=r"^budget_set"),
]

# ----- Admin -----
admin_handlers = [
    CommandHandler("approve", approve_cmd),
    CommandHandler("unapprove", unapprove_cmd),
    CommandHandler("approvelist", approvelist_cmd),
    CommandHandler("wish", wish_cmd),
    CommandHandler("feedback", feedback_cmd),
]

# ----- Other -----
other_handlers = [
    MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members),
    MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_photos_for_banks),

    # Yuuki chat handlers
    MessageHandler(filters.TEXT & ~filters.COMMAND, yuuki_chat),
    MessageHandler(filters.Sticker.ALL, yuuki_chat),  # ✅ fixed

    # Keep your message_router if you want fallback handling
    MessageHandler(filters.TEXT & ~filters.COMMAND, message_router),
]

# ----- Membership / Premium / Infinity Handlers -----
membership_premium_handlers = [
    CommandHandler("credits", credits_cmd),
    CommandHandler("buycredit", buycredit_cmd),
    CommandHandler("creditshop", creditshop_cmd),
    CommandHandler("buy", buy_cmd),

    CommandHandler("pdaily", pdaily_cmd),
    CommandHandler("claim", claim_cmd),
    CommandHandler("bet", bet_cmd),
    CommandHandler("editname", editname_cmd),
    CommandHandler("protect", protect_cmd_extended),
    CommandHandler("free", free_cmd),
    CommandHandler("gmute", gmute_cmd),

    CommandHandler("prob", prob_cmd),
    CommandHandler("peditbal", peditbal_cmd),
    CommandHandler("check", check_cmd),

    CommandHandler("infinity", buy_cmd),
    CommandHandler("giftmembership", giftmembership_cmd),
    CommandHandler("giftpremium", giftpremium_cmd),

    # Fun commands usable by everyone
    CommandHandler("punch", punch_cmd),
    CommandHandler("slap", slap_cmd),
    CommandHandler("hug", hug_cmd),
    CommandHandler("kiss", kiss_cmd),
    CommandHandler("bonk", bonk_cmd),
    CommandHandler("throw", throw_cmd),
    CommandHandler("rub", rub_cmd),

    # Photo handler for premium image upload
    MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_private_photo_sessions),
]

# ========= MERGE ALL HANDLERS =========
all_handlers = (
    management_handlers +
    start_help_handlers +
    economy_handlers +
    shop_handlers +
    fun_handlers +
    bank_handlers +
    admin_handlers +
    other_handlers +
    membership_premium_handlers
)

# ========= ADD HANDLERS =========
for handler in all_handlers:
    app.add_handler(handler)

print("Yuuki_ is running now!!")
app.run_polling(drop_pending_updates=True)
