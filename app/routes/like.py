from app import db, bucket
from app.functions.notification import *
from app.utils.decorators import *
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from google.cloud.firestore_v1.field_path import FieldPath
import concurrent.futures
from datetime import datetime
import pytz

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
        print(like_count)

        time_utc = datetime.now(pytz.timezone('UTC'))
        
        def send_notifications():
            try:
                notification_body = {
                    'user_id' : article_data['user_id'],
                    'article_id': article_id,
                    'like_count': like_count,
                    'time': time_utc.strftime('%Y-%m-%d %H:%M')
                }

                #좋아요 1개일 때, 10의 배수일 때마다 알림 오게 설정
                if (like_count == 1 or like_count % 10 == 0) and increment:
                    if user_id != article_data['user_id']:
                        writer_ref = db.collection('users').document(article_data['user_id'])
                        writer_data = writer_ref.get().to_dict()
                        fcm_tokens = writer_data.get('fcm_tokens', [])
                        for fcm_token in fcm_tokens:
                            try:
                                send_push_notification(fcm_token, "likes", notification_body)
                            except Exception as e:
                                print("Notification Error:", e)
                                user_ref = db.collection('users').document(article_data['user_id'])
                                user_doc = user_ref.get()

                                user_data = user_doc.to_dict()
                                fcm_tokens = user_data.get('fcm_tokens', [])

                                if fcm_token in fcm_tokens:
                                    fcm_tokens.remove(fcm_token)
                                    user_ref.update({'fcm_tokens': fcm_tokens})

            except Exception as e:
                print("Notification Exception:", e)

        # 비동기로 알림 전송
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(send_notifications)

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
            liked_article_ids = user_doc.to_dict().get('article_liked', [])
        else:
            liked_article_ids = []

        if not liked_article_ids:
            return jsonify({
                'success': True,
                'articles': []
            }), 200

        # last_article_id 이후의 문서를 제외하고 리스트를 슬라이스
        if last_article_id:
            try:
                last_index = liked_article_ids.index(last_article_id)
                liked_article_ids = liked_article_ids[:last_index]
            except ValueError:
                return jsonify({
                    'success': False, 
                    'msg': '잘못된 last_article_id 입니다.'
                }), 400

        # 역순으로 가져올 문서 리스트
        liked_article_ids.reverse()
        limit = 20  # 가져올 게시글 개수

        articles_list = []
        total_fetched_articles = 0
        
        for article_id in liked_article_ids:
            if total_fetched_articles >= limit:
                break

            article_ref = db.collection('articles').document(article_id)
            article_doc = article_ref.get()

            if article_doc.exists:
                article_data = article_doc.to_dict()
                article_item = {
                    'uid': article_id,
                    'contents': article_data.get('contents', ''),
                    'cat1': article_data.get('cat1', ''),
                    'cat2': article_data.get('cat2', ''),
                    'keywords': article_data.get('keywords', []),
                    'time': article_data.get('time', None).strftime("%Y-%m-%d %H:%M"),
                    'comment_counts': article_data.get('comment_counts', 0),
                    'like_count': article_data.get('like_count', 0),
                    'image_urls': article_data.get('image_urls', []),
                }
                articles_list.append(article_item)
                total_fetched_articles += 1

        # 작성자의 uid를 auth에서 가져오기
        try:
            user = auth.get_user(user_id)
            picture = user.photo_url
            nickname = user.display_name
        except Exception as e:
            print("Error Occurred!!", e)
            picture = None
            nickname = None

        for article in articles_list:
            article['user_img'] = picture
            article['writer'] = nickname
            article['can_delete'] = True

        return jsonify({
            'success': True,
            'articles': articles_list
        }), 200

    except Exception as e:
        print(f"Exception: {e}")
        response = {
            'success': False,
            'msg': str(e),
            'articles': []
        }
        return jsonify(response), 500
    