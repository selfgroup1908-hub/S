import logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ChatMemberHandler, filters
import urllib.request
import re
import asyncio
import pytz

# ============ تنظیمات ============
TOKEN = "8724156247:AAH26WN2k9dlI-K3PFgj665F2r1aGRH4OMw"  # توکن جدید بذار
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
channel_posts = {}

# ============ توابع کمکی ============
def now_tehran():
    return datetime.now(TEHRAN_TZ)

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

def clean_title(title):
    return re.sub(r'\s*\d{2}:\d{2}$', '', title)

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

برای تنظیم کانال از گزینه <b>تنظیم کانال</b> استفاده کنید.
"""
    else:
        channel_list = ""
        for idx, (channel_id, data) in enumerate(channels.items(), 1):
            time_status = "✅" if data.get("time_enabled", False) else "❌"
            post_status = "✅" if data.get("post_enabled", False) else "❌"
            channel_list += f"{idx}. {data['name'][:30]}\n"
            channel_list += f"   🕐 ساعت: {time_status} | 📝 پست: {post_status}\n"
            channel_list += f"   🆔 {channel_id}\n\n"
        
        text = f"""
<b>📋 لیست کانال‌ها</b>
━━━━━━━━━━━━━━

<b>📊 تعداد کانال‌ها:</b> {len(channels)}

{channel_list}

<b>راهنما:</b>
✅ = فعال
❌ = غیرفعال
🕐 = ساعت کانال
📝 = پست
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
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

لطفاً یک <b>پست</b> را به ربات <b>فوروارد</b> کنید.

این پست به صورت خودکار در کانال‌های تنظیم شده ارسال خواهد شد.

<b>⚠️ نکته:</b>
• پست را <b>فوروارد</b> کنید (نه کپی)
• ربات باید در کانال <b>ادمین</b> باشد
"""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    waiting_for_post[user_id] = True
    logger.info(f"User {user_id} is waiting for post forward")

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
            
            original_name = clean_title(chat_info.title or "بدون نام")
            
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
                "post_enabled": False,
                "original_name": original_name,
                "post_text": None,
                "post_message_id": None,
                "post_from_chat": None
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
                [
                    InlineKeyboardButton("📝 فعال‌سازی پست", callback_data=f"post_on_{channel_id}"),
                    InlineKeyboardButton("🚫 غیرفعال‌سازی پست", callback_data=f"post_off_{channel_id}")
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

# ============ دریافت فوروارد پست ============
async def handle_post_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message
    
    if user_id not in waiting_for_post:
        return
    
    del waiting_for_post[user_id]
    
    # بررسی اینکه پیام فوروارد شده
    if not message.forward_from and not message.forward_from_chat:
        await update.message.reply_text(
            """
<b>❌ خطا!</b>
━━━━━━━━━━━━━━

لطفاً یک <b>پست را فوروارد</b> کنید (نه کپی).

دوباره روی <b>تنظیم پست</b> کلیک کنید و پست را فوروارد کنید.
""",
            parse_mode='HTML'
        )
        return
    
    # دریافت متن پست
    post_text = message.text or message.caption or ""
    
    # ذخیره پست برای همه کانال‌ها
    for channel_id in channels.keys():
        channels[channel_id]["post_text"] = post_text
        channels[channel_id]["post_message_id"] = message.message_id
        channels[channel_id]["post_from_chat"] = message.chat.id
    
    # ارسال پست به همه کانال‌ها با ساعت
    current_time = get_tehran_time_str()
    await send_post_to_channels(context, current_time)
    
    await update.message.reply_text(
        f"""
<b>✅ پست با موفقیت تنظیم شد!</b>
━━━━━━━━━━━━━━

<b>📝 متن پست:</b>
{post_text[:200]}{'...' if len(post_text) > 200 else ''}

پست به <b>{len(channels)}</b> کانال ارسال شد.
""",
        parse_mode='HTML'
    )
    
    logger.info(f"Post set by user {user_id}")

async def send_post_to_channels(context, time_str):
    """ارسال پست به همه کانال‌ها با ساعت"""
    for channel_id, data in channels.items():
        if data.get("post_enabled", False):
            try:
                post_text = data.get("post_text", "")
                # اضافه کردن ساعت به ابتدای پست
                post_with_time = f"{time_str} {post_text}" if post_text else f"{time_str}"
                
                # اگر پست فوروارد شده بود
                if data.get("post_message_id") and data.get("post_from_chat"):
                    try:
                        await context.bot.forward_message(
                            chat_id=channel_id,
                            from_chat_id=data["post_from_chat"],
                            message_id=data["post_message_id"]
                        )
                    except Exception as e:
                        logger.error(f"Error forwarding post: {e}")
                        # اگر فوروارد نشد، متن رو بفرست
                        await context.bot.send_message(
                            chat_id=channel_id,
                            text=post_with_time
                        )
                else:
                    # ارسال متن با ساعت
                    await context.bot.send_message(
                        chat_id=channel_id,
                        text=post_with_time
                    )
                
                logger.info(f"Post sent to channel {channel_id}")
                
            except Exception as e:
                logger.error(f"Error sending post to {channel_id}: {e}")

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
        original_name = channel_data.get("original_name", channel_data["name"])
        clean = clean_title(original_name)
        new_title = add_time_to_title(clean, current_time)
        
        await context.bot.set_chat_title(
            chat_id=channel_id,
            title=new_title
        )
        
        channel_data["name"] = new_title
        channel_data["original_name"] = clean
        
        await show_channel_settings(update, context, channel_id)
        logger.info(f"Time enabled for channel {channel_id}")
        
    except Exception as e:
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
        original_name = channel_data.get("original_name", channel_data["name"])
        clean = clean_title(original_name)
        
        await context.bot.set_chat_title(
            chat_id=channel_id,
            title=clean
        )
        
        channel_data["name"] = clean
        channel_data["original_name"] = clean
        
        await show_channel_settings(update, context, channel_id)
        logger.info(f"Time disabled for channel {channel_id}")
        
    except Exception as e:
        logger.error(f"Error disabling time for {channel_id}: {e}")

# ============ فعال‌سازی پست ============
async def post_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.split("_")[2]
    
    if channel_id not in channels:
        await query.edit_message_text("❌ کانال پیدا نشد!")
        return
    
    channel_data = channels[channel_id]
    
    # بررسی اینکه پست تنظیم شده یا نه
    if not channel_data.get("post_text"):
        text = """
<b>❌ پستی تنظیم نشده است!</b>
━━━━━━━━━━━━━━

ابتدا از گزینه <b>تنظیم پست</b> یک پست را فوروارد کنید.
"""
        keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    channel_data["post_enabled"] = True
    
    # ارسال پست با ساعت
    current_time = get_tehran_time_str()
    post_text = channel_data.get("post_text", "")
    post_with_time = f"{current_time} {post_text}"
    
    try:
        if channel_data.get("post_message_id") and channel_data.get("post_from_chat"):
            await context.bot.forward_message(
                chat_id=channel_id,
                from_chat_id=channel_data["post_from_chat"],
                message_id=channel_data["post_message_id"]
            )
        else:
            await context.bot.send_message(
                chat_id=channel_id,
                text=post_with_time
            )
        
        await show_channel_settings(update, context, channel_id)
        logger.info(f"Post enabled for channel {channel_id}")
        
    except Exception as e:
        logger.error(f"Error enabling post for {channel_id}: {e}")

# ============ غیرفعال‌سازی پست ============
async def post_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data.split("_")[2]
    
    if channel_id not in channels:
        await query.edit_message_text("❌ کانال پیدا نشد!")
        return
    
    channel_data = channels[channel_id]
    channel_data["post_enabled"] = False
    
    await show_channel_settings(update, context, channel_id)
    logger.info(f"Post disabled for channel {channel_id}")

# ============ نمایش تنظیمات کانال ============
async def show_channel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id):
    channel_data = channels[channel_id]
    
    time_status = "✅ فعال" if channel_data.get("time_enabled", False) else "❌ غیرفعال"
    post_status = "✅ فعال" if channel_data.get("post_enabled", False) else "❌ غیرفعال"
    post_text = channel_data.get("post_text", "تنظیم نشده")[:50]
    
    text = f"""
<b>⚙️ تنظیمات کانال</b>
━━━━━━━━━━━━━━

<b>📌 نام:</b> {channel_data['name']}
<b>🆔 آیدی:</b> <code>{channel_id}</code>
<b>👥 تعداد اعضا:</b> {channel_data['member_count']}

<b>🕐 وضعیت ساعت:</b> {time_status}
<b>📝 وضعیت پست:</b> {post_status}
<b>📄 متن پست:</b> {post_text}{'...' if len(channel_data.get('post_text', '')) > 50 else ''}

برای تغییر هر کدام روی دکمه مربوطه کلیک کنید.
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
    
    try:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

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
    clean = clean_title(current_title)
    
    if channel_data.get("time_enabled", False):
        time_str = get_tehran_time_str()
        new_title = add_time_to_title(clean, time_str)
        
        try:
            if new_title != current_title:
                await context.bot.set_chat_title(
                    chat_id=chat_id,
                    title=new_title
                )
                channel_data["original_name"] = clean
                channel_data["name"] = new_title
                logger.info(f"Re-added time to channel {chat_id}: {new_title}")
        except Exception as e:
            logger.error(f"Error re-adding time to {chat_id}: {e}")
    else:
        channel_data["original_name"] = clean
        channel_data["name"] = current_title

# ============ حذف پیام‌های خدماتی ============
async def delete_service_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    
    if message and message.chat and str(message.chat.id) in channels:
        if message.new_chat_title:
            try:
                await context.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=message.message_id
                )
                logger.info(f"Deleted service message: {message.new_chat_title}")
            except Exception as e:
                logger.error(f"Error deleting service message: {e}")

# ============ به‌روزرسانی دقیق ساعت ============
async def update_time_every_minute(context: ContextTypes.DEFAULT_TYPE):
    try:
        current_time = get_tehran_time_str()
        current_second = now_tehran().second
        
        if current_second == 0:
            for channel_id, channel_data in channels.items():
                if channel_data.get("time_enabled", False):
                    try:
                        chat = await context.bot.get_chat(channel_id)
                        current_title = chat.title or ""
                        
                        clean = clean_title(current_title)
                        new_title = add_time_to_title(clean, current_time)
                        
                        if new_title != current_title:
                            await context.bot.set_chat_title(
                                chat_id=channel_id,
                                title=new_title
                            )
                            channel_data["name"] = new_title
                            channel_data["original_name"] = clean
                            logger.info(f"Updated time for channel {channel_id}: {new_title}")
                            
                    except Exception as e:
                        logger.error(f"Error updating time for {channel_id}: {e}")
    except Exception as e:
        logger.error(f"Error in time update: {e}")

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
            job_queue.run_repeating(update_time_every_minute, interval=1, first=1)
            print("✅ ساعت‌شمار فعال شد (آپدیت دقیق هر دقیقه)")
        
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
