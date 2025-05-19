"""
Helper Functions Module for CinemaBot

This module contains various utility functions used throughout the bot application.
These functions are not specific to any particular feature but provide common
functionality like text formatting, rating visualization, and command detection.
"""

import html
from datetime import datetime

def separator(text: str = "") -> str:
    """
    Return a separator line, optionally with text in the middle.
    
    This function creates visual separators in messages to improve readability.
    
    Args:
        text (str, optional): Text to include in the middle of the separator. Defaults to "".
    
    Returns:
        str: A formatted separator line
    
    Examples:
        >>> separator()
        "────────────"
        >>> separator("Title")
        "────── Title ──────"
    """
    return f"────── {text} ──────" if text else "────────────"

def rating_stars(rating: float) -> str:
    """
    Convert a numeric rating to a star representation.
    
    Args:
        rating (float): A numeric rating, typically on a scale of 0-10
    
    Returns:
        str: A string of stars representing the rating:
             - ⭐ for full stars
             - ✨ for half stars
             - ☆ for empty stars
    
    Examples:
        >>> rating_stars(7.5)
        "⭐⭐⭐✨☆"
        >>> rating_stars(None)
        "☆☆☆☆☆"
    """
    if not rating:
        return "☆" * 5
    full_stars = int(rating // 2)
    half_star = int(rating % 2 >= 0.5)
    return '⭐' * full_stars + '✨' * half_star + '☆' * (5 - full_stars - half_star)

def format_datetime(iso_date: str) -> str:
    """
    Format ISO datetime to a more readable format.
    
    Args:
        iso_date (str): Date in ISO format (e.g. "2023-05-19T15:30:45.123456")
    
    Returns:
        str: Formatted date (e.g. "19.05.2023 15:30")
    """
    dt = datetime.fromisoformat(iso_date)
    return dt.strftime("%d.%m.%Y %H:%M")
    
def pluralize_times(count: int) -> str:
    """
    Pluralize the Russian word 'раз' based on count.
    
    This function implements Russian grammatical rules for pluralization.
    
    Args:
        count (int): The number to determine the correct pluralization form
    
    Returns:
        str: "раз", "раза", or "раз" depending on the count
    
    Examples:
        >>> pluralize_times(1)
        "раз"
        >>> pluralize_times(2)
        "раза"
        >>> pluralize_times(5)
        "раз"
    """
    if count % 10 == 1 and count % 100 != 11:
        return "раз"
    elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
        return "раза"
    else:
        return "раз"

def is_command_without_slash(text):
    """
    Check if text looks like a command but without the leading slash.
    
    This helps detect when users forget to add the slash prefix to commands.
    
    Args:
        text (str): The text to check
    
    Returns:
        bool: True if the text matches a known command without slash, False otherwise
    """
    command_keywords = [
        "clear_cache", "clear_posters", "clear_movie_data", "clear_rutube", 
        "start", "help", "settings", "history", "stats", "turn_links", "turn_kp"
    ]
    # Strip any spaces and convert to lowercase
    text = text.strip().lower()
    return text in command_keywords

def get_source_status(links_on, kp_on):
    """
    Return a formatted string describing the enabled search sources.
    
    Args:
        links_on (bool): Whether Rutube links search is enabled
        kp_on (bool): Whether Kinopoisk search is enabled
    
    Returns:
        str: A formatted string showing the status of each search source
    """
    return (
        f"{'✅' if links_on else '❌'} Поиск ссылок (Rutube)\n"
        f"{'✅' if kp_on else '❌'} Поиск в Кинопоиске"
    ) 