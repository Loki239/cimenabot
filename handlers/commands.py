import logging
import html
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.formatting import Text
from aiogram.enums import ParseMode

from utils.helpers import separator, get_source_status
from utils.cache import clear_cache

router = Router()

# Global variables for settings (will be moved to config in the future)
links_on = True  # This refers to Rutube search
kp_on = True

# Обработчик команды /start
@router.message(CommandStart())
async def send_welcome(message: Message):
    logging.info(f"Получена команда /start от {message.from_user.id}")
    response = (
        f"🎬 <b>Кино-бот приветствует вас!</b>\n"
        f"{separator()}"
        f"Отправьте мне название фильма или сериала,\n"
        f"и я найду информацию и прямые ссылки на просмотр в Rutube.\n"
        f"{separator('Доступные команды')}"
        f"/help - Показать справку\n"
        f"/settings - Настройки поиска\n"
        f"/history - История поиска\n"
        f"/stats - Статистика просмотров"
    )
    logging.info(f"HTML ответа приветствия: {response}")
    await message.answer(response, parse_mode=ParseMode.HTML)

# Обработчик команды /help
@router.message(Command("help"))
async def send_help(message: Message):
    logging.info(f"Получена команда /help от {message.from_user.id}")
    response = Text(
        "🛠 <b>Справка по использованию бота</b>",
        separator(),
        "Просто отправьте название фильма или сериала,",
        "и бот найдет информацию о нем и ссылки на просмотр в Rutube.",
        separator("Команды"),
        "/start - Начальное приветствие",
        "/turn_links - Вкл/выкл поиск ссылок (Rutube)",
        "/turn_kp - Вкл/выкл поиск в Кинопоиске",
        "/settings - Текущие настройки",
        "/history - История поиска",
        "/stats - Статистика просмотров",
        separator("Кэш"),
        "/clear_cache - Очистить весь кэш",
        "/clear_posters - Очистить кэш постеров",
        "/clear_movie_data - Очистить кэш данных о фильмах",
        "/clear_rutube - Очистить кэш ссылок Rutube",
        separator("Статус поиска"),
        get_source_status(links_on, kp_on)
    ).as_html()
    await message.answer(response, parse_mode=ParseMode.HTML)

# Обработчики команд включения/выключения источников
@router.message(Command("turn_links"))
async def toggle_links(message: Message):
    global links_on
    links_on = not links_on
    status = "включен" if links_on else "выключен"
    logging.info(f"Поиск ссылок (Rutube) {status} пользователем {message.from_user.id}")
    await message.answer(f"🔘 Поиск ссылок (Rutube) теперь <b>{status}</b>", parse_mode=ParseMode.HTML)

@router.message(Command("turn_kp"))
async def toggle_kp(message: Message):
    global kp_on
    kp_on = not kp_on
    status = "включен" if kp_on else "выключен"
    logging.info(f"Поиск в Кинопоиске {status} пользователем {message.from_user.id}")
    await message.answer(f"🔘 Поиск в Кинопоиске теперь <b>{status}</b>", parse_mode=ParseMode.HTML)

# Обработчик команды /settings
@router.message(Command("settings"))
async def show_settings(message: Message):
    logging.info(f"Запрос настроек от {message.from_user.id}")
    response = (
        f"⚙ <b>Текущие настройки поиска</b>\n"
        f"{separator()}"
        f"{get_source_status(links_on, kp_on)}\n"
        f"{separator()}"
        f"Изменить настройки:\n"
        f"/turn_links - Вкл/выкл поиск ссылок (Rutube)\n"
        f"/turn_kp - Вкл/выкл Кинопоиск"
    )
    logging.info(f"HTML ответа настроек: {response}")
    await message.answer(response, parse_mode=ParseMode.HTML)

# Command handlers for cache clearing
@router.message(Command("clear_cache"))
async def cmd_clear_cache(message: Message):
    """Clear all cache"""
    logging.info(f"User {message.from_user.id} requested to clear all cache")
    
    # Send a "working" message
    wait_msg = await message.answer("🧹 Очистка кэша...")
    
    # Clear the cache
    result = await clear_cache(clear_all=True)
    
    # Delete the wait message and send the result
    await wait_msg.delete()
    await message.answer(f"🧹 Кэш очищен\n\n{result}")

@router.message(Command("clear_posters"))
async def cmd_clear_posters(message: Message):
    """Clear only poster cache"""
    logging.info(f"User {message.from_user.id} requested to clear poster cache")
    
    # Send a "working" message
    wait_msg = await message.answer("🧹 Очистка кэша постеров...")
    
    # Clear the poster cache
    result = await clear_cache(clear_all=False, clear_posters=True)
    
    # Delete the wait message and send the result
    await wait_msg.delete()
    await message.answer(f"🧹 Кэш постеров очищен\n\n{result}")

@router.message(Command("clear_movie_data"))
async def cmd_clear_movie_data(message: Message):
    """Clear only movie data cache"""
    logging.info(f"User {message.from_user.id} requested to clear movie data cache")
    
    # Send a "working" message
    wait_msg = await message.answer("🧹 Очистка кэша данных о фильмах...")
    
    # Clear the movie data cache
    result = await clear_cache(clear_all=False, clear_movie_data=True)
    
    # Delete the wait message and send the result
    await wait_msg.delete()
    await message.answer(f"🧹 Кэш данных о фильмах очищен\n\n{result}")

@router.message(Command("clear_rutube"))
async def cmd_clear_rutube(message: Message):
    """Clear only Rutube links cache"""
    logging.info(f"User {message.from_user.id} requested to clear Rutube links cache")
    
    # Send a "working" message
    wait_msg = await message.answer("🧹 Очистка кэша ссылок Rutube...")
    
    # Clear the Rutube links cache
    result = await clear_cache(clear_all=False, clear_rutube=True)
    
    # Delete the wait message and send the result
    await wait_msg.delete()
    await message.answer(f"🧹 Кэш ссылок Rutube очищен\n\n{result}")

# Function to get the current source settings
def get_search_settings():
    return {
        'links_on': links_on,
        'kp_on': kp_on
    } 