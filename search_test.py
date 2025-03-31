from flask import Flask, render_template, request, send_file, jsonify
import requests
from openpyxl import Workbook
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import zipfile
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication 
from email.mime.multipart import MIMEMultipart

dir_path = "uploads"
all_files = os.listdir(dir_path)
xlsx_files = []

app = Flask(__name__)

load_dotenv()
client_id = os.getenv('Client_id')
client_secret = os.getenv('Client_secret')

@app.route('/', methods=['GET', 'POST'])
def search():
    xlsx_files = []  # 함수 안에서 리스트 초기화

    for file in os.listdir(dir_path):
        if file.endswith(".xlsx"): 
            xlsx_files.append(file)

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

            # 엑셀 파일 저장 (키워드로 파일 이름 설정)
            excel_filename = f"uploads/{keyword}.xlsx"
            wb.save(excel_filename)

            return render_template('result.html', results=results, excel_filename=excel_filename)

        else:
            return f"API 요청 실패: {response.status_code} - {response.text}"

    return render_template('search.html', xlsx_file=xlsx_files)

@app.route('/download/<keyword>')
def download(keyword):
    excel_filename = f"uploads/{keyword}.xlsx"
    return send_file(excel_filename, as_attachment=True)

@app.route('/mail', methods=['POST'])
def mail_sender(save_path):
    '''
    생성된 엑셀 파일을 사용자의 이메일과 pw를 .env 파일에 저장하면 
    지정한 메일 주소로 파일 저장 날짜와 함께 전송합니다.
    '''
    load_dotenv()
    send_email = os.getenv("SECRET_ID")
    send_pwd = os.getenv("SECRET_PASS")
    recv_email = "56637@naver.com"

    smtp = smtplib.SMTP('smtp.naver.com', 587)
    smtp.ehlo()
    smtp.starttls()

    smtp.login(send_email,send_pwd)

    msg = MIMEMultipart()
    msg['Subject'] = f"검색 결과 전송"  
    msg['From'] = send_email          
    msg['To'] = recv_email

    etc_file_path = save_path
    with open(etc_file_path, 'rb') as f : 
        etc_part = MIMEApplication( f.read() )
        etc_part.add_header('Content-Disposition','attachment', filename= os.path.basename(save_path))
        msg.attach(etc_part)

    email_string = msg.as_string()

    smtp.sendmail(send_email, recv_email, email_string)
    smtp.quit()

if __name__ == '__main__':
    app.run(debug=True)
