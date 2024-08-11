from firebase_admin import auth
import requests

def get_kakao_user_info(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get('https://kapi.kakao.com/v1/oidc/userinfo', headers=headers)
    response.raise_for_status()
    return response.json()

def get_google_token_info(id_token):
    response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}')
    response.raise_for_status()
    return response.json()

def get_or_create_user(email, platform, nickname, picture):
    try:
        #이메일 기반으로 유저 조회
        user = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        #유저 존재 안하면 계정 생성
        user = auth.create_user(email=email)
        auth.set_custom_user_claims(user.uid, {'platform': platform})
        user = auth.update_user(
            user.uid,
            display_name=nickname,
            photo_url=picture
        )
    return user

def create_custom_token(uid):
    #커스텀 토큰 발급
    custom_token = auth.create_custom_token(uid)
    return custom_token
