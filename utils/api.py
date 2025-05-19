import aiohttp
import asyncio
import logging
import os
from utils.cache import (
    get_movie_from_cache, save_movie_to_cache,
    get_rutube_from_cache, save_rutube_to_cache
)

# URL для Rutube API
RUTUBE_API_SEARCH_URL = 'https://rutube.ru/api/search/video/?query='

# Токен API для кинопоиска
KINOPOISK_TOKEN = os.getenv("KINOPOISK_TOKEN")

async def search_rutube_api(title: str):
    """Поиск видео на Rutube через API и формирование прямых ссылок на видео."""
    # Check cache first
    cached_links = get_rutube_from_cache(title)
    if cached_links is not None:
        logging.info(f"🔄 Возвращаем кэшированные ссылки на Rutube для '{title}' ({len(cached_links)} ссылок)")
        # Add a flag to identify cached links (for debugging)
        for link in cached_links:
            link['from_cache'] = True
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
                                    "url": video_url,
                                    "from_cache": False
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
        logging.info(f"Сохранено {len(rutube_links)} ссылок в кэше")
        
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