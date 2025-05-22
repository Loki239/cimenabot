"""
Command Handlers Module for CinemaBot

This module contains all the command handlers for the Telegram bot,
including basic commands like /start and /help, as well as settings
commands like /turn_links and /turn_kp.
"""

import logging
import html
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.formatting import Text
from aiogram.enums import ParseMode
from typing import Optional, Dict, Any

from utils.helpers import separator, get_source_status
from utils.cache import clear_cache, clear_posters, clear_movie_data, clear_rutube
from database import Database

router = Router()

# Global variables for settings (will be moved to config in the future)
LINKS_ON = True  # This refers to Rutube search
KP_ON = True

def get_search_settings() -> Dict[str, Any]:
    """Return current search settings as a dictionary"""
    return {
        'links_on': LINKS_ON,
        'kp_on': KP_ON
    }

# Обработчик команды /start
@router.message(CommandStart())
async def send_welcome(message: Message):
    """Handle /start command - send welcome message"""
    # Check if user exists
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя")
        return
        
    user_id = message.from_user.id
    logging.info("Команда /start от пользователя %s", user_id)
    
    welcome_message = (
        "🍿 <b>Добро пожаловать в CinemaBot!</b>\n\n"
        "Этот бот поможет вам найти информацию о фильмах и сериалах, а также прямые ссылки для просмотра.\n\n"
        "<b>Как пользоваться:</b>\n"
        "- Просто напишите название фильма или сериала\n"
        "- Используйте /help чтобы увидеть все команды\n"
        "- Используйте /settings чтобы настроить источники поиска"
    )
    
    await message.answer(welcome_message, parse_mode=ParseMode.HTML)

# Обработчик команды /help
@router.message(Command("help"))
async def send_help(message: Message):
    """Handle /help command - show available commands"""
    # Check if user exists
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя")
        return
        
    user_id = message.from_user.id
    logging.info("Команда /help от пользователя %s", user_id)
    
    help_message = (
        "🎬 <b>Команды CinemaBot:</b>\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/settings - Показать текущие настройки\n"
        "/turn_links - Включить/выключить поиск ссылок (Rutube)\n"
        "/turn_kp - Включить/выключить поиск в Кинопоиске\n"
        "/history - Показать историю поиска\n"
        "/stats - Показать статистику просмотров\n"
        "/clear_cache - Очистить весь кэш\n"
        "/clear_posters - Очистить кэш постеров\n"
        "/clear_movie_data - Очистить кэш данных фильмов\n"
        "/clear_rutube - Очистить кэш ссылок Rutube\n\n"
        "<b>Как пользоваться:</b>\n"
        "Просто напишите название фильма или сериала, и бот найдет информацию и ссылки"
    )
    
    await message.answer(help_message, parse_mode=ParseMode.HTML)

# Обработчики команд включения/выключения источников
@router.message(Command("turn_links"))
async def toggle_links(message: Message):
    """Toggle Rutube links search on/off"""
    # Check if user exists
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя")
        return
        
    global LINKS_ON
    LINKS_ON = not LINKS_ON
    
    user_id = message.from_user.id
    logging.info("Поиск ссылок %s пользователем %s", "включен" if LINKS_ON else "выключен", user_id)
    
    status = "включен ✅" if LINKS_ON else "выключен ❌"
    await message.answer(f"Поиск ссылок на Rutube {status}", parse_mode=ParseMode.HTML)

@router.message(Command("turn_kp"))
async def toggle_kp(message: Message):
    """Toggle Kinopoisk search on/off"""
    # Check if user exists
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя")
        return
        
    global KP_ON
    KP_ON = not KP_ON
    
    user_id = message.from_user.id
    logging.info("Поиск на Кинопоиске %s пользователем %s", "включен" if KP_ON else "выключен", user_id)
    
    status = "включен ✅" if KP_ON else "выключен ❌"
    await message.answer(f"Поиск на Кинопоиске {status}", parse_mode=ParseMode.HTML)

# Обработчик команды /settings
@router.message(Command("settings"))
async def show_settings(message: Message):
    """Handle /settings command - show current settings"""
    # Check if user exists
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя")
        return
        
    global LINKS_ON, KP_ON
    
    user_id = message.from_user.id
    logging.info("Команда /settings от пользователя %s", user_id)
    
    settings_text = (
        "⚙️ <b>Настройки поиска:</b>\n\n"
        f"{get_source_status(LINKS_ON, KP_ON)}\n\n"
        "Используйте команды /turn_links и /turn_kp для изменения настроек."
    )
    
    await message.answer(settings_text, parse_mode=ParseMode.HTML)