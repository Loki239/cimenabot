#!/bin/bash

BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$BOT_DIR/vk_token.log"
PID_FILE="$BOT_DIR/.token_monitor.pid"
PYTHON_SCRIPT="$BOT_DIR/vk_token_manager.py"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo "$1"
}

check_dependencies() {
    if [ ! -f "$BOT_DIR/.env" ]; then
        log "Ошибка: Файл .env не найден"
        exit 1
    fi

    if [ ! -f "$PYTHON_SCRIPT" ]; then
        log "Ошибка: Файл vk_token_manager.py не найден"
        exit 1
    fi
}

start_monitor() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log "Монитор токена уже запущен (PID: $pid)"
            exit 0
        else
            rm "$PID_FILE"
        fi
    fi

    log "Запуск монитора токена..."
    nohup python3 "$PYTHON_SCRIPT" --monitor > /dev/null 2>&1 &
    echo $! > "$PID_FILE"
    log "Монитор токена запущен (PID: $!)"
}

stop_monitor() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid"
            rm "$PID_FILE"
            log "Монитор токена остановлен (PID: $pid)"
        else
            log "Процесс монитора не найден"
            rm "$PID_FILE"
        fi
    else
        log "PID файл не найден"
    fi
}

status_monitor() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log "Монитор токена работает (PID: $pid)"
        else
            log "Монитор токена не работает (найден устаревший PID файл)"
            rm "$PID_FILE"
        fi
    else
        log "Монитор токена не запущен"
    fi
}

case "$1" in
    start)
        check_dependencies
        start_monitor
        ;;
    stop)
        stop_monitor
        ;;
    restart)
        stop_monitor
        sleep 2
        check_dependencies
        start_monitor
        ;;
    status)
        status_monitor
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0 