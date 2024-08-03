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
def add_article_like(user_id):
    try:
        article_id = request.json.get('article_id') 
        increment = request.json.get('like')
        
        print(article_id)
        print(increment)

        like_ref = db.collection('articles').document(article_id)
        article_doc = like_ref.get()

        # Check if the article document exists
        if not article_doc.exists:
            return jsonify({
                'success': False,
                'msg': 'Article not found'
            }), 404
        
        article_data = article_doc.to_dict()

        # 특정 사용자 데이터 참조 후 가져오기 (사용자에게 좋아요한 게시글 목록 추가 또는 제거)
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        liked_user_ref = like_ref.collection('liked_users').document(user_id)
        liked_user_doc = liked_user_ref.get()

        # like_users에 일치하는 user_id가 없을 경우 좋아요 추가
        if increment:
            if not liked_user_doc.exists:
                liked_user_ref.set({})
                if 'like_count' not in article_data:
                    like_ref.set({'like_count': 1}, merge=True)
                else:
                    like_ref.update({
                        'like_count': firestore.Increment(1)
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
                    'like_count': firestore.Increment(-1)
                })
                if user_doc.exists:
                    user_ref.update({
                        'article_liked': firestore.ArrayRemove([article_id])
                    })

        # 좋아요 수 반환 (timeline 부분에 like_count에 사용)
        updated_like_ref = like_ref.get()
        like_count = updated_like_ref.to_dict().get('like_count', 0)

        return jsonify({
            'success': True,
            'msg': 'Like updated successfully',
            'like_count': like_count
        }), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify(response = {
            'success': False,
            'msg': str(e),
            'articles': []
        }), 500

# 내가 좋아요 누른 게시글 목록 확인하는 부분
@like_routes.route('/get_like_article_list', methods=['GET'])
@validation_token()
def user_liked_article_list(user_id):
    last_article_id = request.args.get('last_article_id')
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

        limit = 20  # 가져올 게시글 개수

        query = db.collection('articles').where(FieldPath.document_id(), "in", liked_article_ids).order_by("time", direction=firestore.Query.DESCENDING)

        # last_article_id가 있을 경우 해당 문서 다음부터 limit 만큼 탐색
        if last_article_id:
            last_article_ref = db.collection('articles').document(last_article_id)
            last_article_snapshot = last_article_ref.get()
            if last_article_snapshot.exists:
                query = query.start_after(last_article_snapshot).limit(limit)
            else:
                return jsonify({
                    'success': False, 
                    'msg': '잘못된 last_article_id 입니다.'
                }), 400
        else:
            query = query.limit(limit)

        docs = query.stream()

        articles_list = []

        # 작성자의 uid를 auth에서 가져오기
        try:
            user = auth.get_user(user_id)
            picture = user.photo_url
            nickname = user.display_name
        except Exception as e:
            print("Error Occured!!", e)
            picture = None
            nickname = None

        for doc in docs:
            article_data = doc.to_dict()
            article_item = {
                'uid': doc.id,
                'contents': article_data.get('contents', ''),
                'cat1': article_data.get('cat1', ''),
                'cat2': article_data.get('cat2', ''),
                'keywords': article_data.get('keywords', []),
                'time': article_data.get('time', None).strftime("%Y-%m-%d %H:%M"),
                'like_count': article_data.get('like_count', 0),
                'image_urls': article_data.get('image_urls', []),
                'user_img': picture,
                'writer': nickname,
                'can_delete': True
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
    