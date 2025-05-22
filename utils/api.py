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
    url = "https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword"
    
    # Get API key and log if it's missing
    api_key = os.getenv("KINOPOISK_TOKEN")
    if not api_key:
        logging.error("KINOPOISK_TOKEN environment variable is not set or empty")
        return None
        
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    logging.info(f"Searching Kinopoisk for: '{query}' using URL: {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={'keyword': query}, headers=headers) as response:
                status = response.status
                logging.info(f"Kinopoisk API response status: {status}")
                
                if status == 200:
                    data = await response.json()
                    films = data.get('films', [])
                    films_count = len(films)
                    logging.info(f"Found {films_count} films for query '{query}'")
                    
                    if films:
                        # Log the first 3 results for debugging
                        for i, film in enumerate(films[:3]):
                            name_ru = film.get('nameRu', '')
                            name_en = film.get('nameEn', '')
                            year = film.get('year', '')
                            logging.info(f"Search result #{i+1}: {name_ru} / {name_en} ({year})")
                        
                        return [{
                            'title': film.get('nameRu', film.get('nameEn', '')),
                            'url': f"https://www.kinopoisk.ru/film/{film['filmId']}/",
                            'year': film.get('year', ''),
                            'description': film.get('description', ''),
                            'filmId': film['filmId'],
                            'rating': film.get('rating', ''),
                            'posterUrl': film.get('posterUrl', '')
                        } for film in films]
                else:
                    response_text = await response.text()
                    logging.error(f"Kinopoisk API request failed, status: {status}, response: {response_text}")
    except Exception as e:
        logging.error(f"Error in search_kinopoisk: {e}", exc_info=True)
    
    return None

async def get_film_details(film_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed information about a film by its ID"""
    url = f"https://kinopoiskapiunofficial.tech/api/v2.2/films/{film_id}"
    
    api_key = os.getenv("KINOPOISK_TOKEN")
    if not api_key:
        logging.error("KINOPOISK_TOKEN environment variable is not set or empty")
        return None
        
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    
    logging.info(f"Fetching film details for ID: {film_id}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                status = response.status
                
                if status == 200:
                    data = await response.json()
                    logging.info(f"Successfully fetched details for film ID: {film_id}")
                    return data
                else:
                    response_text = await response.text()
                    logging.error(f"Failed to fetch film details, status: {status}, response: {response_text}")
    except Exception as e:
        logging.error(f"Error in get_film_details: {e}", exc_info=True)
    
    return None

async def get_kinopoisk_data(movie_title):
    """Получение данных о фильме с Кинопоиска"""
    # Check cache first
    cached_data = get_movie_from_cache(movie_title)
    if cached_data is not None:
        logging.info(f"Returning cached movie data for '{movie_title}'")
        cached_data["cache_source"] = True
        return cached_data
    
    # Use the search function
    search_results = await search_kinopoisk(movie_title)
    if not search_results:
        logging.info(f"No Kinopoisk results found for '{movie_title}'")
        return {}
    
    # Try to find an exact match first
    exact_match = find_exact_match(search_results, movie_title)
    if exact_match:
        movie = exact_match
        logging.info(f"Found exact match for '{movie_title}': {movie.get('title')}")
    else:
        # Get the first result if no exact match
        movie = search_results[0]
        logging.info(f"Using first result for '{movie_title}': {movie.get('title')}")
    
    film_id = movie.get('filmId')
    
    # Initialize the output with basic info
    kinopoisk_data_output = {
        "kinopoiskId": film_id,
        "nameRu": movie.get('title'),
        "year": movie.get('year'),
        "description": movie.get('description', 'Описание отсутствует'),
        "ratingKinopoisk": movie.get('rating'),
        "genres": [],
        "countries": [],
        "filmLength": None,
        "posterUrlPreview": movie.get('posterUrl')
    }
    
    # Get detailed information if we have a film ID
    if film_id:
        details = await get_film_details(film_id)
        if details:
            # Update with detailed information
            kinopoisk_data_output["description"] = details.get("description", "Описание отсутствует")
            kinopoisk_data_output["ratingKinopoisk"] = details.get("ratingKinopoisk")
            kinopoisk_data_output["filmLength"] = details.get("filmLength")
            
            # Format genres
            if "genres" in details:
                kinopoisk_data_output["genres"] = [{"genre": g.get("genre")} for g in details.get("genres", [])]
                
            # Format countries
            if "countries" in details:
                kinopoisk_data_output["countries"] = [{"country": c.get("country")} for c in details.get("countries", [])]
                
            # Update poster if available
            if details.get("posterUrl"):
                kinopoisk_data_output["posterUrlPreview"] = details.get("posterUrl")
            elif details.get("posterUrlPreview"):
                kinopoisk_data_output["posterUrlPreview"] = details.get("posterUrlPreview")
    
    # Log the poster URL for debugging
    logging.info(f"Poster URL for '{movie_title}': {kinopoisk_data_output['posterUrlPreview']}")
    
    # Save to cache
    if kinopoisk_data_output["kinopoiskId"]:
        save_movie_to_cache(movie_title, kinopoisk_data_output)
        logging.info(f"Saved movie data to cache for '{movie_title}'")
    else:
        logging.warning(f"Missing kinopoiskId for '{movie_title}', not saving to cache")
    
    return kinopoisk_data_output

def find_exact_match(search_results: List[Dict[str, Any]], query: str) -> Optional[Dict[str, Any]]:
    """Find an exact match for a movie title in search results"""
    # Clean up query for matching
    query_clean = query.lower().strip()
    
    # Special case for some popular movie titles with translations
    special_titles = {
        'venom': ['веном', 'venom'],
        'веном': ['веном', 'venom'],
        'avatar': ['аватар', 'avatar'],
        'аватар': ['аватар', 'avatar'],
        'spider-man': ['человек-паук', 'spider-man', 'spiderman'],
        'человек-паук': ['человек-паук', 'spider-man', 'spiderman'],
        'spiderman': ['человек-паук', 'spider-man', 'spiderman'],
        'matrix': ['матрица', 'matrix'],
        'матрица': ['матрица', 'matrix'],
        'star wars': ['звездные войны', 'star wars'],
        'звездные войны': ['звездные войны', 'star wars'],
        'avengers': ['мстители', 'avengers'],
        'мстители': ['мстители', 'avengers'],
        'terminator': ['терминатор', 'terminator'],
        'терминатор': ['терминатор', 'terminator'],
    }
    
    # Get alternative titles to check
    alt_titles = special_titles.get(query_clean, [query_clean])
    logging.info(f"Searching for exact matches with terms: {alt_titles}")
    
    # First priority: exact title match
    for result in search_results:
        title_ru = result.get('title', '').lower().strip()
        title_en = ''
        
        # Try to get English title if present
        if 'nameEn' in result:
            title_en = result.get('nameEn', '').lower().strip()
        
        for alt in alt_titles:
            # Check for exact matches
            if alt == title_ru or alt == title_en:
                logging.info(f"Found exact title match: {result.get('title')}")
                return result
    
    # Second priority: titles containing the search term
    for result in search_results:
        title_ru = result.get('title', '').lower().strip()
        
        # For special cases like Venom, check if the title contains the search term
        for alt in alt_titles:
            # For specific popular titles, do an exact word match
            if any(alt == word for word in title_ru.split()):
                logging.info(f"Found word match in title: {result.get('title')}")
                return result
    
    # Third priority: titles containing the search term as substring
    for result in search_results:
        title_ru = result.get('title', '').lower().strip()
        
        for alt in alt_titles:
            if alt in title_ru:
                logging.info(f"Found substring match in title: {result.get('title')}")
                return result
    
    logging.info("No exact match found, using first result")
    return None 