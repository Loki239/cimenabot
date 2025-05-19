#!/bin/bash

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping all bot instances...${NC}"

# Remove the PID file if it exists
if [ -f bot.pid ]; then
    echo -e "${YELLOW}Removing PID file${NC}"
    rm -f bot.pid
fi

# Find and kill all Python processes running main.py
PROCESSES=$(ps aux | grep -E "python.*main\.py" | grep -v grep | awk '{print $2}')

if [ -z "$PROCESSES" ]; then
    echo -e "${GREEN}No bot processes found running${NC}"
else
    echo -e "${YELLOW}Found the following bot processes:${NC}"
    ps aux | grep -E "python.*main\.py" | grep -v grep
    
    # Kill each process
    for pid in $PROCESSES; do
        echo -e "${YELLOW}Killing process $pid${NC}"
        kill $pid 2>/dev/null
        sleep 1
        
        # Check if it's still running
        if ps -p $pid > /dev/null; then
            echo -e "${RED}Process $pid didn't terminate gracefully. Force killing...${NC}"
            kill -9 $pid 2>/dev/null
        else
            echo -e "${GREEN}Process $pid terminated${NC}"
        fi
    done
fi

# Double check no processes are left
REMAINING=$(ps aux | grep -E "python.*main\.py" | grep -v grep | awk '{print $2}')
if [ -z "$REMAINING" ]; then
    echo -e "${GREEN}All bot processes successfully terminated${NC}"
else
    echo -e "${RED}Warning: Some processes couldn't be terminated. Manual intervention needed.${NC}"
    ps aux | grep -E "python.*main\.py" | grep -v grep
fi

# Clean up any leftover files
echo -e "${YELLOW}Cleaning up leftover files...${NC}"
rm -f bot.pid 