import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    BufferedInputFile, ReplyKeyboardRemove,
)

from config import BOT_TOKEN, ALLOWED_USERS
from database import (
    init_db, get_by_id, get_by_username, get_by_phone,
    search_by_name, upsert_user, delete_user, count_users, export_all,
)
from security import init_logs, log_search, get_recent_logs, count_searches
from keyboards import main_menu, user_actions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class EditState(StatesGroup):
    waiting_value = State()


def allowed(m: Message) -> bool:
    return m.from_user.id in ALLOWED_USERS


def fmt_user(u: dict) -> str:
    rows = [
        ("🆔 آیدی",      u.get("user_id")),
        ("👤 یوزرنیم",   f"@{u['username']}" if u.get("username") else None),
        ("📛 نام",       u.get("first_name")),
        ("📛 فامیل",     u.get("last_name")),
        ("📱 شماره",     u.get("phone")),
        ("📝 یادداشت",   u.get("note")),
        ("🕒 بروزرسانی", u.get("updated_at")),
    ]
    out = ["<b>✅ اطلاعات پیدا شد</b>\n"]
    for label, val in rows:
        if val:
            out.append(f"{label}: <code>{val}</code>")
    return "\n".join(out)


# ══════════════ /start ══════════════
@dp.message(Command("start"))
async def cmd_start(m: Message):
    if not allowed(m):
        await m.answer("⛔️ دسترسی نداری.")
        return
    await m.answer(
        "👋 سلام!\n\nاز منوی پایین استفاده کن یا دستورات:\n"
        "<code>/id 12345</code>\n"
        "<code>/user @ali</code>\n"
        "<code>/phone +98912...</code>\n"
        "<code>/find ali</code>\n"
        "<code>/add</code> (ریپلای)\n"
        "<code>/export</code>\n"
        "<code>/stats</code>",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# ══════════════ جستجو با آیدی ══════════════
@dp.message(Command("id"))
async def cmd_id(m: Message):
    if not allowed(m):
        return
    p = m.text.split(maxsplit=1)
    if len(p) < 2 or not p[1].isdigit():
        await m.answer("مثال: <code>/id 123456789</code>", parse_mode="HTML")
        return
    uid = int(p[1])
    u = await get_by_id(uid)
    await log_search(m.from_user.id, str(uid), "id", bool(u))
    if u:
        await m.answer(fmt_user(u), parse_mode="HTML",
                       reply_markup=user_actions(uid))
    else:
        await m.answer("❌ پیدا نشد.")


@dp.message(F.text == "🔍 جستجو با آیدی")
async def btn_id(m: Message):
    await m.answer("آیدی عددی رو بفرست:\n<code>/id 123456789</code>",
                   parse_mode="HTML")


# ══════════════ جستجو با یوزرنیم ══════════════
@dp.message(Command("user"))
async def cmd_user(m: Message):
    if not allowed(m):
        return
    p = m.text.split(maxsplit=1)
    if len(p) < 2:
        await m.answer("مثال: <code>/user @ali</code>", parse_mode="HTML")
        return
    u = await get_by_username(p[1])
    await log_search(m.from_user.id, p[1], "username", bool(u))
    if u:
        await m.answer(fmt_user(u), parse_mode="HTML",
                       reply_markup=user_actions(u["user_id"]))
    else:
        await m.answer("❌ پیدا نشد.")


@dp.message(F.text == "👤 جستجو با یوزرنیم")
async def btn_user(m: Message):
    await m.answer("یوزرنیم رو بفرست:\n<code>/user @ali</code>",
                   parse_mode="HTML")


# ══════════════ جستجو با شماره ══════════════
@dp.message(Command("phone"))
async def cmd_phone(m: Message):
    if not allowed(m):
        return
    p = m.text.split(maxsplit=1)
    if len(p) < 2:
        await m.answer("مثال: <code>/phone +989121234567</code>",
                       parse_mode="HTML")
        return
    u = await get_by_phone(p[1])
    await log_search(m.from_user.id, p[1], "phone", bool(u))
    if u:
        await m.answer(fmt_user(u), parse_mode="HTML",
                       reply_markup=user_actions(u["user_id"]))
    else:
        await m.answer("❌ پیدا نشد.")


@dp.message(F.text == "📱 جستجو با شماره")
async def btn_phone(m: Message):
    await m.answer("شماره رو بفرست:\n<code>/phone +98912...</code>",
                   parse_mode="HTML")


# ══════════════ جستجوی نام (FTS) ══════════════
@dp.message(Command("find"))
async def cmd_find(m: Message):
    if not allowed(m):
        return
    p = m.text.split(maxsplit=1)
    if len(p) < 2:
        await m.answer("مثال: <code>/find ali</code>", parse_mode="HTML")
        return
    results = await search_by_name(p[1], limit=10)
    await log_search(m.from_user.id, p[1], "name", bool(results))
    if not results:
        await m.answer("❌ چیزی پیدا نشد.")
        return
    await m.answer(f"🔎 <b>{len(results)}</b> نتیجه:", parse_mode="HTML")
    for u in results:
        await m.answer(fmt_user(u), parse_mode="HTML",
                       reply_markup=user_actions(u["user_id"]))


@dp.message(F.text == "📝 جستجوی نام")
async def btn_find(m: Message):
    await m.answer("بخشی از نام رو بفرست:\n<code>/find ali</code>",
                   parse_mode="HTML")


# ══════════════ افزودن ══════════════
@dp.message(Command("add"))
async def cmd_add(m: Message):
    if not allowed(m):
        return
    if not m.reply_to_message:
        await m.answer("روی پیام کاربر ریپلای کن، بعد /add بزن.")
        return
    t = m.reply_to_message.from_user
    fields = {
        "username":   t.username,
        "first_name": t.first_name,
        "last_name":  t.last_name,
    }
    for token in m.text.split()[1:]:
        if "=" in token:
            k, v = token.split("=", 1)
            fields[k] = v
    await upsert_user(t.id, **fields)
    await m.answer(f"✅ ذخیره شد: <code>{t.id}</code>", parse_mode="HTML")


# ══════════════ ویرایش تعاملی ══════════════
@dp.callback_query(F.data.startswith("edit:"))
async def cb_edit(cq: CallbackQuery, state: FSMContext):
    if cq.from_user.id not in ALLOWED_USERS:
        await cq.answer("⛔️", show_alert=True)
        return
    uid = int(cq.data.split(":")[1])
    await state.update_data(uid=uid)
    await state.set_state(EditState.waiting_value)
    await cq.message.answer(
        f"فرم رو بفرست (هر فیلد با `=`):\n"
        f"<code>phone=+98912... note=مشتری</code>",
        parse_mode="HTML",
    )
    await cq.answer()


@dp.message(EditState.waiting_value)
async def edit_receive(m: Message, state: FSMContext):
    if not allowed(m):
        return
    data = await state.get_data()
    uid = data["uid"]
    fields = {}
    for token in m.text.split():
        if "=" in token:
            k, v = token.split("=", 1)
            fields[k] = v
    if not fields:
        await m.answer("چیزی نفهمیدم. مثال: <code>phone=+98912...</code>",
                       parse_mode="HTML")
        return
    await upsert_user(uid, **fields)
    await state.clear()
    u = await get_by_id(uid)
    await m.answer(f"✅ ویرایش شد.\n\n{fmt_user(u)}", parse_mode="HTML")


# ══════════════ حذف ══════════════
@dp.callback_query(F.data.startswith("del:"))
async def cb_del(cq: CallbackQuery):
    if cq.from_user.id not in ALLOWED_USERS:
        await cq.answer("⛔️", show_alert=True)
        return
    uid = int(cq.data.split(":")[1])
    ok = await delete_user(uid)
    await cq.message.edit_text("🗑 حذف شد." if ok else "❌ پیدا نشد.")
    await cq.answer()


@dp.message(Command("del"))
async def cmd_del(m: Message):
    if not allowed(m):
        return
    p = m.text.split(maxsplit=1)
    if len(p) < 2 or not p[1].isdigit():
        await m.answer("مثال: <code>/del 123456789</code>", parse_mode="HTML")
        return
    ok = await delete_user(int(p[1]))
    await m.answer("🗑 حذف شد." if ok else "❌ پیدا نشد.")


# ══════════════ آمار ══════════════
@dp.message(Command("stats"))
@dp.message(F.text == "📊 آمار")
async def cmd_stats(m: Message):
    if not allowed(m):
        return
    n = await count_users()
    s = await count_searches()
    await m.answer(
        f"📊 <b>آمار</b>\n\n"
        f"👥 کاربران: <b>{n}</b>\n"
        f"🔎 جستجوها: <b>{s}</b>",
        parse_mode="HTML",
    )


# ══════════════ لاگ‌ها ══════════════
@dp.message(Command("logs"))
@dp.message(F.text == "📜 لاگ‌ها")
async def cmd_logs(m: Message):
    if not allowed(m):
        return
    logs = await get_recent_logs(15)
    if not logs:
        await m.answer("خالی.")
        return
    lines = ["<b>📜 آخرین جستجوها:</b>\n"]
    for r in logs:
        mark = "✅" if r["found"] else "❌"
        lines.append(f"{mark} <code>{r['query']}</code> "
                     f"[{r['kind']}] — {r['ts']}")
    await m.answer("\n".join(lines), parse_mode="HTML")


# ══════════════ خروجی Excel ══════════════
@dp.message(Command("export"))
@dp.message(F.text == "📤 خروجی Excel")
async def cmd_export(m: Message):
    if not allowed(m):
        return
    from openpyxl import Workbook
    from io import BytesIO

    rows = await export_all()
    if not rows:
        await m.answer("دیتابیس خالیه.")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "users"
    headers = list(rows[0].keys())
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h) for h in headers])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    fname = f"users_{datetime.now():%Y%m%d_%H%M}.xlsx"
    await m.answer_document(
        BufferedInputFile(buf.read(), filename=fname),
        caption=f"📤 {len(rows)} رکورد",
    )


# ══════════════ main ══════════════
async def main():
    await init_db()
    await init_logs()
    print("🤖 Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
