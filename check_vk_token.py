import requests

def check_vk_token(token):
    # URL для проверки токена (запрос информации о пользователе)
    url = "https://api.vk.com/method/users.get"
    params = {
        "access_token": token,
        "v": "5.131",
        "fields": "id,first_name,last_name"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if "error" in data:
            print(f"Ошибка: {data['error']['error_msg']}")
        else:
            user = data["response"][0]
            print(f"Токен действителен. Информация о пользователе:")
            print(f"ID: {user['id']}")
            print(f"Имя: {user['first_name']} {user['last_name']}")
    except Exception as e:
        print(f"Ошибка при запросе: {str(e)}")

# Пример использования
if __name__ == "__main__":
    # Замените на ваш токен
    token = "vk1.a.Iq-YaZ9dbFUEWS34h_sXQIggY1uBymNVgEH-Eis9TewjRLDbJLiikBcHMOLnuXvtUwnrElFyxAg1k4SNmK0RpOj1vepE3PwwCRGNshYqc9GOf_z5133quAVtgIB_Ocy3wMyyU4wkt29T2h19skIkvixQsSMPWcEf_87MJo8Tp4EFYOE4jVsGWGkwByKrG76L"
    check_vk_token(token)