from app import db
from app.utils.decorators import *
from flask import Blueprint, request, jsonify
import datetime

# 댓글 작성 블루프린트 작성
comment_routes = Blueprint('comment', __name__)

# 댓글 작성 엔드포인트
@comment_routes.route('/add_comment', methods=['POST'])
@validation_token()
def create_comment(uid, user_id):
    try:
        article_id = request.json.get('uid')
        contents = request.json.get('contents')
        time = datetime.now().strftime('%Y-%m-%d %H:%M')

        if not article_id or not contents:
            raise ValueError("article_id and contents are required")

        comment_data = {
            'article_id': article_id,
            'user_id': user_id,
            'contents': contents,
            'time': time
        }

        # articles 컬렉션의 하위 컬렉션으로 저장
        article_ref = db.collection('articles').document(article_id)
        article_ref.collection('comments').add(comment_data)

        return jsonify({'success': True, 'msg': '성공적으로 작성되었습니다'}), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({
            'success': False, 
            'msg': str(e)
        }), 500
