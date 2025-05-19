import os
import json
import time
import logging
import hashlib

# Cache-related constants
CACHE_DIR = "cache"
POSTERS_DIR = os.path.join(CACHE_DIR, "posters")
MOVIE_DATA_CACHE = os.path.join(CACHE_DIR, "movie_data.json")
RUTUBE_CACHE = os.path.join(CACHE_DIR, "rutube_links.json")
CACHE_EXPIRY_DAYS = 21  # 3 weeks cache

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
        
        # Make a deep copy of links to avoid modifying cache
        links = []
        for link in cached_data['links']:
            links.append(dict(link))
            
        return links
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