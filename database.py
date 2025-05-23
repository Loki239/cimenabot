"""
Database Module for CinemaBot

This module handles all database operations for the CinemaBot, including:
- Initializing the database schema
- Storing and retrieving search history
- Tracking movie view statistics
- Storing movie information

The module uses SQLite through aiosqlite for asynchronous database operations.
Each user has their own search history and movie statistics.
"""

import aiosqlite
import logging
from datetime import datetime

class Database:
    """
    Database handler for CinemaBot.
    
    This class manages all interactions with the SQLite database, providing
    asynchronous methods for storing and retrieving user data, search history,
    and movie statistics.
    
    Attributes:
        db_path (str): Path to the SQLite database file
    """
    
    def __init__(self, db_path='cinema_bot.db'):
        """
        Initialize Database handler.
        
        Args:
            db_path (str, optional): Path to the database file. Defaults to 'cinema_bot.db'.
        """
        self.db_path = db_path
        
    async def init(self):
        """
        Initialize database tables if they don't exist.
        
        Creates the following tables:
        - searches: Stores user search history
        - movies: Stores movie information and view counts
        
        Also adds the description column to the movies table if it doesn't exist.
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Create searches table to store search history
            await db.execute('''
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    query TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            # Create movies table to store movie statistics
            await db.execute('''
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    year TEXT,
                    kinopoisk_id TEXT,
                    description TEXT,
                    count INTEGER DEFAULT 1,
                    last_shown TEXT NOT NULL
                )
            ''')
            
            # Check if description column exists in movies table
            async with db.execute("PRAGMA table_info(movies)") as cursor:
                columns = await cursor.fetchall()
                has_description = any(col[1] == 'description' for col in columns)
                
            # Add description column if it doesn't exist
            if not has_description:
                logging.info("Adding description column to movies table")
                await db.execute("ALTER TABLE movies ADD COLUMN description TEXT")
            
            await db.commit()
            logging.info("Database initialized")
    
    async def add_search(self, user_id, query):
        """
        Add a search query to the user's history.
        
        Args:
            user_id (int): Telegram user ID
            query (str): The search query text
            
        Returns:
            None
        """
        async with aiosqlite.connect(self.db_path) as db:
            timestamp = datetime.now().isoformat()
            await db.execute(
                "INSERT INTO searches (user_id, query, timestamp) VALUES (?, ?, ?)",
                (user_id, query, timestamp)
            )
            await db.commit()
            logging.info(f"Added search from user {user_id}: {query}")
    
    async def add_movie(self, user_id, title, year=None, description=None):
        """
        Add or update a movie in the statistics.
        
        If the movie already exists for this user, increment its count.
        Otherwise, create a new record.
        
        Args:
            user_id (int): Telegram user ID
            title (str): Movie title
            year (str, optional): Release year. Defaults to None.
            description (str, optional): Movie description. Defaults to None.
            
        Returns:
            None
        """
        async with aiosqlite.connect(self.db_path) as db:
            timestamp = datetime.now().isoformat()
            
            # Check if movie already exists for this user
            async with db.execute(
                "SELECT id, count FROM movies WHERE user_id = ? AND title = ?",
                (user_id, title)
            ) as cursor:
                movie = await cursor.fetchone()
                
                if movie:
                    # Update existing movie count
                    movie_id, count = movie
                    await db.execute(
                        "UPDATE movies SET count = ?, last_shown = ?, description = ? WHERE id = ?",
                        (count + 1, timestamp, description, movie_id)
                    )
                else:
                    # Add new movie
                    await db.execute(
                        "INSERT INTO movies (user_id, title, year, description, last_shown) VALUES (?, ?, ?, ?, ?)",
                        (user_id, title, year, description, timestamp)
                    )
            
            await db.commit()
            logging.info(f"Updated stats for movie '{title}' for user {user_id}")
    
    async def get_search_history(self, user_id, limit=10):
        """
        Get user's search history.
        
        Args:
            user_id (int): Telegram user ID
            limit (int, optional): Maximum number of history items to return. Defaults to 10.
            
        Returns:
            list: List of dictionaries containing search history items
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT query, timestamp FROM searches WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            ) as cursor:
                return [dict(row) for row in await cursor.fetchall()]
    
    async def get_movie_stats(self, user_id):
        """
        Get statistics of movies shown to a user.
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            list: List of dictionaries containing movie statistics
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT title, year, count, description FROM movies WHERE user_id = ? ORDER BY count DESC",
                (user_id,)
            ) as cursor:
                return [dict(row) for row in await cursor.fetchall()] 