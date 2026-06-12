import asyncio
import os
import logging
from datetime import date, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, MenuButtonWebApp
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8810915038:AAGTEeAsFHOMa2CfzlGlruQYDqnPL9Irp2Q")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rukqsdvemwxaxtirfvah.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_muTAclhyFVyHp2FgUwMhvw_u5gNI6GI")
WEBAPP_URL = "https://greenline-tasks.vercel.app"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Кнопка Mini App ─────────────────────────────────────────────────────────

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📋 Открыть Tasks",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]])

# ─── Шаблоны подзадач ────────────────────────────────────────────────────────

SUBTASKS = {
    "out": [
        ("Еврорумы", "Проверить в каких евро есть игрок"),
        ("Еврорумы", "Отписать о выводе из всех еврорумов (список + балансы)"),
        ("Еврорумы", "Сообщение о прекращении + инструкции игроку"),
        ("Еврорумы", "Аудит — запросить и зафиксировать"),
        ("Пинги", "Пинг день 1"),
        ("Пинги", "Пинг день 2"),
        ("Пинги", "Пинг день 3 → передача менеджеру"),
        ("Пинги", "Через 2 дня спросить менеджера"),
        ("Ближайшая среда", "Проверить вывел ли с евро"),
        ("Ближайшая среда", "Полагается ли выплата?"),
        ("Ближайшая среда", "Если да: проверить депозит и вывод из евро"),
        ("Ближайшая среда", "Проверить аванс"),
        ("Ближайшая среда", "Переместить в таблице дохода, обнулить доли"),
    ],
    "euro": [
        ("По каждому руму", "Отписать игроку по выводу"),
        ("По каждому руму", "Пинг день 1"),
        ("По каждому руму", "Пинг день 2"),
        ("По каждому руму", "Вывел из рума"),
        ("По каждому руму", "Оформить в ЛК + скрин в задачу"),
        ("По каждому руму", "Зафиксировать в бух таблице"),
        ("По каждому руму", "Обнулить в таблице саппортов"),
        ("По каждому руму", "Прислал аудит"),
        ("По каждому руму", "Отписать менеджеру"),
    ],
    "dep": [
        ("", "Получить реквизиты от игрока"),
        ("", "Провести депозит"),
        ("", "Зафиксировать в таблице"),
        ("", "Подтвердить игроку + скрин"),
        ("", "Сверить баланс"),
    ],
    "pay": [
        ("", "Запросить реквизиты у игрока"),
        ("", "Сверить с таблицей дохода"),
        ("", "Провести выплату"),
        ("", "Зафиксировать скрин"),
        ("", "Подтвердить игроку"),
    ],
    "cycle": [
        ("Расчёт", "Собрать итоги цикла (профит, РБ, раздачи)"),
        ("Расчёт", "Рассчитать затраты на софт"),
        ("Расчёт", "Рассчитать долю (65%)"),
        ("Расчёт", "Учесть предыдущие циклы"),
        ("Таблицы", "Обновить таблицу дохода"),
        ("Таблицы", "Зафиксировать выплату в еврорумах"),
        ("Таблицы", "Обнулить текущий результат"),
        ("Таблицы", "Переместить вверх по списку"),
        ("Выплаты", "Закрыть Барту (стандартно)"),
        ("Выплаты", "Выплаты по евро"),
        ("Выплаты", "Отправить итоги игроку"),
    ],
    "wed": [
        ("", "Запросить скрины балансов всех еврорумов"),
        ("", "Отметить кто прислал"),
        ("", "Зафиксировать балансы в таблице"),
        ("", "Проверить аудиты"),
        ("", "Сверить руки"),
        ("", "Выплаты по тем кто вышел"),
    ],
    "question": [
        ("", "Прочитать вопрос"),
        ("", "Ответить в комментарии"),
        ("", "Передать обратно помощнице"),
    ],
}

async def create_task(template, player, title, assignee="asema", due=None, cyclic=False):
    result = sb.table("tasks").insert({
        "template": template, "player": player, "title": title,
        "assignee": assignee, "status": "new", "due": due,
        "cyclic": cyclic, "note": "",
    }).execute()
    if not result.data:
        return None
    task = result.data[0]
    subs = SUBTASKS.get(template, [])
    if subs:
        rows = [{"task_id": task["id"], "grp": g, "text": t, "done": False, "sort_order": i}
                for i, (g, t) in enumerate(subs)]
        sb.table("subtasks").insert(rows).execute()
    return task

def next_wednesday():
    today = date.today()
    days = (2 - today.weekday()) % 7
    if days == 0:
        days = 7
    return str(today + timedelta(days=days))

# ─── Хендлеры ─────────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Устанавливаем кнопку Menu в виде кнопки открытия Mini App
    await bot.set_chat_menu_button(
        chat_id=message.chat.id,
        menu_button=MenuButtonWebApp(text="📋 Tasks", web_app=WebAppInfo(url=WEBAPP_URL))
    )
    await message.answer(
        "👋 <b>GreenLine Tasks</b>\n\n"
        "Нажми кнопку <b>📋 Tasks</b> слева от поля ввода — откроется доска задач.\n\n"
        "Или создавай задачи командами:\n\n"
        "<code>#out [ник]</code> — аут игрока\n"
        "<code>#euro [ник]</code> — вывод из евро\n"
        "<code>#dep [ник] [рум] [сумма]</code> — депозит\n"
        "<code>#pay [ник] [сумма]</code> — выплата\n"
        "<code>#cycle</code> — закрытие цикла\n"
        "<code>#wed</code> — среда\n"
        "<code>#q [вопрос]</code> — вопрос менеджеру",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

@dp.message(Command("tasks"))
async def cmd_tasks(message: types.Message):
    await message.answer(
        "📋 Открой доску задач:",
        reply_markup=main_keyboard()
    )

@dp.message(F.text)
async def handle_text(message: types.Message):
    text = message.text.strip()

    if text.lower().startswith("#out"):
        parts = text.split(maxsplit=1)
        player = parts[1].strip() if len(parts) > 1 else "unknown"
        task = await create_task("out", player, f"Аут игрока — @{player}", "asema", next_wednesday())
        if task:
            await message.answer(
                f"✅ <b>Задача создана</b>\n\nТип: Аут игрока\nИгрок: <code>@{player}</code>\nСрок: {next_wednesday()} (среда)\nПодзадач: {len(SUBTASKS['out'])}",
                parse_mode="HTML", reply_markup=main_keyboard()
            )
        else:
            await message.answer("❌ Ошибка создания задачи.")

    elif text.lower().startswith("#euro"):
        parts = text.split(maxsplit=1)
        player = parts[1].strip() if len(parts) > 1 else "unknown"
        due = str(date.today() + timedelta(days=1))
        task = await create_task("euro", player, f"Вывод из Евро — @{player}", "asema", due)
        if task:
            await message.answer(
                f"✅ <b>Задача создана</b>\n\nТип: Вывод из Евро\nИгрок: <code>@{player}</code>",
                parse_mode="HTML", reply_markup=main_keyboard()
            )
        else:
            await message.answer("❌ Ошибка создания задачи.")

    elif text.lower().startswith("#dep"):
        parts = text.split(maxsplit=3)
        player = parts[1] if len(parts) > 1 else "unknown"
        room = parts[2] if len(parts) > 2 else "?"
        amount = parts[3] if len(parts) > 3 else "?"
        task = await create_task("dep", player, f"Депозит @{player} — {room} {amount}", "asema", str(date.today()))
        if task:
            await message.answer(
                f"✅ <b>Задача создана</b>\n\nДепозит: <code>@{player}</code> / {room} / {amount}",
                parse_mode="HTML", reply_markup=main_keyboard()
            )
        else:
            await message.answer("❌ Ошибка создания задачи.")

    elif text.lower().startswith("#pay"):
        parts = text.split(maxsplit=2)
        player = parts[1] if len(parts) > 1 else "unknown"
        amount = parts[2] if len(parts) > 2 else "?"
        task = await create_task("pay", player, f"Выплата @{player} — {amount}", "asema", str(date.today()))
        if task:
            await message.answer(
                f"✅ <b>Задача создана</b>\n\nВыплата: <code>@{player}</code> / {amount}",
                parse_mode="HTML", reply_markup=main_keyboard()
            )
        else:
            await message.answer("❌ Ошибка создания задачи.")

    elif text.lower().startswith("#cycle"):
        task = await create_task("cycle", "", "Закрытие цикла", "manager", str(date.today()))
        if task:
            await message.answer(
                f"✅ <b>Закрытие цикла создано</b>\n\nПодзадач: {len(SUBTASKS['cycle'])}",
                parse_mode="HTML", reply_markup=main_keyboard()
            )
        else:
            await message.answer("❌ Ошибка создания задачи.")

    elif text.lower().startswith("#wed"):
        task = await create_task("wed", "", "Среда — еженедельная", "asema", next_wednesday(), cyclic=True)
        if task:
            await message.answer(
                f"✅ <b>Среда создана</b> 🔄\n\nСрок: {next_wednesday()}",
                parse_mode="HTML", reply_markup=main_keyboard()
            )
        else:
            await message.answer("❌ Ошибка создания задачи.")

    elif text.lower().startswith("#q"):
        parts = text.split(maxsplit=1)
        question = parts[1].strip() if len(parts) > 1 else "Вопрос без текста"
        task = await create_task("question", "", f"Вопрос: {question[:80]}", "manager", str(date.today()))
        if task:
            sender = message.from_user.full_name or "Помощница"
            sb.table("comments").insert({"task_id": task["id"], "author": sender, "text": question}).execute()
            await message.answer(
                f"✅ <b>Вопрос передан менеджеру</b>\n\n<i>{question[:200]}</i>",
                parse_mode="HTML", reply_markup=main_keyboard()
            )
        else:
            await message.answer("❌ Ошибка создания задачи.")

    elif text.startswith("#"):
        await message.answer("❓ Неизвестная команда. Напиши /start чтобы увидеть список.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
