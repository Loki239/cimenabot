"""
CinemaBot - Telegram Bot for Movie and TV Show Information

This is the main entry point for the CinemaBot application. It initializes the bot,
connects to the Telegram API, sets up handlers, and starts the polling loop.

The bot provides movie information from Kinopoisk and streaming links from Rutube,
with a comprehensive caching system to optimize performance.
"""

import asyncio
import logging
import signal
import sys
import os
import aiohttp
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from database import Database
from utils.cache import init_cache_directories

# Import routers
from handlers.commands import router as commands_router
from handlers.history import router as history_router
from handlers.search import router as search_router

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# API Tokens from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# PID file to prevent multiple instances
PID_FILE = "bot.pid"

def check_pid_file():
    """Check if another instance is running by examining the PID file"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            
            # Check if process with this PID exists
            if os.name == 'posix':  # Unix/Linux/MacOS
                try:
                    os.kill(old_pid, 0)  # Signal 0 just checks if process exists
                    logging.error(f"Another bot instance is already running with PID {old_pid}. Exiting.")
                    sys.exit(1)
                except OSError:  # Process doesn't exist
                    logging.warning(f"Stale PID file found. Previous process (PID {old_pid}) is not running.")
            else:  # Windows or other OS
                logging.warning("PID checking not fully implemented for this OS. Proceeding with caution.")
        except Exception as e:
            logging.warning(f"Error reading PID file: {e}")
    
    # Create/update PID file with current process ID
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    logging.info(f"PID file created with process ID {os.getpid()}")

def remove_pid_file():
    """Remove PID file on exit"""
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
            logging.info("PID file removed")
        except Exception as e:
            logging.error(f"Error removing PID file: {e}")

# Initialize bot and dispatcher
if not TELEGRAM_TOKEN:
    logging.error("TELEGRAM_TOKEN not found in environment variables. Please set it in the .env file.")
    sys.exit(1)

bot = Bot(token=TELEGRAM_TOKEN)
# Use memory storage for state management
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Initialize database
db = Database()

# Register routers
dp.include_router(commands_router)
dp.include_router(history_router)
dp.include_router(search_router)

# Middleware to pass database to handlers
@dp.update.middleware()
async def database_middleware(handler, event, data):
    """Pass database instance to all handlers that expect it"""
    data["db"] = db
    return await handler(event, data)

async def main():
    """
    Main application function that initializes the bot and starts polling.
    
    Sets up signal handlers for graceful shutdown, initializes cache directories
    and database, establishes connection with Telegram API, and starts the bot.
    """
    # Check for other running instances
    check_pid_file()

    # Set up signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
    
    # Initialize cache directories
    init_cache_directories()
    
    # Initialize database
    logging.info("Инициализация базы данных")
    await db.init()
    
    # Connect to Telegram
    try:
        me = await bot.get_me()
        logging.info("Соединение с Telegram API установлено. Бот: @%s (%s)", me.username, me.id)
    except Exception as e:
        logging.error("Ошибка соединения с Telegram API: %s", e)
        remove_pid_file()
        sys.exit(1)
    
    # Start the bot
    logging.info("Запуск бота")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

async def shutdown():
    """
    Gracefully shuts down the bot and closes connections.
    
    This function is called when the bot receives a termination signal
    (SIGINT or SIGTERM).
    """
    logging.info("Завершение работы бота...")
    await bot.session.close()
    remove_pid_file()
    sys.exit(0)

if __name__ == '__main__':
    try:
        timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_connect=10, sock_read=10)
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
        remove_pid_file()
    except Exception as e:
        logging.error("Неожиданная ошибка: %s", e)
        remove_pid_file()
        sys.exit(1) 