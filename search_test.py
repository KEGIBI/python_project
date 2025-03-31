from flask import Flask, render_template, request, send_file
import requests
from openpyxl import Workbook
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client_id = os.getenv('Client_id')
client_secret = os.getenv('Client_secret')

@app.route('/', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        keyword = request.form['keyword']
        count = request.form['count']

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

            # 엑셀 파일 생성
            wb = Workbook()
            ws = wb.active
            ws.title = "네이버 검색"

            headers = ['상품명', '가격', '브랜드', '카테고리', '링크']
            ws.append(headers)

            for item in results:
                ws.append([item['title'], item['lprice'], item['brand'], item['category'], item['link']])

            # 엑셀 파일 저장
            excel_filename = "shopping.xlsx"
            wb.save(excel_filename)

            return render_template('result.html', results=results, excel_filename=excel_filename)

        else:
            return f"API 요청 실패: {response.status_code} - {response.text}"

    return render_template('search.html')

@app.route('/download')
def download():
    return send_file("shopping.xlsx", as_attachment=True)

#메일 보내기 함수
@app.route('/mail')
def mail():

    return ()

#슬랙 보내기 함수
@app.route('/slack')
def slack():

    return ()


if __name__ == '__main__':
    app.run(debug=True)
