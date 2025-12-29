from telegram import (                                                                                                    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,                                                                                                   CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= CONFIG =================
TOKEN = "8160955111:AAH4rSihP8JQdt-AcXYGapebuuT2F-BglxA"   # <-- BotFather token
BOTNAME = "˹ 𝐄𝐥𝐢𝐭𝐞 ✘ 𝐇ᴏꜱᴛᴇʀ ˼"                                                                                        DEVELOPER_USERNAME = "RJVTAX"
CHANNEL = "@YUUKIUPDATES"

# ================= TEXTS =================                                                                           START_TEXT = f"""
┌────── ˹ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ˼ ⏤͟͟͞͞‌‌‌‌★
┆◍ ʜᴇʏ, ɪ ᴀᴍ : ˹ 𝐄𝐥𝐢𝐭𝐞 ✘ 𝐇ᴏꜱᴛᴇʀ ˼                                                                                     ┆● ɴɪᴄᴇ ᴛᴏ ᴍᴇᴇᴛ ʏᴏᴜ !
└─────────────────────•
❖ ɪ ᴀᴍ ᴀ ᴘᴏᴡᴇʀғᴜʟ ɪᴅ-ᴜsᴇʀ-ʙᴏᴛ
❖ ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ᴍᴇ ғᴏʀ ғᴜɴ.                                                                                             ❖ ɪ ᴄᴀɴ ʙᴏᴏsᴛ ʏᴏᴜʀ ɪᴅ
•─────────────────────•
❖ ʙʏ : <a href="https://t.me/{DEVELOPER_USERNAME}">『𓋹』 🇷 🇯 『〔☤〕』</a>
"""

ABOUT_TEXT = f"""
ᴀʙᴏᴜᴛ ᴛʜɪꜱ ʙᴏᴛ 🌙

ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴛᴏ ʙᴏᴏsᴛ ʏᴏᴜʀ ɪᴅ
ᴡɪᴛʜ ʙᴇᴀᴜᴛɪғᴜʟ ᴀɴɪᴍᴀᴛɪᴏɴ.

◌ ʟᴀɴɢᴜᴀɢᴇ : ᴘʏᴛʜᴏɴ
◌ ᴘᴏᴡᴇʀᴇᴅ ʙʏ : {CHANNEL}
◌ ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href="https://t.me/{DEVELOPER_USERNAME}">『𓋹』 🇷 🇯 『〔☤〕』</a>
"""

HELP_TEXT = """
ʜᴇʟᴘ ᴍᴇɴᴜ ⚙️                                                                                                           
➤ /start
ꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ
                                                                                                                      ➤ /help
ᴏᴘᴇɴ ʜᴇʟᴘ ᴍᴇɴᴜ
                                                                                                                      ➤ /about
ᴀʙᴏᴜᴛ ᴛʜᴇ ʙᴏᴛ
"""
                                                                                                                      # ================= KEYBOARD =================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌨️ Basic Guide 🌨️", callback_data="help")],
        [
            InlineKeyboardButton("❓ How to use", callback_data="help"),
            InlineKeyboardButton("about 🎶", callback_data="about")
        ],
        [
            InlineKeyboardButton("⚡ Updates", url="https://t.me/YUUKIUPDATES"),
            InlineKeyboardButton("support 🌨️", url="https://t.me/team_bright_lightX")
        ],
        [
            InlineKeyboardButton("🌿 Developer 🌿", url=f"https://t.me/{DEVELOPER_USERNAME}")
        ]
    ])

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        START_TEXT,
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        HELP_TEXT,
        parse_mode="HTML"
    )

async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        ABOUT_TEXT,
        parse_mode="HTML"
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        await query.message.edit_text(
            HELP_TEXT,
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )
    elif query.data == "about":
        await query.message.edit_text(
            ABOUT_TEXT,
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("about", about_cmd))
app.add_handler(CallbackQueryHandler(buttons))

print("🤖 Bot is running...")
app.run_polling()