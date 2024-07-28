from app import db, bucket
from app.utils.decorators import *
import concurrent.futures
from firebase_admin import firestore
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
import pytz

# 게시글 블루프린트 작성
article_routes = Blueprint('article', __name__)

# 게시글 작성 처리
@article_routes.route('/add_article', methods=['POST'])
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
        time_utc = datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M')

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
            'keywords': keywords,
            'contents': contents,
            'time': time_utc,
            'lat': lat,
            'lng': lng,
            'image_urls': image_urls, 
            'user_id': user_id
        }

        _, city_ref = db.collection('articles').add(doc_data)
        doc_data['uid'] = city_ref.id
        doc_data['writer'] = nickname
        doc_data['user_img'] = picture
        
        return jsonify({'success': True, 'msg': '게시글이 성공적으로 작성되었습니다', 'article': doc_data}), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'success': False, 'msg': str(e)}), 500

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

    doc_ref.delete()
    return jsonify({
        'success': True, 
        'msg': '게시글 삭제 완료'
    }), 200

# 게시글 자세히 보기 + 댓글 반환
@article_routes.route('/get_article_detail', methods=['GET'])
@validation_token()
def get_article_detail(user_id):
    # 게시글 id 받아오기
    article_id = request.args.get('uid')
    print("게시글 id", article_id)
        
    if not article_id:
        return jsonify({
            'success': False,
            'msg': '게시글 ID가 제공되지 않았습니다.'
        }), 400

    # articles 컬렉션에서 article_id에 해당하는 게시글 가져오기 
    article_ref = db.collection("articles").document(article_id)
    article = article_ref.get()
        
    # articles 컬렉션 안에 있는 article_id에 해당하는 게시글의 모든 댓글 id 가져와서 보내는 부분
    # comments 컬렉션의 모든 문서 가져오기
    comments_ref = article_ref.collection('comments')
    comments = comments_ref.stream()

    # 모든 comment 문서의 ID를 저장할 리스트
    comment_ids = []
    for comment in comments:
        comment_ids.append(comment.id)
    
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
    except Exception as e:
        print("Error Occured!!", e)
        picture = None
        nickname = None
        
    # 가져온 게시글에서 내용 뽑아내기
    article_item = {
        'uid': article_id,
        'contents': article_data.get('contents', ''),
        'cat1': article_data.get('cat1', ''),
        'cat2': article_data.get('cat2', ''),
        'keywords': article_data.get('keywords', []),
        'time': article_data.get('time', ''),
        'comment_count': len(comment_ids),
        'like_count': article_data.get('like_count', 0),
        'image_urls': article_data.get('image_urls', []),
        'user_img': picture,
        'writer': nickname,
        'can_delete': True if article_data['user_id'] == user_id else False
    }
    
    # 모든 댓글을 저장하기 위한 리스트
    comment_list = []
     
    # 특정 문서의 comments 하위 컬렉션 참조 및 최신순 정렬
    comments_ref = db.collection('articles').document(article_id).collection('comments')

    # comments 컬렉션의 모든 문서 가져오기
    comments = comments_ref.stream()

    # 댓글 작성자 정보를 병렬로 가져오기 위한 함수
    def fetch_user_info(comment):
        comment_data = comment.to_dict()
        comment_id = comment.id
        comment_user_id = comment_data.get('user_id', '')
        if not comment_user_id:
            return None
        
        # 작성자의 uid를 auth에서 가져오기
        try:
            user = auth.get_user(comment_user_id)
            comment_item = {
                'time': comment_data.get('time', ''),
                'comment_id': comment_id,
                'contents': comment_data.get('contents', ''),
                'user_img': user.photo_url,
                'writer': user.display_name,
                'can_delete': True if user_id == comment_user_id else False
            }
        except Exception as e:
            print("Error Occured!!", e)
            comment_item = {
                'time': comment_data.get('time', ''),
                'comment_id': comment_id,
                'contents': comment_data.get('contents', ''),
                'user_img': None,
                'writer': None,
                'can_delete': True if user_id == comment_user_id else False
            }
        return comment_item

    # 병렬로 댓글 작성자 정보 가져오기
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_comment = {executor.submit(fetch_user_info, comment): comment for comment in comments}
        for future in concurrent.futures.as_completed(future_to_comment):
            comment_item = future.result()
            if comment_item:
                comment_list.append(comment_item)

    comment_list = sorted(comment_list, key=lambda x: x['time'], reverse=True)   
    print(comment_list)

    return jsonify({
        'success': True,
        'msg': '게시글 및 댓글 목록 반환에 성공했습니다.',
        'article': article_item,
        'comments': comment_list
    }), 200

# 특정 유저가 작성한 게시글 목록 받아오기
@article_routes.route('/get_user_article_list', methods=['GET'])
@validation_token()
def get_article_detail(user_id):
    # articles 컬렉션에서 특정 user_id가 작성한 게시글 가져오기
    articles_ref = db.collection('articles')
    query = articles_ref.where('user_id', '==', user_id)
    articles = query.stream()

    # 결과를 저장할 리스트
    articles_list = []
    for article in articles:
        article_data = article.to_dict()
        # articles 컬렉션 안에 있는 article_id에 해당하는 게시글의 모든 댓글 id 가져와서 보내는 부분
        # comments 컬렉션의 모든 문서 가져오기
        comments_ref = articles_ref.collection('comments')
        comments = comments_ref.stream()

        # 모든 comment 문서의 ID를 저장할 리스트
        comment_ids = []
        for comment in comments:
            comment_ids.append(comment.id)
            
        article_data = article.to_dict()
            
        # 작성자의 uid를 auth에서 가져오기
        try:
            user = auth.get_user(user_id)
            picture = user.photo_url
            nickname = user.display_name
        except Exception as e:
            print("Error Occured!!", e)
            picture = None
            nickname = None
        # 가져온 게시글에서 내용 뽑아내기
        article_item = {
            'uid': article.id,
            'contents': article_data.get('contents', ''),
            'cat1': article_data.get('cat1', ''),
            'cat2': article_data.get('cat2', ''),
            'keywords': article_data.get('keywords', []),
            'time': article_data.get('time', ''),
            'comment_count': len(comment_ids),
            'like_count': article_data.get('like_count', 0),
            'image_urls': article_data.get('image_urls', []),
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