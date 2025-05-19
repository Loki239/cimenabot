# Cinema Bot

A Telegram bot that searches for movies and TV shows, providing information from Kinopoisk and links to watch online for free.

## Setup

1. Clone this repository
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```
3. Set up your environment variables by running:
   ```
   python create_env.py
   ```
   This will create a `.env` file with your API tokens.

4. Run the bot:
   ```
   ./run.py
   ```
   This script ensures only one instance of the bot is running.

## Running the Bot

The bot can be managed using these commands:

- **Start the bot**: `./run.py`
- **View logs**: `tail -f bot.log`
- **Stop the bot**: `pkill -f "python bot.py"`

If you encounter "Conflict" errors, it means multiple instances of the bot are running. Use the run script to automatically handle this.

## API Keys Required

- **Telegram Bot Token**: Get from [BotFather](https://t.me/botfather)
- **Kinopoisk API Token**: Get from [Kinopoisk API](https://api.kinopoisk.dev/)

## Features

- Search for movies and TV shows by simply typing the name
- Get information like title, year, rating, countries, and genres
- View movie descriptions from Kinopoisk
- Find links to websites where you can watch content for free without registration
- View your search history with `/history` command
- Check statistics of which movies you've looked up most with `/stats` command
- Enable/disable different search sources with `/turn_links` and `/turn_kp` commands

## Database

The bot uses SQLite to store:
- User search history
- Movie view statistics 
- Movie descriptions

All data is stored per user, so each user has their own history and statistics. 