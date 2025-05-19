#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting CinemaBot...${NC}"

# First, make sure to stop all existing bot instances
echo -e "${YELLOW}Stopping any existing instances...${NC}"
./stop_all_bots.sh

# Make sure no Python processes for this bot are running
echo -e "${YELLOW}Double-checking no processes are running...${NC}"
PROCESSES=$(ps aux | grep -E "python.*main\.py" | grep -v grep | awk '{print $2}')
if [ -n "$PROCESSES" ]; then
    echo -e "${RED}Some bot processes are still running. Trying to force kill...${NC}"
    pkill -9 -f "python main.py" || true
    sleep 2
fi

# Start the bot in the background
echo -e "${GREEN}Starting new bot instance...${NC}"
python main.py > bot_output.log 2>&1 &

# Wait a moment to make sure it started
sleep 3

# Check if it's running
if [ -f bot.pid ]; then
    new_pid=$(cat bot.pid)
    if ps -p $new_pid > /dev/null; then
        echo -e "${GREEN}Bot started successfully with PID $new_pid${NC}"
        echo -e "${YELLOW}Logs are being written to bot_output.log${NC}"
        echo -e "${YELLOW}To check logs: ${NC}tail -f bot_output.log"
        echo -e "${YELLOW}To stop the bot: ${NC}./stop_all_bots.sh"
    else
        echo -e "${RED}Bot failed to start properly. Check bot_output.log for details${NC}"
    fi
else
    echo -e "${RED}Bot failed to start. PID file not created. Check bot_output.log for details${NC}"
fi 