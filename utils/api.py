import aiohttp
import asyncio
import logging
import os
from typing import Optional, List, Dict, Any
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
        # Add a flag to identify cached links
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
            # Fix: Using proper ClientTimeout object instead of integer
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.get(url, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Process results
                    results = data.get('results', [])
                    logging.info(f"Rutube API: получено {len(results)} результатов")
                    
                    count = 0
                    for result in results:
                        if count >= 3:  # Ограничимся тремя ссылками
                            break
                            
                        title = result.get('title', '')
                        video_url = result.get('video_url', '')
                        
                        if video_url:
                            logging.info(f"Найдено видео на Rutube: {video_url} ({title[:25]}...)")
                            rutube_links.append({
                                'name': title,
                                'url': video_url,
                                'from_cache': False  # Mark as fresh search result
                            })
                            count += 1
    except Exception as e:
        logging.info(f"Ошибка при поиске на Rutube: {e}")
    
    logging.info(f"Сохранено {len(rutube_links)} ссылок в кэше")
    save_rutube_to_cache(title, rutube_links)
    
    return rutube_links

async def search_kinopoisk(query: str) -> Optional[List[Dict[str, Any]]]:
    """Search for movies on Kinopoisk by keyword"""
    # Use v2.2 API
    url = "https://kinopoiskapiunofficial.tech/api/v2.2/films"
    
    # Get API key and log if it's missing
    api_key = os.getenv("KINOPOISK_TOKEN")
    if not api_key:
        logging.error("KINOPOISK_TOKEN environment variable is not set or empty")
        return None
        
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    
    # Use search parameters
    params = {
        'keyword': query,
        'order': 'RATING',
        'type': 'ALL'
    }
    
    logging.info(f"Searching Kinopoisk for: '{query}' using URL: {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                status = response.status
                logging.info(f"Kinopoisk API response status: {status}")
                
                if status == 200:
                    data = await response.json()
                    # Log the entire response for debugging
                    logging.debug(f"Kinopoisk API response: {data}")
                    
                    items = data.get('items', [])
                    films_count = len(items)
                    logging.info(f"Found {films_count} films for query '{query}'")
                    
                    if items:
                        results = []
                        for film in items:
                            poster_url = film.get('posterUrl', '')
                            if not poster_url:
                                poster_url = film.get('posterUrlPreview', '')
                                
                            logging.info(f"Film: {film.get('nameRu', '')}, Poster URL: {poster_url}")
                            
                            # Build result with proper field mappings
                            result = {
                                'title': film.get('nameRu', film.get('nameEn', '')),
                                'url': f"https://www.kinopoisk.ru/film/{film['kinopoiskId']}/",
                                'year': film.get('year', ''),
                                'description': film.get('description', ''),
                                'filmId': film['kinopoiskId'],
                                'rating': film.get('ratingKinopoisk', ''),
                                'posterUrl': poster_url
                            }
                            results.append(result)
                        return results
                else:
                    response_text = await response.text()
                    logging.error(f"Kinopoisk API request failed, status: {status}, response: {response_text}")
    except Exception as e:
        logging.error(f"Error in search_kinopoisk: {e}", exc_info=True)
    
    return None

async def get_kinopoisk_data(movie_title):
    """Получение данных о фильме с Кинопоиска"""
    # Check cache first
    cached_data = get_movie_from_cache(movie_title)
    if cached_data is not None:
        logging.info(f"Returning cached movie data for '{movie_title}'")
        cached_data["cache_source"] = True
        return cached_data
    
    # Use the new search function
    search_results = await search_kinopoisk(movie_title)
    if not search_results:
        logging.info(f"No Kinopoisk results found for '{movie_title}'")
        return {}
    
    # Get the first result
    movie = search_results[0]
    
    # Create the formatted response
    kinopoisk_data_output = {
        "kinopoiskId": movie.get('filmId'),
        "nameRu": movie.get('title'),
        "year": movie.get('year'),
        "description": movie.get('description', 'Описание отсутствует'),
        "ratingKinopoisk": movie.get('rating'),
        "genres": [],  # Will be populated if available
        "countries": [],  # Will be populated if available
        "filmLength": None,  # Not available in basic search
        "posterUrlPreview": movie.get('posterUrl')
    }
    
    # Log the poster URL for debugging
    logging.info(f"Poster URL for '{movie_title}': {kinopoisk_data_output['posterUrlPreview']}")
    
    # Save to cache
    if kinopoisk_data_output["kinopoiskId"]:
        save_movie_to_cache(movie_title, kinopoisk_data_output)
        logging.info(f"Saved movie data to cache for '{movie_title}'")
    else:
        logging.warning(f"Missing kinopoiskId for '{movie_title}', not saving to cache")
    
    return kinopoisk_data_output 