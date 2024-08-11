# 
# <article.py>
# 
# 게시글과 관련관 API 엔드포인트를 관리합니다.
#
# 주요 기능:
# - 게시글 작성 처리
# - 게시글 삭제 처리
# - 게시글 상세 보기
# - 특정 유저가 작성한 게시글 목록 받아오기
#

# import libraries
from app import db, bucket
from app.utils.decorators import *
from app.utils.exceptions import *
from firebase_admin import firestore
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
import pytz

# 게시글 블루프린트 작성
article_routes = Blueprint('article', __name__)

# 게시글 작성 처리
@article_routes.route('/add_article', methods=['POST'])
@error_handler()
@validation_token()
def create_article(user_id):
    try:
        images = request.files.getlist('images')
        cats = request.form.getlist('categories')
        cat1 = cats[0]
        cat2 = cats[1]
        keywords = request.form.getlist('keywords')
        contents = request.form.get('contents')
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        print(lat, lng)
        

        if (all(len(keyword) == 0 for keyword in keywords) or
            any(len(keyword) > 20 for keyword in keywords)):
            return jsonify({
                "success": False, 
                "msg": "add_article, plz write one keywords",
                'article': "no data"
            }), 400


        
        #print(f"파일 이름: {images.filename}")
        #print(f"파일 타입: {images.content_type}")

        #UTC 저장
        time_utc = datetime.now(pytz.timezone('UTC'))
        
        image_urls = []
        for image in images:
            if image:
                image_filename = f'{uuid.uuid4()}.jpg'
                blob = bucket.blob(f'images/{image_filename}')
                # https://stackoverflow.com/questions/65616314/how-to-upload-an-image-to-google-firestore-bucket 참고
                blob.upload_from_file(image.stream, content_type=image.content_type)
                blob.make_public()
                image_urls.append(blob.public_url)
                
        # 헤더에서 작성자의 uid를 가져와 게시글에 닉네임 추가하는 코드        
        # 작성자의 uid를 auth에서 가져오기
        try:
            user = auth.get_user(user_id)
            picture = user.photo_url
            nickname = user.display_name
        except Exception as e:
            picture = None
            nickname = None
        
        doc_data = {
            'cat1': cat1,
            'cat2': cat2,
            'contents': contents,
            'image_urls': image_urls, 
            'keywords': keywords,
            'lat': lat,
            'lng': lng,
            'time': time_utc,
            'user_id': user_id
        }
        
        _, city_ref = db.collection('articles').add(doc_data)
        doc_data['uid'] = city_ref.id
        doc_data['comment_counts'] = 0
        doc_data['like_count'] = 0
        doc_data['user_img'] = picture
        doc_data['writer'] = nickname
        doc_data['is_liked'] = False
        doc_data['can_delete'] = True
        doc_data['time'] = time_utc.strftime('%Y-%m-%d %H:%M')
        
        return jsonify({
            'success': True, 
            'msg': '게시글이 성공적으로 작성되었습니다', 
            'article': doc_data
        }), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({
            'success': False, 
            'msg': str(e)
        }), 500

# 게시글 삭제 처리
@article_routes.route('/delete_article/<article_id>', methods=['DELETE'])
@validation_token()
def delete_article(article_id, user_id):
    docs_ref = db.collection('articles')
    doc_ref = docs_ref.document(article_id)
    article_doc = doc_ref.get()
    
    if not article_doc.exists:
        return jsonify({
            'success': False, 
            'msg': '게시글이 존재하지 않음'
        }), 404
    
    article_data = article_doc.to_dict()
    article_uid = article_data.get('user_id')
    
    if article_uid != user_id:
        return jsonify({
            'success': False, 
            'msg': '글쓴이가 아님'
        }), 403
    
    # 댓글 서브컬렉션과 그 하위의 sub_comments 삭제
    comments_ref = doc_ref.collection('comments')
    comments = comments_ref.stream()

    for comment in comments:
        # sub_comments 서브컬렉션 삭제
        sub_comments_ref = comment.reference.collection('sub_comments')
        sub_comments = sub_comments_ref.stream()
        for sub_comment in sub_comments:
            sub_comment.reference.delete()

        # 댓글 삭제
        comment.reference.delete()

    # liked_users 서브컬렉션 삭제
    liked_users_ref = doc_ref.collection('liked_users')
    liked_users = liked_users_ref.stream()

    for liked_user in liked_users:
        liked_user.reference.delete()

    # 최종적으로 게시글 삭제
    doc_ref.delete()

    return jsonify({
        'success': True, 
        'msg': '게시글 삭제 완료'
    }), 200

# 게시글 자세히 보기 + 댓글 반환
@article_routes.route('/get_article', methods=['GET'])
@validation_token()
def get_article_detail(user_id):
    # 게시글 id 받아오기
    article_id = request.args.get('uid')

    if not article_id:
        return jsonify({
            'success': False,
            'msg': '게시글 ID가 제공되지 않았습니다.'
        }), 400
    
    # articles 컬렉션에서 article_id에 해당하는 게시글 가져오기 
    article_ref = db.collection("articles").document(article_id)
    article = article_ref.get()

    if not article.exists:
        return jsonify({
            'success': False,
            'msg': '게시글을 찾을 수 없습니다.'
        }), 404
        
    article_data = article.to_dict()
    print(article_data['user_id'])
        
    # 작성자의 uid를 auth에서 가져오기
    try:
        user = auth.get_user(article_data['user_id'])
        picture = user.photo_url
        nickname = user.display_name
        print("USER:", picture, nickname)
    except Exception as e:
        print("Error Occured!!", e)
        picture = None
        nickname = None
    
    # 좋아요 여부 확인
    liked_users_ref = article_ref.collection('liked_users')
    liked_users = liked_users_ref.stream()
    liked_user_ids = [liked_user.id for liked_user in liked_users]
    print(liked_user_ids)
    
    # 가져온 게시글에서 내용 뽑아내기
    article_item = {
        'uid': article_id,
        'contents': article_data.get('contents', ''),
        'cat1': article_data.get('cat1', ''),
        'cat2': article_data.get('cat2', ''),
        'keywords': article_data.get('keywords', []),
        'time': article_data.get('time').strftime('%Y-%m-%d %H:%M'),
        'comment_counts': article_data.get('comment_counts', 0),
        'like_count': article_data.get('like_count'),
        'image_urls': article_data.get('image_urls', []),
        'user_img': picture,
        'writer': nickname,
        'is_liked': True if user_id in liked_user_ids else False,
        'can_delete': True if article_data['user_id'] == user_id else False
    }
    
    return jsonify({
        'success': True,
        'msg': '게시글 반환에 성공했습니다.',
        'article': article_item
    }), 200

# 특정 유저가 작성한 게시글 목록 받아오기
# 여기 부분에서 리스트를 반환할 때 최신 순으로 위에서부터
@article_routes.route('/get_user_article_list', methods=['GET'])
@validation_token()
def get_user_article_list(user_id):
    last_article_id = request.args.get('last_article_id')
    # 최근 순으로 불러오도록 order_by 활용 .order_by('time', direction=firestore.Query.DESCENDING) 여기 부분 추가
    # 근데 지금 처음에 3개에 대해서만 진행됨.
    articles_ref = db.collection('articles').order_by("time", direction=firestore.Query.DESCENDING)
    query = articles_ref.where('user_id', '==', user_id)
    
    # 차후 20으로 수정
    limit = 5
    
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
        
    # 여기까지    
    articles = query.stream()

    # 결과를 저장할 리스트
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
    
    for article in articles:
        article_data = article.to_dict()
        
        # 가져온 게시글에서 내용 뽑아내기
        article_item = {
            'uid': article.id,
            'contents': article_data.get('contents', ''),
            'cat1': article_data.get('cat1', ''),
            'cat2': article_data.get('cat2', ''),
            'keywords': article_data.get('keywords', []),
            'time': article_data.get('time', None).strftime("%Y-%m-%d %H:%M"),
            'like_count': article_data.get('like_count', 0),
            'image_urls': article_data.get('image_urls', []),
            'comment_counts': article_data.get('comment_counts', 0),
            'user_img': picture,
            'writer': nickname,
            'can_delete': True
        }
        articles_list.append(article_item)

    if not articles_list:
        return jsonify({
            'success': True,
            'msg': '해당 사용자가 작성한 게시글을 찾을 수 없습니다.',
            'articles': []
        }), 200

    return jsonify({
        'success': True,
        'msg': '사용자가 작성한 게시글 목록 반환',
        'articles': articles_list
    })


