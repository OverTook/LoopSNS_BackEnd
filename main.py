from flask import Flask, request, jsonify, current_app
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
from google.cloud import firestore as fs
import uuid
import os
from datetime import datetime
from sklearn.cluster import KMeans
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.field_path import FieldPath
from sklearn.cluster import MeanShift, estimate_bandwidth
import numpy as np
import requests
from PIL import Image
from io import BytesIO
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
import base64
import re
import cv2
from datetime import datetime
import pytz

# Firebase 초기화
cred_path = "kdb-b-569e9-firebase-adminsdk-iowq7-709344ad03.json"
cred = credentials.Certificate(cred_path)
firebase_app = firebase_admin.initialize_app(cred, {
    'storageBucket': 'kdb-b-569e9.appspot.com'
})

# Google Cloud 프로젝트 ID 설정
project_id = "hci202401"
# 서비스 계정 인증 파일 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "hci202401-073e7248e4b8.json"

db = firestore.client(app=firebase_app)
bucket = storage.bucket(app=firebase_app)

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = './KDB_uploaded/images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 토큰 인증하는 함수
def token():
    id_token = request.headers.get('Authorization')
    user_id = request.headers.get('User-ID')
    print("user_id : ", user_id)

    # 여기 부분이 토큰이 "Bearer "로 시작하는지 확인하는 부분인데 없으면 오류 발생.
    if not id_token or not id_token.startswith('Bearer '):
        return jsonify({'success': False}), 400

    # id_token = id_token.split(' ')[1]으로 토큰을 추출하기 전에 위에서 id_token.startswith('Bearer ')을 먼저 확인해야 함.
    # 토큰이 "Bearer "로 시작하지 않는 경우, split(' ') 메서드는 오류가 발생할 수 있음.
    
    id_token = id_token.split(' ')[1]

    decoded_token = auth.verify_id_token(id_token)
    uid = decoded_token['uid']
    print("uid : ", uid)

    if uid != user_id:
        # 401 = 미승인 및 비인증
        return jsonify({'success': False}), 401
    
#     #갱신 토큰 취소
#     try:
#         auth.revoke_refresh_tokens(uid)
#         user = auth.get_user(uid)
        
#         #토큰 클레임의 auth_time이 초 단위이므로 초로 변환
#         revocation_second = user.tokens_valid_after_timestamp / 1000
#         print('Tokens revoked at: {0}'.format(revocation_second))
        
#     except Exception as e:
#         print("Error revoking refresh tokens:", str(e))
#         return jsonify({'success': False}), 500

#     return jsonify({'success': True}), 200


@app.route('/delete_article', methods=['POST'])
def delete_article():
    token()
    
    header_uid = request.headers.get('User-ID')    
    article_id = request.json.get('article_id')

    docs_ref = db.collection('articles')
    doc_ref = docs_ref.document(article_id)
    article_doc = doc_ref.get()
    
    if not article_doc.exists:
        return jsonify({'success': False, 'msg': '게시글이 존재하지 않음'}), 404
    
    article_data = article_doc.to_dict()
    article_uid = article_data.get('user_id')
    
    if article_uid != header_uid:
        return jsonify({'success': False, 'msg': '글쓴이가 아님'}), 403

    doc_ref.delete()
    return jsonify({'success': True, 'msg': '게시글 삭제 완료'}), 200
                        
    
#게시글 작성 처리
@app.route('/add_article', methods=['POST'])
def create_article():
    try:
        token()
        
        images = request.files.getlist('images')
        #title = request.json.get('title')
        cats = request.form.getlist('categories')
        cat1 = cats[0]
        cat2 = cats[1]
        keywords = request.form.getlist('keywords')
        contents = request.form.get('contents')
        time = request.form.get('time')
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        
        print(lat)
        print(lng)
        
        time_utc = datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M')
        
        user_id = request.headers.get('User-ID')
        

        image_urls = []
        for image in images:
            if image:
                image_filename = f'{uuid.uuid4()}.jpg'
                blob = bucket.blob(f'images/{image_filename}')
                #https://stackoverflow.com/questions/65616314/how-to-upload-an-image-to-google-firestore-bucket 참고
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

#댓글 작성
@app.route('/add_comment', methods=['POST'])
def create_comment():
    try:
        token()
        
        user_id = request.headers.get('User-ID')
        if not user_id:
            raise ValueError("User-ID header is required")

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

        # #상위 컬렉션에 저장
        # db.collection('comments').add(comment_data)
        
        #articles 컬렉션의 하위 컬렉션으로 저장
        article_ref = db.collection('articles').document(article_id)
        article_ref.collection('comments').add(comment_data)
        
        
        #방금 넣은 코드
        comment_list = article_ref.collection('comments').get()
        comment_count = len(comment_list)

        return jsonify({'success': True, 'msg': '성공적으로 작성되었습니다'}), 200

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'success': False, 'msg': str(e)}), 500


# 마커를 눌렀을 때 게시글의 타임라인이 나오는 함수
@app.route('/get_marker_timeline', methods=['GET'])
def get_article_timeline():
    try:
        # 앱으로부터 데이터 수신
        articles = request.args.getlist('articles')
        #print(articles)
        
        if len(articles) == 0:
            return jsonify({
                'success': False,
                'msg': 'No article IDs provided',
                'articles': []
            }), 400
        
        # 최대 문서 ID 개수 30개로 고정시킴
        max = 30
        
        # 쿼리 분할을 통해 일단은 30개를 최대로 정하고
        articles_count = [articles[i:i + max] for i in range(0, len(articles), max)]
        
        # Firestore에서 데이터 가져오기
        articles_list = []
        for count in articles_count:
            docs = db.collection('articles').where(FieldPath.document_id(), "in", count).stream()
            for doc in docs:
                article_data = doc.to_dict()
                article_item = {
                    'uid': doc.id,
                    'writer': article_data.get('writer', ''),
                    'title': article_data.get('title', ''),
                    'contents': article_data.get('contents', ''),
                    'cat1': article_data.get('cat1', ''),
                    'cat2': article_data.get('cat2', ''),
                    'keywords': article_data.get('keywords', []),
                    'time': article_data.get('time', ''),
                    'comment_count': article_data.get('comment_count', 0),
                    'like_count': article_data.get('like_count', 0),
                    'image_urls': article_data.get('image_urls', [])
                }
                articles_list.append(article_item)

        time_list = sorted(articles_list, key=lambda x: datetime.strptime(x['time'], "%Y-%m-%d %H:%M"), reverse=True)
        '''
        for item in time_list:
            print(item['time'])
        '''    
        

        response = {
            'success': True,
            'msg': '',
            'articles': time_list
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

# 좋아요 기능 추가
@app.route('/add_article_like', methods=['POST'])
def addlike():
    try:
        token()
        
        user_id = request.headers.get('User-ID')
        article_id = request.json.get('article_id') 
        increment = request.json.get('like')

        #print(f"user_id: {user_id}, article_id: {article_id}, increment: {increment}")
        
        #좋아요 누르면 true, 취소하면 false
        if increment.lower() == 'true':
            increment = True
        elif increment.lower() == 'false':
            increment = False
        
        like_ref = db.collection('articles').document(article_id)
        article_doc = like_ref.get()
        
        # 특정 사용자 데이터 참조 후 가져오기 (사용자에게 좋아요한 게시글 목록 추가 또는 제거)
        #해당 자료 https://www.googlecloudcommunity.com/gc/Databases/Using-Firestore-with-Python-Web-and-Flutter-Clients/m-p/609316
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        liked_user_ref = like_ref.collection('liked_users').document(user_id)
        liked_user_doc = liked_user_ref.get()

        # like_users에 일치하는 user_id가 없을 경우 좋아요 추가
        if increment:
            if not liked_user_doc.exists:
                liked_user_ref.set({})
                if 'like_count' not in article_doc.to_dict():
                    like_ref.set({'like_count': 1}, merge=True)
                else:
                    like_ref.update({
                        'like_count': Increment(1)
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
                    'like_count': Increment(-1)
                })
                if user_doc.exists:
                    user_ref.update({
                        'article_liked': firestore.ArrayRemove([article_id])
                    })

        # 좋아요 수 반환 (timeline 부분에 like_count에 사용)
        updated_like_ref = like_ref.get()
        like_count = updated_like_ref.to_dict().get('like_count', 0)

        liked_users_snapshot = like_ref.collection('liked_users').get()
        liked_user_ids = [doc.id for doc in liked_users_snapshot]

        response = {
            'success': True,
            'msg': 'Like updated successfully'
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

# 내가 좋아요 누른 게시글 목록 확인하는 부분
@app.route('/user_liked_article_list', methods=['GET'])
def liked_article_list():
    try:
        token()
        
        user_id = request.headers.get('User-ID') 
        
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

        articles_list = []
        docs = db.collection('articles').where(FieldPath.document_id(), "in", liked_article_ids).stream()

        for doc in docs:
            article_data = doc.to_dict()
            article_item = {
                'uid': doc.id,
                'contents': article_data.get('contents', '')
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
    
# 마커 클러스터
@app.route('/get_marker_clusterer', methods=['GET'])
def retrieve_article_marker():
    lat_from = float(request.args.get('lat_from'))
    lng_from = float(request.args.get('lng_from'))
    lat_to = float(request.args.get('lat_to'))
    lng_to = float(request.args.get('lng_to'))
    
    if None in (lat_from, lng_from, lat_to, lng_to):
        return jsonify({'success': False, 'msg': '좌표가 없거나 누락되었습니다.', 'markers': []}), 400

    try:
        # 좌표 범위 계산
        nw_coord = (min(lat_from, lat_to), min(lng_from, lng_to))
        se_coord = (max(lat_from, lat_to), max(lng_from, lng_to))
        
        # Firestore에서 좌표 범위 내의 articles 가져오기
        articles_ref = db.collection('articles')
        query = articles_ref.where(filter=FieldFilter('lat', '>=', str(nw_coord[0]))).where(filter=FieldFilter('lat', '<=', str(se_coord[0]))) \
                            .where(filter=FieldFilter('lng', '>=', str(nw_coord[1]))).where(filter=FieldFilter('lng', '<=', str(se_coord[1])))
        
        articles = query.stream()
        
        # 클러스터링 함수 호출
        clustered_markers = cluster_articles(articles)
        
        # 성공 시 클러스터링된 좌표와 문서 ID 반환
        response = {
            'success': True,
            'msg': 'success',
            'markers': clustered_markers,
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        error_msg = f"Error occurred: {str(e)}"
        print(error_msg)
        return jsonify({'success': False, 'msg': error_msg, 'markers': []}), 500

# 클러스터링 함수
def cluster_articles(articles):
    coordinates = []
    article_ids = []

    # Firestore에서 가져온 각 article의 좌표와 ID를 리스트에 저장
    for article in articles:
        article_data = article.to_dict()
        coordinates.append([float(article_data['lat']), float(article_data['lng'])])
        article_ids.append(article.reference.id)  # 문서 ID 추가
        
    coordinates = np.array(coordinates)
    
    try:
        if len(coordinates) == 0:
            return []  # 데이터가 없으면 빈 리스트 반환해서 데이터가 없는 공간에 가도 오류가 발생하지 않도록 함.
        
        # bandwidth 값 설정, 0.1로 무조건 설정해서 값이 0으로 떨어지지 않도록 유지. 0으로 떨어지면 오류 발생함.
        bandwidth = estimate_bandwidth(coordinates, quantile=0.3, n_samples=len(coordinates))
        if bandwidth <= 0:
            bandwidth = 0.1  # 기본 bandwidth 값 설정
        
        # MeanShift 클러스터링 부분
        mean_shift = MeanShift(bandwidth=bandwidth)
        mean_shift.fit(coordinates)

        # 클러스터 중심점과 레이블 가져옴
        cluster_centers = mean_shift.cluster_centers_
        labels = mean_shift.labels_

        clustered_markers = []
        
        # 클러스터링된 결과를 딕셔너리에 추가
        for i, center in enumerate(cluster_centers):
            cluster_article_ids = [article_ids[j] for j in range(len(labels)) if labels[j] == i]
            clustered_markers.append({
                'articles': cluster_article_ids,
                'lat': center[0],
                'lng': center[1]
            })

        return clustered_markers
    
    except Exception as e:
        raise RuntimeError(f"Error in clustering process: {str(e)}")


@app.route('/login', methods=['GET'])
def login():
    platform = request.args.get('platform')
    token = request.args.get('token')
    
    print("-"*50)
    print(platform)
    print(token)
    print("-"*50)
    
    if not platform or not token:
        return jsonify({'success': False, 'msg': '필수 파라미터가 누락되었습니다.', 'token': ''}), 200
    try:
        if platform == 'google':
            #구글 아이디 토큰을 기반으로 이메일 추출
            token_info = get_google_token_info(token)
            
            picture = token_info.get('picture')
            nickname = token_info.get('name')
            
            email = token_info.get('email')
        elif platform == 'kakao':
            #카카오 엑세스 토큰을 기반으로 이메일 추출
            user_info = get_kakao_user_info(token)
            
            picture = user_info.get('picture')
            nickname = user_info.get('nickname')
            
            email = user_info.get('email')
        else:
            return jsonify({'success': False, 'msg': '지원하지 않는 플랫폼으로 로그인을 진행하였습니다.', 'token': ''}), 200
        
        if email:
            #유저를 로그인/회원가입 진행
            user = get_or_create_user(email)
            c_user = user.uid
            
            doc_ref = db.collection('users').document(c_user)
            doc_ref.set({
                'nickname': nickname,
                'picture': picture
            })
            
            #계정 기반으로 토큰 발행
            custom_token = create_custom_token(user.uid)      
            
            return jsonify({'success': True, 'msg': '', 'token': custom_token.decode('utf-8')})
        else:
            return jsonify({'success': False, 'msg': '토큰 정보에서 이메일을 조회할 수 없습니다.', 'token': ''}), 200
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e), 'token': ''}), 200
    
def get_kakao_user_info(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get('https://kapi.kakao.com/v1/oidc/userinfo', headers=headers)
    response.raise_for_status()
    return response.json()

def get_google_token_info(id_token):
    response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}')
    response.raise_for_status()
    return response.json()

def get_or_create_user(email):
    try:
        #이메일 기반으로 유저 조회
        user = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        #유저 존재 안하면 계정 생성
        user = auth.create_user(email=email)
    return user

def create_custom_token(uid):
    #커스텀 토큰 발급
    custom_token = auth.create_custom_token(uid)
    return custom_token


# 게시글 자세히 보기 + 댓글 반환
@app.route('/get_article_detail', methods=['GET'])
def user_history():
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

            return {
                'article': article_item,
                'comments': comment_list
            }, 200
        else:
            return "잘못된 게시글입니다.", 404
        
    except Exception as e:
        error_msg = f"Error occurred: {str(e)}"
        print(error_msg)
        return jsonify({'success': False, 'msg': error_msg, 'markers': []}), 500
    
#카테고리 파트    
def process_image_and_text(image_bytes, text_content=""):
    if image_bytes:
        encode_image = base64.b64encode(image_bytes).decode('utf-8')
        image_part = Part.from_data(data=base64.b64decode(encode_image), mime_type="image/jpeg")
        print("good")
    else:
        image_part = None

    if not text_content:
        text_content = ""

    prompt = """
    Your job will be to analyze the images and text you're sent and classify them into categories and keywords.
    Even if you don't have either the image or the text, you still need to categorize it.
    You should output two categories and four keywords.

    For each input, you should do the following
    1. determine a primary and secondary category based on the content.
    2. extract the four relevant keywords that best describe the content.

    The categories should be chosen from the examples given, and the keywords should be relevant to the image, text, or both.

    Output format:
    - Primary categories should be enclosed in parentheses ().
    - Secondary categories should be enclosed in parentheses ().
    - Keywords should be enclosed in square brackets [].
    
    The example below shows a primary category and secondary categories that fall under the primary category.
    When analyzing images and text, be sure to pick the primary and secondary categories from the example below so that you can categorize them.
    
    카테고리 예시:
    (일상): [취미, 생활정보, 설득, 공감, 소통, 감정, 예술성, 창의성, 칭찬, 사과, 불만, 교류, 고민, 상담, 가족, 여행, 음식, 운동, 양치질, 식사]
    (동물): [고양이, 강아지, 호랑이, 사슴, 사자, 기린, 판다, 오리, 비둘기, 사람, 하마, 코뿔소]
    (전자제품): [키보드, 노트북, 컴퓨터, 마우스, 오디오, TV, 세탁기, 냉장고, 조명]
    (정보공유): [뉴스, 팁/노하우, 교육, 기술, 건강, 경제, 문화, 정치, 과학]
    (질문): [정보요청, 의견수렴, 고민, 소통, 상담, 교육, 추천, 도움 요청]
    (일정): [모임, 기념일, 이벤트, 회의, 약속, 일정 관리]
    (광고): [프로모션, 구인/구직, 음식점, 의류, 아르바이트, 서비스, 제품 출시, 할인 행사]
    (제보): [분실물, 발견물, 사건사고, 재난사고, 불법 행위, 신고, 교통사고]
    (제안): [아이디어 제안, 피드백 요청, 협동, 타협, 정책 제안, 개선안, 프로젝트 제안]
    (폭력적): [출혈, 사망, 살인, 칼, 흉기, 사고, 시신, 폭행, 협박]
    (성인물): [성폭행, 성폭력, 성기, 성기 노출, 노상방뇨, 섹스, 음란물, 성매매]
    (기타): [상품, 공지사항, 일반, 이벤트, 제안, 도움말]
    (건강): [운동, 영양, 정신건강, 질병, 의학정보, 건강관리, 심리, 피트니스]
    (여행): [여행지 추천, 여행 팁, 숙소 정보, 맛집, 교통, 여행기, 여행사진, 여행 계획]
    (음식): [레시피, 요리법, 음식 리뷰, 맛집 추천, 식품 정보, 건강 식품, 요리 사진, 음식 문화]
    (기술): [IT, 소프트웨어, 하드웨어, 프로그래밍, 모바일, 가젯, 인터넷, 혁신 기술]
    (문화): [영화, 음악, 책, 전시, 공연, 역사, 예술, 축제, 문화 행사]
    (경제): [주식, 투자, 부동산, 재테크, 금융, 경제뉴스, 소비자 정보, 경제 동향]
    (정치): [정치뉴스, 선거, 정책, 국제정치, 정치인, 정치 토론, 사회 이슈]
    (과학): [물리학, 화학, 생물학, 천문학, 지구과학, 과학뉴스, 연구, 발명]
    (기타): [상품, 생활, 잡화]
    
    Be sure to follow the example below to output 
    
    결과물 출력 예시:
    1차 카테고리: (전자제품)
    2차 카테고리: (키보드)
    키워드: [리뷰], [기능], [신제품], [품질]
    
    1차 카테고리: (일상)
    2차 카테고리: (불만)
    키워드: [쓰레기], [분리수거 불이행], [환경오염], [청소]
    
    1차 카테고리: (정보공유)
    2차 카테고리: (교육)
    키워드: [문제집], [수학], [풀이], [공부]
    
    1차 카테고리: (음식)
    2차 카테고리: (레시피)
    키워드: [김치], [계란볶음밥], [간편한], [추천메뉴]
    
    1차 카테고리: (문화)
    2차 카테고리: (영화)
    키워드: [어벤져스], [유행], [박스오피스], [아이언맨]
    
    1차 카테고리: (일상)
    2차 카테고리: (취미)
    키워드: [피아노], [연주], [취미생활], [악기]

    1차 카테고리: (정보공유)
    2차 카테고리: (팁/노하우)
    키워드: [컴퓨터], [키보드], [단축키], [사용법]

    1차 카테고리: (질문)
    2차 카테고리: (정보요청)
    키워드: [여행지], [추천], [유럽], [여행 팁]

    1차 카테고리: (기술)
    2차 카테고리: (IT)
    키워드: [키보드], [리뷰], [기능], [신제품]
    
    1차 카테고리: (일정)
    2차 카테고리: (모임)
    키워드: [친구], [만남], [저녁식사], [약속]

    1차 카테고리: (광고)
    2차 카테고리: (구인/구직)
    키워드: [알바], [채용], [일자리], [근무조건]

    1차 카테고리: (제안)
    2차 카테고리: (아이디어 제안)
    키워드: [프로젝트], [혁신], [창의적], [개선]

    1차 카테고리: (여행)
    2차 카테고리: (여행지 추천)
    키워드: [휴양지], [추천], [바다], [리조트]
    
    The primary and secondary categories must be chosen from the provided examples.
    Ensure to output both the primary and secondary categories.
    The four keywords should be derived based on the context of the image and text, and must align with the selected categories.
    """

    # 모델
    model = GenerativeModel("gemini-pro-vision")
    
    # 이미지와 텍스트를 모두 사용하는 경우
    if image_part and text_content:
        response = model.generate_content(
            [image_part, text_content, prompt],
            generation_config={"max_output_tokens": 1000, "temperature": 0.5, "top_p": 1, "top_k": 32},
            stream=False
        )

    # 이미지만 사용하는 경우
    elif image_part:
        response = model.generate_content(
            [image_part, prompt],
            generation_config={"max_output_tokens": 1000, "temperature": 0.5, "top_p": 1, "top_k": 32},
            stream=False  
        )

    # 텍스트만 사용하는 경우
    else:
        response = model.generate_content(
            [text_content, prompt],
            generation_config={"max_output_tokens": 1000, "temperature": 0.5, "top_p": 1, "top_k": 32},
            stream=False  
        )
        
    return response.candidates[0].content.parts[0].text

# 출력 결과에 대해서 카테고리와 키워드를 분류하는 함수
def category_and_keyword(result):
    category_pattern = re.compile(r'\(([가-힣A-Za-z]+)\)')
    keyword_pattern = re.compile(r'\[([가-힣A-Za-z]+)\]')

    category_match = category_pattern.findall(result)
    keyword_match = keyword_pattern.findall(result)
    
    # 공백 제거
    category_match = [c.strip() for c in category_match]
    keyword_match = [k.strip() for k in keyword_match]

    # 각각의 변수에 값 저장
    c1 = c2 = k1 = k2 = k3 = k4 = ""

    if len(category_match) >= 2:
        c1 = category_match[0]
        c2 = category_match[1]

    if len(keyword_match) >= 4:
        k1 = keyword_match[0]
        k2 = keyword_match[1]
        k3 = keyword_match[2]
        k4 = keyword_match[3]

    return c1, c2, k1, k2, k3, k4

# 자동차 번호판 모자이크
def mosaic(image_bytes):
    # OpenCV에서 제공하는 사전 학습된 번호판 검출기 로드
    plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml')

    img_array = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    if img is None:
        print("이미지를 로드할 수 없습니다.")
        return None
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 번호판 검출
    plates = plate_cascade.detectMultiScale(gray, 1.1, 10)

    for (x, y, w, h) in plates:
        # 번호판 영역 추출
        plate_region = img[y:y+h, x:x+w]
        
        # 모자이크 효과 적용
        plate_region = cv2.resize(plate_region, (w//10, h//10))
        plate_region = cv2.resize(plate_region, (w, h), interpolation=cv2.INTER_NEAREST)
        
        # 원본 이미지의 번호판 영역을 모자이크 처리된 영역으로 교체
        img[y:y+h, x:x+w] = plate_region

    _, output_img = cv2.imencode('.jpg', img)
    return output_img.tobytes()

# 이미지 업로드 함수
def upload_image(image_bytes):
    try:
        image_filename = f'{uuid.uuid4()}.jpg'
        blob = bucket.blob(f'images/{image_filename}')
        blob.upload_from_string(image_bytes, content_type='image/jpeg')
        blob.make_public()
        return blob.public_url
    
    except Exception as e:
        print(f"Image upload failed: {e}")
        return None    

@app.route('/get_category', methods=['POST'])
def get_category():
    try:
        images = request.files.getlist('images')
        contents = request.form.get('contents')
        
        if contents.strip():  # 내용이 있는지 확인
            contents = contents.replace(" ", "")
        else:
            contents = "no_content"
        
        print(contents)

        # ##7월 25일 오류 발생하여 임시로 사용중임.
        # ##고쳐지면 아래 코드 제거 바람. -건호-
        # return jsonify(
        #     {"success": True, 
        #      "msg": "get category", 
        #      "categories": ["사고", "화재"], 
        #      "keywords": ["하나", "둘"]
        #     }
        # )
        
        
        # 각 이미지에 대해 모자이크 적용
        image_urls = []
        for image in images:
            image_bytes = image.read()
            mosaic_image_bytes = mosaic(image_bytes)
            
            image_url = upload_image(mosaic_image_bytes)
            if image_url:
                image_urls.append(image_url)

        doc_data = {
            'contents': contents,
            'image_urls': image_urls,
        }

        db.collection('save_articles').add(doc_data)
        
        
        image = images[0]
        
        if image:
            image_by = image.read()
        else:
            image_bytes = None
        result_text = process_image_and_text(image_bytes, contents if contents else " ")
        
        print(result_text)
        
        # 카테고리와 키워드 추출
        c1, c2, k1, k2, k3, k4 = category_and_keyword(result_text)
        
        
        # 지금 카테고리가 제대로 분류되지 않았을 경우엔 무조건 기타, 잡화로 선정되도록 함.
        if bool(c1):
            c1 = c1
        else:
            c1 = "기타"
        
        if bool(c2):
            c2 = c2
        else:
            c2 = "잡화"
        
        
        print(c1)
        print(c2)
        print(k1)
        print(k2)
        print(k3)
        print(k4)
        
        return jsonify({"success": True, "msg": "get category", "categories": [c1, c2], "keywords": [k1, k2, k3, k4]})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="csgpu.kku.ac.kr", port=5126, debug=True)