import asyncio
import aiohttp
import aiovk
import logging
import html
import aiosqlite
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, URLInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.formatting import Text
from aiogram.enums import ParseMode
from dotenv import load_dotenv
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Загрузка переменных окружения
load_dotenv()

# Токены API из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
VK_TOKEN = os.getenv("VK_TOKEN")
KINOPOISK_TOKEN = os.getenv("KINOPOISK_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

if not all([TELEGRAM_TOKEN, VK_TOKEN, KINOPOISK_TOKEN]):
    logging.error("Не все токены найдены в .env файле!")
    exit(1)

vk_id = 53531262

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Вспомогательные функции
def separator(text: str = "") -> str:
    return f"\n────── {text} ──────\n" if text else "\n────────────\n"

def rating_stars(rating: float) -> str:
    if not rating:
        return "☆" * 5
    full_stars = int(rating // 2)
    half_star = int(rating % 2 >= 0.5)
    return '⭐' * full_stars + '✨' * half_star + '☆' * (5 - full_stars - half_star)

async def get_user_settings(user_id: int) -> tuple[bool, bool]:
    async with aiosqlite.connect('bot.db') as db:
        cursor = await db.execute("SELECT vk_on, kp_on FROM user_settings WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO user_settings (user_id, vk_on, kp_on) VALUES (?, ?, ?)", (user_id, 1, 1))
            await db.commit()
            return True, True
        return bool(row[0]), bool(row[1])

async def send_loading_message(message: Message) -> Message:
    return await message.answer("🔍 <i>Ищу информацию...</i>", parse_mode=ParseMode.HTML)

async def get_movie_description(film_id: int) -> str:
    url = f"https://api.kinopoisk.dev/v1.4/movie/{film_id}"
    headers = {
        "X-API-KEY": KINOPOISK_TOKEN,
        "Accept": "application/json"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logging.info(f"Получены данные о фильме {film_id}: {str(data)[:500]}")
                    description = data.get('description', '')
                    if not description:
                        description = data.get('shortDescription', '')
                    if not description:
                        description = "Описание не найдено"
                    return description
                else:
                    logging.error(f"Не удалось получить описание фильма (статус {resp.status})")
                    return f"Описание не найдено (статус {resp.status})"
    except Exception as e:
        logging.error(f"Ошибка при получении описания фильма: {str(e)}")
        return "Описание не найдено: ошибка запроса"

async def get_watch_link(title: str) -> str:
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        return ""
    search_query = f"{title} смотреть без смс и регистрации"
    url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={aiohttp.helpers.quote(search_query)}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("items"):
                        first_link = data["items"][0]["link"]
                        return first_link
                    else:
                        return ""
                else:
                    logging.error(f"Google API вернул статус {resp.status}")
                    return ""
    except Exception as e:
        logging.error(f"Ошибка при получении ссылки для просмотра: {str(e)}")
        return ""

########## /start handler ####################

@dp.message(CommandStart())
async def send_welcome(message: Message):
    logging.info(f"Получена команда /start от {message.from_user.id}")
    response = (
        f"🎬 <b>Кино-бот приветствует вас!</b>\n"
        f"{separator()}"
        f"Отправьте мне название фильма или сериала,\n"
        f"и я найду информацию и ссылки для просмотра.\n"
        f"{separator('Доступные команды')}"
        f"/help - Показать справку\n"
        f"/settings - Настройки поиска\n"
        # f"/new - Показать новинки кино\n"
        # f"/best - Топ 10 фильмов всех времён\n"
        f"/history - История поиска\n"
        f"/stats - Статистика предложенных фильмов"
    )
    logging.info(f"HTML ответа приветствия: {response}")
    await message.answer(response, parse_mode=ParseMode.HTML)

########## /help handler ####################

@dp.message(Command("help"))
async def send_help(message: Message):
    logging.info(f"Получена команда /help от {message.from_user.id}")
    user_id = message.from_user.id
    vk_on, kp_on = await get_user_settings(user_id)
    response = (
        f"🛠 <b>Справка по использованию бота</b>\n"
        f"{separator()}"
        f"Просто отправьте название фильма или сериала,\n"
        f"и бот найдет информацию о нем и ссылки для просмотра.\n"
        f"{separator('Команды')}"
        f"/start - Начальное приветствие\n"
        f"/turn_vk - Вкл/выкл поиск в VK\n"
        f"/turn_kp - Вкл/выкл поиск в Кинопоиске\n"
        f"/settings - Текущие настройки\n"
        f"/new - Показать новинки кино\n"
        f"/best - Топ 10 фильмов всех времён\n"
        f"/history - История поиска\n"
        f"/stats - Статистика предложенных фильмов\n"
        f"{separator('Статус поиска')}"
        f"{'✅' if vk_on else '❌'} Поиск в VK\n"
        f"{'✅' if kp_on else '❌'} Поиск в Кинопоиске"
    )
    logging.info(f"HTML ответа справки: {response}")
    await message.answer(response, parse_mode=ParseMode.HTML)

########## turn on/off cources ####################

@dp.message(Command("turn_vk"))
async def toggle_vk(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect('bot.db') as db:
        cursor = await db.execute("SELECT vk_on FROM user_settings WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO user_settings (user_id, vk_on, kp_on) VALUES (?, ?, ?)", (user_id, 0, 1))
            status = "выключен"
        else:
            new_vk_on = 1 - row[0]
            await db.execute("UPDATE user_settings SET vk_on = ? WHERE user_id = ?", (new_vk_on, user_id))
            status = "включен" if new_vk_on else "выключен"
        await db.commit()
    logging.info(f"Поиск по VK {status} пользователем {user_id}")
    await message.answer(f"🔘 Поиск в VK теперь <b>{status}</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("turn_kp"))
async def toggle_kp(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect('bot.db') as db:
        cursor = await db.execute("SELECT kp_on FROM user_settings WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO user_settings (user_id, vk_on, kp_on) VALUES (?, ?, ?)", (user_id, 1, 0))
            status = "выключен"
        else:
            new_kp_on = 1 - row[0]
            await db.execute("UPDATE user_settings SET kp_on = ? WHERE user_id = ?", (new_kp_on, user_id))
            status = "включен" if new_kp_on else "выключен"
        await db.commit()
    logging.info(f"Поиск по Кинопоиску {status} пользователем {user_id}")
    await message.answer(f"🔘 Поиск в Кинопоиске теперь <b>{status}</b>", parse_mode=ParseMode.HTML)

########## /settings handler ####################

@dp.message(Command("settings"))
async def show_settings(message: Message):
    user_id = message.from_user.id
    vk_on, kp_on = await get_user_settings(user_id)
    logging.info(f"Запрос настроек от {user_id}")
    response = (
        "⚙ <b>Текущие настройки поиска</b>\n"
        f"{separator()}"
        f"{'✅' if vk_on else '❌'} Поиск в VK\n"
        f"{'✅' if kp_on else '❌'} Поиск в Кинопоиске\n"
        f"{separator()}"
        "Изменить настройки:\n"
        "/turn_vk - Вкл/выкл VK\n"
        "/turn_kp - Вкл/выкл Кинопоиск"
    )
    logging.info(f"HTML ответа настроек: {response}")
    await message.answer(response, parse_mode=ParseMode.HTML)

# Обработчик команды /new
@dp.message(Command("new"))
async def show_new_movies(message: Message):
    user_id = message.from_user.id
    _, kp_on = await get_user_settings(user_id)
    if not kp_on:
        logging.info(f"Попытка запроса новинок с отключенным Кинопоиском от {user_id}")
        await message.answer("🔎 <b>Поиск в Кинопоиске отключен.</b> Включите его командой /turn_kp", parse_mode=ParseMode.HTML)
        return

    logging.info(f"Запрос новинок от {user_id}")
    wait_message = await send_loading_message(message)
    
    current_year = 2024  # Используем 2024 для тестирования, так как 2025 может не иметь данных
    current_month = datetime.now().strftime("%B").upper()
    url = f"https://api.kinopoisk.dev/v2.2/films/premieres?year={current_year}&month={current_month}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"X-API-KEY": KINOPOISK_TOKEN}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    movies = data.get("items", [])
                    if not movies:
                        response = "😕 <b>Новые фильмы не найдены.</b>"
                        await message.answer(response, parse_mode=ParseMode.HTML)
                        await wait_message.delete()
                        return
                    response = f"🎬 <b>Новые фильмы {current_year} года:</b>\n{separator()}"
                    for movie in movies[:10]:
                        title = movie.get('nameRu', movie.get('nameEn', 'Нет названия'))
                        year = movie.get('year', 'Нет данных')
                        film_id = movie.get('kinopoiskId')
                        kp_url = f"https://www.kinopoisk.ru/film/{film_id}/" if film_id else None
                        vk_search_query = f"{title} {year}" if year != 'Нет данных' else title
                        vk_search_url = f"https://vk.com/video?q={aiohttp.helpers.quote(vk_search_query)}"
                        response += f"- <a href='{kp_url}'>{html.escape(title)}</a> | <a href='{vk_search_url}'>Поиск в VK</a>\n"
                    logging.info(f"HTML ответа новинок: {response}")
                    await message.answer(response, parse_mode=ParseMode.HTML)
                else:
                    response = f"⚠ <i>Не удалось получить информацию с Кинопоиска (статус {resp.status})</i>"
                    logging.error(f"Kinopoisk API вернул статус {resp.status}")
                    await message.answer(response, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Ошибка при получении новых фильмов: {str(e)}")
        response = "⚠ <i>Произошла ошибка при получении данных</i>"
        await message.answer(response, parse_mode=ParseMode.HTML)
    finally:
        await wait_message.delete()

# Обработчик команды /best
@dp.message(Command("best"))
async def show_best_movies(message: Message):
    user_id = message.from_user.id
    _, kp_on = await get_user_settings(user_id)
    if not kp_on:
        logging.info(f"Попытка запроса топ фильмов с отключенным Кинопоиском от {user_id}")
        await message.answer("🔎 <b>Поиск в Кинопоиске отключен.</b> Включите его командой /turn_kp", parse_mode=ParseMode.HTML)
        return

    logging.info(f"Запрос топ фильмов от {user_id}")
    wait_message = await send_loading_message(message)
    
    url = "https://api.kinopoisk.dev/v2.2/films/top?type=TOP_250_BEST_FILMS&page=1"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"X-API-KEY": KINOPOISK_TOKEN}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    movies = data.get("films", [])
                    if not movies:
                        response = "😕 <b>Фильмы не найдены.</b>"
                        await message.answer(response, parse_mode=ParseMode.HTML)
                        await wait_message.delete()
                        return
                    response = f"🎬 <b>Топ 10 фильмов всех времён:</b>\n{separator()}"
                    for movie in movies[:10]:
                        title = movie.get('nameRu', movie.get('nameEn', 'Нет названия'))
                        year = movie.get('year', 'Нет данных')
                        film_id = movie.get('filmId')
                        kp_url = f"https://www.kinopoisk.ru/film/{film_id}/" if film_id else None
                        vk_search_query = f"{title} {year}" if year != 'Нет данных' else title
                        vk_search_url = f"https://vk.com/video?q={aiohttp.helpers.quote(vk_search_query)}"
                        response += f"- <a href='{kp_url}'>{html.escape(title)}</a> | <a href='{vk_search_url}'>Поиск в VK</a>\n"
                    logging.info(f"HTML ответа топ фильмов: {response}")
                    await message.answer(response, parse_mode=ParseMode.HTML)
                else:
                    response = f"⚠ <i>Не удалось получить информацию с Кинопоиска (статус {resp.status})</i>"
                    logging.error(f"Kinopoisk API вернул статус {resp.status}")
                    await message.answer(response, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Ошибка при получении топ фильмов: {str(e)}")
        response = "⚠ <i>Произошла ошибка при получении данных</i>"
        await message.answer(response, parse_mode=ParseMode.HTML)
    finally:
        await wait_message.delete()

########## /history handler ####################
@dp.message(Command("history"))
async def show_history(message: Message):
    user_id = message.from_user.id
    logging.info(f"Запрос истории поиска от {user_id}")
    async with aiosqlite.connect('bot.db') as db:
        cursor = await db.execute("SELECT query, timestamp FROM search_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
        rows = await cursor.fetchall()
        if not rows:
            response = "📜 <b>История поиска пуста.</b>"
        else:
            response = f"📜 <b>Последние поиски:</b>\n{separator()}"
            for row in rows:
                query, timestamp = row
                response += f"- {html.escape(query)} ({timestamp})\n"
        logging.info(f"HTML ответа истории: {response}")
        await message.answer(response, parse_mode=ParseMode.HTML)

########## /stats handler ####################
@dp.message(Command("stats"))
async def show_stats(message: Message):
    user_id = message.from_user.id
    logging.info(f"Запрос статистики от {user_id}")
    async with aiosqlite.connect('bot.db') as db:
        cursor = await db.execute("SELECT movie_title, count FROM suggestions WHERE user_id = ? ORDER BY count DESC LIMIT 10", (user_id,))
        rows = await cursor.fetchall()
        if not rows:
            response = "📊 <b>Статистика предложений пуста.</b>"
        else:
            response = f"📊 <b>Часто предлагаемые фильмы:</b>{separator()}"
            for row in rows:
                movie_title, count = row
                response += f"- {html.escape(movie_title)}: {count} раз\n"
        logging.info(f"HTML ответа статистики: {response}")
        await message.answer(response, parse_mode=ParseMode.HTML)

# Основной обработчик поиска фильмов
@dp.message(F.text)
async def search_movie(message: Message):
    user_id = message.from_user.id
    vk_on, kp_on = await get_user_settings(user_id)
    
    if not vk_on and not kp_on:
        logging.info(f"Попытка поиска при отключенных источниках от {user_id}")
        response = (
            f"🔎 <b>Все источники поиска отключены!</b>\n"
            f"{separator()}"
            f"Чтобы начать поиск, включите хотя бы один источник:\n"
            f"/turn_vk - поиск в ВК\n"
            f"/turn_kp - поиск в Кинопоиске\n"
            f"{separator()}"
            f"<i>Вы можете включать/выключать источники в любой момент</i>"
        )
        logging.info(f"HTML ответа отключенных источников: {response}")
        await message.answer(response, parse_mode=ParseMode.HTML)
        return

    movie_title = message.text
    logging.info(f"Поиск фильма: {movie_title} для пользователя {user_id}")
    
    # Запись в историю поиска
    async with aiosqlite.connect('bot.db') as db:
        await db.execute("INSERT INTO search_history (user_id, query) VALUES (?, ?)", (user_id, movie_title))
        await db.commit()
    
    wait_message = await send_loading_message(message)
    
    movie_details = ""
    watch_link = ""
    poster_url = None
    suggestion_title = None
    video_title = None
    vk_search_query = movie_title
    description = ""
    watch_link_google = ""

    if kp_on:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.kinopoisk.dev/v1.4/movie/search?query={aiohttp.helpers.quote(movie_title)}&page=1&limit=1"
                async with session.get(url, headers={"X-API-KEY": KINOPOISK_TOKEN}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("docs"):
                            movie = data["docs"][0]
                            title = movie.get('name', movie.get('alternativeName', 'Нет названия'))
                            year = movie.get('year', 'Нет данных')
                            rating = movie.get('rating', {}).get('kp', 0)
                            countries = ", ".join([c.get('name', '') for c in movie.get('countries', [])][:3])
                            genres = ", ".join([g.get('name', '') for g in movie.get('genres', [])][:3])
                            film_id = movie.get('id')
                            kp_url = f"https://www.kinopoisk.ru/film/{film_id}/" if film_id else None
                            poster_url = movie.get('poster', {}).get('url')
                            
                            title_escaped = html.escape(str(title))
                            year_escaped = html.escape(str(year))
                            countries_escaped = html.escape(str(countries) or 'Нет данных')
                            genres_escaped = html.escape(str(genres) or 'Нет данных')
                            
                            movie_details = (
                                f"🎬 <b>{title_escaped}</b> ({year_escaped})\n"
                                f"{separator()}"
                                f"{rating_stars(rating)} <b>{rating}/10</b>\n"
                                f"🌍 <i>Страны:</i> {countries_escaped}\n"
                                f"🎭 <i>Жанры:</i> {genres_escaped}\n"
                                f"{separator()}"
                            )
                            if kp_url:
                                movie_details += f"🔗 <a href='{kp_url}'>Страница на Кинопоиске</a>\n"
                            suggestion_title = title
                            logging.info(f"HTML ответа Кинопоиск: {movie_details}")
                            vk_search_query = f"{title} {year}" if year != 'Нет данных' else title
                            
                            # Получить описание
                            description = await get_movie_description(film_id)
                            movie_details += f"\n<b>Описание:</b> {html.escape(description)}\n"
                            
                            # Получить ссылку для просмотра
                            watch_link_google = await get_watch_link(title)
                            if watch_link_google:
                                movie_details += f"\n🔗 <a href='{watch_link_google}'>Смотреть онлайн</a>\n"
                    else:
                        logging.error(f"Kinopoisk API вернул статус {resp.status}")
        except Exception as e:
            logging.error(f"Kinopoisk API ошибка: {str(e)}")
            movie_details = "⚠ <i>Не удалось получить информацию с Кинопоиска</i>\n"

    vk_search_url = f"https://vk.com/video?q={aiohttp.helpers.quote(vk_search_query)}"
    
    if vk_on:
        try:
            async with aiovk.TokenSession(access_token=VK_TOKEN) as session:
                vk_api = aiovk.API(session)
                videos = await vk_api.video.search(q=vk_search_query, count=1, sort=2)
                logging.info(f"VK API ответ: {videos}")
                if videos.get("items"):
                    video = videos["items"][0]
                    watch_link = video.get("player")
                    video_title = video.get("title")
                    logging.info(f"VK видео найдено: {video_title}, URL: {watch_link}")
                else:
                    watch_link = None
                    video_title = None
                    logging.info("VK видео не найдено")
        except Exception as e:
            logging.error(f"VK API ошибка: {str(e)}")
            watch_link = None
            video_title = None
    
    if not watch_link and vk_on:
        movie_details += f"🔍 <a href='{vk_search_url}'>Найти видео в VK</a>\n"
    
    if not movie_details and watch_link and video_title:
        movie_details = f"🎬 <b>{html.escape(video_title)}</b>\n{separator()}\n<i>Информация с VK</i>\n"
        suggestion_title = video_title
    
    if suggestion_title:
        async with aiosqlite.connect('bot.db') as db:
            await db.execute("""
                INSERT INTO suggestions (user_id, movie_title, count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, movie_title) DO UPDATE SET count = count + 1
            """, (user_id, suggestion_title))
            await db.commit()
    
    response_parts = []
    if movie_details:
        response_parts.append(movie_details)
    
    if watch_link:
        watch_button = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶ Смотреть в VK", url=watch_link)]
        ])
    else:
        watch_button = None
    
    if not response_parts and not watch_link:
        response = (
            f"😕 <b>Ничего не найдено</b>\n"
            f"{separator()}"
            f"Попробуйте:\n"
            f"- Уточнить название\n"
            f"- Проверить орфографию\n"
            f"- Использовать английское название\n"
        )
        if vk_on:
            response += f"🔍 <a href='{vk_search_url}'>Найти видео в VK</a>"
        logging.info(f"HTML ответа (ничего не найдено): {response}")
        await message.answer(response, parse_mode=ParseMode.HTML)
    else:
        if poster_url:
            try:
                await message.answer_photo(
                    URLInputFile(poster_url),
                    caption=movie_details,
                    parse_mode=ParseMode.HTML,
                    reply_markup=watch_button
                )
            except Exception as e:
                logging.error(f"Ошибка отправки фото: {str(e)}")
                await message.answer(
                    movie_details,
                    parse_mode=ParseMode.HTML,
                    reply_markup=watch_button
                )
        else:
            await message.answer(
                movie_details,
                parse_mode=ParseMode.HTML,
                reply_markup=watch_button
            )
    
    await wait_message.delete()

# Запуск бота
async def main():
    logging.info("Запуск бота")
    async with aiosqlite.connect('bot.db') as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                vk_on BOOLEAN DEFAULT 1,
                kp_on BOOLEAN DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                user_id INTEGER,
                movie_title TEXT,
                count INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, movie_title)
            )
        """)
        await db.commit()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())