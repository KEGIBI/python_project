from flask import Flask, render_template, request
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

app = Flask(__name__)

SHOPPING_URL = 'https://shopping.naver.com/ns/home#SEARCH_LAYER'

# 네이버 쇼핑에서 인기 검색어를 크롤링하는 함수
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
        try: # //*[@id="gnb-search-layer"]/div/div[4]/ul/li[1]
            keyword_element = driver.find_element(By.XPATH, f'//*[@id="gnb-search-layer"]/div/div[4]/ul/li[{i}]')                                                                                                                                               
            keyword_text = keyword_element.text.strip()
            tokens = keyword_text.split()
            # 토큰 배열의 마지막 요소만 쓰기
            keyword_clean = tokens[-1]

            hot_keywords.append(keyword_clean)
        except Exception as e:
            print(f"Error fetching rank {i}: {e}")

    return hot_keywords

# 기본 홈 페이지
@app.route('/', methods=['GET', 'POST'])
def home():
    hot_keywords = []
    if request.method == 'POST':
        # POST 요청이 오면 실시간 검색어를 갱신
        hot_keywords = get_hot_keywords()
    return render_template('index.html', hot_keywords=hot_keywords)

# 앱 실행
if __name__ == '__main__':
    app.run(debug=True)
