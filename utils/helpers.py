import html
from datetime import datetime

def separator(text: str = "") -> str:
    """Return a separator line, optionally with text in the middle"""
    return f"────── {text} ──────" if text else "────────────"

def rating_stars(rating: float) -> str:
    """Convert numeric rating to star representation"""
    if not rating:
        return "☆" * 5
    full_stars = int(rating // 2)
    half_star = int(rating % 2 >= 0.5)
    return '⭐' * full_stars + '✨' * half_star + '☆' * (5 - full_stars - half_star)

def format_datetime(iso_date: str) -> str:
    """Format ISO datetime to a more readable format"""
    dt = datetime.fromisoformat(iso_date)
    return dt.strftime("%d.%m.%Y %H:%M")
    
def pluralize_times(count: int) -> str:
    """Pluralize Russian word 'раз' based on count"""
    if count % 10 == 1 and count % 100 != 11:
        return "раз"
    elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
        return "раза"
    else:
        return "раз"

def is_command_without_slash(text):
    """Check if text looks like a command but without the leading slash"""
    command_keywords = [
        "clear_cache", "clear_posters", "clear_movie_data", "clear_rutube", 
        "start", "help", "settings", "history", "stats", "turn_links", "turn_kp"
    ]
    # Strip any spaces and convert to lowercase
    text = text.strip().lower()
    return text in command_keywords

def get_source_status(links_on, kp_on):
    """Return a formatted string describing the enabled search sources"""
    return (
        f"{'✅' if links_on else '❌'} Поиск ссылок (Rutube)\n"
        f"{'✅' if kp_on else '❌'} Поиск в Кинопоиске"
    ) 