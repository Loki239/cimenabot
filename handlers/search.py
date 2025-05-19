"""
Search Handler Module for CinemaBot

This module handles the main search functionality, including processing
user queries, fetching movie data, and displaying results with streaming links.
"""

import os
import html
import random
import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional, Union
from PIL import Image, ImageDraw, ImageFont
from aiogram import Router, F, Bot
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode

from database import Database
from utils.api import search_rutube_api, get_kinopoisk_data
from utils.cache import (
    get_movie_from_cache, save_movie_to_cache,
    get_cached_poster_path, save_poster_to_cache,
    CACHE_DIR, POSTERS_DIR, MOVIE_DATA_CACHE, RUTUBE_CACHE
)
from utils.helpers import separator, rating_stars, is_command_without_slash
from handlers.commands import get_search_settings

router = Router()
db = Database()

async def send_loading_message(message: Message) -> Message:
    """Send a loading message when search starts"""
    return await message.answer("🔍 <i>Ищу информацию...</i>", parse_mode=ParseMode.HTML)

@router.message()
async def handle_message(message: Message, bot: Bot, db: Optional[Database] = None):
    """
    Handle regular text messages and search for movies.
    
    This is the main handler that processes user's search queries
    and returns movie information with streaming links.
    
    Args:
        message: The message object from Telegram
        bot: The bot instance
        db: Database instance (injected by middleware)
    """
    # Use global database if middleware didn't provide one
    if db is None:
        db = Database()
        
    # Fix: safely get message text and check if it's None
    message_text = message.text
    if message_text is None:
        return
        
    # Clean and trim the query
    query = message_text.strip()
    
    # Don't process empty messages
    if not query:
        return
        
    # Check if message looks like a command without slash
    if is_command_without_slash(query):
        await message.answer(f"Похоже, вы пытались ввести команду, но забыли добавить слеш (/). Попробуйте: /{query}")
        return
    
    # Fix: Check if user is None
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return
        
    # Get user ID
    user_id = message.from_user.id
        
    # Log the search
    logging.info(f"Поиск фильма: '{query}' от пользователя {user_id}")
    
    # Add to search history
    await db.add_search(user_id, query)
    
    # Create and send a "loading" message
    loading_msg = await message.answer("🔍 <b>Ищу фильм...</b>", parse_mode=ParseMode.HTML)
    
    # Get current search settings
    settings = get_search_settings()
    links_on = settings['links_on']
    kp_on = settings['kp_on']

    if not links_on and not kp_on:
        logging.info(f"Попытка поиска при отключенных источниках от {user_id}")
        response = (
            f"🔎 <b>Все источники поиска отключены!</b>\n"
            f"{separator()}"
            f"Чтобы начать поиск, включите хотя бы один источник:\n"
            f"/turn_links - Вкл/выкл поиск ссылок (Rutube)\n"
            f"/turn_kp - Вкл/выкл Кинопоиск"
        )
        await message.answer(response, parse_mode=ParseMode.HTML)
        return

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
        
        # Добавляем текстовые ссылки вместо кнопок
        for i, link_info in enumerate(video_links[:5], 1): # Ограничиваем до 5 ссылок
            name = link_info['name']
            url = link_info['url']
            
            # Ensure URL is properly formatted
            if not url.startswith('http'):
                url = 'https://' + url
                
            # Добавляем текстовую ссылку
            response_parts.append(f"{i}. <a href='{url}'>{html.escape(name)}</a>")
            
            # Log for debugging
            from_cache = link_info.get('from_cache', False)
            cache_status = "из кэша" if from_cache else "из поиска"
            logging.info(f"Добавлена ссылка {i}: {name} ({cache_status})")
        
        # Создаем пустую клавиатуру (нам не нужны кнопки)
        rutube_keyboard = None
    else:
        rutube_keyboard = None

    if not kinopoisk_data and not links_on: # Если КП выключен и ссылки тоже (хотя это проверяется в начале)
        response_parts.append("😔 Поиск отключен. Включите источники через /settings.")
    elif not kinopoisk_data and not video_links and not links_on: # КП выключен, ссылок не искали (например, links_on был false изначально)
        response_parts.append("😔 Поиск по Кинопоиску отключен. Результатов по Rutube также нет или поиск по ним отключен.")

    final_response = "\n".join(response_parts)

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
        
        if cached_poster and kinopoisk_data is not None:
            poster_paths.append(cached_poster)
            poster_loaded = True
            logging.info(f"Using cached poster for movie: {kinopoisk_data.get('nameRu', 'Unknown')}")
        else:
            # Regular poster download logic
            try:
                logging.info(f"Загружаем постер: {image_url}")
                async with aiohttp.ClientSession() as session:
                    # Fix timeout parameter to use ClientTimeout object
                    timeout = aiohttp.ClientTimeout(total=10)
                    async with session.get(image_url, timeout=timeout) as resp:
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

        # Если не удалось загрузить постер, создаем дефолтный
        if not poster_loaded:
            # Fix: Check if kinopoisk_data is None
            movie_title = "Фильм"
            movie_year = ""
            if kinopoisk_data is not None:
                movie_title = kinopoisk_data.get("nameRu", "Фильм")
                movie_year = str(kinopoisk_data.get("year", ""))
                
            logging.warning(f"Не удалось загрузить постер для '{movie_title}', создаем дефолтный")
            
            try:
                # Создаем более красивое изображение с текстом
                # Создаем основу постера - темно-синий фон
                img = Image.new('RGB', (500, 750), color=(15, 30, 60))
                draw = ImageDraw.Draw(img)
                
                # Получаем название и год фильма
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
                    title_lines: List[str] = []
                    if len(movie_title) > 20:
                        words = movie_title.split()
                        current_line: List[str] = []
                        for word in words:
                            current_line.append(word)
                            if len(' '.join(current_line)) > 20:
                                if len(current_line) > 1:
                                    current_line.pop()  # Remove last word that made it too long
                                    title_lines.append(' '.join(current_line))
                                    current_line = [word]
                                else:
                                    title_lines.append(' '.join(current_line))
                                    current_line = []
                        if current_line:  # Add any remaining words
                            title_lines.append(' '.join(current_line))
                    else:
                        title_lines = [movie_title]
                    
                    # Рисуем название фильма
                    y_position = 250
                    # Fix: Create font object for text drawing
                    # Note: This is placeholder code since we don't have access to the actual font file
                    # In a real environment, you'd use a font like:
                    # font = ImageFont.truetype("path/to/font.ttf", size=20)
                    # For default system font:
                    font = None
                    try:
                        font = ImageFont.load_default()
                    except:
                        pass
                    
                    for line in title_lines:
                        # Fix: Add font parameter to draw.text
                        draw.text((250, y_position), line, fill=text_color, anchor="mm", font=font)
                        y_position += 40
                    
                    # Добавляем год выпуска
                    if movie_year:
                        # Fix: Add font parameter to draw.text
                        draw.text((250, y_position + 20), movie_year, fill=(200, 200, 200), anchor="mm", font=font)
                except Exception as e:
                    logging.error(f"Ошибка при отрисовке текста: {str(e)}")
                    # Простая альтернатива если разбивка текста не сработала
                    draw.text((250, 250), movie_title[:20], fill=text_color, anchor="mm", font=font)
                    if len(movie_title) > 20:
                        draw.text((250, 290), movie_title[20:40], fill=text_color, anchor="mm", font=font)
                    if movie_year:
                        draw.text((250, 330), movie_year, fill=(200, 200, 200), anchor="mm", font=font)
                
                # Добавляем надпись "Информация о фильме" внизу
                draw.text((250, 650), "Информация о фильме", fill=(180, 180, 180), anchor="mm", font=font)
                
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
                    # Get default font
                    font = None
                    try:
                        font = ImageFont.load_default()
                    except:
                        pass
                    draw.text((250, 375), "Фильм", fill=(255, 255, 255), anchor="mm", font=font)
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
                    movie_name = "Фильм"
                    if kinopoisk_data is not None:
                        movie_name = kinopoisk_data.get("nameRu", "Фильм")
                    short_caption = f"🎬 <b>{movie_name}</b>"
                    await message.answer_photo(
                        photo=FSInputFile(poster_paths[0]),
                        caption=short_caption,
                        parse_mode=ParseMode.HTML
                    )
                    await message.answer(final_response, parse_mode=ParseMode.HTML, 
                                        disable_web_page_preview=False)
                else:
                    await message.answer_photo(
                        photo=FSInputFile(poster_paths[0]),
                        caption=final_response,
                        parse_mode=ParseMode.HTML
                    )
                logging.info("Постер успешно отправлен")
            except Exception as e:
                logging.error(f"Ошибка при отправке фото: {e}. Отправляю текстовое сообщение.")
                await loading_msg.delete()  # Удаляем, только если произошла ошибка
                await message.answer(final_response, parse_mode=ParseMode.HTML, 
                                    disable_web_page_preview=False)
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
                                disable_web_page_preview=False)
    elif final_response:
        await loading_msg.delete()
        await message.answer(final_response, parse_mode=ParseMode.HTML, 
                            disable_web_page_preview=False)
    else:
        await loading_msg.delete()
        await message.answer(f"😔 Не удалось обработать ваш запрос <b>{html.escape(query)}</b>. Попробуйте позже.", parse_mode=ParseMode.HTML) 