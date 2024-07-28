from app import db
from app.functions.notification import *
from app.utils.decorators import *
from firebase_admin import firestore
from flask import Blueprint, request, jsonify
from datetime import datetime
import pytz

# 댓글 작성 블루프린트 작성
comment_routes = Blueprint('comment', __name__)

# 댓글 작성 엔드포인트
@comment_routes.route('/add_comment', methods=['POST'])
@validation_token()
def create_comment(user_id):
    try:
        article_id = request.json.get('uid')
        contents = request.json.get('contents')
        time2 = datetime.now().astimezone(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M')
        print(time2)
        
        time = datetime.now().astimezone(pytz.timezone('UTC'))
        print(time)
        
        if not article_id or not contents:
            return jsonify({
                'success': False, 
                'msg': 'article_id 혹은 contents 파라미터가 누락됨'
            }), 400
        
        comment_data = {
            'article_id': article_id,
            'user_id': user_id,
            'contents': contents,
            'time': time
        }
        
        # articles 컬렉션의 하위 컬렉션으로 저장
        article_ref = db.collection('articles').document(article_id)
        article = article_ref.get()
        article_data = article.to_dict()
        
        # comments 컬렉션에 comment_data 추가하고 문서 참조 반환
        _, comment_ref = article_ref.collection('comments').add(comment_data)
        comment_id = comment_ref.id
        
        # 댓글 작성한 작성자의 uid
        # 작성자의 uid를 auth에서 가져오기
        try:
            user = auth.get_user(user_id)
            nickname = user.display_name
        except Exception as e:
            print("Error Occured!!", e)
            nickname = "알 수 없음"

        # 여기 내가 작성한 댓글을 올리는 부분인데 꼭 can_delete 체크를 해야해요??
        #com = comment_ref.get()
        #if com.exists:
        #    comment_data = com.to_dict()
        #    comment_user_id = comment_data.get('user_id')

        #if user_id == comment_user_id:
        #    can_delete = True
        #else:
        #    can_delete = False
        
        # 댓글 수 증가
        article_ref.update({
            'comment_counts': firestore.Increment(1)
        })

        # 게시글 작성자에게 notification
        if user_id != article_data['user_id']:  # 본인이 본인 게시글에 댓글 달면 알림 X
            writer_ref = db.collection('users').document(article_data['user_id'])
            writer_doc = writer_ref.get()
            writer_data = writer_doc.to_dict()
            for fcm_token in writer_data['fcm_tokens']:
                try:
                    send_push_notification(fcm_token, nickname, contents)
                except Exception as e:
                    print("except:", e)
        
        return jsonify({
            'success': True, 
            'msg': '성공적으로 작성되었습니다',
            'time': time.strftime('%Y-%m-%d %H:%M'),
            'comment_id': comment_id,
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
def delete_article(article_id, comment_id, user_id):
    docs_ref = db.collection('articles').document(article_id).collection('comments')
    doc_ref = docs_ref.document(comment_id)
    comment_doc = doc_ref.get()
    
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

    doc_ref.delete()
    
    # 댓글 수 감소
    article_ref = db.collection('articles').document(article_id)
    article_ref.update({
        'comment_counts': firestore.Increment(-1)
    })
    
    return jsonify({
        'success': True, 
        'msg': '댓글 삭제 완료'
    }), 200
