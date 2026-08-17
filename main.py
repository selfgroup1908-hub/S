import asyncio
from datetime import datetime
from pytz import timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import re

# ============ توکن شما ============
TOKEN = "8724156247:AAH26WN2k9dlI-K3PFgj665F2r1aGRH4OMw"
TEHRAN_TZ = timezone('Asia/Tehran')

# دیکشنری ساده برای ذخیره زمان‌بندی‌ها
schedules = {"groups": {}, "channels": {}}

# ============ دستورات ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    chat_type = "کانال" if chat.type == "channel" else "گروه"
    
    text = f"""
✨ **به ربات هوشمند زمان‌بندی خوش آمدید!** ✨

سلام {user.first_name} 👋

من یه **ربات پیشرفته ساعت‌گذاری گروه و کانال** هستم.

⏰ **دستورات:**
/set_time HH:MM - تنظیم ساعت ارسال
/view_schedule - مشاهده زمان‌بندی
/remove_schedule - حذف زمان‌بندی
/status - وضعیت ربات

📌 نوع چت فعلی: {chat_type}
"""
    keyboard = [
        [InlineKeyboardButton("⏰ تنظیم زمان", callback_data="set_time")],
        [InlineKeyboardButton("📋 برنامه", callback_data="view_schedule")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = "channels" if chat.type == "channel" else "groups"
    
    if not context.args:
        await update.message.reply_text("⏰ لطفاً زمان را وارد کنید: `/set_time 14:30`", parse_mode='Markdown')
        return
    
    time_str = context.args[0]
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
        await update.message.reply_text("❌ فرمت اشتباه! از HH:MM استفاده کنید.")
        return
    
    schedules[chat_type][chat_id] = {"time": time_str, "enabled": True}
    await update.message.reply_text(f"✅ زمان {time_str} تنظیم شد!")

async def view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = "channels" if chat.type == "channel" else "groups"
    
    if chat_id in schedules[chat_type]:
        s = schedules[chat_type][chat_id]
        await update.message.reply_text(f"📋 زمان فعلی: {s['time']}\nوضعیت: {'✅ فعال' if s['enabled'] else '❌ غیرفعال'}")
    else:
        await update.message.reply_text("❌ زمانی تنظیم نشده.")

async def remove_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_type = "channels" if chat.type == "channel" else "groups"
    
    if chat_id in schedules[chat_type]:
        del schedules[chat_type][chat_id]
        await update.message.reply_text("✅ زمان‌بندی حذف شد.")
    else:
        await update.message.reply_text("❌ چیزی برای حذف نیست.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 وضعیت ربات\n"
        f"گروه‌ها: {len(schedules['groups'])}\n"
        f"کانال‌ها: {len(schedules['channels'])}"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("از دستور /set_time استفاده کنید.")

async def send_messages(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TEHRAN_TZ).strftime("%H:%M")
    
    for chat_id, s in schedules["groups"].items():
        if s["enabled"] and s["time"] == now:
            await context.bot.send_message(chat_id, f"⏰ ساعت {now} - پیام خودکار گروه")
    
    for chat_id, s in schedules["channels"].items():
        if s["enabled"] and s["time"] == now:
            await context.bot.send_message(chat_id, f"📢 ساعت {now} - پست خودکار کانال")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set_time", set_time))
    app.add_handler(CommandHandler("view_schedule", view_schedule))
    app.add_handler(CommandHandler("remove_schedule", remove_schedule))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    app.job_queue.run_repeating(send_messages, interval=60, first=10)
    
    print("✅ ربات روشن شد! (با توکن شما)")
    app.run_polling()

if __name__ == "__main__":
    main()
