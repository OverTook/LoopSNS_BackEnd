from app import db
from app.functions.user_auth import *
from app.utils.decorators import *
from flask import Blueprint, request, jsonify

# 게시글 블루프린트 작성
auth_routes = Blueprint('auth', __name__)

@auth_routes.route('/login', methods=['GET'])
def login():
    platform = request.args.get('platform')
    token = request.args.get('token')

    if not platform or not token:
        return jsonify({
            'success': False, 
            'msg': '필수 파라미터가 누락되었습니다.', 
            'token': ''
        }), 400
    try:
        if platform == 'google':
            #구글 아이디 토큰을 기반으로 이메일 추출
            token_info = get_google_token_info(token)
            
            picture = token_info.get('picture')
            nickname = token_info.get('name')
            
            email = token_info.get('email')
        elif platform == 'kakao':
            #카카오 엑세스 토큰을 기반으로 이메일 추출
            user_info = get_kakao_user_info(token)
            
            picture = user_info.get('picture')
            nickname = user_info.get('nickname')
            
            email = user_info.get('email')
        else:
            return jsonify({'success': False, 'msg': '지원하지 않는 플랫폼으로 로그인을 진행하였습니다.', 'token': ''}), 200
        
        if email:
            #유저를 로그인/회원가입 진행
            user = get_or_create_user(email)
            c_user = user.uid
            
            doc_ref = db.collection('users').document(c_user)
            doc_ref.set({
                'nickname': nickname,
                'picture': picture
            })
            
            #계정 기반으로 토큰 발행
            custom_token = create_custom_token(user.uid)      
            
            return jsonify({
                'success': True, 
                'msg': '', 'token': 
                custom_token.decode('utf-8')
            }), 200
        else:
            return jsonify({
                'success': False, 
                'msg': '토큰 정보에서 이메일을 조회할 수 없습니다.', 
                'token': ''
            }), 401
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e), 'token': ''}), 200