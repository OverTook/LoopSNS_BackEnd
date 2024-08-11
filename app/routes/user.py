from app import db, bucket
from app.utils.decorators import *
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
import uuid

# 사용자 블루프린트 작성
user_routes = Blueprint('user', __name__)

@user_routes.route('/update_profile_img', methods=['POST'])
@validation_token()
def update_img(user_id):
    if 'image' not in request.files:
        return jsonify(
            {'success': False, 
             'msg': '이미지 파일이 누락되었습니다.'
            }), 400

    img_file = request.files['image']
    print(img_file)
    
    # 파일 정보 확인용
    print(f"파일 이름: {img_file.filename}")
    print(f"파일 타입: {img_file.content_type}")

    try:
        image_filename = f'{uuid.uuid4()}.jpg'
        blob = bucket.blob(f'images/{image_filename}')
        
        # 파일 업로드
        blob.upload_from_file(img_file.stream, content_type=img_file.content_type)
        
        # 파일 공개 URL 가져오기
        blob.make_public()
        picture_url = blob.public_url
        
        return jsonify({
            'success': True,
            'msg': '이미지가 업로드되었습니다.',
            'picture_url': picture_url
        }), 200
    
    except Exception as e:
        print(str(e))
        return jsonify({'success': False, 'msg': str(e)}), 500

@user_routes.route('/delete_user', methods=['DELETE'])
@validation_token()
def delete_user(user_id):
    try:
        auth.delete_user(user_id)

        user_ref = db.collection('users').document(user_id)
        user_ref.delete()
        
        return jsonify({
            'success': True,
            'msg': '계정이 성공적으로 삭제되었습니다.'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'msg': str(e)
        }), 500
