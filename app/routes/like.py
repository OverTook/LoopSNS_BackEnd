from app import db, bucket
from app.utils.decorators import *
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from google.cloud.firestore_v1.field_path import FieldPath

# 좋아요 블루프린트 작성
like_routes = Blueprint('like', __name__)

# 좋아요 기능 추가
@like_routes.route('/add_article_like', methods=['POST'])
@validation_token()
def add_article_like(uid, user_id):
    try:
        article_id = request.json.get('article_id') 
        increment = request.json.get('like')

        #좋아요 누르면 true, 취소하면 false
        if increment.lower() == 'true':
            increment = True
        elif increment.lower() == 'false':
            increment = False
        
        like_ref = db.collection('articles').document(article_id)
        article_doc = like_ref.get()
        
        # 특정 사용자 데이터 참조 후 가져오기 (사용자에게 좋아요한 게시글 목록 추가 또는 제거)
        # 해당 자료 https://www.googlecloudcommunity.com/gc/Databases/Using-Firestore-with-Python-Web-and-Flutter-Clients/m-p/609316
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        liked_user_ref = like_ref.collection('liked_users').document(user_id)
        liked_user_doc = liked_user_ref.get()

        # like_users에 일치하는 user_id가 없을 경우 좋아요 추가
        if increment:
            if not liked_user_doc.exists:
                liked_user_ref.set({})
                if 'like_count' not in article_doc.to_dict():
                    like_ref.set({'like_count': 1}, merge=True)
                else:
                    like_ref.update({
                        'like_count': Increment(1)
                    })
                if user_doc.exists:
                    user_ref.update({
                        'article_liked': firestore.ArrayUnion([article_id])
                    })
                else:
                    user_ref.set({
                        'article_liked': [article_id]
                    })
        # like_users에 일치하는 user_id가 있을 경우 좋아요 취소
        else:
            if liked_user_doc.exists:
                liked_user_ref.delete()
                like_ref.update({
                    'like_count': Increment(-1)
                })
                if user_doc.exists:
                    user_ref.update({
                        'article_liked': firestore.ArrayRemove([article_id])
                    })

        # 좋아요 수 반환 (timeline 부분에 like_count에 사용)
        updated_like_ref = like_ref.get()
        like_count = updated_like_ref.to_dict().get('like_count', 0)

        liked_users_snapshot = like_ref.collection('liked_users').get()
        liked_user_ids = [doc.id for doc in liked_users_snapshot]

        response = {
            'success': True,
            'msg': 'Like updated successfully'
        }

        return jsonify(response), 200

    except Exception as e:
        print(f"Exception: {e}")
        response = {
            'success': False,
            'msg': str(e),
            'articles': []
        }
        return jsonify(response), 500

# 내가 좋아요 누른 게시글 목록 확인하는 부분
@like_routes.route('/user_liked_article_list', methods=['GET'])
@validation_token()
def user_liked_article_list(uid, user_id):
    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            liked_article_ids = user_doc.get('article_liked')
        else:
            liked_article_ids = []

        if not liked_article_ids:
            return jsonify({
                'success': True,
                'articles': []
            }), 200

        articles_list = []
        docs = db.collection('articles').where(FieldPath.document_id(), "in", liked_article_ids).stream()

        for doc in docs:
            article_data = doc.to_dict()
            article_item = {
                'uid': doc.id,
                'contents': article_data.get('contents', '')
            }
            articles_list.append(article_item)

        response = {
            'success': True,
            'articles': articles_list
        }

        return jsonify(response), 200

    except Exception as e:
        print(f"Exception: {e}")
        response = {
            'success': False,
            'msg': str(e),
            'articles': []
        }
        return jsonify(response), 500