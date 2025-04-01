from flask import Flask, render_template
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

app = Flask(__name__)

@app.route('/')
def home():
    # 1단계: 크롬창 열기
    options = Options()
    options.add_experimental_option("detach", False)  # 자동 창 종료하지 않도록 설정
    driver = webdriver.Chrome(options=options)

    # 2단계: 네이버 로그인 페이지 접속
    driver.get('https://nid.naver.com/nidlogin.login')
    print("로그인 창이 열렸습니다. 로그인 후 자동으로 이동합니다...")

    # 로그인 성공 시 URL 변화 감지 (최대 120초 대기)
    try:
        WebDriverWait(driver, 120).until(
            EC.url_contains('naver.com')
        )
        print("✅ 로그인 성공 감지됨! 장바구니로 이동합니다...")
        time.sleep(1)
    except:
        print("❌ 로그인 감지 실패. 시간을 초과했거나 로그인에 실패했습니다.")
        driver.quit()
        return "로그인 실패 또는 시간 초과"

    # 3단계: 장바구니 페이지 이동
    print('장바구니 페이지로 자동 이동 중...')
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

    raw_prices = [div.get_text(strip=True) for div in soup.select("div[class^='price']")]
    prices = [text.replace("상품금액", "") for text in raw_prices if "상품금액" in text]

    items = list(zip(titles[:len(prices)], prices))  # 짝 맞추기

    print("🛍 추출된 장바구니 목록:")
    for t, p in items:
        print(f"{t}: {p}")

    return render_template('shopping.html', items=items)

if __name__ == '__main__':
    app.run(debug=True)
