import requests

APP_ID = "53534552"
CLIENT_SECRET = "oS2GQv1dWsMYYhKU9gcN"
REDIRECT_URI = "https://oauth.vk.com/blank.html"
SCOPE = "video"  # нужные права

# 1. Получение кода авторизации (пользователь должен перейти по ссылке)
auth_url = f"https://oauth.vk.com/authorize?client_id={APP_ID}&display=page&redirect_uri={REDIRECT_URI}&scope={SCOPE}&response_type=code&v=5.131"
print("Перейдите по ссылке:", auth_url)

# 2. После авторизации получите code из URL и обменяйте на токен
CODE = "0fc760506bcf2bea65"  # из URL после авторизации

response = requests.get(
    "https://oauth.vk.com/access_token",
    params={
        "client_id": APP_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": CODE,
    }
)

access_token = response.json()["access_token"]
print("Токен:", access_token)