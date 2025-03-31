from flask import Flask, redirect, request, render_template
import requests
from urllib.parse import urlencode
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time

app = Flask(__name__)

# 네이버에서 발급받은 Client ID와 Client Secret
CLIENT_ID = '3ktA9pOnQfsTwhRJErIO'
CLIENT_SECRET = '19RY3hTp_w'
REDIRECT_URI = 'http://localhost:5000/callback'  # Callback URL

# 네이버 로그인 API URL
AUTH_URL = 'https://nid.naver.com/oauth2.0/authorize'
TOKEN_URL = 'https://nid.naver.com/oauth2.0/token'
USER_INFO_URL = 'https://openapi.naver.com/v1/nid/me'

# 네이버 쇼핑 URL
SHOPPING_URL = 'https://shopping.naver.com/ns/home#SEARCH_LAYER'

# Selenium으로 네이버 쇼핑 인기 검색어 크롤링
def get_hot_keywords():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)  # 브라우저 창 유지
    options.add_argument("--window-size=800,500")  
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get(SHOPPING_URL)
    time.sleep(5)  # 페이지 로딩 대기

    hot_keywords = []
    
    # 인기 검색어 크롤링 (1~10위)
    for i in range(1, 11):
        try:
            keyword_element = driver.find_element(By.XPATH, f'//a[@data-shp-contents-rank="{i}"]')
            keyword_text = keyword_element.text.strip()
            hot_keywords.append((i, keyword_text))
        except Exception as e:
            print(f"Error fetching rank {i}: {e}")

    # 창 유지: driver.quit() 제거

    return hot_keywords

# 네이버 로그인 페이지로 리디렉션
@app.route('/')
def home():
    auth_params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'state': 'random_state',
    }
    auth_url = f"{AUTH_URL}?{urlencode(auth_params)}"
    return redirect(auth_url)

# 네이버 로그인 후 리디렉션된 URL을 처리 (액세스 토큰 획득)
@app.route('/callback')
def callback():
    code = request.args.get('code')
    state = request.args.get('state')

    # 액세스 토큰 요청
    token_params = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'state': state
    }

    response = requests.post(TOKEN_URL, data=token_params)
    token_data = response.json()

    access_token = token_data.get('access_token')
    if not access_token:
        return "로그인 실패"

    # 핫키워드 가져오기
    hot_keywords = get_hot_keywords()

    # shopping.html로 데이터 전달
    return render_template('shopping.html', hot_keywords=hot_keywords)

if __name__ == '__main__':
    app.run(debug=True)
