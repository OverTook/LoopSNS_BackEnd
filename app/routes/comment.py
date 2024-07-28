from app import db
from app.utils.decorators import *
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
        time = datetime.now().astimezone(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M')
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
        
        # comments 컬렉션에 comment_data 추가하고 문서 참조 반환
        _, comment_ref = article_ref.collection('comments').add(comment_data)
        comment_id = comment_ref.id
        
        print("댓글 id", comment_id)
        
        # 헤더 uid
        comment_user_id = request.headers.get('User-ID')
        
        # 댓글 작성한 작성자의 uid
        com = comment_ref.get()
        if com.exists:
            comment_data = com.to_dict()
            user_id = comment_data.get('user_id')

        if comment_user_id == user_id:
            can_delete = True
        else:
            can_delete = False
        
        return jsonify({
            'success': True, 
            'msg': '성공적으로 작성되었습니다',
            'time': time,
            'comment_id': comment_id,
            'can_delete': can_delete
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
    return jsonify({
        'success': True, 
        'msg': '댓글 삭제 완료'
    }), 200
