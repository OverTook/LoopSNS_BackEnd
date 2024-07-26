from functools import wraps
from flask import request, jsonify
from firebase_admin import auth

def validation_token() -> object:
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            id_token = request.headers.get("Authorization")
            user_id = request.headers.get("User-ID")
            print("user_id : ", user_id)

            # 여기 부분이 토큰이 "Bearer "로 시작하는지 확인하는 부분인데 없으면 오류 발생.
            if not id_token or not id_token.startswith("Bearer "):
                return jsonify({
                    'success': False,
                    'msg': 'token does not exist'
                })

            id_token = id_token.split(" ")[1]

            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token["uid"]
            print("uid : ", uid)

            if uid != user_id:
                return jsonify({
                    'success': False,
                    'msg': 'token not authenticated'
                })
            
            # uid를 kwargs에 추가
            kwargs['uid'] = uid
            kwargs['user_id'] = user_id
            return f(*args, **kwargs)
        return wrapped
    return decorator