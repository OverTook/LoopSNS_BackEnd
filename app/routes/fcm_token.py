from app import db
from app.utils.decorators import *
from flask import Blueprint, request, jsonify

# FCM 토큰 블루프린트 작성
fcm_token_routes = Blueprint('fcm_token', __name__)

# FCM 토큰 추가 처리
@fcm_token_routes.route('/add_fcm_token', methods=['POST'])
@validation_token()
def add_fcm_token(user_id):
    fcm_token = request.json.get('fcm_token')
    if not fcm_token:
        return jsonify({
            'success': False, 
            'msg': 'FCM 토큰이 제공되지 않았습니다.'
        }), 400

    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        # 새로운 사용자를 생성하고 FCM 토큰을 추가
        user_ref.set({
            'fcm_tokens': [fcm_token]
        })
        return jsonify({
            'success': True,
            'msg': '새로운 사용자가 생성되고 FCM 토큰이 추가되었습니다.'
        }), 200

    user_data = user_doc.to_dict()
    fcm_tokens = user_data.get('fcm_tokens', [])

    if fcm_token not in fcm_tokens:
        fcm_tokens.append(fcm_token)
        user_ref.update({'fcm_tokens': fcm_tokens})
        return jsonify({
            'success': True, 
            'msg': 'FCM 토큰이 추가되었습니다.'
        }), 200
    else:
        return jsonify({
            'success': True, 
            'msg': '이미 존재하는 FCM 토큰입니다.'
        }), 200
    
# FCM 토큰 삭제 처리
@fcm_token_routes.route('/delete_fcm_token', methods=['POST'])
@validation_token()
def delete_fcm_token(user_id):
    fcm_token = request.json.get('fcm_token')
    if not fcm_token:
        return jsonify({
            'success': False, 
            'msg': 'FCM 토큰이 제공되지 않았습니다.'
        }), 400

    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        return jsonify({
            'success': False, 
            'msg': '해당 사용자를 찾을 수 없습니다.'
        }), 404

    user_data = user_doc.to_dict()
    fcm_tokens = user_data.get('fcm_tokens', [])

    if fcm_token in fcm_tokens:
        fcm_tokens.remove(fcm_token)
        user_ref.update({'fcm_tokens': fcm_tokens})
        return jsonify({
            'success': True, 
            'msg': 'FCM 토큰이 삭제되었습니다.'
        }), 200
    else:
        return jsonify({
            'success': False, 
            'msg': '존재하지 않는 FCM 토큰입니다.'
        }), 404
