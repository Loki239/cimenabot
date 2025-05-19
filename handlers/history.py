import logging
import html
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

from utils.helpers import separator, pluralize_times, format_datetime
from database import Database

router = Router()
db = Database()

# Обработчик команды /history
@router.message(Command("history"))
async def show_history(message: Message):
    logging.info(f"Запрос истории поиска от {message.from_user.id}")
    user_id = message.from_user.id
    history = await db.get_search_history(user_id)
    if not history:
        await message.answer("📝 <b>История поиска пуста</b>", parse_mode=ParseMode.HTML)
        return
    history_text = [f"📝 <b>История поиска</b>", separator()]
    for i, item in enumerate(history, 1):
        search_time = format_datetime(item["timestamp"])
        history_text.append(f"{i}. <b>{html.escape(item['query'])}</b> ({search_time})")
    response = "\n".join(history_text)
    await message.answer(response, parse_mode=ParseMode.HTML)

# Обработчик команды /stats
@router.message(Command("stats"))
async def show_stats(message: Message):
    logging.info(f"Запрос статистики от {message.from_user.id}")
    user_id = message.from_user.id
    stats = await db.get_movie_stats(user_id)
    if not stats:
        await message.answer("📊 <b>Статистика просмотров пуста</b>", parse_mode=ParseMode.HTML)
        return
    stats_text = [f"📊 <b>Статистика просмотров</b>", separator()]
    for i, item in enumerate(stats, 1):
        title = html.escape(item["title"])
        year = f" ({item['year']})" if item["year"] else ""
        count = item["count"]
        description = item.get("description", "")
        if description:
            short_desc = html.escape(description[:50] + "..." if len(description) > 50 else description)
            stats_text.append(f"{i}. <b>{title}{year}</b> — {count} {pluralize_times(count)}\n   <i>{short_desc}</i>")
        else:
            stats_text.append(f"{i}. <b>{title}{year}</b> — {count} {pluralize_times(count)}")
    stats_text.append(separator())
    stats_text.append("<i>Чтобы посмотреть полное описание фильма, введите его название</i>")
    response = "\n".join(stats_text)
    await message.answer(response, parse_mode=ParseMode.HTML) 