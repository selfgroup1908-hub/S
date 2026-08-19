import logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import urllib.request
import json

# ============ تنظیمات ============
TOKEN = "8724156247:AAH26WN2k9dlI-K3PFgj665F2r1aGRH4OMw"  # توکن جدید بذار

# زمان تهران (UTC+3:30)
TEHRAN_OFFSET = timedelta(hours=3, minutes=30)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دیکشنری زمان‌بندی‌ها
schedules = {}
user_data = {}  # ذخیره اطلاعات کاربران

# ============ توابع کمکی ============
def now_tehran():
    return datetime.now(timezone.utc) + TEHRAN_OFFSET

def get_chat_type(chat):
    if chat.type == "channel":
        return "📢 کانال"
    elif chat.type in ["group", "supergroup"]:
        return "👥 گروه"
    return "📌 ناشناخته"

def get_status_emoji(enabled):
    return "✅" if enabled else "❌"

def get_status_text(enabled):
    return "فعال" if enabled else "غیرفعال"

def delete_webhook():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        with urllib.request.urlopen(url) as response:
            return True
    except:
        return False

def format_number(num):
    return f"{num:,}".replace(",", ".")

# ============ دکمه‌ها ============
def back_button():
    return InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back")

def main_menu_keyboard():
    return [
        [
            InlineKeyboardButton("⏰ تنظیم زمان", callback_data="set_time"),
            InlineKeyboardButton("📋 مشاهده زمان", callback_data="view_time")
        ],
        [
            InlineKeyboardButton("✏️ ویرایش زمان", callback_data="edit_time"),
            InlineKeyboardButton("🗑 حذف زمان‌بندی", callback_data="remove_time")
        ],
        [
            InlineKeyboardButton("📊 داشبورد مدیریت", callback_data="dashboard"),
            InlineKeyboardButton("⚙️ تنظیمات پیشرفته", callback_data="settings")
        ],
        [
            InlineKeyboardButton("❓ راهنمای استفاده", callback_data="help_guide")
        ]
    ]

# ============ منوی اصلی ============
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    chat = update.effective_chat
    chat_type = get_chat_type(chat)
    
    # ثبت کاربر
    user_id = str(user.id)
    if user_id not in user_data:
        user_data[user_id] = {
            "first_seen": now_tehran().strftime("%Y/%m/%d %H:%M"),
            "username": user.username or "ندارد",
            "first_name": user.first_name
        }
    
    text = f"""
<b>🤖 ربات هوشمند زمان‌بندی دیجیاتالی</b>
━━━━━━━━━━━━━━━━━━━

<b>👋 خوش آمدید</b> {user.first_name} عزیز

من یک <b>ربات حرفه‌ای</b> برای <b>مدیریت زمان‌بندی</b> گروه‌ها و کانال‌ها هستم.

<b>📌 اطلاعات جلسه:</b>
• <b>نوع چت:</b> {chat_type}
• <b>تاریخ:</b> {now_tehran().strftime('%Y/%m/%d')}
• <b>زمان:</b> {now_tehran().strftime('%H:%M:%S')}

<b>⚙️ قابلیت‌های ربات:</b>
🎯 تنظیم زمان ارسال خودکار
📊 آمار و گزارش‌گیری دقیق
🔄 ویرایش زمان‌بندی
🗑 حذف آسان زمان‌بندی

<b>💡 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:</b>
"""
    
    if edit:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(main_menu_keyboard()),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(main_menu_keyboard()),
            parse_mode='HTML'
        )

# ============ دستور start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

# ============ تنظیم زمان (دکمه‌ای) ============
async def set_time_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
<b>⏰ تنظیم زمان ارسال خودکار</b>
━━━━━━━━━━━━━━━━━━━

<b>مرحله ۱:</b> لطفاً <b>ساعت</b> مورد نظر را انتخاب کنید:

📌 <i>زمان به فرمت ۲۴ ساعته</i>
"""
    
    keyboard = []
    row = []
    for hour in range(0, 24):
        row.append(InlineKeyboardButton(f"{hour:02d}", callback_data=f"hour_{hour}"))
        if len(row) == 6:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([back_button()])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def select_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    hour = int(query.data.split("_")[1])
    context.user_data['selected_hour'] = hour
    
    text = f"""
<b>⏰ تنظیم زمان ارسال خودکار</b>
━━━━━━━━━━━━━━━━━━━

<b>مرحله ۲:</b> ساعت <b>{hour:02d}</b> انتخاب شد

لطفاً <b>دقیقه</b> مورد نظر را انتخاب کنید:

📌 <i>فواصل ۵ دقیقه‌ای</i>
"""
    
    keyboard = []
    row = []
    for minute in range(0, 60, 5):
        row.append(InlineKeyboardButton(f"{minute:02d}", callback_data=f"minute_{hour}_{minute}"))
        if len(row) == 6:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به ساعت", callback_data="set_time")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def select_minute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    hour = int(parts[1])
    minute = int(parts[2])
    time_str = f"{hour:02d}:{minute:02d}"
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = get_chat_type(chat)
    
    # ذخیره زمان
    schedules[chat_id] = {
        "time": time_str,
        "enabled": True,
        "chat_type": chat_type,
        "chat_title": chat.title or chat_id,
        "created_at": now_tehran().strftime("%Y/%m/%d %H:%M"),
        "message_count": 0
    }
    
    text = f"""
<b>✅ زمان با موفقیت تنظیم شد</b>
━━━━━━━━━━━━━━━━━━━

<b>📌 اطلاعات زمان‌بندی:</b>
• <b>نوع:</b> {chat_type}
• <b>ساعت ارسال:</b> <code>{time_str}</code>
• <b>وضعیت:</b> ✅ <b>فعال</b>
• <b>تاریخ تنظیم:</b> {now_tehran().strftime('%Y/%m/%d')}

ربات هر روز در ساعت <b>{time_str}</b> پیام ارسال خواهد کرد.

💡 <i>برای ویرایش زمان از گزینه "ویرایش زمان" استفاده کنید.</i>
"""
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    logger.info(f"Time set for {chat_id}: {time_str}")

# ============ مشاهده زمان ============
async def view_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = get_chat_type(chat)
    
    if chat_id not in schedules:
        text = f"""
<b>📋 وضعیت زمان‌بندی</b>
━━━━━━━━━━━━━━━━━━━

<b>❌ هیچ زمان‌بندی</b> برای این {chat_type} تنظیم نشده است.

برای تنظیم زمان از گزینه <b>تنظیم زمان</b> استفاده کنید.
"""
    else:
        data = schedules[chat_id]
        status = f"{get_status_emoji(data['enabled'])} <b>{get_status_text(data['enabled'])}</b>"
        
        text = f"""
<b>📋 جزئیات زمان‌بندی</b>
━━━━━━━━━━━━━━━━━━━

<b>📌 نوع:</b> {data['chat_type']}
<b>🕐 ساعت ارسال:</b> <code>{data['time']}</code>
<b>📊 وضعیت:</b> {status}
<b>📅 تاریخ تنظیم:</b> {data.get('created_at', 'نامشخص')}
<b>📨 تعداد پیام‌های ارسال شده:</b> {data.get('message_count', 0)}

ربات هر روز در ساعت <b>{data['time']}</b> پیام ارسال می‌کند.
"""
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ ویرایش زمان ============
async def edit_time_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id not in schedules:
        text = """
<b>✏️ ویرایش زمان</b>
━━━━━━━━━━━━━━━━━━━

<b>❌ هیچ زمان‌بندی برای ویرایش وجود ندارد.</b>

ابتدا با گزینه <b>تنظیم زمان</b> یک زمان‌بندی ایجاد کنید.
"""
        keyboard = [[back_button()]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    current_time = schedules[chat_id]['time']
    
    text = f"""
<b>✏️ ویرایش زمان ارسال</b>
━━━━━━━━━━━━━━━━━━━

<b>زمان فعلی:</b> <code>{current_time}</code>

لطفاً <b>ساعت جدید</b> را انتخاب کنید:
"""
    
    keyboard = []
    row = []
    for hour in range(0, 24):
        row.append(InlineKeyboardButton(f"{hour:02d}", callback_data=f"edit_hour_{hour}"))
        if len(row) == 6:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([back_button()])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def edit_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    hour = int(query.data.split("_")[2])
    context.user_data['edit_hour'] = hour
    
    text = f"""
<b>✏️ ویرایش زمان ارسال</b>
━━━━━━━━━━━━━━━━━━━

<b>ساعت جدید:</b> {hour:02d}

لطفاً <b>دقیقه جدید</b> را انتخاب کنید:
"""
    
    keyboard = []
    row = []
    for minute in range(0, 60, 5):
        row.append(InlineKeyboardButton(f"{minute:02d}", callback_data=f"edit_minute_{hour}_{minute}"))
        if len(row) == 6:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="edit_time")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def edit_minute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    hour = int(parts[2])
    minute = int(parts[3])
    new_time = f"{hour:02d}:{minute:02d}"
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id in schedules:
        old_time = schedules[chat_id]['time']
        schedules[chat_id]['time'] = new_time
        
        text = f"""
<b>✅ زمان با موفقیت ویرایش شد</b>
━━━━━━━━━━━━━━━━━━━

<b>🕐 زمان قبلی:</b> <code>{old_time}</code>
<b>🕐 زمان جدید:</b> <code>{new_time}</code>

ربات از این پس در ساعت <b>{new_time}</b> پیام ارسال خواهد کرد.
"""
    else:
        text = "<b>❌ خطا!</b> زمان‌بندی یافت نشد."
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    logger.info(f"Time edited for {chat_id}: {old_time} -> {new_time}")

# ============ حذف زمان‌بندی با تایید ============
async def remove_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = get_chat_type(chat)
    
    if chat_id not in schedules:
        text = f"""
<b>🗑 حذف زمان‌بندی</b>
━━━━━━━━━━━━━━━━━━━

<b>❌ هیچ زمان‌بندی</b> برای این {chat_type} وجود ندارد.
"""
        keyboard = [[back_button()]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    
    data = schedules[chat_id]
    
    text = f"""
<b>⚠️ تایید حذف زمان‌بندی</b>
━━━━━━━━━━━━━━━━━━━

<b>📌 نوع:</b> {data['chat_type']}
<b>🕐 ساعت:</b> <code>{data['time']}</code>
<b>📊 وضعیت:</b> {get_status_emoji(data['enabled'])} {get_status_text(data['enabled'])}

<b>❗️ آیا از حذف این زمان‌بندی اطمینان دارید؟</b>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ بله، حذف کن", callback_data="confirm_remove"),
            InlineKeyboardButton("❌ انصراف", callback_data="back")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def confirm_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = get_chat_type(chat)
    
    if chat_id in schedules:
        data = schedules[chat_id]
        del schedules[chat_id]
        
        text = f"""
<b>✅ زمان‌بندی با موفقیت حذف شد</b>
━━━━━━━━━━━━━━━━━━━

<b>📌 نوع:</b> {data['chat_type']}
<b>🕐 ساعت حذف شده:</b> <code>{data['time']}</code>

زمان‌بندی این {chat_type} <b>غیرفعال</b> شد.
"""
        logger.info(f"Schedule removed for {chat_id}")
    else:
        text = "<b>❌ خطا!</b> زمان‌بندی یافت نشد."
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ داشبورد مدیریت ============
async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    now = now_tehran()
    total = len(schedules)
    active = sum(1 for s in schedules.values() if s["enabled"])
    total_messages = sum(s.get('message_count', 0) for s in schedules.values())
    
    # لیست زمان‌بندی‌ها
    schedule_list = ""
    if schedules:
        for idx, (chat_id, data) in enumerate(list(schedules.items())[:10], 1):
            status_icon = get_status_emoji(data['enabled'])
            schedule_list += f"{idx}. {data['chat_type']} → <code>{data['time']}</code> {status_icon}\n"
        if len(schedules) > 10:
            schedule_list += f"\n... و {len(schedules) - 10} مورد دیگر"
    else:
        schedule_list = "<i>هیچ زمان‌بندی فعالی وجود ندارد</i>"
    
    text = f"""
<b>📊 داشبورد مدیریت</b>
━━━━━━━━━━━━━━━━━━━

<b>⏰ اطلاعات سیستم:</b>
• <b>زمان سرور:</b> <code>{now.strftime('%H:%M:%S')}</code>
• <b>تاریخ:</b> <code>{now.strftime('%Y/%m/%d')}</code>

<b>📈 آمار کلی:</b>
• <b>کل زمان‌بندی‌ها:</b> {format_number(total)}
• <b>فعال:</b> {format_number(active)}
• <b>غیرفعال:</b> {format_number(total - active)}
• <b>پیام‌های ارسال شده:</b> {format_number(total_messages)}

<b>📋 لیست زمان‌بندی‌ها:</b>
{schedule_list}

<b>🟢 وضعیت:</b> سیستم در حال اجرا
"""
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ تنظیمات پیشرفته ============
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id in schedules:
        current_status = schedules[chat_id]['enabled']
        status_text = "غیرفعال" if current_status else "فعال"
        action_text = "غیرفعال" if current_status else "فعال"
    else:
        status_text = "زمان‌بندی تنظیم نشده"
        action_text = "تنظیم زمان"
    
    text = f"""
<b>⚙️ تنظیمات پیشرفته</b>
━━━━━━━━━━━━━━━━━━━

<b>📌 وضعیت فعلی:</b> {status_text}

<b>🔧 گزینه‌های موجود:</b>
• فعال/غیرفعال‌سازی زمان‌بندی
• تغییر زمان ارسال
• حذف زمان‌بندی
"""
    
    keyboard = []
    
    if chat_id in schedules:
        current = schedules[chat_id]['enabled']
        toggle_text = "⏸ غیرفعال‌سازی" if current else "▶️ فعال‌سازی"
        keyboard.append([InlineKeyboardButton(toggle_text, callback_data="toggle_status")])
    
    keyboard.append([InlineKeyboardButton("🔄 بازنشانی همه تنظیمات", callback_data="reset_all")])
    keyboard.append([back_button()])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def toggle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id in schedules:
        schedules[chat_id]['enabled'] = not schedules[chat_id]['enabled']
        status = schedules[chat_id]['enabled']
        status_text = "فعال" if status else "غیرفعال"
        emoji = get_status_emoji(status)
        
        text = f"""
<b>✅ وضعیت زمان‌بندی تغییر کرد</b>
━━━━━━━━━━━━━━━━━━━

<b>📌 وضعیت جدید:</b> {emoji} <b>{status_text}</b>
<b>🕐 ساعت:</b> <code>{schedules[chat_id]['time']}</code>

ربات در حالت <b>{status_text}</b> قرار گرفت.
"""
    else:
        text = "<b>❌ خطا!</b> زمان‌بندی یافت نشد."
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    if chat_id in schedules:
        del schedules[chat_id]
        text = """
<b>🔄 همه تنظیمات بازنشانی شد</b>
━━━━━━━━━━━━━━━━━━━

✅ تمام زمان‌بندی‌های این چت حذف شد.

برای تنظیم مجدد از گزینه <b>تنظیم زمان</b> استفاده کنید.
"""
    else:
        text = "<b>❌ هیچ تنظیماتی برای بازنشانی وجود ندارد.</b>"
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ راهنما ============
async def help_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
<b>❓ راهنمای جامع استفاده از ربات</b>
━━━━━━━━━━━━━━━━━━━

<b>🔹 نحوه کار:</b>
۱. ربات را به <b>گروه</b> یا <b>کانال</b> خود اضافه کنید
۲. از گزینه <b>تنظیم زمان</b> استفاده کنید
۳. ربات هر روز در ساعت مشخص پیام ارسال می‌کند

<b>🔸 امکانات:</b>
✅ تنظیم زمان ارسال خودکار (دکمه‌ای)
✅ مشاهده زمان‌بندی فعلی
✅ ویرایش زمان ارسال
✅ حذف زمان‌بندی با تایید
✅ داشبورد مدیریت کامل
✅ فعال/غیرفعال‌سازی زمان‌بندی

<b>🔹 نکات مهم:</b>
• ربات باید در گروه/کانال <b>ادمین</b> باشد
• زمان به <b>فرمت ۲۴ ساعته</b> انتخاب می‌شود
• امکان ویرایش و حذف زمان‌بندی وجود دارد

<b>⚡️ پشتیبانی:</b>
در صورت بروز مشکل با ادمین تماس بگیرید.
"""
    
    keyboard = [[back_button()]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# ============ دکمه برگشت ============
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await main_menu(update, context, edit=True)

# ============ ارسال خودکار ============
async def auto_send_messages(context: ContextTypes.DEFAULT_TYPE):
    try:
        now = now_tehran()
        current_time = now.strftime("%H:%M")
        today = now.strftime("%Y/%m/%d")
        weekday = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یک‌شنبه"][now.weekday()]
        
        for chat_id, data in list(schedules.items()):
            if data["enabled"] and data["time"] == current_time:
                try:
                    # به‌روزرسانی تعداد پیام‌ها
                    data['message_count'] = data.get('message_count', 0) + 1
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"""
<b>⏰ اعلان ساعت دیجیاتالی</b>
━━━━━━━━━━━━━━━━━━━

<b>🕐 زمان:</b> <code>{current_time}</code>
<b>📅 تاریخ:</b> <code>{today}</code>
<b>📆 روز هفته:</b> {weekday}
<b>📌 نوع:</b> {data['chat_type']}

<i>این پیام به صورت خودکار توسط ربات هوشمند ارسال شده است.</i>

━━━━━━━━━━━━━━━━━━━
<b>📊 آمار:</b>
• تعداد ارسال‌ها: {data['message_count']}
""",
                        parse_mode='HTML'
                    )
                    logger.info(f"✅ Auto message sent to {chat_id} at {current_time}")
                except Exception as e:
                    logger.error(f"❌ Error sending to {chat_id}: {e}")
                    if "chat not found" in str(e) or "bot was blocked" in str(e):
                        data["enabled"] = False
                        logger.warning(f"⚠️ Disabled schedule for {chat_id}")
    except Exception as e:
        logger.error(f"Error in auto_send: {e}")

# ============ اجرا ============
def main():
    try:
        delete_webhook()
        
        print("=" * 60)
        print("🚀 راه‌اندازی ربات حرفه‌ای ساعت دیجیاتالی")
        print("=" * 60)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print(f"⏰ زمان سرور: {now_tehran().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        application = Application.builder().token(TOKEN).build()
        
        # دستورات
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_guide))
        
        # دکمه‌های منو
        application.add_handler(CallbackQueryHandler(set_time_menu, pattern="^set_time$"))
        application.add_handler(CallbackQueryHandler(view_time, pattern="^view_time$"))
        application.add_handler(CallbackQueryHandler(edit_time_menu, pattern="^edit_time$"))
        application.add_handler(CallbackQueryHandler(remove_time, pattern="^remove_time$"))
        application.add_handler(CallbackQueryHandler(dashboard, pattern="^dashboard$"))
        application.add_handler(CallbackQueryHandler(settings, pattern="^settings$"))
        application.add_handler(CallbackQueryHandler(help_guide, pattern="^help_guide$"))
        
        # دکمه‌های تنظیم زمان
        application.add_handler(CallbackQueryHandler(select_hour, pattern="^hour_"))
        application.add_handler(CallbackQueryHandler(select_minute, pattern="^minute_"))
        
        # دکمه‌های ویرایش
        application.add_handler(CallbackQueryHandler(edit_hour, pattern="^edit_hour_"))
        application.add_handler(CallbackQueryHandler(edit_minute, pattern="^edit_minute_"))
        
        # دکمه‌های دیگر
        application.add_handler(CallbackQueryHandler(confirm_remove, pattern="^confirm_remove$"))
        application.add_handler(CallbackQueryHandler(toggle_status, pattern="^toggle_status$"))
        application.add_handler(CallbackQueryHandler(reset_all, pattern="^reset_all$"))
        application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
        
        # JobQueue
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(auto_send_messages, interval=60, first=10)
            print("✅ زمان‌بندی خودکار فعال شد")
        
        print("✅ ربات با موفقیت راه‌اندازی شد!")
        print("💡 برای تست به ربات /start بفرستید")
        print("=" * 60)
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی: {e}")

if __name__ == "__main__":
    main()
