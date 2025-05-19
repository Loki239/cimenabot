# CinemaBot

Telegram bot for searching movies and TV shows information via Kinopoisk API with streaming links from Rutube.

## Features

- Get movie information from Kinopoisk API (description, rating, genres, etc.)
- Find streaming links on Rutube
- View posters for movies
- Store search history and track movie views
- Comprehensive caching system to improve performance

## Setup

1. Clone the repository
2. Create a virtual environment and install dependencies:
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the following variables:
```
TELEGRAM_TOKEN=your_telegram_bot_token
KINOPOISK_TOKEN=your_kinopoisk_api_token
```

## Running the Bot

### Option 1: Using the start script (recommended)

The bot includes a start script that handles process management and ensures only one instance is running at a time.

```bash
./start_bot.sh
```

This script:
- Checks if any instances are already running
- Terminates existing instances if found
- Starts the bot in the background
- Logs output to `bot_output.log`

### Option 2: Running directly

```bash
python main.py
```

## Process Management

The bot now includes a PID file system to prevent multiple instances from running at the same time, which can cause Telegram API conflicts. A file called `bot.pid` stores the process ID of the running instance.

If you see the error: `Conflict: terminated by other getUpdates request; make sure that only one bot instance is running`, it means you have multiple bot instances trying to connect to the Telegram API. Use the start script to resolve this.

## Commands

- `/start` - Begin interaction with the bot
- `/help` - Display available commands
- `/settings` - View current search settings
- `/turn_links` - Toggle Rutube links search on/off
- `/turn_kp` - Toggle Kinopoisk search on/off
- `/history` - Show search history
- `/stats` - Show movie viewing statistics
- `/clear_cache` - Clear all cache
- `/clear_posters` - Clear poster cache
- `/clear_movie_data` - Clear movie data cache
- `/clear_rutube` - Clear Rutube links cache

## Project Structure

- `main.py` - Entry point and bot initialization
- `database.py` - Database operations
- `handlers/` - Command and message handlers
  - `commands.py` - Basic command handlers
  - `search.py` - Search functionality
  - `history.py` - History and stats handlers
- `utils/` - Utility functions
  - `api.py` - API communication
  - `cache.py` - Caching system
  - `helpers.py` - Helper functions

## Troubleshooting

If you encounter issues starting the bot:

1. Check if another instance is running: `ps aux | grep python`
2. Kill any existing bot processes: `pkill -f "python main.py"`
3. Remove the PID file if it exists: `rm bot.pid`
4. Check the log files for errors: `cat bot.log` and `cat bot_output.log`

## License

This project is licensed under the MIT License. 