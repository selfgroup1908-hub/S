import logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ChatMemberHandler, filters
import urllib.request
import re
import asyncio

# ============ تنظیمات ============
TOKEN = "8724156247:AAH26WN2k9dlI-K3PFgj665F2r1aGRH4OMw"  # توکن جدید بذار
BOT_USERNAME = "@SlefGroupbot"

TEHRAN_OFFSET = timedelta(hours=3, minutes=30)

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
    return datetime.now(timezone.utc) + TEHRAN_OFFSET

def get_tehran_time_str():
    return now_tehran().strftime("%H:%M")

def get_chat_type(chat):
    if chat.type == "channel":
        return "کانال"
    elif chat.type in ["group", "supergroup"]:
        return "گروه"
    return "ناشناخته"

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
        return str(num)

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

# ============ تنظیم کانال ============
async def setup_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    text = f"""
<b>⚙️ تنظیم کانال</b>
━━━━━━━━━━━━━━

<b>به تنظیم کانال خوش آمدید!</b>

لطفاً <b>آیدی عددی</b> کانال مورد نظر را وارد کنید.

<b>📝 مثال:</b>
<code>-1001234567890</code>

<b>⚠️ نکته:</b>
ربات باید قبلاً به کانال اضافه شده باشد!
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    waiting_for_channel_id[user_id] = True
    logger.info(f"User {user_id} is waiting for channel ID")

# ============ تنظیم پست ============
async def setup_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    text = f"""
<b>📝 تنظیم پست</b>
━━━━━━━━━━━━━━

<b>به تنظیم پست خوش آمدید!</b>

لطفاً <b>متن پست</b> مورد نظر را ارسال کنید.

این پست به صورت خودکار در کانال‌های تنظیم شده ارسال خواهد شد.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    waiting_for_post[user_id] = True
    logger.info(f"User {user_id} is waiting for post text")

# ============ دریافت آیدی کانال ============
async def handle_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in waiting_for_channel_id:
        return
    
    del waiting_for_channel_id[user_id]
    
    if not is_telegram_id(text):
        await update.message.reply_text(
            f"""
<b>❌ آیدی نامعتبر!</b>
━━━━━━━━━━━━━━

لطفاً یک <b>آیدی عددی</b> معتبر وارد کنید.

<b>📝 مثال:</b>
<code>-1001234567890</code>
""",
            parse_mode='HTML'
        )
        return
    
    channel_id = int(text)
    
    try:
        chat_info = await context.bot.get_chat(channel_id)
        
        if chat_info.type == "channel":
            chat_link = f"https://t.me/{chat_info.username}" if chat_info.username else "لینک عمومی ندارد"
            
            private_link = "ندارد"
            try:
                bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
                if bot_member.status in ["administrator", "creator"]:
                    invite_link = await context.bot.create_chat_invite_link(
                        chat_id=channel_id,
                        member_limit=1,
                        expire_date=None
                    )
                    private_link = invite_link.invite_link
            except:
                pass
            
            try:
                member_count = await context.bot.get_chat_members_count(channel_id)
                member_count_formatted = format_number(member_count)
            except:
                member_count_formatted = "0"
            
            channels[str(channel_id)] = {
                "name": chat_info.title or "بدون نام",
                "id": channel_id,
                "username": chat_info.username,
                "link": chat_link,
                "private_link": private_link,
                "member_count": member_count_formatted,
                "setup_at": now_tehran().strftime("%Y/%m/%d %H:%M"),
                "set_by": user_mention(update.effective_user),
                "time_enabled": False,
                "original_name": chat_info.title or "بدون نام"
            }
            
            text = f"""
<b>✅ کانال با موفقیت تنظیم شد!</b>
━━━━━━━━━━━━━━

<b>📌 نام:</b> {chat_info.title}
<b>🆔 آیدی:</b> <code>{channel_id}</code>
<b>🔗 لینک عمومی:</b> {chat_link}
<b>🔒 لینک خصوصی:</b> {private_link}
<b>👥 تعداد اعضا:</b> {member_count_formatted}

ربات الان این کانال رو مدیریت میکنه.
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🕐 فعال‌سازی ساعت", callback_data=f"time_on_{channel_id}"),
                    InlineKeyboardButton("🚫 غیرفعال‌سازی ساعت", callback_data=f"time_off_{channel_id}")
                ],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
            ]
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            
            logger.info(f"Channel setup: {chat_info.title} ({channel_id})")
        else:
            await update.message.reply_text(
                f"""
<b>❌ این آیدی یک کانال نیست!</b>
━━━━━━━━━━━━━━

لطفاً <b>آیدی یک کانال</b> معتبر وارد کنید.
""",
                parse_mode='HTML'
            )
            
    except Exception as e:
        error_message = str(e).lower()
        
        if "chat not found" in error_message or "not found" in error_message:
            keyboard = [[
                InlineKeyboardButton("➕ افزودن ربات به کانال", url=f"https://t.me/{BOT_USERNAME[1:]}?startchannel=admin")
            ]]
            
            text = f"""
<b>❌ ربات در کانال عضو نیست!</b>
━━━━━━━━━━━━━━

برای تنظیم کانال باید <b>ربات را به کانال اضافه کنید</b>.

<b>⚠️ مراحل:</b>
۱. روی دکمه <b>افزودن ربات به کانال</b> کلیک کنید
۲. کانال خود را انتخاب کنید
۳. ربات را به عنوان <b>ادمین</b> اضافه کنید
۴. بعد از اضافه شدن، <b>آیدی عددی</b> کانال را دوباره بفرستید

<b>📌 ربات:</b> {BOT_USERNAME}
"""
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            text = f"""
<b>❌ خطا در تنظیم کانال!</b>
━━━━━━━━━━━━━━

خطا: {str(e)[:100]}

<b>⚠️ راه حل:</b>
۱. مطمئن شوید ربات در کانال عضو است
۲. آیدی را درست وارد کنید
۳. دوباره تلاش کنید
"""
            
            await update.message.reply_text(
                text,
                parse_mode='HTML'
            )
            logger.error(f"Error setting channel {channel_id}: {e}")

# ============ دریافت متن پست ============
async def handle_post_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in waiting_for_post:
        return
    
    del waiting_for_post[user_id]
    
    context.user_data['post_text'] = text
    
    await update.message.reply_text(
        f"""
<b>✅ متن پست با موفقیت ذخیره شد!</b>
━━━━━━━━━━━━━━

<b>📝 متن پست:</b>
{text[:200]}{'...' if len(text) > 200 else ''}

پست آماده ارسال به کانال‌های تنظیم شده است.
""",
        parse_mode='HTML'
    )

# ============ فعال‌سازی ساعت ============
async def time_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.split("_")[2]
    
    if channel_id not in channels:
        await query.edit_message_text("❌ کانال پیدا نشد!")
        return
    
    channel_data = channels[channel_id]
    channel_data["time_enabled"] = True
    
    try:
        current_time = get_tehran_time_str()
        current_title = channel_data.get("original_name", channel_data["name"])
        clean_title = re.sub(r'^\d{2}:\d{2}\s*', '', current_title)
        new_title = f"{current_time} {clean_title}"
        
        await context.bot.set_chat_title(
            chat_id=channel_id,
            title=new_title
        )
        
        channel_data["name"] = new_title
        channel_data["original_name"] = clean_title
        
        # ساخت پیام جدید با متن متفاوت برای جلوگیری از خطای "Message is not modified"
        text = f"""
<b>✅ ساعت با موفقیت فعال شد!</b>
━━━━━━━━━━━━━━

<b>🕐 ساعت:</b> {current_time}
<b>📌 اسم جدید کانال:</b> {new_title}

ساعت به اسم کانال اضافه شد و هر دقیقه آپدیت میشه.
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🕐 فعال‌سازی ساعت", callback_data=f"time_on_{channel_id}"),
                InlineKeyboardButton("🚫 غیرفعال‌سازی ساعت", callback_data=f"time_off_{channel_id}")
            ],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
        ]
        
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        except Exception as e:
            # اگر پیام تغییر نکرده بود، فقط دکمه‌ها رو آپدیت کن
            if "Message is not modified" in str(e):
                await query.edit_message_reply_markup(
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                raise e
        
        logger.info(f"Time enabled for channel {channel_id}")
        
    except Exception as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Error enabling time for {channel_id}: {e}")

# ============ غیرفعال‌سازی ساعت ============
async def time_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.split("_")[2]
    
    if channel_id not in channels:
        await query.edit_message_text("❌ کانال پیدا نشد!")
        return
    
    channel_data = channels[channel_id]
    channel_data["time_enabled"] = False
    
    try:
        current_title = channel_data.get("original_name", channel_data["name"])
        clean_title = re.sub(r'^\d{2}:\d{2}\s*', '', current_title)
        
        await context.bot.set_chat_title(
            chat_id=channel_id,
            title=clean_title
        )
        
        channel_data["name"] = clean_title
        channel_data["original_name"] = clean_title
        
        text = f"""
<b>✅ ساعت با موفقیت غیرفعال شد!</b>
━━━━━━━━━━━━━━

<b>📌 اسم جدید کانال:</b> {clean_title}

ساعت از اسم کانال حذف شد.
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🕐 فعال‌سازی ساعت", callback_data=f"time_on_{channel_id}"),
                InlineKeyboardButton("🚫 غیرفعال‌سازی ساعت", callback_data=f"time_off_{channel_id}")
            ],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]
        ]
        
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        except Exception as e:
            if "Message is not modified" in str(e):
                await query.edit_message_reply_markup(
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                raise e
        
        logger.info(f"Time disabled for channel {channel_id}")
        
    except Exception as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Error disabling time for {channel_id}: {e}")

# ============ تغییر اسم کانال ============
async def handle_channel_title_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id not in channels:
        return
    
    if not chat.title:
        return
    
    channel_data = channels[chat_id]
    
    current_title = chat.title
    clean_title = re.sub(r'^\d{2}:\d{2}\s*', '', current_title)
    
    if channel_data.get("time_enabled", False):
        time_str = get_tehran_time_str()
        new_title = f"{time_str} {clean_title}"
        
        try:
            if new_title != current_title:
                await context.bot.set_chat_title(
                    chat_id=chat_id,
                    title=new_title
                )
                channel_data["original_name"] = clean_title
                channel_data["name"] = new_title
                logger.info(f"Re-added time to channel {chat_id}: {new_title}")
        except Exception as e:
            logger.error(f"Error re-adding time to {chat_id}: {e}")
    else:
        channel_data["original_name"] = clean_title
        channel_data["name"] = current_title

# ============ به‌روزرسانی ساعت ============
async def update_time_every_minute(context: ContextTypes.DEFAULT_TYPE):
    current_time = get_tehran_time_str()
    
    for channel_id, channel_data in channels.items():
        if channel_data.get("time_enabled", False):
            try:
                chat = await context.bot.get_chat(channel_id)
                current_title = chat.title or ""
                
                clean_title = re.sub(r'^\d{2}:\d{2}\s*', '', current_title)
                new_title = f"{current_time} {clean_title}"
                
                if new_title != current_title:
                    await context.bot.set_chat_title(
                        chat_id=channel_id,
                        title=new_title
                    )
                    channel_data["name"] = new_title
                    channel_data["original_name"] = clean_title
                    logger.info(f"Updated time for channel {channel_id}: {new_title}")
                    
            except Exception as e:
                logger.error(f"Error updating time for {channel_id}: {e}")

# ============ ورود به کانال/گروه ============
async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_member = update.chat_member
    
    if not chat_member:
        return
    
    if chat_member.new_chat_member.user.id == context.bot.id:
        if chat_member.new_chat_member.status in ["member", "administrator"]:
            chat_type = "کانال" if chat.type == "channel" else "گروه"
            chat_title = chat.title or "بدون نام"
            chat_id = chat.id
            chat_username = chat.username
            chat_link = f"https://t.me/{chat_username}" if chat_username else "لینک عمومی ندارد"
            
            private_link = "ندارد"
            try:
                if chat_member.new_chat_member.status == "administrator":
                    invite_link = await context.bot.create_chat_invite_link(
                        chat_id=chat_id,
                        member_limit=1,
                        expire_date=None
                    )
                    private_link = invite_link.invite_link
            except:
                pass
            
            try:
                member_count = await context.bot.get_chat_members_count(chat_id)
                member_count_formatted = format_number(member_count)
            except:
                member_count_formatted = "0"
            
            admins_list = []
            try:
                admins = await context.bot.get_chat_administrators(chat_id)
                for admin in admins[:5]:
                    if admin.user.username:
                        admins_list.append(f"@{admin.user.username}")
                    else:
                        admins_list.append(admin.user.first_name)
                if len(admins) > 5:
                    admins_list.append(f"... و {len(admins) - 5} نفر دیگه")
            except:
                admins_list = ["نامشخص"]
            
            admins_text = "، ".join(admins_list) if admins_list else "نامشخص"
            
            description = "ندارد"
            if chat.type == "channel":
                try:
                    chat_info = await context.bot.get_chat(chat_id)
                    if chat_info.description:
                        description = chat_info.description[:100] + "..." if len(chat_info.description) > 100 else chat_info.description
                except:
                    pass
            
            report_text = f"""
<b>✅ ربات به {chat_type} اضافه شد!</b>
━━━━━━━━━━━━━━━━━━━

<b>📌 اطلاعات کلی:</b>
• <b>نام:</b> {chat_title}
• <b>نوع:</b> {chat_type}
• <b>🆔 آیدی:</b> <code>{chat_id}</code>
• <b>🔗 لینک عمومی:</b> {chat_link}
• <b>🔒 لینک خصوصی:</b> {private_link}

<b>👥 آمار اعضا:</b>
• <b>تعداد اعضا:</b> {member_count_formatted}

<b>👑 لیست ادمین‌ها:</b>
{admins_text}

<b>📝 توضیحات:</b>
{description}

<b>⏰ زمان ورود:</b> {now_tehran().strftime('%Y/%m/%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━
<i>✅ ربات با موفقیت به {chat_type} اضافه شد!</i>
"""
            
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=report_text,
                    parse_mode='HTML'
                )
                logger.info(f"✅ Bot joined {chat_type}: {chat_title} ({chat_id})")
            except Exception as e:
                logger.error(f"❌ Error sending join report: {e}")

# ============ دکمه برگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context, edit=True)

# ============ دستور start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🚀 ربات مدیریت کانال دیجیاتالی")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print(f"🤖 ربات: {BOT_USERNAME}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        
        application.add_handler(CallbackQueryHandler(setup_channel, pattern="^setup_channel$"))
        application.add_handler(CallbackQueryHandler(setup_post, pattern="^setup_post$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        application.add_handler(CallbackQueryHandler(time_on, pattern="^time_on_"))
        application.add_handler(CallbackQueryHandler(time_off, pattern="^time_off_"))
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_id))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_post_text))
        
        application.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER))
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_TITLE, handle_channel_title_change))
        
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(update_time_every_minute, interval=60, first=10)
            print("✅ ساعت‌شمار فعال شد (هر ۱ دقیقه)")
        
        print("✅ ربات روشن شد!")
        print("💡 برای شروع /start بفرست")
        print("=" * 60)
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
