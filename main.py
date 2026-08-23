import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler
import urllib.request
import asyncio
import os

# ============ تنظیمات ============
TOKEN = "8954675509:AAGkdKpnKjoPPf-irMnCHZyswmqJCoIruiI"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ وضعیت‌ها ============
WAITING_FOR_PHONE = 1
WAITING_FOR_API_ID = 2
WAITING_FOR_API_HASH = 3
WAITING_FOR_CODE = 4
WAITING_FOR_PASSWORD = 5

user_sessions = {}
user_messages = {}  # ذخیره پیام‌ها برای ادیت

# ============ توابع کمکی ============
def delete_webhook():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        with urllib.request.urlopen(url) as response:
            return True
    except:
        return False

def is_valid_phone(text):
    phone = re.sub(r'[^0-9+]', '', text)
    return len(phone) >= 10

def is_valid_api_id(text):
    return text.isdigit()

def is_valid_api_hash(text):
    return len(text) >= 30

def clean_code(text):
    """تمیز کردن کد ورودی (حذف نقطه و فاصله)"""
    return re.sub(r'[.\s\-]', '', text).strip()

def mask_password(password):
    return "*" * len(password)

def get_user_key(user_id):
    return f"user_{user_id}"

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    mention = f"@{user.username}" if user.username else user.first_name
    
    text = f"""
<b>🤖 ربات سشن‌ساز حرفه‌ای</b>
━━━━━━━━━━━━━━━━━━━

<b>سلام</b> {mention} 👋

به ربات <b>سشن‌ساز</b> خوش اومدی!

اینجا می‌تونی <b>سشن تلگرام</b> واقعی بسازی.

<b>⚡️ برای شروع روی دکمه زیر کلیک کن:</b>
"""
    
    keyboard = [
        [InlineKeyboardButton("🔑 ساخت سشن جدید", callback_data="new_session")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help")]
    ]
    
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        await update.callback_query.answer("🔙 برگشتی به منو!")
    else:
        msg = await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        user_messages[update.effective_user.id] = msg.message_id

# ============ راهنما ============
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
<b>📖 راهنمای ساخت سشن</b>
━━━━━━━━━━━━━━━━━━━

<b>🔹 مراحل:</b>

۱. <b>شماره تلفن</b> رو وارد کن (با کد کشور)
۲. <b>API ID</b> رو از my.telegram.org بگیر
۳. <b>API Hash</b> رو از my.telegram.org بگیر
۴. <b>کد تایید</b> که از تلگرام میاد رو وارد کن
۵. اگر <b>پسورد دو مرحله‌ای</b> داری، وارد کن

<b>🔸 نکات مهم:</b>
• شماره رو با کد کشور وارد کن
• مثال: <code>989123456789</code>
• کد رو به صورت <code>12345</code> یا <code>1.2.3.4.5</code> وارد کن
• اطلاعاتت ذخیره نمیشه!
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
    user_sessions[user_id] = {}
    
    text = """
<b>🔑 ساخت سشن جدید</b>
━━━━━━━━━━━━━━━━━━━

<b>مرحله ۱:</b> لطفاً <b>شماره تلفن</b> خودت رو وارد کن.

📱 <b>مثال:</b> <code>989123456789</code>
(با کد کشور، بدون +)

⚠️ شماره رو درست وارد کن!
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    return WAITING_FOR_PHONE

# ============ دریافت شماره ============
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    phone = re.sub(r'[^0-9+]', '', text)
    
    if not is_valid_phone(phone):
        msg = await update.message.reply_text(
            "❌ شماره تلفن نامعتبره!\n\n"
            "لطفاً با کد کشور وارد کن:\n"
            "<b>مثال:</b> <code>989123456789</code>",
            parse_mode='HTML'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_PHONE
    
    user_sessions[user_id]['phone'] = phone
    
    text = f"""
<b>✅ شماره تلفن ذخیره شد!</b>
━━━━━━━━━━━━━━━━━━━

📱 <b>شماره:</b> <code>{phone}</code>

━━━━━━━━━━━━━━━━━━━
<b>مرحله ۲:</b> لطفاً <b>API ID</b> خودت رو وارد کن.

🔑 از <a href="https://my.telegram.org">my.telegram.org</a> بگیرش.

<b>مثال:</b> <code>123456</code>
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    msg = await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    user_messages[user_id] = msg.message_id
    
    return WAITING_FOR_API_ID

# ============ دریافت API ID ============
async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    if not is_valid_api_id(text):
        msg = await update.message.reply_text(
            "❌ API ID باید عدد باشه!\n\n"
            "لطفاً دوباره وارد کن:",
            parse_mode='HTML'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_API_ID
    
    user_sessions[user_id]['api_id'] = int(text)
    
    text = f"""
<b>✅ API ID ذخیره شد!</b>
━━━━━━━━━━━━━━━━━━━

🔑 <b>API ID:</b> <code>{text}</code>

━━━━━━━━━━━━━━━━━━━
<b>مرحله ۳:</b> لطفاً <b>API Hash</b> خودت رو وارد کن.

🔐 از <a href="https://my.telegram.org">my.telegram.org</a> بگیرش.

<b>مثال:</b> <code>0123456789abcdef0123456789abcdef</code>
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    msg = await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    user_messages[user_id] = msg.message_id
    
    return WAITING_FOR_API_HASH

# ============ دریافت API Hash ============
async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    if not is_valid_api_hash(text):
        msg = await update.message.reply_text(
            "❌ API Hash نامعتبره! (حداقل ۳۰ کاراکتر)\n\n"
            "لطفاً دوباره وارد کن:",
            parse_mode='HTML'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_API_HASH
    
    user_sessions[user_id]['api_hash'] = text
    
    # ذخیره پیام برای ادیت بعدی
    msg = await update.message.reply_text(
        "⏳ در حال ارسال کد به شماره شما...",
        parse_mode='HTML'
    )
    user_messages[user_id] = msg.message_id
    user_sessions[user_id]['message_id'] = msg.message_id
    
    # ارسال کد با Telethon
    try:
        from telethon import TelegramClient
        
        data = user_sessions[user_id]
        phone = data['phone']
        api_id = data['api_id']
        api_hash = data['api_hash']
        
        session_name = f"temp_{phone}_{api_id}"
        client = TelegramClient(session_name, api_id, api_hash)
        
        await client.connect()
        
        try:
            await client.send_code_request(phone)
            
            user_sessions[user_id]['client'] = client
            user_sessions[user_id]['session_name'] = session_name
            
            # ادیت پیام قبلی
            text = f"""
<b>✅ کد تایید ارسال شد!</b>
━━━━━━━━━━━━━━━━━━━

📩 کد ۵ رقمی به شماره <code>{phone}</code> ارسال شد.

لطفاً کد رو وارد کن:
<b>مثال:</b> <code>12345</code> یا <code>1.2.3.4.5</code>
"""
            
            keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=user_sessions[user_id]['message_id'],
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            
            return WAITING_FOR_CODE
            
        except Exception as e:
            error = str(e)
            if "FLOOD" in error:
                text = f"❌ خطا: درخواست زیاد! لطفاً چند دقیقه صبر کن.\n\n{error[:100]}"
            else:
                text = f"❌ خطا در ارسال کد: {error[:200]}\n\nلطفاً شماره رو چک کن و دوباره تلاش کن."
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=user_sessions[user_id]['message_id'],
                text=text,
                parse_mode='HTML'
            )
            return ConversationHandler.END
            
    except ImportError:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=user_sessions[user_id]['message_id'],
            text="❌ کتابخانه Telethon نصب نیست! لطفاً با ادمین تماس بگیر.",
            parse_mode='HTML'
        )
        return ConversationHandler.END

# ============ دریافت کد ============
async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_code = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    # تمیز کردن کد (حذف نقطه و فاصله)
    code = clean_code(raw_code)
    
    if not code.isdigit() or len(code) != 5:
        msg = await update.message.reply_text(
            "❌ کد باید ۵ رقم باشد!\n\n"
            "مثال: <code>12345</code> یا <code>1.2.3.4.5</code>",
            parse_mode='HTML'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_CODE
    
    data = user_sessions[user_id]
    
    try:
        client = data.get('client')
        if not client:
            await update.message.reply_text(
                "❌ اتصال معتبر نیست! لطفاً دوباره شروع کن.",
                parse_mode='HTML'
            )
            return ConversationHandler.END
        
        phone = data['phone']
        api_id = data['api_id']
        api_hash = data['api_hash']
        
        from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError
        
        try:
            # امتحان ورود با کد
            await client.sign_in(phone, code)
            
            # موفقیت - گرفتن سشن
            session_string = client.session.save()
            
            await client.disconnect()
            
            try:
                os.remove(f"{data.get('session_name', 'temp')}.session")
            except:
                pass
            
            # ادیت پیام آخر
            result_text = f"""
<b>✅ سشن با موفقیت ساخته شد!</b>
━━━━━━━━━━━━━━━━━━━

<b>📋 اطلاعات اکانت:</b>
• <b>شماره:</b> <code>{phone}</code>
• <b>API ID:</b> <code>{api_id}</code>
• <b>API Hash:</b> <code>{api_hash[:10]}...{api_hash[-5:]}</code>

━━━━━━━━━━━━━━━━━━━
<b>🔑 سشن شما:</b>
<code>{session_string}</code>
━━━━━━━━━━━━━━━━━━━

⚠️ <b>نکته مهم:</b>
این سشن رو در جای امن نگهداری کن!
به هیچکس نده!
"""
            
            keyboard = [
                [InlineKeyboardButton("🔑 ساخت سشن جدید", callback_data="new_session")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
            ]
            
            # ادیت پیام قبلی
            if user_id in user_messages:
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=user_messages[user_id],
                        text=result_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                except:
                    await update.message.reply_text(
                        result_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(
                    result_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            
            if user_id in user_sessions:
                del user_sessions[user_id]
            if user_id in user_messages:
                del user_messages[user_id]
            
            return ConversationHandler.END
            
        except PhoneCodeExpiredError:
            # کد منقضی شده - درخواست کد جدید
            try:
                # درخواست کد جدید
                await client.send_code_request(phone)
                
                text = f"""
<b>🔄 کد جدید ارسال شد!</b>
━━━━━━━━━━━━━━━━━━━

کد قبلی <b>منقضی</b> شده بود.

📩 کد جدید ۵ رقمی به شماره <code>{phone}</code> ارسال شد.

لطفاً کد جدید رو وارد کن:
<b>مثال:</b> <code>12345</code> یا <code>1.2.3.4.5</code>
"""
                
                keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
                
                msg = await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
                user_messages[user_id] = msg.message_id
                
                return WAITING_FOR_CODE
                
            except Exception as e:
                await update.message.reply_text(
                    f"❌ خطا در ارسال کد جدید: {str(e)[:100]}",
                    parse_mode='HTML'
                )
                return ConversationHandler.END
            
        except PhoneCodeInvalidError:
            msg = await update.message.reply_text(
                "❌ کد وارد شده اشتباه است!\n\n"
                "لطفاً دوباره کد رو وارد کن:",
                parse_mode='HTML'
            )
            user_messages[user_id] = msg.message_id
            return WAITING_FOR_CODE
            
        except SessionPasswordNeededError:
            text = f"""
<b>🔐 نیاز به پسورد دو مرحله‌ای!</b>
━━━━━━━━━━━━━━━━━━━

اکانت شما <b>پسورد دو مرحله‌ای</b> دارد.

لطفاً پسورد خود را وارد کن:
"""
            
            keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
            
            msg = await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            user_messages[user_id] = msg.message_id
            
            return WAITING_FOR_PASSWORD
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)[:200]}",
                parse_mode='HTML'
            )
            return ConversationHandler.END
            
    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا: {str(e)[:200]}",
            parse_mode='HTML'
        )
        return ConversationHandler.END

# ============ دریافت پسورد ============
async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً از منو شروع کن!", parse_mode='HTML')
        return ConversationHandler.END
    
    data = user_sessions[user_id]
    
    try:
        client = data.get('client')
        if not client:
            await update.message.reply_text(
                "❌ اتصال معتبر نیست! لطفاً دوباره شروع کن.",
                parse_mode='HTML'
            )
            return ConversationHandler.END
        
        await client.sign_in(password=password)
        
        session_string = client.session.save()
        
        await client.disconnect()
        
        try:
            os.remove(f"{data.get('session_name', 'temp')}.session")
        except:
            pass
        
        result_text = f"""
<b>✅ سشن با موفقیت ساخته شد!</b>
━━━━━━━━━━━━━━━━━━━

<b>📋 اطلاعات اکانت:</b>
• <b>شماره:</b> <code>{data['phone']}</code>
• <b>API ID:</b> <code>{data['api_id']}</code>
• <b>API Hash:</b> <code>{data['api_hash'][:10]}...{data['api_hash'][-5:]}</code>
• <b>پسورد:</b> {mask_password(password)}

━━━━━━━━━━━━━━━━━━━
<b>🔑 سشن شما:</b>
<code>{session_string}</code>
━━━━━━━━━━━━━━━━━━━

⚠️ <b>نکته مهم:</b>
این سشن رو در جای امن نگهداری کن!
به هیچکس نده!
"""
        
        keyboard = [
            [InlineKeyboardButton("🔑 ساخت سشن جدید", callback_data="new_session")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
        ]
        
        if user_id in user_messages:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=user_messages[user_id],
                    text=result_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            except:
                await update.message.reply_text(
                    result_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_text(
                result_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        if user_id in user_sessions:
            del user_sessions[user_id]
        if user_id in user_messages:
            del user_messages[user_id]
        
        return ConversationHandler.END
        
    except Exception as e:
        msg = await update.message.reply_text(
            f"❌ پسورد اشتباه است! {str(e)[:100]}\n\n"
            "لطفاً دوباره پسورد رو وارد کن:",
            parse_mode='HTML'
        )
        user_messages[user_id] = msg.message_id
        return WAITING_FOR_PASSWORD

# ============ دکمه برگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id in user_sessions:
        try:
            client = user_sessions[user_id].get('client')
            if client:
                await client.disconnect()
        except:
            pass
        del user_sessions[user_id]
    if user_id in user_messages:
        del user_messages[user_id]
    
    await main_menu(update, context, edit=True)

# ============ لغو ============
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        try:
            client = user_sessions[user_id].get('client')
            if client:
                await client.disconnect()
        except:
            pass
        del user_sessions[user_id]
    if user_id in user_messages:
        del user_messages[user_id]
    
    await update.message.reply_text(
        "❌ ساخت سشن لغو شد!\n\n"
        "برای شروع دوباره از /start استفاده کن.",
        parse_mode='HTML'
    )
    return ConversationHandler.END

# ============ start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🚀 ربات سشن‌ساز حرفه‌ای")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(new_session, pattern="^new_session$")
            ],
            states={
                WAITING_FOR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
                WAITING_FOR_API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_id)],
                WAITING_FOR_API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_hash)],
                WAITING_FOR_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)],
                WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
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
        application.add_handler(conv_handler)
        
        print("✅ ربات روشن شد!")
        print("💡 برای شروع /start بفرست")
        print("=" * 60)
        
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
