import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import re
import os

# ============ تنظیمات ============
TOKEN = "8724156247:AAH26WN2k9dlI-K3PFgj665F2r1aGRH4OMw"  # توکن جدید بذار

# زمان تهران (UTC+3:30)
TEHRAN = timedelta(hours=3, minutes=30)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دیکشنری زمان‌بندی‌ها
schedules = {}

# ============ توابع کمکی ============
def now_tehran():
    return datetime.utcnow() + TEHRAN

def get_chat_type(chat):
    if chat.type == "channel":
        return "کانال"
    elif chat.type in ["group", "supergroup"]:
        return "گروه"
    return "ناشناخته"

def is_valid_time(time_str):
    return bool(re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str))

# ============ دستورات اصلی ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام خوشامدگویی با دکمه‌ها"""
    user = update.effective_user
    chat = update.effective_chat
    chat_type = get_chat_type(chat)
    
    text = f"""
✨ **به ربات هوشمند زمان‌بندی خوش آمدید!** ✨

سلام {user.first_name} 👋

من یک ربات **پیشرفته ساعت‌گذاری گروه و کانال** هستم.

📌 **نوع چت فعلی:** {chat_type}

⏰ **دستورات:**
/set_time HH:MM - تنظیم ساعت ارسال
/view - مشاهده زمان‌بندی فعلی
/remove - حذف زمان‌بندی
/status - وضعیت ربات
/help - راهنمای کامل
/start - پیام خوشامد

💡 **نکته:** برای تنظیم زمان از فرمت ۲۴ ساعته استفاده کنید.
"""
    
    keyboard = [
        [
            InlineKeyboardButton("⏰ تنظیم زمان", callback_data="set"),
            InlineKeyboardButton("📋 مشاهده", callback_data="view")
        ],
        [
            InlineKeyboardButton("❌ حذف", callback_data="remove"),
            InlineKeyboardButton("📊 وضعیت", callback_data="status")
        ],
        [
            InlineKeyboardButton("❓ راهنما", callback_data="help")
        ]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای کامل ربات"""
    text = """
📖 **راهنمای کامل ربات**

🔹 **دستورات:**
/start - نمایش پیام خوشامد
/set_time HH:MM - تنظیم ساعت ارسال
/view - مشاهده زمان تنظیم شده
/remove - حذف زمان‌بندی
/status - مشاهده وضعیت ربات
/help - نمایش این راهنما

🔸 **نحوه استفاده:**
1. ربات را به گروه یا کانال خود اضافه کنید
2. با دستور /set_time زمان را تنظیم کنید
3. ربات هر روز در ساعت مشخص پیام ارسال می‌کند

⚠️ **توجه:**
• ربات باید در گروه/کانال ادمین باشد
• زمان به فرمت ۲۴ ساعته وارد شود
• مثال: /set_time 14:30

⏰ **ساعت دیجیاتالی هوشمند**
ربات به صورت خودکار در زمان تعیین شده پیام ارسال می‌کند.
"""
    await update.message.reply_text(text)

async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم زمان ارسال"""
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = get_chat_type(chat)
    
    # بررسی وجود آرگومان
    if not context.args:
        await update.message.reply_text(
            f"⏰ لطفاً زمان را به فرمت HH:MM وارد کنید.\n"
            f"مثال: `/set_time 14:30`\n\n"
            f"📌 نوع چت: {chat_type}",
            parse_mode='Markdown'
        )
        return
    
    time_str = context.args[0]
    
    # اعتبارسنجی زمان
    if not is_valid_time(time_str):
        await update.message.reply_text(
            "❌ **فرمت زمان نامعتبر!**\n\n"
            "لطفاً از فرمت HH:MM استفاده کنید.\n"
            "مثال: 14:30 یا 09:00\n\n"
            "⏰ ساعت باید بین 00:00 تا 23:59 باشد.",
            parse_mode='Markdown'
        )
        return
    
    # ذخیره زمان
    schedules[chat_id] = {
        "time": time_str,
        "enabled": True,
        "chat_type": chat_type,
        "chat_title": chat.title or chat_id
    }
    
    await update.message.reply_text(
        f"✅ **زمان با موفقیت تنظیم شد!**\n\n"
        f"📌 {chat_type}: {chat.title or chat_id}\n"
        f"🕐 ساعت ارسال: `{time_str}`\n"
        f"📊 وضعیت: فعال\n\n"
        f"ربات هر روز در این ساعت پیام ارسال خواهد کرد.",
        parse_mode='Markdown'
    )
    
    logger.info(f"Time set for {chat_id}: {time_str}")

async def view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشاهده زمان‌بندی فعلی"""
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = get_chat_type(chat)
    
    if chat_id not in schedules:
        await update.message.reply_text(
            f"❌ **هیچ زمان‌بندی برای این {chat_type} تنظیم نشده است.**\n\n"
            f"با دستور `/set_time HH:MM` زمان را تنظیم کنید.",
            parse_mode='Markdown'
        )
        return
    
    data = schedules[chat_id]
    status = "✅ فعال" if data["enabled"] else "❌ غیرفعال"
    
    await update.message.reply_text(
        f"📋 **زمان‌بندی فعلی**\n\n"
        f"📌 نوع: {data['chat_type']}\n"
        f"🆔 آیدی: `{chat_id}`\n"
        f"🕐 ساعت: `{data['time']}`\n"
        f"📊 وضعیت: {status}\n\n"
        f"⏰ ساعت دیجیاتالی هوشمند فعال است.",
        parse_mode='Markdown'
    )

async def remove_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف زمان‌بندی"""
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = get_chat_type(chat)
    
    if chat_id not in schedules:
        await update.message.reply_text(
            f"❌ **هیچ زمان‌بندی برای حذف وجود ندارد.**\n\n"
            f"ابتدا با `/set_time` زمان را تنظیم کنید.",
            parse_mode='Markdown'
        )
        return
    
    # حذف زمان‌بندی
    del schedules[chat_id]
    
    await update.message.reply_text(
        f"✅ **زمان‌بندی با موفقیت حذف شد!**\n\n"
        f"📌 {chat_type}: {chat.title or chat_id}\n"
        f"⏰ ساعت دیجیاتالی غیرفعال شد.",
        parse_mode='Markdown'
    )
    
    logger.info(f"Schedule removed for {chat_id}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وضعیت ربات"""
    now = now_tehran()
    total = len(schedules)
    active = sum(1 for s in schedules.values() if s["enabled"])
    
    # لیست زمان‌بندی‌ها
    schedule_list = ""
    if schedules:
        for chat_id, data in list(schedules.items())[:5]:  # حداکثر ۵ تا
            schedule_list += f"• {data['chat_type']}: {data['time']} { '✅' if data['enabled'] else '❌'}\n"
        if len(schedules) > 5:
            schedule_list += f"... و {len(schedules) - 5} مورد دیگر"
    else:
        schedule_list = "هیچ زمان‌بندی فعالی وجود ندارد"
    
    await update.message.reply_text(
        f"📊 **وضعیت ربات ساعت دیجیاتالی**\n\n"
        f"⏰ زمان سرور: `{now.strftime('%H:%M:%S')}`\n"
        f"📅 تاریخ: `{now.strftime('%Y/%m/%d')}`\n\n"
        f"📌 تعداد کل زمان‌بندی‌ها: `{total}`\n"
        f"✅ فعال: `{active}`\n"
        f"❌ غیرفعال: `{total - active}`\n\n"
        f"📋 **لیست زمان‌بندی‌ها:**\n{schedule_list}\n\n"
        f"🟢 ربات به صورت ۲۴/۷ در حال اجراست.",
        parse_mode='Markdown'
    )

# ============ مدیریت دکمه‌ها ============
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "set":
        await query.edit_message_text(
            "⏰ **تنظیم زمان**\n\n"
            "از دستور زیر استفاده کنید:\n"
            "`/set_time HH:MM`\n\n"
            "مثال: `/set_time 18:30`\n"
            "مثال: `/set_time 09:00`\n\n"
            "📌 ساعت به فرمت ۲۴ ساعته وارد شود.",
            parse_mode='Markdown'
        )
    
    elif query.data == "view":
        # ایجاد یک پیام جدید برای مشاهده
        chat = update.effective_chat
        chat_id = str(chat.id)
        
        if chat_id in schedules:
            data = schedules[chat_id]
            status = "✅ فعال" if data["enabled"] else "❌ غیرفعال"
            text = (
                f"📋 **زمان‌بندی فعلی**\n\n"
                f"🕐 ساعت: `{data['time']}`\n"
                f"📊 وضعیت: {status}\n"
                f"📌 نوع: {data['chat_type']}"
            )
        else:
            text = "❌ هیچ زمان‌بندی تنظیم نشده است."
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "remove":
        chat_id = str(update.effective_chat.id)
        if chat_id in schedules:
            del schedules[chat_id]
            await query.edit_message_text("✅ زمان‌بندی با موفقیت حذف شد!")
        else:
            await query.edit_message_text("❌ هیچ زمان‌بندی برای حذف وجود ندارد.")
    
    elif query.data == "status":
        now = now_tehran()
        total = len(schedules)
        active = sum(1 for s in schedules.values() if s["enabled"])
        
        await query.edit_message_text(
            f"📊 **وضعیت ربات**\n\n"
            f"⏰ زمان: `{now.strftime('%H:%M:%S')}`\n"
            f"📅 تاریخ: `{now.strftime('%Y/%m/%d')}`\n\n"
            f"📌 کل تنظیمات: `{total}`\n"
            f"✅ فعال: `{active}`\n"
            f"❌ غیرفعال: `{total - active}`",
            parse_mode='Markdown'
        )
    
    elif query.data == "help":
        await query.edit_message_text(
            "📖 **راهنمای سریع**\n\n"
            "/start - پیام خوشامد\n"
            "/set_time - تنظیم ساعت\n"
            "/view - مشاهده زمان\n"
            "/remove - حذف زمان‌بندی\n"
            "/status - وضعیت ربات\n"
            "/help - راهنمای کامل\n\n"
            "💡 برای اطلاعات بیشتر از /help استفاده کنید."
        )

# ============ ارسال خودکار پیام ============
async def auto_send_messages(context: ContextTypes.DEFAULT_TYPE):
    """ارسال خودکار پیام‌ها در ساعت مشخص"""
    now = now_tehran()
    current_time = now.strftime("%H:%M")
    today = now.strftime("%Y/%m/%d")
    
    logger.info(f"Checking time: {current_time}")
    
    for chat_id, data in list(schedules.items()):
        if data["enabled"] and data["time"] == current_time:
            try:
                # ارسال پیام دیجیاتالی
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⏰ **ساعت دیجیاتالی هوشمند**\n\n"
                         f"🕐 زمان: `{current_time}`\n"
                         f"📅 تاریخ: `{today}`\n"
                         f"📌 نوع: {data['chat_type']}\n\n"
                         f"✨ این پیام به صورت خودکار ارسال شد.\n"
                         f"🔔 ربات ساعت هوشمند دیجیاتالی",
                    parse_mode='Markdown'
                )
                
                logger.info(f"✅ Message sent to {data['chat_type']} {chat_id}")
                
            except Exception as e:
                logger.error(f"❌ Error sending to {chat_id}: {e}")
                
                # اگر خطا بود، غیرفعالش کن تا دوباره تلاش نکنه
                if "chat not found" in str(e) or "bot was blocked" in str(e):
                    data["enabled"] = False
                    logger.warning(f"Disabled schedule for {chat_id}")

# ============ تابع اصلی ============
def main():
    """راه‌اندازی ربات"""
    try:
        print("=" * 50)
        print("🚀 راه‌اندازی ربات ساعت دیجیاتالی هوشمند")
        print("=" * 50)
        print(f"📌 توکن: {TOKEN[:10]}...{TOKEN[-5:]}")
        print(f"⏰ منطقه زمانی: تهران (UTC+3:30)")
        print("=" * 50)
        
        # ساخت اپلیکیشن
        application = Application.builder().token(TOKEN).build()
        
        # اضافه کردن هندلرهای دستورات
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("set_time", set_time))
        application.add_handler(CommandHandler("view", view_schedule))
        application.add_handler(CommandHandler("remove", remove_schedule))
        application.add_handler(CommandHandler("status", status_command))
        
        # هندلر دکمه‌ها
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # تنظیم Job برای ارسال خودکار (هر دقیقه)
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(auto_send_messages, interval=60, first=10)
            print("✅ زمان‌بندی خودکار فعال شد")
        else:
            print("⚠️ JobQueue در دسترس نیست!")
        
        # شروع ربات
        print("✅ ربات با موفقیت راه‌اندازی شد!")
        print("💡 منتظر پیام‌های کاربران هستم...")
        print("=" * 50)
        print()
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی: {e}")
        print("\n🔍 راه‌حل‌ها:")
        print("1. توکن را چک کنید (به @BotFather بروید)")
        print("2. اینترنت خود را بررسی کنید")
        print("3. اگر خطا ادامه داشت، توکن را ریست کنید")

if __name__ == "__main__":
    main()
