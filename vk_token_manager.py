import requests
from dotenv import load_dotenv, set_key
import os
import sys
from datetime import datetime
import logging
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vk_token.log'),
        logging.StreamHandler()
    ]
)

def load_env_file():
    """Загрузка и проверка переменных окружения"""
    load_dotenv()
    required_vars = ["VK_APP_ID", "VK_CLIENT_SECRET", "VK_REDIRECT_URI", "VK_SCOPE", "VK_TOKEN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logging.error(f"Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
        return None
    
    return {var: os.getenv(var) for var in required_vars}

def update_env_file(token):
    """Обновление токена в .env файле"""
    try:
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        set_key(env_path, 'VK_TOKEN', token)
        logging.info("Токен успешно обновлен в .env файле")
        return True
    except Exception as e:
        logging.error(f"Ошибка при обновлении .env файла: {e}")
        return False

def check_token(token):
    """Проверка валидности токена"""
    url = "https://api.vk.com/method/users.get"
    params = {
        "access_token": token,
        "v": "5.131",
        "fields": "id"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if "error" in data:
            logging.error(f"Ошибка проверки токена: {data['error']['error_msg']}")
            return False
        return True
    except Exception as e:
        logging.error(f"Ошибка при проверке токена: {str(e)}")
        return False

def get_token_from_service():
    """Получение токена через сервисный аккаунт"""
    env_vars = load_env_file()
    if not env_vars:
        return None

    try:
        response = requests.get(
            "https://oauth.vk.com/access_token",
            params={
                "client_id": env_vars["VK_APP_ID"],
                "client_secret": env_vars["VK_CLIENT_SECRET"],
                "grant_type": "client_credentials",
                "v": "5.131"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                return data["access_token"]
            logging.error(f"Нет токена в ответе: {data}")
            return None
        else:
            logging.error(f"Ошибка получения сервисного токена: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Ошибка при получении сервисного токена: {str(e)}")
        return None

def refresh_token_if_needed():
    """Проверка и обновление токена при необходимости"""
    env_vars = load_env_file()
    if not env_vars:
        return False

    current_token = env_vars["VK_TOKEN"]
    
    # Проверяем текущий токен
    if check_token(current_token):
        logging.info("Текущий токен валиден")
        return True
    
    # Пробуем получить новый токен
    logging.info("Получение нового токена...")
    new_token = get_token_from_service()
    
    if new_token and update_env_file(new_token):
        logging.info("Токен успешно обновлен")
        return True
    
    logging.error("Не удалось обновить токен")
    return False

def run_token_monitor(check_interval=21600):  # 6 часов = 21600 секунд
    """Запуск мониторинга токена с заданным интервалом"""
    logging.info(f"Запуск мониторинга токена (интервал: {check_interval} секунд)")
    
    while True:
        refresh_token_if_needed()
        time.sleep(check_interval)

if __name__ == "__main__":
    if "--monitor" in sys.argv:
        run_token_monitor()
    else:
        refresh_token_if_needed() 