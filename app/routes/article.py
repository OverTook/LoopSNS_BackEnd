from app import db, bucket
from app.utils.decorators import *
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
import pytz

# 게시글 블루프린트 작성
article_routes = Blueprint('article', __name__)

# 게시글 작성 처리
@article_routes.route('/add_article', methods=['POST'])
@validation_token()
def create_article(uid, user_id):
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
        user_doc = db.collection('users').document(user_id)
        user = user_doc.get()
        user_data = user.to_dict()
        nickname = user_data.get('nickname', '')
        picture = user_data.get('picture', [])
        
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
def delete_article(article_id, uid, user_id):
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
def get_article_detail():
    try:
        # 게시글 id 받아오기
        article_id = request.args.get('uid')
        print("게시글 id", article_id)
        
        # articles 컬렉션에서 article_id에 해당하는 게시글 가져오기 
        article_ref = db.collection("articles").document(article_id)
        article = article_ref.get()
        
        comment_list = article_ref.collection('comments').get()
        comment_count = len(comment_list)
        
        if article.exists:
            article_data = article.to_dict()
            user_id = article_data.get('user_id')
            print("사용자 id", user_id)
        
        # 헤더에서 작성자의 uid를 가져와 유저 테이블에서 사진 가져오는 코드       
        user_doc = db.collection('users').document(user_id)
        user = user_doc.get()
        user_data = user.to_dict()
        picture = user_data.get('picture', [])
        nickname = user_data.get('nickname', '')
        
        if article.exists:   
            # 가져온 게시글에서 내용 뽑아내기
            article_data = article.to_dict()

            article_item = {
                'uid': article_id,
                'contents': article_data.get('contents', ''),
                'cat1': article_data.get('cat1', ''),
                'cat2': article_data.get('cat2', ''),
                'keywords': article_data.get('keywords', []),
                'time': article_data.get('time', ''),
                'like_count': article_data.get('like_count', 0),
                'comment_count': comment_count,
                'image_urls': article_data.get('image_urls', []),
                'user_img': picture,
                'writer': nickname
            }            
            
            print(article_item)
            
            # 모든 댓글을 저장하기 위한 리스트
            comment_list = []
         
            # 특정 문서의 comments 하위 컬렉션 참조
            comments_ref = db.collection('articles').document(article_id).collection('comments')

            # comments 컬렉션의 모든 문서 가져오기
            comments = comments_ref.stream()

            # 각 comment 문서의 데이터 출력
            for comment in comments:
                
                comment_data = comment.to_dict()
                
                # 댓글에서 댓글을 작성한 유저의 id를 가져옴 => 가져온 아이디로 유저 테이블을 탐색해 사진과 닉네임 반환
                comment_user_id = comment_data.get('user_id', '')
                user_doc = db.collection('users').document(comment_user_id)
                user = user_doc.get()
                user_data = user.to_dict()
                picture = user_data.get('picture', [])
                #nickname = user_data.get('nickname'. '')
                
                comment_item = {
                    'time': comment_data.get('time', ''),
                    'contents': comment_data.get('contents', ''),
                    'user_img': picture,
                    'writer': ''
                }
                comment_list.append(comment_item)
                print(f'{comment.id} => {comment_item}')

            return jsonify({
                'success': True,
                'msg': '게시글 및 댓글 목록 반환에 성공했습니다.',
                'article': article_item,
                'comments': comment_list
            }), 200
        else:
            return jsonify({
                'success': False,
                'msg': '잘못된 게시글입니다.'
            }), 404
        
    except Exception as e:
        error_msg = f"Error occurred: {str(e)}"
        print(error_msg)
        return jsonify({
            'success': False, 
            'msg': error_msg
        }), 500
    
