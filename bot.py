import asyncio
import aiohttp
import logging
import html
import os
import signal
import sys
import re
import urllib.parse
import random
import json
import time
import os.path
import hashlib
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, URLInputFile, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.utils.formatting import Text
from aiogram.enums import ParseMode
from datetime import datetime, timedelta
from database import Database
from PIL import Image, ImageDraw, ImageFont

# Load environment variables from .env file
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Токены API (загружаются из переменных окружения)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
KINOPOISK_TOKEN = os.getenv("KINOPOISK_TOKEN")

# URL для Rutube API
RUTUBE_API_SEARCH_URL = 'https://rutube.ru/api/search/video/?query='

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
links_on = True # This now refers to Rutube search
kp_on = True

# Инициализация базы данных
db = Database()

# Add these cache-related constants after other constants
CACHE_DIR = "cache"
POSTERS_DIR = os.path.join(CACHE_DIR, "posters")
MOVIE_DATA_CACHE = os.path.join(CACHE_DIR, "movie_data.json")
RUTUBE_CACHE = os.path.join(CACHE_DIR, "rutube_links.json")
CACHE_EXPIRY_DAYS = 21  # 3 weeks cache

# Вспомогательные функции
def separator(text: str = "") -> str:
    return f"────── {text} ──────" if text else "────────────"

def rating_stars(rating: float) -> str:
    if not rating:
        return "☆" * 5
    full_stars = int(rating // 2)
    half_star = int(rating % 2 >= 0.5)
    return '⭐' * full_stars + '✨' * half_star + '☆' * (5 - full_stars - half_star)

def get_source_status() -> str:
    return (
        f"{'✅' if links_on else '❌'} Поиск ссылок (Rutube)\n"
        f"{'✅' if kp_on else '❌'} Поиск в Кинопоиске"
    )

async def send_loading_message(message: Message) -> Message:
    return await message.answer("🔍 <i>Ищу информацию...</i>", parse_mode=ParseMode.HTML)

def format_datetime(iso_date: str) -> str:
    """Format ISO datetime to a more readable format"""
    dt = datetime.fromisoformat(iso_date)
    return dt.strftime("%d.%m.%Y %H:%M")

# Обработчик команды /start
@dp.message(CommandStart())
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
@dp.message(Command("help"))
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
        get_source_status()
    ).as_html()
    await message.answer(response, parse_mode=ParseMode.HTML)

# Обработчики команд включения/выключения источников
@dp.message(Command("turn_links"))
async def toggle_links(message: Message):
    global links_on
    links_on = not links_on
    status = "включен" if links_on else "выключен"
    logging.info(f"Поиск ссылок (Rutube) {status} пользователем {message.from_user.id}")
    await message.answer(f"🔘 Поиск ссылок (Rutube) теперь <b>{status}</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("turn_kp"))
async def toggle_kp(message: Message):
    global kp_on
    kp_on = not kp_on
    status = "включен" if kp_on else "выключен"
    logging.info(f"Поиск в Кинопоиске {status} пользователем {message.from_user.id}")
    await message.answer(f"🔘 Поиск в Кинопоиске теперь <b>{status}</b>", parse_mode=ParseMode.HTML)

# Обработчик команды /settings
@dp.message(Command("settings"))
async def show_settings(message: Message):
    logging.info(f"Запрос настроек от {message.from_user.id}")
    response = (
        f"⚙ <b>Текущие настройки поиска</b>\n"
        f"{separator()}"
        f"{get_source_status()}\n"
        f"{separator()}"
        f"Изменить настройки:\n"
        f"/turn_links - Вкл/выкл поиск ссылок (Rutube)\n"
        f"/turn_kp - Вкл/выкл Кинопоиск"
    )
    logging.info(f"HTML ответа настроек: {response}")
    await message.answer(response, parse_mode=ParseMode.HTML)

# Обработчик команды /history
@dp.message(Command("history"))
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
@dp.message(Command("stats"))
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

def pluralize_times(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "раз"
    elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
        return "раза"
    else:
        return "раз"

def init_cache_directories():
    """Initialize cache directories if they don't exist"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(POSTERS_DIR, exist_ok=True)
    
    # Initialize cache files if they don't exist
    for cache_file in [MOVIE_DATA_CACHE, RUTUBE_CACHE]:
        if not os.path.exists(cache_file):
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    logging.info("Cache directories initialized")

def get_cache_key(text):
    """Generate a consistent cache key for a text search query"""
    # Normalize the text: lowercase and remove extra whitespace
    normalized = ' '.join(text.lower().split())
    # Create a hash for the normalized text
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()

def save_movie_to_cache(query, movie_data):
    """Save movie data to cache"""
    try:
        cache_key = get_cache_key(query)
        
        # Load existing cache
        with open(MOVIE_DATA_CACHE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        # Add the data with timestamp
        cache[cache_key] = {
            'timestamp': time.time(),
            'data': movie_data,
            'original_query': query
        }
        
        # Save updated cache
        with open(MOVIE_DATA_CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Movie data for '{query}' saved to cache")
        return True
    except Exception as e:
        logging.error(f"Failed to save movie data to cache: {str(e)}")
        return False

def get_movie_from_cache(query):
    """Get movie data from cache if it exists and is not expired"""
    try:
        cache_key = get_cache_key(query)
        
        # Check if cache file exists
        if not os.path.exists(MOVIE_DATA_CACHE):
            return None
        
        # Load cache
        with open(MOVIE_DATA_CACHE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        # Check if key exists
        if cache_key not in cache:
            return None
        
        # Check if cache is expired
        cached_data = cache[cache_key]
        cache_time = cached_data['timestamp']
        current_time = time.time()
        
        if current_time - cache_time > CACHE_EXPIRY_DAYS * 24 * 60 * 60:
            logging.info(f"Cache for '{query}' is expired")
            return None
        
        # Enhanced logging
        movie_title = cached_data['data'].get('nameRu', query)
        movie_id = cached_data['data'].get('kinopoiskId', 'Unknown')
        logging.info(f"🔄 Используем кэшированные данные для фильма '{movie_title}' (ID: {movie_id})")
        return cached_data['data']
    except Exception as e:
        logging.error(f"Error reading movie cache: {str(e)}")
        return None

def save_rutube_to_cache(query, links):
    """Save Rutube links to cache"""
    try:
        cache_key = get_cache_key(query)
        
        # Load existing cache
        with open(RUTUBE_CACHE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        # Add the data with timestamp
        cache[cache_key] = {
            'timestamp': time.time(),
            'links': links,
            'original_query': query
        }
        
        # Save updated cache
        with open(RUTUBE_CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Rutube links for '{query}' saved to cache")
        return True
    except Exception as e:
        logging.error(f"Failed to save Rutube links to cache: {str(e)}")
        return False

def get_rutube_from_cache(query):
    """Get Rutube links from cache if they exist and are not expired"""
    try:
        cache_key = get_cache_key(query)
        
        # Check if cache file exists
        if not os.path.exists(RUTUBE_CACHE):
            return None
        
        # Load cache
        with open(RUTUBE_CACHE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        # Check if key exists
        if cache_key not in cache:
            return None
        
        # Check if cache is expired
        cached_data = cache[cache_key]
        cache_time = cached_data['timestamp']
        current_time = time.time()
        
        if current_time - cache_time > CACHE_EXPIRY_DAYS * 24 * 60 * 60:
            logging.info(f"Rutube links cache for '{query}' is expired")
            return None
        
        # Enhanced logging
        num_links = len(cached_data['links'])
        logging.info(f"🔄 Используем кэшированные ссылки Rutube для '{query}' ({num_links} ссылок)")
        return cached_data['links']
    except Exception as e:
        logging.error(f"Error reading Rutube links cache: {str(e)}")
        return None

def get_cached_poster_path(movie_id):
    """Get path to cached poster if it exists and is not expired"""
    try:
        if not movie_id:
            return None
            
        # Check poster directory
        for filename in os.listdir(POSTERS_DIR):
            # Format: movieid_timestamp.jpg
            if filename.startswith(f"{movie_id}_"):
                file_path = os.path.join(POSTERS_DIR, filename)
                
                # Parse timestamp from filename
                try:
                    timestamp_str = filename.split('_')[1].split('.')[0]
                    timestamp = float(timestamp_str)
                    
                    # Check if expired
                    current_time = time.time()
                    if current_time - timestamp > CACHE_EXPIRY_DAYS * 24 * 60 * 60:
                        logging.info(f"Cached poster for movie {movie_id} is expired")
                        os.remove(file_path)  # Remove expired poster
                        return None
                    
                    logging.info(f"Using cached poster for movie {movie_id}")
                    return file_path
                except Exception as e:
                    logging.error(f"Error parsing poster filename: {str(e)}")
        
        return None
    except Exception as e:
        logging.error(f"Error checking for cached poster: {str(e)}")
        return None

def save_poster_to_cache(movie_id, poster_data):
    """Save poster data to cache"""
    try:
        if not movie_id:
            return None
            
        # Create filename with timestamp
        timestamp = time.time()
        filename = f"{movie_id}_{timestamp}.jpg"
        file_path = os.path.join(POSTERS_DIR, filename)
        
        # Save poster
        with open(file_path, 'wb') as f:
            f.write(poster_data)
        
        logging.info(f"Poster for movie {movie_id} saved to cache")
        return file_path
    except Exception as e:
        logging.error(f"Failed to save poster to cache: {str(e)}")
        return None

# Add a function to check for command-like text
def is_command_without_slash(text):
    """Check if text looks like a command but without the leading slash"""
    command_keywords = [
        "clear_cache", "clear_posters", "clear_movie_data", "clear_rutube", 
        "start", "help", "settings", "history", "stats", "turn_links", "turn_kp"
    ]
    # Strip any spaces and convert to lowercase
    text = text.strip().lower()
    return text in command_keywords

# Modify the search_movie function to check for command-like text
@dp.message(F.text)
async def search_movie(message: Message):
    # Check if message looks like a command without slash
    if is_command_without_slash(message.text.strip().lower()):
        command_name = message.text.strip().lower()
        await message.answer(
            f"Похоже, вы хотели использовать команду, но забыли слэш.\n\n"
            f"Попробуйте: <code>/{command_name}</code>",
            parse_mode=ParseMode.HTML
        )
        return

    if not links_on and not kp_on:
        logging.info(f"Попытка поиска при отключенных источниках от {message.from_user.id}")
        response = (
            f"🔎 <b>Все источники поиска отключены!</b>\n"
            f"{separator()}"
            f"Чтобы начать поиск, включите хотя бы один источник:\n"
            f"/turn_links - Вкл/выкл поиск ссылок (Rutube)\n"
            f"/turn_kp - Вкл/выкл Кинопоиск"
        )
        await message.answer(response, parse_mode=ParseMode.HTML)
        return

    query = message.text.strip()
    user_id = message.from_user.id
    
    # Log request with cache-awareness flag
    cache_log = "🔄" if (get_movie_from_cache(query) is not None or get_rutube_from_cache(query) is not None) else "🔍"
    logging.info(f"{cache_log} Получен запрос '{query}' от {user_id}")
    
    # Сохраняем запрос в историю
    await db.add_search(user_id, query)
    
    loading_msg = await send_loading_message(message)
    
    tasks = []
    if kp_on:
        tasks.append(asyncio.create_task(get_kinopoisk_data(query)))
    if links_on: # Rutube links
        tasks.append(asyncio.create_task(search_rutube_api(query)))

    kinopoisk_data = None
    video_links = [] # Только для Rutube

    if tasks:
        # Выполняем задачи и собираем результаты
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        for res_item in task_results:
            if isinstance(res_item, Exception):
                logging.error(f"Ошибка при выполнении задачи: {res_item}")
            elif isinstance(res_item, dict) and "kinopoiskId" in res_item: # Результат от Кинопоиска
                kinopoisk_data = res_item
            elif isinstance(res_item, list): # Результат от Rutube
                video_links.extend(res_item)

        from_cache = ""
        if kinopoisk_data and "cache_source" in kinopoisk_data:
            from_cache = " (данные из кэша)"
        logging.info(f"Получены данные с Кинопоиска{from_cache}: {'Да' if kinopoisk_data else 'Нет'}")
        
        from_cache = ""
        if len(video_links) > 0 and hasattr(video_links[0], "cache_source"):
            from_cache = " (данные из кэша)"
        logging.info(f"Получены видео ссылки (Rutube){from_cache}: {len(video_links)}")
    else:
        logging.info("Все источники поиска отключены, задачи не создавались.")

    response_parts = []
    image_url = None

    if kinopoisk_data:
        await db.add_movie(user_id, kinopoisk_data.get("nameRu", query), kinopoisk_data.get("year"), kinopoisk_data.get("description"))
        title = kinopoisk_data.get("nameRu", "Без названия")
        year = kinopoisk_data.get("year", "Год не указан")
        description = kinopoisk_data.get("description", "Описание отсутствует.")
        rating_kp = kinopoisk_data.get("ratingKinopoisk")
        genres = ", ".join([g["genre"] for g in kinopoisk_data.get("genres", [])])
        countries = ", ".join([c["country"] for c in kinopoisk_data.get("countries", [])])
        film_length = kinopoisk_data.get("filmLength", "Не указана")

        response_parts.append(f"🎬 <b>{html.escape(title)} ({year})</b>")
        response_parts.append(f"<b>Жанр:</b> {html.escape(genres)}")
        response_parts.append(f"<b>Страна:</b> {html.escape(countries)}")
        if film_length and film_length > 0:
            response_parts.append(f"<b>Длительность:</b> {film_length} мин.")
        if rating_kp:
            response_parts.append(f"<b>Рейтинг Кинопоиска:</b> {rating_kp} {rating_stars(rating_kp)}")
        response_parts.append(separator())
        response_parts.append(f"<i>{html.escape(description)}</i>")
        
        image_url = kinopoisk_data.get("posterUrlPreview")

    if links_on and not video_links and not kinopoisk_data: # Если искали ссылки, но ничего не нашли (даже инфо о фильме)
        response_parts.append(f"😔 К сожалению, по запросу <b>{html.escape(query)}</b> ничего не найдено ни на Кинопоиске, ни на Rutube.")
    elif links_on and not video_links and kinopoisk_data: # Если инфо есть, но ссылок нет
        response_parts.append(separator("Ссылки на просмотр"))
        response_parts.append("ℹ К сожалению, прямых ссылок на Rutube для этого фильма/сериала не найдено.")
    elif video_links: # Если ссылки есть
        response_parts.append(separator("Ссылки на просмотр (Rutube)"))
        response_parts.append("👇 Нажмите на кнопки ниже, чтобы перейти к просмотру")
        
        # Create an inline keyboard with buttons for Rutube links
        keyboard = []
        for i, link_info in enumerate(video_links[:5], 1): # Ограничиваем до 5 ссылок
            # Ensure button text is safe, limit length further to avoid huge buttons
            name = link_info['name']
            # Remove "Rutube:" prefix if it exists
            if name.startswith("Rutube: "):
                name = name[8:]  # Remove "Rutube: " (8 characters)
                
            safe_name = html.escape(name)
            if len(safe_name) > 25:
                safe_name = safe_name[:25] + "..."
            button_text = f"{i}. {safe_name}"
            
            # Ensure URL is properly formatted
            url = link_info['url']
            if not url.startswith('http'):
                url = 'https://' + url
                
            # Create button with properly escaped text and URL
            keyboard.append([InlineKeyboardButton(text=button_text, url=url)])
            logging.info(f"Created button with text: '{button_text}', URL: {url}")
        
        # Create keyboard markup
        try:
            rutube_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
            logging.info(f"Created inline keyboard with {len(keyboard)} buttons")
        except Exception as e:
            logging.error(f"Failed to create keyboard: {str(e)}")
            rutube_keyboard = None
    else:
        rutube_keyboard = None

    if not kinopoisk_data and not links_on: # Если КП выключен и ссылки тоже (хотя это проверяется в начале)
        response_parts.append("😔 Поиск отключен. Включите источники через /settings.")
    elif not kinopoisk_data and not video_links and not links_on: # КП выключен, ссылок не искали (например, links_on был false изначально)
        response_parts.append("😔 Поиск по Кинопоиску отключен. Результатов по Rutube также нет или поиск по ним отключен.")

    final_response = "\n".join(response_parts)

    # Удаляем loading_msg только после загрузки постера, непосредственно перед отправкой ответа
    # await loading_msg.delete()

    # Обновленный код для надежной загрузки постеров
    if image_url:
        poster_paths = []
        poster_loaded = False
        random_filename = f"poster_{random.randint(1000, 9999)}.jpg"
        
        # First check for cached poster
        cached_poster = None
        if kinopoisk_data and kinopoisk_data.get("kinopoiskId"):
            movie_id = kinopoisk_data.get("kinopoiskId")
            cached_poster = get_cached_poster_path(movie_id)
        
        if cached_poster:
            poster_paths.append(cached_poster)
            poster_loaded = True
            logging.info(f"Using cached poster for movie: {kinopoisk_data.get('nameRu', 'Unknown')}")
        else:
            # Regular poster download logic
            try:
                logging.info(f"Загружаем постер: {image_url}")
                async with aiohttp.ClientSession() as session:
                    try:
                        # Увеличиваем таймаут для постера до 15 секунд
                        async with session.get(image_url, timeout=15) as resp:
                            if resp.status == 200:
                                poster_data = await resp.read()
                                
                                # If we have movie ID, save to cache
                                if kinopoisk_data and kinopoisk_data.get("kinopoiskId"):
                                    movie_id = kinopoisk_data.get("kinopoiskId")
                                    cached_path = save_poster_to_cache(movie_id, poster_data)
                                    if cached_path:
                                        poster_paths.append(cached_path)
                                        poster_loaded = True
                                        logging.info(f"Poster saved to cache and loaded for movie ID: {movie_id}")
                                    else:
                                        # Fallback to temporary file if caching fails
                                        with open(random_filename, "wb") as f:
                                            f.write(poster_data)
                                        poster_paths.append(random_filename)
                                        poster_loaded = True
                                else:
                                    # No movie ID, use temporary file
                                    with open(random_filename, "wb") as f:
                                        f.write(poster_data)
                                    poster_paths.append(random_filename)
                                    poster_loaded = True
                                
                                logging.info(f"Постер успешно загружен: {image_url}")
                            else:
                                logging.error(f"Ошибка загрузки постера, статус: {resp.status}, URL: {image_url}")
                    except asyncio.TimeoutError:
                        logging.error(f"Таймаут при загрузке постера (15 сек): {image_url}")
                    except Exception as e:
                        logging.error(f"Ошибка при загрузке постера {image_url}: {str(e)}")
            except Exception as e:
                logging.error(f"Внешняя ошибка при загрузке постера {image_url}: {str(e)}")

        # Если не удалось загрузить постер, создаем дефолтный
        if not poster_loaded:
            logging.warning(f"Не удалось загрузить постер для '{kinopoisk_data.get('nameRu', 'Фильм')}', создаем дефолтный")
            try:
                # Создаем более красивое изображение с текстом
                from PIL import Image, ImageDraw, ImageFont
                
                # Создаем основу постера - темно-синий фон
                img = Image.new('RGB', (500, 750), color=(15, 30, 60))
                draw = ImageDraw.Draw(img)
                
                # Получаем название и год фильма
                movie_title = kinopoisk_data.get("nameRu", "Фильм") if kinopoisk_data else "Фильм"
                movie_year = str(kinopoisk_data.get("year", "")) if kinopoisk_data else ""
                
                logging.info(f"Создаем дефолтный постер для: '{movie_title}' ({movie_year})")
                
                # Создаем градиентный фон (от темно-синего до черного)
                for y in range(750):
                    # Вычисляем цвет для текущей строки (градиент)
                    color_value = max(0, 15 - int(y / 750 * 15))
                    color_value2 = max(0, 30 - int(y / 750 * 30))
                    draw.line([(0, y), (500, y)], fill=(color_value, color_value2, color_value * 4))
                
                # Добавляем эмблему кинопленки вверху
                draw.rectangle([(50, 50), (450, 100)], fill=(20, 40, 80), outline=(255, 255, 255), width=2)
                
                # Рисуем перфорацию пленки
                for x in range(70, 450, 40):
                    draw.rectangle([(x, 60), (x+20, 90)], fill=(40, 60, 100))
                
                # Текстовые настройки
                text_color = (255, 255, 255)  # Белый цвет
                
                try:
                    # Разбиваем длинное название на несколько строк если нужно
                    title_lines = []
                    if len(movie_title) > 20:
                        words = movie_title.split()
                        line = []
                        for word in words:
                            line.append(word)
                            if len(' '.join(line)) > 20:
                                if len(line) > 1:
                                    line.pop()  # Remove last word that made it too long
                                    title_lines.append(' '.join(line))
                                    line = [word]
                                else:
                                    title_lines.append(' '.join(line))
                                    line = []
                        if line:  # Add any remaining words
                            title_lines.append(' '.join(line))
                    else:
                        title_lines = [movie_title]
                    
                    # Рисуем название фильма
                    y_position = 250
                    for line in title_lines:
                        draw.text((250, y_position), line, fill=text_color, anchor="mm")
                        y_position += 40
                    
                    # Добавляем год выпуска
                    if movie_year:
                        draw.text((250, y_position + 20), movie_year, fill=(200, 200, 200), anchor="mm")
                except Exception as e:
                    logging.error(f"Ошибка при отрисовке текста: {str(e)}")
                    # Простая альтернатива если разбивка текста не сработала
                    draw.text((250, 250), movie_title[:20], fill=text_color, anchor="mm")
                    if len(movie_title) > 20:
                        draw.text((250, 290), movie_title[20:40], fill=text_color, anchor="mm")
                    if movie_year:
                        draw.text((250, 330), movie_year, fill=(200, 200, 200), anchor="mm")
                
                # Добавляем надпись "Информация о фильме" внизу
                draw.text((250, 650), "Информация о фильме", fill=(180, 180, 180), anchor="mm")
                
                # Сохраняем дефолтный постер
                img.save(random_filename)
                poster_paths.append(random_filename)
                poster_loaded = True
                logging.info(f"Создан дефолтный постер для '{movie_title}'")
            except Exception as e:
                logging.error(f"Критическая ошибка при создании дефолтного постера: {str(e)}")
                # Даже с этой ошибкой не останавливаемся, а пытаемся создать минимальный постер
                try:
                    # Создаем самый простой постер с фоном и текстом "Фильм"
                    img = Image.new('RGB', (500, 750), color=(15, 30, 60))
                    draw = ImageDraw.Draw(img)
                    draw.text((250, 375), "Фильм", fill=(255, 255, 255), anchor="mm")
                    img.save(random_filename)
                    poster_paths.append(random_filename)
                    poster_loaded = True
                    logging.info("Создан аварийный постер")
                except Exception as e2:
                    logging.error(f"Не удалось создать даже аварийный постер: {str(e2)}")

        if poster_loaded and poster_paths:
            try:
                await loading_msg.delete()
                if len(final_response) > 1000:
                    # Отправляем сначала фото с кратким описанием
                    movie_name = kinopoisk_data.get("nameRu", "Фильм") if kinopoisk_data else "Фильм"
                    short_caption = f"🎬 <b>{movie_name}</b>"
                    await message.answer_photo(
                        photo=FSInputFile(poster_paths[0]),
                        caption=short_caption,
                        parse_mode=ParseMode.HTML
                    )
                    await message.answer(final_response, parse_mode=ParseMode.HTML, 
                                        disable_web_page_preview=True,
                                        reply_markup=rutube_keyboard)
                else:
                    await message.answer_photo(
                        photo=FSInputFile(poster_paths[0]),
                        caption=final_response,
                        parse_mode=ParseMode.HTML,
                        reply_markup=rutube_keyboard
                    )
                logging.info("Постер успешно отправлен")
            except Exception as e:
                logging.error(f"Ошибка при отправке фото: {e}. Отправляю текстовое сообщение.")
                await loading_msg.delete()  # Удаляем, только если произошла ошибка
                await message.answer(final_response, parse_mode=ParseMode.HTML, 
                                    disable_web_page_preview=True,
                                    reply_markup=rutube_keyboard)
            finally:
                # Удаляем только временные файлы, но НЕ кэшированные постеры
                for path in poster_paths:
                    if os.path.exists(path):
                        # Если путь не содержит директорию с постерами, значит это временный файл
                        if os.path.dirname(path) != POSTERS_DIR:
                            try:
                                os.remove(path)
                                logging.info(f"Удален временный файл постера: {path}")
                            except Exception as e:
                                logging.error(f"Ошибка при удалении временного файла {path}: {e}")
        else:
            logging.error("Не удалось загрузить или создать постер")
            await loading_msg.delete()
            await message.answer(final_response, parse_mode=ParseMode.HTML, 
                                disable_web_page_preview=True,
                                reply_markup=rutube_keyboard)
    elif final_response:
        await loading_msg.delete()
        await message.answer(final_response, parse_mode=ParseMode.HTML, 
                            disable_web_page_preview=True,
                            reply_markup=rutube_keyboard)
    else:
        await loading_msg.delete()
        await message.answer(f"😔 Не удалось обработать ваш запрос <b>{html.escape(query)}</b>. Попробуйте позже.", parse_mode=ParseMode.HTML)

async def search_rutube_api(title: str):
    """Поиск видео на Rutube через API и формирование прямых ссылок на видео."""
    # Check cache first
    cached_links = get_rutube_from_cache(title)
    if cached_links is not None:
        logging.info(f"🔄 Возвращаем кэшированные ссылки на Rutube для '{title}'")
        return cached_links
        
    rutube_links = []
    search_query = f"{title} фильм"
    encoded_query = aiohttp.helpers.quote(search_query)
    url = f"{RUTUBE_API_SEARCH_URL}{encoded_query}"
    logging.info(f"Выполнение запроса к Rutube API: {url}")
        try:
            async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=7) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                    results = data.get('results', [])
                    logging.info(f"Rutube API: получено {len(results)} результатов")
                    
                    if results:
                        # Берем первые 3 результата
                        for video_item in results[:3]:
                            video_id = video_item.get('id')
                            rutube_title = video_item.get('title', 'Видео Rutube')
                            
                            if video_id:
                                # Формируем ссылку на страницу видео (не на embed)
                                video_url = f"https://rutube.ru/video/{video_id}/"
                                # Validate URL
                                if not video_url.startswith('http'):
                                    video_url = 'https://rutube.ru/video/' + video_id + '/'
                                
                                # Создаем название БЕЗ префикса "Rutube:"
                                name = rutube_title[:30] + "..." if len(rutube_title) > 30 else rutube_title
                                rutube_links.append({
                                    "name": name,
                                    "url": video_url
                                })
                                logging.info(f"Найдено видео на Rutube: {video_url} ({name})")
                            else:
                                logging.warning(f"Rutube item без video_id: {video_item}")
                else:
                    logging.error(f"Rutube API запрос не удался, статус: {resp.status}, ответ: {await resp.text(errors='ignore')}")
    except asyncio.TimeoutError:
        logging.error("Таймаут при запросе к Rutube API.")
    except Exception as e:
        logging.error(f"Ошибка при поиске через Rutube API: {str(e)}")
    
    if not rutube_links:
        logging.info("Не найдено видео через Rutube API.")
    else:
        # Save to cache if we found results
        save_rutube_to_cache(title, rutube_links)
        
    return rutube_links

async def get_kinopoisk_data(movie_title):
    """Получение данных о фильме с Кинопоиска"""
    # Check cache first
    cached_data = get_movie_from_cache(movie_title)
    if cached_data is not None:
        logging.info(f"Returning cached movie data for '{movie_title}'")
        return cached_data
    
    # Continue with regular API call if not in cache
    # Initialize with all keys search_movie expects for kinopoisk_data
    # This ensures that if some fields are missing from API, they are None.
    kinopoisk_data_output = {
        "kinopoiskId": None,
        "nameRu": None,
        "year": None,
        "description": None,
        "ratingKinopoisk": None,
        "genres": [],
        "countries": [],
        "filmLength": None,
        "posterUrlPreview": None
    }
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.kinopoisk.dev/v1.4/movie/search?query={aiohttp.helpers.quote(movie_title)}&page=1&limit=1"
            headers = {"X-API-KEY": KINOPOISK_TOKEN}
            logging.debug(f"Requesting Kinopoisk API: {url} with headers {headers}")
            async with session.get(url, headers=headers, timeout=7) as resp: # Increased timeout slightly
                logging.debug(f"Kinopoisk API response status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    logging.debug(f"Kinopoisk API response data: {data}")
                    if data.get("docs") and len(data["docs"]) > 0:
                        movie = data["docs"][0]
                        
                        kinopoisk_data_output["kinopoiskId"] = movie.get('id')
                        kinopoisk_data_output["nameRu"] = movie.get('name')
                        if not kinopoisk_data_output["nameRu"]: # Fallback to alternativeName
                            kinopoisk_data_output["nameRu"] = movie.get('alternativeName')
                        
                        kinopoisk_data_output["year"] = movie.get('year')
                        kinopoisk_data_output["description"] = movie.get('description')
                        
                        rating_data = movie.get('rating', {})
                        if isinstance(rating_data, dict):
                            kinopoisk_data_output["ratingKinopoisk"] = rating_data.get('kp')
                        
                        api_genres = movie.get('genres', [])
                        if isinstance(api_genres, list):
                            kinopoisk_data_output["genres"] = [{'genre': g.get('name')} for g in api_genres if isinstance(g, dict) and g.get('name')]

                        api_countries = movie.get('countries', [])
                        if isinstance(api_countries, list):
                            kinopoisk_data_output["countries"] = [{'country': c.get('name')} for c in api_countries if isinstance(c, dict) and c.get('name')]
                        
                        kinopoisk_data_output["filmLength"] = movie.get('movieLength')
                        if kinopoisk_data_output["filmLength"] is None:
                            kinopoisk_data_output["filmLength"] = movie.get('filmLength')

                        poster_data = movie.get('poster', {})
                        if isinstance(poster_data, dict):
                            # Берем URL постера напрямую без изменений размера
                            poster_url = poster_data.get('url')
                            if poster_url:
                                kinopoisk_data_output["posterUrlPreview"] = poster_url
                                
                            # Log the poster URL for debugging
                            logging.info(f"Poster URL for '{movie_title}': {kinopoisk_data_output['posterUrlPreview']}")
                        
                        # Critical check: if no ID or name, treat as not found.
                        if not kinopoisk_data_output["kinopoiskId"] or not kinopoisk_data_output["nameRu"]:
                            logging.warning(f"Kinopoisk API: Movie found for '{movie_title}' but missing essential id or name. Data: {movie}")
                            return {} # Return empty dict
                        
                        logging.info(f"Successfully fetched Kinopoisk data for '{movie_title}': ID {kinopoisk_data_output['kinopoiskId']}")
                        if kinopoisk_data_output["kinopoiskId"]:
                            save_movie_to_cache(movie_title, kinopoisk_data_output)
                        return kinopoisk_data_output
                    else:
                        logging.info(f"Kinopoisk API: No movie found for query '{movie_title}'.")
                        return {} 
                else:
                    responseText = await resp.text(errors='ignore')
                    logging.error(f"Kinopoisk API request failed for '{movie_title}', status: {resp.status}, response: {responseText}")
                    return {}
    except asyncio.TimeoutError:
        logging.warning(f"Timeout during Kinopoisk API request for '{movie_title}'")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error in get_kinopoisk_data for '{movie_title}': {e}", exc_info=True)
        return {}

# Add a new function to clear cache
async def clear_cache(clear_all=True, clear_posters=False, clear_movie_data=False, clear_rutube=False):
    """
    Clear cache files and directories
    
    Parameters:
    - clear_all: Whether to clear all cache types
    - clear_posters: Whether to clear the poster cache
    - clear_movie_data: Whether to clear the movie data cache
    - clear_rutube: Whether to clear the Rutube links cache
    
    Returns:
    - result_string: A string describing what was cleared
    """
    results = []
    
    # If clear_all is True, set all other flags to True
    if clear_all:
        clear_posters = True
        clear_movie_data = True
        clear_rutube = True
    
    # Clear poster cache
    if clear_posters:
        try:
            poster_count = 0
            if os.path.exists(POSTERS_DIR):
                for filename in os.listdir(POSTERS_DIR):
                    file_path = os.path.join(POSTERS_DIR, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            poster_count += 1
                    except Exception as e:
                        logging.error(f"Error removing {file_path}: {str(e)}")
            results.append(f"Удалено постеров: {poster_count}")
            logging.info(f"Cleared {poster_count} posters from cache")
        except Exception as e:
            error_msg = f"Ошибка при очистке кэша постеров: {str(e)}"
            results.append(error_msg)
            logging.error(error_msg)
    
    # Clear movie data cache
    if clear_movie_data:
        try:
            if os.path.exists(MOVIE_DATA_CACHE):
                # Reset to empty dictionary
                with open(MOVIE_DATA_CACHE, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                results.append("Кэш данных о фильмах очищен")
                logging.info("Cleared movie data cache")
            else:
                results.append("Кэш данных о фильмах не найден")
        except Exception as e:
            error_msg = f"Ошибка при очистке кэша данных о фильмах: {str(e)}"
            results.append(error_msg)
            logging.error(error_msg)
    
    # Clear Rutube links cache
    if clear_rutube:
        try:
            if os.path.exists(RUTUBE_CACHE):
                # Reset to empty dictionary
                with open(RUTUBE_CACHE, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                results.append("Кэш ссылок Rutube очищен")
                logging.info("Cleared Rutube links cache")
            else:
                results.append("Кэш ссылок Rutube не найден")
        except Exception as e:
            error_msg = f"Ошибка при очистке кэша ссылок Rutube: {str(e)}"
            results.append(error_msg)
            logging.error(error_msg)
    
    # Reinitialize cache directories
    init_cache_directories()
    
    if not results:
        return "Ничего не было очищено"
    
    return "\n".join(results)

# Add command handlers for cache clearing
@dp.message(Command("clear_cache"))
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

@dp.message(Command("clear_posters"))
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

@dp.message(Command("clear_movie_data"))
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

@dp.message(Command("clear_rutube"))
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

# Запуск бота
async def main():
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
    
    # Initialize cache directories
    init_cache_directories()
    
    logging.info("Инициализация базы данных")
    await db.init()
    try:
        me = await bot.get_me()
        logging.info(f"Соединение с Telegram API установлено. Бот: @{me.username} ({me.id})")
    except Exception as e:
        logging.error(f"Ошибка соединения с Telegram API: {e}")
        sys.exit(1)
    logging.info("Запуск бота")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

async def shutdown():
    logging.info("Завершение работы бота...")
    await bot.session.close()
    sys.exit(0)

if __name__ == '__main__':
    try:
        timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_connect=10, sock_read=10)
    asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
    except Exception as e:
        logging.error(f"Неожиданная ошибка: {e}")
        sys.exit(1)