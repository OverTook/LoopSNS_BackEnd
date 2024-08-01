from app import db
from app.functions.notification import *
from app.utils.decorators import *
import concurrent.futures
from firebase_admin.firestore import firestore
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
        comment_id = request.json.get('comment_id')
        contents = request.json.get('contents')
        time_utc = datetime.now(pytz.timezone('UTC'))

        # articles 컬렉션의 하위 컬렉션으로 저장
        article_ref = db.collection('articles').document(article_id)
        article = article_ref.get()
        article_data = article.to_dict()
        
        article_ref.update({
            'comment_counts': firestore.Increment(1)
        })
        
        if not article_id or not contents:
            return jsonify({
                'success': False, 
                'msg': 'article_id 혹은 contents 파라미터가 누락됨'
            }), 400

        # 댓글 작성한 작성자의 uid
        # 작성자의 uid를 auth에서 가져오기
        try:
            user = auth.get_user(user_id)
            picture = user.photo_url
            nickname = user.display_name
        except Exception as e:
            print("Error Occured!!", e)
            picture = None
            nickname = None
        
        # articles 컬렉션의 하위 컬렉션으로 저장
        comment_data = {
            'article_id': article_id,
            'tag_id': comment_id,
            'user_id': user_id,
            'contents': contents,
            'time': time_utc
        }
        _, comment_ref = article_ref.collection('comments').add(comment_data)

        # 댓글 작성자에게 notification
        try:
            if user_id != article_data['user_id']:  # 본인이 본인 게시글에 댓글 달면 알림 X
                writer_ref = db.collection('users').document(article_data['user_id'])
                writer_doc = writer_ref.get()
                writer_data = writer_doc.to_dict()
                notification_body = {
                    'article_id': article_id,
                    'comment_id': comment_ref.id,
                    'tag_id': comment_id,
                    'user_id': user_id,
                    'writer': nickname,
                    'user_img': picture,
                    'contents': contents,
                    'time': time_utc.strftime('%Y-%m-%d %H:%M')
                }
                for fcm_token in writer_data['fcm_tokens']:
                    try:
                        send_push_notification(fcm_token, "comment", notification_body)
                    except Exception as e:
                        print("except:", e)
        except Exception as e:
            print("except:", e)
        
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
def delete_comment(article_id, comment_id, reply_id, user_id):
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

    comment_ref.delete()
    
    # 댓글 수 감소
    article_ref.update({
        'comment_counts': firestore.Increment(-1)
    })
    
    return jsonify({
        'success': True, 
        'msg': '댓글 삭제 완료'
    }), 200

# 댓글 목록 불러오기 엔드포인트
@comment_routes.route("/get_comment_list")
@validation_token()
def get_comment_list(user_id):
    article_id = request.args.get('uid')
    last_comment_id = request.args.get('last_comment_id')
    article_ref = db.collection('articles').document(article_id)
    
    comment_collection = article_ref.collection('comments')
    
    limit = 20
    
    #메인 댓글 여부
    is_main_comment = False
    
    #메인 댓글 아이디
    main_comment_id = ""
    
    #서브 댓글 아이디
    sub_comment_id = ""
    
    #메인 댓글만 받아옴
    query = comment_collection.where('tag_id', '==', '').order_by("time", direction=firestore.Query.ASCENDING)

    total_comments = []
    
    # 댓글 작성자 정보를 병렬로 가져오기 위한 함수
    def fetch_user_info(comment):
        comment_data = comment.to_dict()

        # 작성자의 uid를 auth에서 가져오기
        try:
            user = auth.get_user(comment_data['user_id'])
            picture = user.photo_url
            nickname = user.display_name
        except Exception as e:
            print("Error Occured!!", e)
            picture = None
            nickname = None

        # 가져온 게시글에서 내용 뽑아내기
        comment_item = {
            'time': comment_data.get('time').strftime('%Y-%m-%d %H:%M'),
            'comment_id': comment.id,
            'tag_id': comment_data.get('tag_id', ''),
            'contents': comment_data.get('contents', ''),
            'user_img': picture,
            'writer': nickname,
            'can_delete': True if user_id == comment_data['user_id'] else False
        }
        return comment_item
    
    print("LAST COMMENT ID")
    print(last_comment_id)
    
    if last_comment_id:
        last_comment = comment_collection.document(last_comment_id).get()
        if not last_comment.exists:
            return jsonify({
                'success': False,
                'msg': '잘못된 last_comment_id 입니다.'
            }), 400
        
        last_comment_data = last_comment.to_dict()
        
        #메인 댓글 검사 로직
        if last_comment_data['tag_id'] == '':
            #메인 댓글임
            main_comment_id = last_comment_id
            
            #메인 댓글이니까 여기부터 검색하자
            query = query.start_after(last_comment)
            
            #메인 댓글 ID가 왔으니 해당 메인 댓글의 서브 댓글부터 조회한다.
            sub_query = comment_collection.where('tag_id', '==', main_comment_id).order_by("time", direction=firestore.Query.ASCENDING)
            sub_comments = sub_query.stream()
            
            for sub_comment in sub_comments:
                sub_comment_item = fetch_user_info(sub_comment)
                
                total_comments.append(sub_comment_item)
                if len(total_comments) > limit:
                    return jsonify({
                        'success': True,
                        'msg': '댓글 반환에 성공했습니다.',
                        'comments': total_comments
                    }), 200
                
        else:
            #메인 아이디 가져오기
            main_comment_id = last_comment_data['tag_id']
            
            last_main_comment_snapshot = comment_collection.document(main_comment_id).get()
            if last_comment_snapshot.exists:
                query = query.start_after(last_main_comment_snapshot)
                
                #마지막 대댓글 이후부터 조회
                sub_query = comment_collection.where('tag_id', '==', main_comment_id).order_by("time", direction=firestore.Query.ASCENDING).start_after(last_comment)
                sub_comments = sub_query.stream()
                for sub_comment in sub_comments:
                    sub_comment_item = fetch_user_info(sub_comment)
                
                    total_comments.append(sub_comment_item)
                    if len(total_comments) > limit:
                        return jsonify({
                            'success': True,
                            'msg': '댓글 반환에 성공했습니다.',
                            'comments': total_comments
                        }), 200
                    
                    
            else:
                return jsonify({
                    'success': False,
                    'msg': '잘못된 last_comment_id 입니다.'
                }), 400

    comments = query.stream()
    
    for comment in comments:
        comment_item = fetch_user_info(comment)
        total_comments.append(comment_item)
        print(comment_item["contents"])
        if len(total_comments) > limit:
            return jsonify({
                'success': True,
                'msg': '댓글 반환에 성공했습니다.',
                'comments': total_comments
            }), 200
        
        sub_query = comment_collection.where('tag_id', '==', comment_item['comment_id']).order_by("time", direction=firestore.Query.ASCENDING)
        sub_comments = sub_query.stream()
        for sub_comment in sub_comments:
            sub_comment_item = fetch_user_info(sub_comment)
                
            total_comments.append(sub_comment_item)
            if len(total_comments) > limit:
                return jsonify({
                    'success': True,
                    'msg': '댓글 반환에 성공했습니다.',
                    'comments': total_comments
                }), 200
    
    print(json.dumps(total_comments, indent=4))
    
    return jsonify({
        'success': True,
        'msg': '댓글 반환에 성공했습니다.',
        'comments': total_comments
    }), 200
