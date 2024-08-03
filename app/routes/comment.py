from app import db
from app.functions.notification import *
from app.utils.decorators import *
import concurrent.futures
from firebase_admin.firestore import firestore
from flask import Blueprint, request, jsonify
from datetime import datetime
import pytz
import time

# 댓글 작성 블루프린트 작성
comment_routes = Blueprint('comment', __name__)

# 댓글 작성 엔드포인트
@comment_routes.route('/add_comment', methods=['POST'])
@validation_token()
def create_comment(user_id):
    try:
        article_id = request.json.get('uid')
        contents = request.json.get('contents')
        time_utc = datetime.now(pytz.timezone('UTC'))

        if not article_id or not contents:
            return jsonify({
                'success': False, 
                'msg': 'article_id 혹은 contents 파라미터가 누락됨'
            }), 400
        
        # articles 컬렉션의 하위 컬렉션으로 저장
        article_ref = db.collection('articles').document(article_id)
        article_data = article_ref.get().to_dict()
        
        # 댓글 수 증가
        article_ref.update({
            'comment_counts': firestore.Increment(1)
        })
        
        # 댓글 작성자의 uid
        try:
            user = auth.get_user(user_id)
            picture = user.photo_url
            nickname = user.display_name
        except Exception as e:
            print("Error Occured!!", e)
            picture = None
            nickname = None
        
        # 댓글 데이터 생성
        comment_data = {
            'article_id': article_id,
            'user_id': user_id,
            'contents': contents,
            'time': time_utc,
            'sub_comment_counts': 0
        }
        _, comment_ref = article_ref.collection('comments').add(comment_data)
        
        # 비동기 알림 전송 함수
        def send_notifications():
            try:
                notification_body = {
                    'article_id': article_id,
                    'comment_id': comment_ref.id,
                    'user_id': user_id,
                    'writer': nickname,
                    'user_img': picture,
                    'contents': contents,
                    'time': time_utc.strftime('%Y-%m-%d %H:%M')
                }

                # 게시글 작성자에게 notification
                if user_id != article_data['user_id']:
                    writer_ref = db.collection('users').document(article_data['user_id'])
                    writer_data = writer_ref.get().to_dict()
                    for fcm_token in writer_data['fcm_tokens']:
                        try:
                            send_push_notification(fcm_token, "comment", notification_body)
                        except Exception as e:
                            print("Notification Error:", e)
            except Exception as e:
                print("Notification Exception:", e)
        
        # 비동기로 알림 전송
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(send_notifications)
        
        return jsonify({
            'success': True, 
            'msg': '성공적으로 작성되었습니다',
            'time': time_utc.strftime('%Y-%m-%d %H:%M'),
            'comment_id': comment_ref.id,
            'can_delete': True
        }), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({
            'success': False, 
            'msg': str(e)
        }), 500

# 대댓글 작성 엔드포인트
@comment_routes.route('/add_sub_comment', methods=['POST'])
@validation_token()
def create_sub_comment(user_id):
    try:
        article_id = request.json.get('uid')
        comment_id = request.json.get('comment_id')
        contents = request.json.get('contents')
        time_utc = datetime.now(pytz.timezone('UTC'))

        if not article_id or not contents:
            return jsonify({
                'success': False, 
                'msg': 'article_id 혹은 contents 파라미터가 누락됨'
            }), 400
        
        # articles 컬렉션의 하위 컬렉션으로 저장
        article_ref = db.collection('articles').document(article_id)
        comment_ref = article_ref.collection('comments').document(comment_id)
        comment_data = comment_ref.get().to_dict()
        
        # 대댓글 수 증가
        comment_ref.update({
            'sub_comment_counts': firestore.Increment(1)
        })
        
        # 댓글 작성자의 uid
        try:
            user = auth.get_user(user_id)
            picture = user.photo_url
            nickname = user.display_name
        except Exception as e:
            print("Error Occured!!", e)
            picture = None
            nickname = None
        
        # 대댓글 데이터 생성
        sub_comment_data = {
            'article_id': article_id,
            'comment_id': comment_id,
            'user_id': user_id,
            'contents': contents,
            'time': time_utc
        }
        _, sub_comment_ref = comment_ref.collection('sub_comments').add(sub_comment_data)
        
        # 비동기 알림 전송 함수
        def send_notifications():
            try:
                notification_body = {
                    'article_id': article_id,
                    'comment_id': comment_id,
                    'sub_comment_id': sub_comment_ref.id,
                    'user_id': user_id,
                    'writer': nickname,
                    'user_img': picture,
                    'contents': contents,
                    'time': time_utc.strftime('%Y-%m-%d %H:%M')
                }

                # 댓글 작성자에게 notification
                if user_id != comment_data['user_id']:
                    writer_ref = db.collection('users').document(comment_data['user_id'])
                    writer_data = writer_ref.get().to_dict()
                    for fcm_token in writer_data['fcm_tokens']:
                        try:
                            send_push_notification(fcm_token, "comment", notification_body)
                        except Exception as e:
                            print("Notification Error:", e)
            except Exception as e:
                print("Notification Exception:", e)
        
        # 비동기로 알림 전송
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(send_notifications)
        
        return jsonify({
            'success': True, 
            'msg': '성공적으로 작성되었습니다',
            'time': time_utc.strftime('%Y-%m-%d %H:%M'),
            'comment_id': comment_ref.id,
            'can_delete': True
        }), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({
            'success': False, 
            'msg': str(e)
        }), 500

# 댓글 삭제 엔드포인트    
@comment_routes.route('/delete_comment/<article_id>/<comment_id>', methods=['DELETE'])
@validation_token()
def delete_comment(article_id, comment_id, user_id):
    article_ref = db.collection('articles').document(article_id)
    comment_ref = article_ref.collection('comments').document(comment_id)
    comment_doc = comment_ref.get()
    
    if not comment_doc.exists:
        return jsonify({
            'success': False, 
            'msg': '댓글이 존재하지 않음'
        }), 404
    
    comment_data = comment_doc.to_dict()
    comment_uid = comment_data.get('user_id')
    
    if comment_uid != user_id:
        return jsonify({
            'success': False, 
            'msg': '댓글 작성자가 아님'
        }), 403

    comment_ref.update({
        'is_deleted': True
    })
    
    # 댓글 수 감소
    article_ref.update({
        'comment_counts': firestore.Increment(-1)
    })
    
    return jsonify({
        'success': True, 
        'msg': '댓글 삭제 완료'
    }), 200

# 대댓글 삭제 엔드포인트    
@comment_routes.route('/delete_sub_comment/<article_id>/<comment_id>/<sub_comment_id>', methods=['DELETE'])
@validation_token()
def delete_sub_comment(article_id, comment_id, sub_comment_id, user_id):
    article_ref = db.collection('articles').document(article_id)
    comment_ref = article_ref.collection('comments').document(comment_id)
    sub_comment_ref = comment_ref.collection('sub_comments').document(sub_comment_id)
    sub_comment_doc = sub_comment_ref.get()
    
    if not sub_comment_doc.exists:
        return jsonify({
            'success': False, 
            'msg': '대댓글이 존재하지 않음'
        }), 404
    
    sub_comment_data = sub_comment_doc.to_dict()
    sub_comment_uid = sub_comment_data.get('user_id')
    
    if sub_comment_uid != user_id:
        return jsonify({
            'success': False, 
            'msg': '댓글 작성자가 아님'
        }), 403

    sub_comment_ref.update({
        'is_deleted': True
    })
    
    # 대댓글 수 감소
    comment_ref.update({
        'sub_comment_counts': firestore.Increment(-1)
    })
    
    return jsonify({
        'success': True, 
        'msg': '대댓글 삭제 완료'
    }), 200


# 댓글 목록 불러오기 엔드포인트
@comment_routes.route("/get_comment_list")
@validation_token()
def get_comment_list(user_id):
    article_id = request.args.get('uid')
    last_comment_id = request.args.get('last_comment_id')
    limit = 20
    
    article_ref = db.collection('articles').document(article_id)
    comment_col = article_ref.collection('comments')
    
    # 모든 댓글을 받아옴
    query = comment_col.order_by('time', direction=firestore.Query.DESCENDING)
    if last_comment_id:
        last_comment = comment_col.document(last_comment_id).get()
        if not last_comment.exists:
            return jsonify({
                'success': False,
                'msg': '잘못된 last_comment_id 입니다.'
            }), 400
        query = query.start_after(last_comment).limit(limit)
    else:
        query = query.limit(limit)
    comments = query.stream()

    def fetch_user_info(comment):
        comment_data = comment.to_dict()
        print(comment_data)
        try:
            user = auth.get_user(comment_data['user_id'])
            picture = user.photo_url
            nickname = user.display_name
        except Exception as e:
            print("Error Occurred!!", e)
            picture = None
            nickname = None

        comment_item = {
            'time': comment_data.get('time'),
            'comment_id': comment.id,
            'tag_id': comment_data.get('tag_id', ''),
            'contents': comment_data.get('contents', ''),
            'user_img': picture,
            'writer': nickname,
            'is_deleted': comment_data.get('is_deleted', False),
            'sub_comment_counts': comment_data.get('sub_comment_counts', 0),
            'can_delete': True if user_id == comment_data['user_id'] else False
        }
        return comment_item

    with concurrent.futures.ThreadPoolExecutor() as executor:
        comment_items = list(executor.map(fetch_user_info, comments))
    
    comment_items.sort(key=lambda x: x['time'], reverse=True)
    for comment_item in comment_items:
        comment_item['time'] = comment_item['time'].strftime('%Y-%m-%d %H:%M')

    return jsonify({
        'success': True,
        'msg': '댓글 반환에 성공했습니다.',
        'comments': comment_items
    }), 200

# 대댓글 목록 불러오기 엔드포인트
@comment_routes.route("/get_sub_comment_list")
@validation_token()
def get_sub_comment_list(user_id):
    article_id = request.args.get('uid')
    comment_id = request.args.get('comment_id')
    last_sub_comment_id = request.args.get('last_sub_comment_id')
    
    article_ref = db.collection('articles').document(article_id)
    comment_ref = article_ref.collection('comments').document(comment_id)
    sub_comment_collection = comment_ref.collection('sub_comments')
    limit = 20
    query = sub_comment_collection.order_by("time", direction=firestore.Query.ASCENDING).limit(limit)
    # 모든 댓글을 받아옴
    if last_sub_comment_id:
        last_sub_comment = sub_comment_collection.document(last_sub_comment_id).get()
        if not last_sub_comment.exists:
            return jsonify({
                'success': False,
                'msg': '잘못된 last_comment_id 입니다.'
            }), 400
        query = query.start_after(last_sub_comment).limit(limit)
    sub_comments = query.stream()
    def fetch_user_info(comment):
        comment_data = comment.to_dict()
        try:
            user = auth.get_user(comment_data['user_id'])
            picture = user.photo_url
            nickname = user.display_name
        except Exception as e:
            print("Error Occurred!!", e)
            picture = None
            nickname = None

        comment_item = {
            'time': comment_data.get('time'),
            'comment_id': comment.id,
            'contents': comment_data.get('contents', ''),
            'user_img': picture,
            'writer': nickname,
            'is_deleted': comment_data.get('is_deleted', False),
            'can_delete': True if user_id == comment_data['user_id'] else False
        }
        return comment_item
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        sub_comment_items = list(executor.map(fetch_user_info, sub_comments))

    sub_comment_items.sort(key=lambda x: x['time'], reverse=False)
    for sub_comment_item in sub_comment_items:
        sub_comment_item['time'] = sub_comment_item['time'].strftime('%Y-%m-%d %H:%M')

    print("sub")
    print(sub_comment_items)

    return jsonify({
        'success': True,
        'msg': '댓글 반환에 성공했습니다.',
        'comments': sub_comment_items
    }), 200



