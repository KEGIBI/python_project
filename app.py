from flask import Flask, redirect, request, render_template
import requests
from urllib.parse import urlencode

app = Flask(__name__)

# 네이버에서 발급받은 Client ID와 Client Secret
CLIENT_ID = '3ktA9pOnQfsTwhRJErIO'
CLIENT_SECRET = '19RY3hTp_w'
REDIRECT_URI = 'http://localhost:5000/callback'  # Callback URL (Flask 앱에서 처리하는 URL)

# 네이버 로그인 API URL
AUTH_URL = 'https://nid.naver.com/oauth2.0/authorize'
TOKEN_URL = 'https://nid.naver.com/oauth2.0/token'
USER_INFO_URL = 'https://openapi.naver.com/v1/nid/me'

# 네이버 쇼핑 API URL
SHOPPING_API_URL = 'https://openapi.naver.com/v1/search/shop'

# 네이버 로그인 페이지로 리디렉션 (로그인 시작)
@app.route('/')
def home():
    auth_params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'state': 'random_state',  # CSRF 보호를 위한 랜덤 상태 값
    }
    auth_url = f"{AUTH_URL}?{urlencode(auth_params)}"
    return redirect(auth_url)

# 네이버 로그인 후 리디렉션된 URL을 처리 (액세스 토큰을 얻음)
@app.route('/callback')
def callback():
    code = request.args.get('code')  # 네이버에서 전달받은 인증 코드
    state = request.args.get('state')  # 네이버에서 전달받은 state 값 (보안용)

    # 인증 코드로 액세스 토큰 요청
    token_params = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'state': state
    }

    # 액세스 토큰 요청
    response = requests.post(TOKEN_URL, data=token_params)
    token_data = response.json()

    # 액세스 토큰 추출
    access_token = token_data['access_token']

    # 액세스 토큰으로 사용자 정보 요청
    headers = {
        'Authorization': f'Bearer {access_token}'  # 인증된 사용자의 정보 요청
    }
    user_info_response = requests.get(USER_INFO_URL, headers=headers)
    user_info = user_info_response.json()


    return render_template('shopping.html')

@app.route('/shopping')
def shopping():
    return redirect('/callback')  # 이미 callback에서 처리되므로 별도로 /shopping에서 호출

if __name__ == '__main__':
    app.run(debug=True)
