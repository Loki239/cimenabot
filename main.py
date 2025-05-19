import asyncio
import aiohttp
import logging
import signal
import sys
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
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

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Initialize database
db = Database()

# Register routers
dp.include_router(commands_router)
dp.include_router(history_router)
dp.include_router(search_router)

async def main():
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
        logging.info(f"Соединение с Telegram API установлено. Бот: @{me.username} ({me.id})")
    except Exception as e:
        logging.error(f"Ошибка соединения с Telegram API: {e}")
        sys.exit(1)
    
    # Start the bot
    logging.info("Запуск бота")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

async def shutdown():
    logging.info("Завершение работы бота...")
    await bot.session.close()
    sys.exit(0)

if __name__ == '__main__':
    try:
        timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_connect=10, sock_read=10)
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
    except Exception as e:
        logging.error(f"Неожиданная ошибка: {e}")
        sys.exit(1) 