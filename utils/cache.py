import os
import json
import time
import logging
import hashlib
import shutil
import asyncio
from typing import Dict, List, Optional, Any, Union

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

async def clear_cache() -> str:
    """Clear all cache directories and files"""
    try:
        # Clear poster directory
        cleared_posters = await clear_posters()
        
        # Clear movie data
        cleared_movie_data = await clear_movie_data()
        
        # Clear Rutube links
        cleared_rutube = await clear_rutube()
        
        total_cleared = cleared_posters + cleared_movie_data + cleared_rutube
        logging.info("Cleared all cache: %s files", total_cleared)
        return f"Cleared {total_cleared} cached items"
    except Exception as e:
        logging.error("Failed to clear cache: %s", e)
        return f"Error clearing cache: {e}"

async def clear_posters() -> int:
    """Clear poster cache"""
    try:
        count = 0
        if os.path.exists(POSTERS_DIR):
            for file in os.listdir(POSTERS_DIR):
                file_path = os.path.join(POSTERS_DIR, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        count += 1
                except Exception as e:
                    logging.error("Error deleting poster file %s: %s", file_path, e)
        logging.info("Cleared %s poster files", count)
        return count
    except Exception as e:
        logging.error("Failed to clear posters: %s", e)
        return 0

async def clear_movie_data() -> int:
    """Clear movie data cache"""
    try:
        if os.path.exists(MOVIE_DATA_CACHE):
            with open(MOVIE_DATA_CACHE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            logging.info("Cleared movie data cache")
            return 1
        return 0
    except Exception as e:
        logging.error("Failed to clear movie data: %s", e)
        return 0

async def clear_rutube() -> int:
    """Clear Rutube links cache"""
    try:
        if os.path.exists(RUTUBE_CACHE):
            with open(RUTUBE_CACHE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            logging.info("Cleared Rutube links cache")
            return 1
        return 0
    except Exception as e:
        logging.error("Failed to clear Rutube links: %s", e)
        return 0

# Export all cache clear functions
__all__ = [
    'init_cache_directories', 
    'clear_cache', 
    'clear_posters', 
    'clear_movie_data', 
    'clear_rutube',
    'get_movie_from_cache',
    'save_movie_to_cache',
    'get_rutube_from_cache',
    'save_rutube_to_cache',
    'get_cached_poster_path',
    'save_poster_to_cache',
    'CACHE_DIR',
    'POSTERS_DIR',
    'MOVIE_DATA_CACHE',
    'RUTUBE_CACHE'
] 