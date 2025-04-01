from flask import Flask, render_template, request, send_file, jsonify, redirect
import requests
from openpyxl import Workbook
from bs4 import BeautifulSoup
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import re
import zipfile
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication 
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# .env 파일에서 클라이언트 아이디와 시크릿을 불러오기
load_dotenv()

client_id = os.getenv('Client_id')
client_secret = os.getenv('Client_secret')

# 네이버 쇼핑 URL
SHOPPING_URL = 'https://shopping.naver.com/ns/home#SEARCH_LAYER'

# 결과를 저장할 폴더
RESULT_FOLDER = 'result'

# 압축 파일 저장할 폴더 
UPLOAD_PATH = 'uploads'

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
    driver.quit()
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


@app.route('/refresh', methods=['POST'])
def refresh():
    return redirect('/cart')


@app.route('/cart', methods = ['GET', 'POST'])
def cart():
    # 1단계: 크롬창 열기
    options = Options()
    options.add_experimental_option("detach", False)  # 자동 창 종료
    driver = webdriver.Chrome(options=options)

    # 2단계: 네이버 로그인 페이지 접속
    driver.get('https://nid.naver.com/nidlogin.login')
    print("로그인 창이 열렸습니다. 로그인 후 자동으로 이동합니다...")

    # 로그인 성공 시 URL 변화 감지 (최대 120초 대기)
    try:
        WebDriverWait(driver, 120).until(
            EC.url_contains('naver.com')
        )
        time.sleep(1)
    except:
        print("❌ 로그인 감지 실패. 시간을 초과했거나 로그인에 실패했습니다.")
        driver.quit()
        return "로그인 실패 또는 시간 초과"

    # 3단계: 장바구니 페이지 이동
    print('장바구니 페이지로 시도 중...')
    driver.get('https://shopping.naver.com/cart')

    # 4단계: 장바구니 로딩 대기
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[class^='price']"))
        )
        print("✅ 장바구니 요소가 로딩되었습니다.")
    except:
        print("❌ 장바구니 요소를 불러오지 못했습니다.")
        driver.quit()
        return "장바구니 데이터를 불러오지 못했습니다."

    # 5단계: 페이지 소스 파싱
    shopping_html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(shopping_html, 'html.parser')
    titles = [div.get_text(strip=True) for div in soup.select("div[class^='title']")]
    titles = [title.replace("네이버플러스멤버십", "") for title in titles]

    raw_prices = [div.get_text(strip=True) for div in soup.select("div[class^='price']")]
    prices = [text.replace("상품금액", "") for text in raw_prices if "상품금액" in text]
    prices = [price.replace("선택", "") for price in prices]

    # 이미지
    img_tags = soup.select("div[class^='thumb--'] > img")
    image_urls = [img['src'] for img in soup.select("img[src^='https://shop-phinf.pstatic.net']")]

    
    items = list(zip(titles, prices, image_urls)) # 짝 맞추기
    print("items 출력 확인:", items)


    print("🛍 추출된 장바구니 목록:")
    for t, p, q in items:
        print(f"{t}: {p}, img : {q}")

    return render_template('index.html', items=items)



@app.route('/search', methods=['GET'])
def search():
    keyword = request.args.get('keyword')
    count = request.args.get('count')

    # 네이버 쇼핑 API를 호출하고 결과 처리
    results, excel_filename = search_items(keyword, count)

    # result 폴더에서 파일 목록 가져오기
    excel_files = os.listdir(RESULT_FOLDER)

    return render_template('result.html', results=results, excel_filename=excel_filename, excel_files=excel_files)



# 압축과 동시에 메일 전송
@app.route('/compress_mail', methods=['POST'])
def compress_mail():
    # 압축할 파일들은 RESULT_FOLDER에 있고, 압축 파일은 UPLOAD_PATH에 저장합니다.
    # HTML에서 전달받은 체크박스 값은 name="excel_files"
    files = request.form.getlist("excel_files")
    if not files:
        return "선택된 파일이 없습니다.", 400

    # UPLOAD_PATH 폴더가 없으면 생성
    if not os.path.exists(UPLOAD_PATH):
        os.makedirs(UPLOAD_PATH, exist_ok=True)

    # 압축 파일 경로 설정 (예: uploads/search_compressed.zip)
    zip_path = os.path.join(UPLOAD_PATH, 'search_compressed.zip')
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        for file in files:
            file_path = os.path.join(RESULT_FOLDER, file)
            if os.path.exists(file_path):
                # 압축 파일 내부에서는 파일명만 유지 (arcname=file)
                zip_file.write(file_path, arcname=file)
            else:
                print(f"파일이 존재하지 않습니다: {file_path}")

    # 메일 전송 기능
    send_email = os.getenv("SECRET_ID")
    send_pwd = os.getenv("SECRET_PASS")
    # 수신 이메일은 고정
    recv_email = "수신 이메일 입력"

    try:
        smtp = smtplib.SMTP('smtp.naver.com', 587)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(send_email, send_pwd)

        msg = MIMEMultipart()
        msg['Subject'] = "압축된 파일 전송"
        msg['From'] = send_email
        msg['To'] = recv_email

        content_text = f"선택한 파일들을 압축하여 첨부합니다:\n{', '.join(files)}"
        msg.attach(MIMEText(content_text, _charset='utf-8'))

        with open(zip_path, 'rb') as f:
            part = MIMEApplication(f.read())
            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(zip_path))
            msg.attach(part)

        smtp.sendmail(send_email, recv_email, msg.as_string())
        smtp.quit()
    except Exception as e:
        print(jsonify({'message': f'메일 전송 실패: {e}'}), 500)

    print(jsonify({'message': '압축 및 메일 전송 완료'}), 200)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
