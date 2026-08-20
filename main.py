import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ChatMemberHandler, filters
import urllib.request
import re
import pytz

# ============ تنظیمات ============
TOKEN = "8724156247:AAH26WN2k9dlI-K3PFgj665F2r1aGRH4OMw"
BOT_USERNAME = "@SlefGroupbot"

TEHRAN_TZ = pytz.timezone('Asia/Tehran')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

channels = {}
waiting_for_channel_id = {}
waiting_for_post = {}

# ============ توابع کمکی ============
def now_tehran():
    return datetime.now(TEHRAN_TZ)

def get_tehran_time_str():
    return now_tehran().strftime("%H:%M")

def user_mention(user):
    if user.username:
        return f"@{user.username}"
    else:
        return f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

def is_telegram_id(text):
    return bool(re.match(r'^-?\d+$', text.strip()))

def delete_webhook():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        with urllib.request.urlopen(url) as response:
            return True
    except:
        return False

def format_number(num):
    try:
        return f"{num:,}".replace(",", ".")
    except:
        return "0"

def clean_title(title):
    if title is None:
        return "بدون نام"
    # حذف ساعت از انتهای اسم
    cleaned = re.sub(r'\s*\d{2}:\d{2}$', '', title)
    return cleaned.strip() if cleaned.strip() else "بدون نام"

def add_time_to_title(title, time_str):
    clean = clean_title(title)
    return f"{clean} {time_str}"

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    mention = user_mention(user)
    
    text = f"""
<b>🤖 ربات مدیریت کانال</b>
━━━━━━━━━━━━━━

<b>خوش اومدی</b> {mention} 👋

این ربات برای <b>مدیریت کانال‌ها</b> ساخته شده.

<b>⚡️ یکی از گزینه‌های زیر رو انتخاب کن:</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("⚙️ تنظیم کانال", callback_data="setup_channel"),
            InlineKeyboardButton("📝 تنظیم پست", callback_data="setup_post")
        ],
        [
            InlineKeyboardButton("📋 لیست کانال‌ها", callback_data="list_channels")
        ]
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

# ============ لیست کانال‌ها ============
async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not channels:
        text = """
<b>📋 لیست کانال‌ها</b>
━━━━━━━━━━━━━━

<i>هیچ کانالی تنظیم نشده است!</i>
"""
    else:
        channel_list = ""
        for idx, (channel_id, data) in enumerate(channels.items(), 1):
            time_status = "✅" if data.get("time_enabled", False) else "❌"
            post_status = "✅" if data.get("post_enabled", False) else "❌"
            channel_list += f"{idx}. {data.get('name', 'بدون نام')[:30]}\n"
            channel_list += f"   🕐 ساعت: {time_status} | 📝 پست: {post_status}\n"
            channel_list += f"   🆔 {channel_id}\n\n"
        
        text = f"""
<b>📋 لیست کانال‌ها</b>
━━━━━━━━━━━━━━

<b>📊 تعداد:</b> {len(channels)}

{channel_list}

<b>راهنما:</b>
✅ = فعال | ❌ = غیرفعال
🕐 = ساعت | 📝 = پست
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ تنظیم کانال ============
async def setup_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    text = f"""
<b>⚙️ تنظیم کانال</b>
━━━━━━━━━━━━━━

<b>به تنظیم کانال خوش آمدید!</b>

لطفاً <b>آیدی عددی</b> کانال را وارد کنید.

<b>📝 مثال:</b>
<code>-1001234567890</code>

<b>⚠️ نکته:</b>
ربات باید در کانال عضو باشد!
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    waiting_for_channel_id[user_id] = True

# ============ تنظیم پست ============
async def setup_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    text = f"""
<b>📝 تنظیم پست</b>
━━━━━━━━━━━━━━

<b>به تنظیم پست خوش آمدید!</b>

لطفاً یک <b>پست</b> را به ربات <b>فوروارد</b> کنید.

⚠️ پست را فوروارد کنید (نه کپی)
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    waiting_for_post[user_id] = True

# ============ دریافت آیدی کانال ============
async def handle_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in waiting_for_channel_id:
        return
    
    del waiting_for_channel_id[user_id]
    
    if not is_telegram_id(text):
        await update.message.reply_text("❌ آیدی نامعتبر! لطفاً یک آیدی عددی وارد کنید.", parse_mode='HTML')
        return
    
    channel_id = int(text)
    
    try:
        chat_info = await context.bot.get_chat(channel_id)
        
        if chat_info.type != "channel":
            await update.message.reply_text("❌ این آیدی یک کانال نیست!", parse_mode='HTML')
            return
        
        # اطلاعات کانال
        chat_link = f"https://t.me/{chat_info.username}" if chat_info.username else "لینک عمومی ندارد"
        
        private_link = "ندارد"
        try:
            bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
            if bot_member.status in ["administrator", "creator"]:
                invite_link = await context.bot.create_chat_invite_link(
                    chat_id=channel_id,
                    member_limit=1
                )
                private_link = invite_link.invite_link
        except:
            pass
        
        try:
            member_count = await context.bot.get_chat_members_count(channel_id)
            member_count_formatted = format_number(member_count)
        except:
            member_count_formatted = "0"
        
        original_name = chat_info.title if chat_info.title else "بدون نام"
        clean = clean_title(original_name)
        
        # ذخیره کانال
        channels[str(channel_id)] = {
            "name": original_name,
            "id": channel_id,
            "username": chat_info.username,
            "link": chat_link,
            "private_link": private_link,
            "member_count": member_count_formatted,
            "setup_at": now_tehran().strftime("%Y/%m/%d %H:%M"),
            "set_by": user_mention(update.effective_user),
            "time_enabled": False,
            "post_enabled": False,
            "original_name": clean,
            "post_text": None,
            "post_message_id": None,
            "post_from_chat": None
        }
        
        # نمایش تنظیمات
        await show_channel_settings(update, context, str(channel_id))
        
    except Exception as e:
        error_msg = str(e).lower()
        
        if "chat not found" in error_msg or "not found" in error_msg:
            keyboard = [[InlineKeyboardButton("➕ افزودن ربات به کانال", url=f"https://t.me/{BOT_USERNAME[1:]}?startchannel=admin")]]
            text = f"""
<b>❌ ربات در کانال عضو نیست!</b>
━━━━━━━━━━━━━━

برای تنظیم کانال باید <b>ربات را به کانال اضافه کنید</b>.

⚠️ مراحل:
۱. روی دکمه زیر کلیک کنید
۲. کانال خود را انتخاب کنید
۳. ربات را به عنوان ادمین اضافه کنید
۴. دوباره آیدی را بفرستید

<b>📌 ربات:</b> {BOT_USERNAME}
"""
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ خطا: {str(e)[:100]}", parse_mode='HTML')
            logger.error(f"Error: {e}")

# ============ نمایش تنظیمات کانال ============
async def show_channel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id):
    data = channels[channel_id]
    
    time_status = "✅ فعال" if data.get("time_enabled", False) else "❌ غیرفعال"
    post_status = "✅ فعال" if data.get("post_enabled", False) else "❌ غیرفعال"
    post_text = data.get("post_text", "تنظیم نشده")
    if post_text and len(post_text) > 50:
        post_text = post_text[:50] + "..."
    
    text = f"""
<b>✅ کانال تنظیم شد!</b>
━━━━━━━━━━━━━━

<b>📌 نام:</b> {data.get('name', 'بدون نام')}
<b>🆔 آیدی:</b> <code>{channel_id}</code>
<b>👥 اعضا:</b> {data.get('member_count', '0')}

<b>⚙️ تنظیمات:</b>
🕐 ساعت: {time_status}
📝 پست: {post_status}
📄 متن پست: {post_text}
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🕐 فعال‌سازی ساعت", callback_data=f"time_on_{channel_id}"),
            InlineKeyboardButton("🚫 غیرفعال‌سازی ساعت", callback_data=f"time_off_{channel_id}")
        ],
        [
            InlineKeyboardButton("📝 فعال‌سازی پست", callback_data=f"post_on_{channel_id}"),
            InlineKeyboardButton("🚫 غیرفعال‌سازی پست", callback_data=f"post_off_{channel_id}")
        ],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ دریافت فوروارد پست ============
async def handle_post_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message
    
    if user_id not in waiting_for_post:
        return
    
    del waiting_for_post[user_id]
    
    if not message.forward_from and not message.forward_from_chat:
        await update.message.reply_text("❌ لطفاً یک پست را فوروارد کنید (نه کپی)!", parse_mode='HTML')
        return
    
    post_text = message.text or message.caption or ""
    
    for channel_id in channels.keys():
        channels[channel_id]["post_text"] = post_text
        channels[channel_id]["post_message_id"] = message.message_id
        channels[channel_id]["post_from_chat"] = message.chat.id
    
    # ارسال پست به کانال‌ها
    current_time = get_tehran_time_str()
    await send_post_to_channels(context, current_time)
    
    await update.message.reply_text(
        f"""
<b>✅ پست تنظیم شد!</b>
━━━━━━━━━━━━━━

<b>📝 متن:</b> {post_text[:200]}{'...' if len(post_text) > 200 else ''}

پست به <b>{len(channels)}</b> کانال ارسال شد.
""",
        parse_mode='HTML'
    )

async def send_post_to_channels(context, time_str):
    for channel_id, data in channels.items():
        try:
            post_text = data.get("post_text", "")
            post_with_time = f"{time_str} {post_text}" if post_text else time_str
            
            if data.get("post_message_id") and data.get("post_from_chat"):
                try:
                    await context.bot.forward_message(
                        chat_id=channel_id,
                        from_chat_id=data["post_from_chat"],
                        message_id=data["post_message_id"]
                    )
                except:
                    await context.bot.send_message(chat_id=channel_id, text=post_with_time)
            else:
                await context.bot.send_message(chat_id=channel_id, text=post_with_time)
            
            logger.info(f"Post sent to {channel_id}")
        except Exception as e:
            logger.error(f"Error sending to {channel_id}: {e}")

# ============ دکمه‌های ساعت و پست ============
async def time_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_id = query.data.split("_")[2]
    
    if channel_id not in channels:
        await query.edit_message_text("❌ کانال پیدا نشد!")
        return
    
    data = channels[channel_id]
    data["time_enabled"] = True
    
    try:
        current_time = get_tehran_time_str()
        clean = clean_title(data.get("original_name", data.get("name", "بدون نام")))
        new_title = add_time_to_title(clean, current_time)
        
        await context.bot.set_chat_title(chat_id=channel_id, title=new_title)
        data["name"] = new_title
        data["original_name"] = clean
        
        await show_channel_settings_from_callback(update, context, channel_id)
    except Exception as e:
        logger.error(f"Error: {e}")

async def time_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_id = query.data.split("_")[2]
    
    if channel_id not in channels:
        await query.edit_message_text("❌ کانال پیدا نشد!")
        return
    
    data = channels[channel_id]
    data["time_enabled"] = False
    
    try:
        clean = clean_title(data.get("original_name", data.get("name", "بدون نام")))
        await context.bot.set_chat_title(chat_id=channel_id, title=clean)
        data["name"] = clean
        data["original_name"] = clean
        
        await show_channel_settings_from_callback(update, context, channel_id)
    except Exception as e:
        logger.error(f"Error: {e}")

async def post_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_id = query.data.split("_")[2]
    
    if channel_id not in channels:
        await query.edit_message_text("❌ کانال پیدا نشد!")
        return
    
    data = channels[channel_id]
    
    if not data.get("post_text"):
        await query.edit_message_text("❌ ابتدا از گزینه تنظیم پست، یک پست را فوروارد کنید!", parse_mode='HTML')
        return
    
    data["post_enabled"] = True
    await show_channel_settings_from_callback(update, context, channel_id)

async def post_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_id = query.data.split("_")[2]
    
    if channel_id not in channels:
        await query.edit_message_text("❌ کانال پیدا نشد!")
        return
    
    channels[channel_id]["post_enabled"] = False
    await show_channel_settings_from_callback(update, context, channel_id)

async def show_channel_settings_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id):
    data = channels[channel_id]
    
    time_status = "✅ فعال" if data.get("time_enabled", False) else "❌ غیرفعال"
    post_status = "✅ فعال" if data.get("post_enabled", False) else "❌ غیرفعال"
    post_text = data.get("post_text", "تنظیم نشده")
    if post_text and len(post_text) > 50:
        post_text = post_text[:50] + "..."
    
    text = f"""
<b>⚙️ تنظیمات کانال</b>
━━━━━━━━━━━━━━

<b>📌 نام:</b> {data.get('name', 'بدون نام')}
<b>🆔 آیدی:</b> <code>{channel_id}</code>
<b>👥 اعضا:</b> {data.get('member_count', '0')}

🕐 ساعت: {time_status}
📝 پست: {post_status}
📄 متن: {post_text}
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🕐 فعال‌سازی ساعت", callback_data=f"time_on_{channel_id}"),
            InlineKeyboardButton("🚫 غیرفعال‌سازی ساعت", callback_data=f"time_off_{channel_id}")
        ],
        [
            InlineKeyboardButton("📝 فعال‌سازی پست", callback_data=f"post_on_{channel_id}"),
            InlineKeyboardButton("🚫 غیرفعال‌سازی پست", callback_data=f"post_off_{channel_id}")
        ],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
    ]
    
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ============ تغییر اسم کانال ============
async def handle_channel_title_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id not in channels or not chat.title:
        return
    
    data = channels[chat_id]
    current_title = chat.title
    clean = clean_title(current_title)
    
    if data.get("time_enabled", False):
        time_str = get_tehran_time_str()
        new_title = add_time_to_title(clean, time_str)
        
        if new_title != current_title:
            try:
                await context.bot.set_chat_title(chat_id=chat_id, title=new_title)
                data["name"] = new_title
                data["original_name"] = clean
            except Exception as e:
                logger.error(f"Error: {e}")
    else:
        data["original_name"] = clean
        data["name"] = current_title

# ============ حذف پیام‌های خدماتی ============
async def delete_service_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message and message.chat and str(message.chat.id) in channels:
        if message.new_chat_title:
            try:
                await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            except:
                pass

# ============ به‌روزرسانی ساعت ============
async def update_time_every_minute(context: ContextTypes.DEFAULT_TYPE):
    try:
        current_time = get_tehran_time_str()
        
        for channel_id, data in channels.items():
            if data.get("time_enabled", False):
                try:
                    chat = await context.bot.get_chat(channel_id)
                    current_title = chat.title if chat.title else "بدون نام"
                    clean = clean_title(current_title)
                    new_title = add_time_to_title(clean, current_time)
                    
                    if new_title != current_title:
                        await context.bot.set_chat_title(chat_id=channel_id, title=new_title)
                        data["name"] = new_title
                        data["original_name"] = clean
                except Exception as e:
                    logger.error(f"Error updating {channel_id}: {e}")
    except Exception as e:
        logger.error(f"Error: {e}")

# ============ ورود به کانال ============
async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member = update.chat_member
    if not chat_member:
        return
    
    if chat_member.new_chat_member.user.id == context.bot.id:
        if chat_member.new_chat_member.status in ["member", "administrator"]:
            chat = update.effective_chat
            chat_id = chat.id
            chat_title = chat.title if chat.title else "بدون نام"
            chat_link = f"https://t.me/{chat.username}" if chat.username else "لینک عمومی ندارد"
            
            try:
                member_count = await context.bot.get_chat_members_count(chat_id)
                member_count_formatted = format_number(member_count)
            except:
                member_count_formatted = "0"
            
            text = f"""
<b>✅ ربات به کانال اضافه شد!</b>
━━━━━━━━━━━━━━

<b>📌 نام:</b> {chat_title}
<b>🆔 آیدی:</b> <code>{chat_id}</code>
<b>🔗 لینک:</b> {chat_link}
<b>👥 اعضا:</b> {member_count_formatted}
<b>⏰ زمان:</b> {now_tehran().strftime('%Y/%m/%d %H:%M')}

ربات آماده استفاده است!
"""
            try:
                await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
            except:
                pass

# ============ دکمه برگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context, edit=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🚀 ربات مدیریت کانال")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        
        application.add_handler(CallbackQueryHandler(setup_channel, pattern="^setup_channel$"))
        application.add_handler(CallbackQueryHandler(setup_post, pattern="^setup_post$"))
        application.add_handler(CallbackQueryHandler(list_channels, pattern="^list_channels$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        application.add_handler(CallbackQueryHandler(time_on, pattern="^time_on_"))
        application.add_handler(CallbackQueryHandler(time_off, pattern="^time_off_"))
        application.add_handler(CallbackQueryHandler(post_on, pattern="^post_on_"))
        application.add_handler(CallbackQueryHandler(post_off, pattern="^post_off_"))
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_id))
        application.add_handler(MessageHandler(filters.ALL, handle_post_forward))
        
        application.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER))
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_TITLE, handle_channel_title_change))
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_TITLE, delete_service_messages), group=1)
        
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(update_time_every_minute, interval=60, first=10)
            print("✅ ساعت‌شمار فعال شد")
        
        print("✅ ربات روشن شد!")
        print("=" * 60)
        
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
