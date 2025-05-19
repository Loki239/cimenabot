"""
History Handler Module for CinemaBot

This module handles user history and statistics requests, including:
- Displaying search history
- Showing movie view statistics
"""

import logging
import html
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from typing import Optional

from utils.helpers import separator, pluralize_times, format_datetime
from database import Database

router = Router()
db = Database()

# Обработчик команды /history
@router.message(F.text == "/history")
async def show_history(message: Message, db: Optional[Database] = None):
    """
    Show user's search history
    
    Args:
        message: The message object from Telegram
        db: Database instance (injected by middleware)
    """
    # Use global database if middleware didn't provide one
    if db is None:
        db = Database()
        
    # Check if user is None
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return
        
    user_id = message.from_user.id
    logging.info("Запрос истории поиска от %s", user_id)
    
    history = await db.get_search_history(user_id)
    
    if not history:
        await message.answer("У вас пока нет истории поиска.")
        return
    
    response = ["<b>История поиска:</b>"]
    for i, item in enumerate(history, 1):
        query = item["query"]
        timestamp = format_datetime(item["timestamp"])
        response.append(f"{i}. {query} - <i>{timestamp}</i>")
    
    await message.answer("\n".join(response), parse_mode=ParseMode.HTML)

# Обработчик команды /stats
@router.message(F.text == "/stats")
async def show_stats(message: Message, db: Optional[Database] = None):
    """
    Show user's movie statistics
    
    Args:
        message: The message object from Telegram
        db: Database instance (injected by middleware)
    """
    # Use global database if middleware didn't provide one
    if db is None:
        db = Database()
        
    # Check if user is None
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return
        
    user_id = message.from_user.id
    logging.info("Запрос статистики от %s", user_id)
    
    stats = await db.get_movie_stats(user_id)
    
    if not stats:
        await message.answer("У вас пока нет статистики просмотров.")
        return
    
    response = ["<b>Ваша статистика просмотров:</b>"]
    
    for i, movie in enumerate(stats[:10], 1):  # Limit to top 10
        title = movie["title"]
        year = f" ({movie['year']})" if movie.get("year") else ""
        count = movie["count"]
        response.append(f"{i}. {title}{year} - {count} {pluralize_times(count)}")
    
    await message.answer("\n".join(response), parse_mode=ParseMode.HTML) 