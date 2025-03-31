from flask import Flask, render_template, request
import requests
from openpyxl import Workbook
from bs4 import BeautifulSoup
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import re

app = Flask(__name__)

# .env 파일에서 클라이언트 아이디와 시크릿을 불러오기
load_dotenv()

client_id = os.getenv('Client_id')
client_secret = os.getenv('Client_secret')

# 네이버 쇼핑 URL
SHOPPING_URL = 'https://shopping.naver.com/ns/home#SEARCH_LAYER'

# 결과를 저장할 폴더
RESULT_FOLDER = 'result'

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
        try:
            keyword_element = driver.find_element(By.XPATH, f'//*[@id="gnb-search-layer"]/div/div[4]/ul/li[{i}]')
            keyword_text = keyword_element.text.strip()
            tokens = keyword_text.split()
            keyword_clean = tokens[-1]

            hot_keywords.append(keyword_clean)
        except Exception as e:
            print(f"Error fetching rank {i}: {e}")

    return hot_keywords


# 네이버 쇼핑 상품 검색
def search_items(keyword, count):
    # 네이버 쇼핑 API URL
    url = f"https://openapi.naver.com/v1/search/shop.json?query={keyword}&display={count}&sort=sim"

    # API 호출 및 응답 받기
    headers = {
        'X-Naver-Client-Id': client_id,
        'X-Naver-Client-Secret': client_secret
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        items = data.get('items', [])

        # 상품 정보를 저장할 리스트 초기화
        results = []

        for item in items:
            title = item.get('title')
            clean_title = BeautifulSoup(title, "html.parser").get_text()  # HTML 태그 제거

            lprice = item.get('lprice')
            brand = item.get('brand')
            link = item.get('link')
            category1 = item.get('category1')

            results.append({
                'title': clean_title,
                'lprice': lprice,
                'brand': brand,
                'category': category1,
                'link': link
            })

        # 'result' 폴더가 없다면 생성
        if not os.path.exists(RESULT_FOLDER):
            os.makedirs(RESULT_FOLDER)

        # 파일 이름 정리 (특수 문자 제거)
        keyword_clean = re.sub(r'[\\/*?:"<>|]', '', keyword)  # 특수 문자 제거
        excel_filename = f"{RESULT_FOLDER}/{keyword_clean}({len(results)}).xlsx"

        # 엑셀 파일 생성
        wb = Workbook()
        ws = wb.active
        ws.title = "네이버 검색"

        headers = ['상품명', '가격', '브랜드', '카테고리', '링크']
        ws.append(headers)

        for item in results:
            ws.append([item['title'], item['lprice'], item['brand'], item['category'], item['link']])

        # 엑셀 파일 저장
        wb.save(excel_filename)

        return results, excel_filename
    else:
        return f"API 요청 실패: {response.status_code} - {response.text}"


@app.route('/', methods=['GET', 'POST'])
def home():
    hot_keywords = []
    excel_files = []

    # result 폴더에서 파일 목록 가져오기
    if os.path.exists(RESULT_FOLDER):
        excel_files = os.listdir(RESULT_FOLDER)

    if request.method == 'POST':
        # POST 요청이 오면 실시간 검색어를 갱신
        hot_keywords = get_hot_keywords()
    
    return render_template('index.html', hot_keywords=hot_keywords, excel_files=excel_files)

@app.route('/search', methods=['GET'])
def search():
    keyword = request.args.get('keyword')
    count = request.args.get('count')

    # 네이버 쇼핑 API를 호출하고 결과 처리
    results, excel_filename = search_items(keyword, count)

    # result 폴더에서 파일 목록 가져오기
    excel_files = os.listdir(RESULT_FOLDER)

    return render_template('result.html', results=results, excel_filename=excel_filename, excel_files=excel_files)


if __name__ == '__main__':
    app.run(debug=True)
