import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler
import urllib.request
import asyncio

# ============ تنظیمات ============
TOKEN = "8954675509:AAGkdKpnKjoPPf-irMnCHZyswmqJCoIruiI"
BOT_USERNAME = "@YourBotUsername"  # یوزرنیم رباتت رو بذار

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ وضعیت‌های Conversation ============
WAITING_FOR_API_ID = 1
WAITING_FOR_API_HASH = 2
WAITING_FOR_PHONE = 3
WAITING_FOR_CODE = 4
WAITING_FOR_PASSWORD = 5

# دیکشنری برای ذخیره اطلاعات موقت کاربران
user_sessions = {}

# ============ توابع کمکی ============
def delete_webhook():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        with urllib.request.urlopen(url) as response:
            return True
    except:
        return False

def is_valid_api_id(text):
    """بررسی اعتبار API ID (عدد صحیح)"""
    return text.isdigit()

def is_valid_api_hash(text):
    """بررسی اعتبار API Hash (حداقل 30 کاراکتر)"""
    return len(text) >= 30

def is_valid_phone(text):
    """بررسی اعتبار شماره تلفن"""
    phone = re.sub(r'[^0-9+]', '', text)
    return len(phone) >= 10

def mask_password(password):
    """مخفی کردن پسورد"""
    return "*" * len(password)

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    mention = f"@{user.username}" if user.username else user.first_name
    
    text = f"""
<b>🤖 ربات سشن‌ساز تلگرام</b>
━━━━━━━━━━━━━━━━━━━

<b>خوش اومدی</b> {mention} 👋

این ربات برای <b>ساخت سشن</b> و <b>وارد کردن اکانت</b> تلگرام ساخته شده.

<b>⚡️ روی دکمه زیر کلیک کن تا ساخت سشن شروع بشه:</b>
"""
    
    keyboard = [
        [InlineKeyboardButton("🔑 ساخت سشن جدید", callback_data="new_session")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help")]
    ]
    
    if edit:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        await update.callback_query.answer("🔙 به منوی اصلی برگشتی!")
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

# ============ راهنما ============
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
<b>❓ راهنمای ساخت سشن</b>
━━━━━━━━━━━━━━━━━━━

<b>🔹 مراحل:</b>
1. <b>API ID</b> رو وارد کن (از my.telegram.org)
2. <b>API Hash</b> رو وارد کن
3. <b>شماره تلفن</b> رو وارد کن (با کد کشور)
4. <b>کد تایید</b> رو وارد کن (از تلگرام)
5. اگر <b>پسورد دو مرحله‌ای</b> داری، وارد کن

<b>🔸 نکات مهم:</b>
• API ID و Hash رو از <a href="https://my.telegram.org">my.telegram.org</a> بگیر
• شماره رو با کد کشور وارد کن (مثال: 989123456789)
• اطلاعات شما ذخیره نمیشه!
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
        disable_web_page_preview=True
    )

# ============ شروع ساخت سشن ============
async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # پاک کردن اطلاعات قبلی کاربر
    user_sessions[user_id] = {}
    
    text = """
<b>🔑 ساخت سشن جدید</b>
━━━━━━━━━━━━━━━━━━━

<b>مرحله ۱:</b> لطفاً <b>API ID</b> خود را وارد کنید.

📌 از <a href="https://my.telegram.org">my.telegram.org</a> بگیرید.

🔑 <b>مثال:</b> <code>123456</code>
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    
    return WAITING_FOR_API_ID

# ============ دریافت API ID ============
async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # بررسی اینکه کاربر در حالت دریافت API ID هست
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کنید!", parse_mode='HTML')
        return ConversationHandler.END
    
    if not is_valid_api_id(text):
        await update.message.reply_text(
            "❌ API ID باید یک عدد صحیح باشد!\n\n"
            "لطفاً دوباره وارد کنید:",
            parse_mode='HTML'
        )
        return WAITING_FOR_API_ID
    
    user_sessions[user_id]['api_id'] = int(text)
    
    text = f"""
<b>✅ API ID ذخیره شد!</b>
━━━━━━━━━━━━━━━━━━━

<b>مرحله ۲:</b> لطفاً <b>API Hash</b> خود را وارد کنید.

📌 از <a href="https://my.telegram.org">my.telegram.org</a> بگیرید.

🔑 <b>مثال:</b> <code>0123456789abcdef0123456789abcdef</code>
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    
    return WAITING_FOR_API_HASH

# ============ دریافت API Hash ============
async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کنید!", parse_mode='HTML')
        return ConversationHandler.END
    
    if not is_valid_api_hash(text):
        await update.message.reply_text(
            "❌ API Hash نامعتبر! (حداقل ۳۰ کاراکتر)\n\n"
            "لطفاً دوباره وارد کنید:",
            parse_mode='HTML'
        )
        return WAITING_FOR_API_HASH
    
    user_sessions[user_id]['api_hash'] = text
    
    text = f"""
<b>✅ API Hash ذخیره شد!</b>
━━━━━━━━━━━━━━━━━━━

<b>مرحله ۳:</b> لطفاً <b>شماره تلفن</b> خود را وارد کنید.

📱 <b>مثال:</b> <code>989123456789</code>
(با کد کشور، بدون +)
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    return WAITING_FOR_PHONE

# ============ دریافت شماره تلفن ============
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کنید!", parse_mode='HTML')
        return ConversationHandler.END
    
    # پاک کردن کاراکترهای اضافی
    phone = re.sub(r'[^0-9+]', '', text)
    
    if not is_valid_phone(phone):
        await update.message.reply_text(
            "❌ شماره تلفن نامعتبر!\n\n"
            "لطفاً با کد کشور وارد کنید:\n"
            "<b>مثال:</b> <code>989123456789</code>",
            parse_mode='HTML'
        )
        return WAITING_FOR_PHONE
    
    user_sessions[user_id]['phone'] = phone
    
    # ساخت متن نمایشی
    text = f"""
<b>✅ شماره تلفن ذخیره شد!</b>
━━━━━━━━━━━━━━━━━━━

📱 <b>شماره:</b> <code>{phone}</code>

<b>مرحله ۴:</b> منتظر دریافت <b>کد تایید</b> از تلگرام باشید.

📩 کد رو وارد کنید:
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    return WAITING_FOR_CODE

# ============ دریافت کد تایید ============
async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کنید!", parse_mode='HTML')
        return ConversationHandler.END
    
    user_sessions[user_id]['code'] = text
    
    text = f"""
<b>✅ کد تایید دریافت شد!</b>
━━━━━━━━━━━━━━━━━━━

📩 <b>کد:</b> <code>{text}</code>

<b>مرحله ۵ (اختیاری):</b>
اگر <b>پسورد دو مرحله‌ای</b> دارید وارد کنید.
در غیر این صورت <b>/skip</b> رو بفرستید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    return WAITING_FOR_PASSWORD

# ============ دریافت پسورد یا اسکیپ ============
async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کنید!", parse_mode='HTML')
        return ConversationHandler.END
    
    # ساخت سشن
    data = user_sessions[user_id]
    
    # ساخت سشن (شبیه‌سازی)
    session_string = f"SESSION_{data.get('api_id')}_{data.get('phone')}_{data.get('code')}"
    if text and text != "/skip":
        session_string += f"_{text}"
    
    # نمایش نتیجه
    result_text = f"""
<b>✅ سشن با موفقیت ساخته شد!</b>
━━━━━━━━━━━━━━━━━━━

<b>📋 اطلاعات سشن:</b>
• <b>API ID:</b> <code>{data.get('api_id')}</code>
• <b>API Hash:</b> <code>{data.get('api_hash')[:10]}...{data.get('api_hash')[-5:]}</code>
• <b>شماره:</b> <code>{data.get('phone')}</code>
• <b>کد:</b> <code>{data.get('code')}</code>
• <b>پسورد:</b> {mask_password(text) if text and text != '/skip' else 'ندارد'}

━━━━━━━━━━━━━━━━━━━
<b>🔑 سشن شما:</b>
<code>{session_string}</code>
━━━━━━━━━━━━━━━━━━━

⚠️ <b>نکته:</b> این سشن رو در جای امن نگهداری کن!
"""
    
    keyboard = [
        [InlineKeyboardButton("🔑 ساخت سشن جدید", callback_data="new_session")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
    ]
    
    await update.message.reply_text(
        result_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    # پاک کردن اطلاعات کاربر
    del user_sessions[user_id]
    
    return ConversationHandler.END

# ============ اسکیپ پسورد ============
async def skip_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کنید!", parse_mode='HTML')
        return ConversationHandler.END
    
    data = user_sessions[user_id]
    
    # ساخت سشن بدون پسورد
    session_string = f"SESSION_{data.get('api_id')}_{data.get('phone')}_{data.get('code')}"
    
    result_text = f"""
<b>✅ سشن با موفقیت ساخته شد!</b>
━━━━━━━━━━━━━━━━━━━

<b>📋 اطلاعات سشن:</b>
• <b>API ID:</b> <code>{data.get('api_id')}</code>
• <b>API Hash:</b> <code>{data.get('api_hash')[:10]}...{data.get('api_hash')[-5:]}</code>
• <b>شماره:</b> <code>{data.get('phone')}</code>
• <b>کد:</b> <code>{data.get('code')}</code>
• <b>پسورد:</b> ندارد

━━━━━━━━━━━━━━━━━━━
<b>🔑 سشن شما:</b>
<code>{session_string}</code>
━━━━━━━━━━━━━━━━━━━

⚠️ <b>نکته:</b> این سشن رو در جای امن نگهداری کن!
"""
    
    keyboard = [
        [InlineKeyboardButton("🔑 ساخت سشن جدید", callback_data="new_session")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
    ]
    
    await update.message.reply_text(
        result_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    del user_sessions[user_id]
    
    return ConversationHandler.END

# ============ دکمه برگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # پاک کردن اطلاعات کاربر
    user_id = query.from_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await main_menu(update, context, edit=True)

# ============ دستور start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ دستور skip ============
async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await skip_password(update, context)

# ============ لغو ============
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text(
        "❌ ساخت سشن لغو شد!\n\n"
        "برای شروع دوباره از /start استفاده کنید.",
        parse_mode='HTML'
    )
    return ConversationHandler.END

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🚀 ربات سشن‌ساز تلگرام")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        # ConversationHandler برای ساخت سشن
        conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(new_session, pattern="^new_session$")
            ],
            states={
                WAITING_FOR_API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_id)],
                WAITING_FOR_API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_hash)],
                WAITING_FOR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
                WAITING_FOR_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)],
                WAITING_FOR_PASSWORD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_password),
                    CommandHandler("skip", skip_password)
                ],
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
                CallbackQueryHandler(back_to_menu, pattern="^back$")
            ],
            name="session_builder",
            persistent=False
        )
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(help_menu, pattern="^help$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        application.add_handler(CallbackQueryHandler(new_session, pattern="^new_session$"))
        application.add_handler(conv_handler)
        
        print("✅ ربات روشن شد!")
        print("💡 برای شروع /start بفرست")
        print("=" * 60)
        
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
