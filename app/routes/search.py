from app import db
from app.utils.decorators import *
from flask import Blueprint, request, jsonify
from google.cloud.firestore_v1.base_query import FieldFilter
import re
from firebase_admin import auth
import time  # time 모듈 추가

# 검색 블루프린트 작성
search_routes = Blueprint('search', __name__)

# 검색 처리
@search_routes.route('/search', methods=['GET'])
def search():
    start_time = time.time()  # 전체 실행 시간 측정 시작

    # lat_from = float(request.args.get('lat_from'))
    # lng_from = float(request.args.get('lng_from'))
    # lat_to = float(request.args.get('lat_to'))
    # lng_to = float(request.args.get('lng_to'))
    c1 = request.args.get('c1')
    c2 = request.args.get('c2')
    q = request.args.get('query', '')  # 검색어 기본값을 빈 문자열로 설정
    search_type = request.args.get('search_type', 'content')

    # 좌표 범위 계산
    # nw_coord = (min(lat_from, lat_to), min(lng_from, lng_to))
    # se_coord = (max(lat_from, lat_to), max(lng_from, lng_to))

    # Firestore에서 좌표 범위 내의 articles 가져오기
    articles_ref = db.collection('articles')
    #query_start_time = time.time()  # 쿼리 시작 시간 측정
    #query = articles_ref \
    #    .where(filter=FieldFilter('lat', '>=', str(nw_coord[0]))) \
    #    .where(filter=FieldFilter('lat', '<=', str(se_coord[0]))) \
    #    .where(filter=FieldFilter('lng', '>=', str(nw_coord[1]))) \
    #    .where(filter=FieldFilter('lng', '<=', str(se_coord[1])))
    
    query = articles_ref
    # 카테고리 필터링
    if c1:
        query = articles_ref.where(field_path='cat1', op_string='==', value=c1)
    if c2:
        query = articles_ref.where(field_path='cat2', op_string='==', value=c2)

    # 검색어 필터링
    articles = []
    if q and search_type:
        # 공백 제거 및 소문자로 변환
        q = re.sub(r'\s+', '', q).lower()

        if search_type == 'writer':
            writers = []

            # Firebase 프로젝트의 모든 유저를 가져오기
            page = auth.list_users()
            while page:
                for user in page.users:
                    nickname = re.sub(r'\s+', '', user.display_name).lower()
                    if nickname and q in nickname:
                        for article in query.where('user_id', '==', user.uid).stream():
                            article_dict = article.to_dict()
                            articles.append({
                                'uid': article.id,
                                'contents': article_dict.get('contents', ''),
                                'cat1': article_dict.get('cat1', ''),
                                'cat2': article_dict.get('cat2', ''),
                                'keywords': article_dict.get('keywords', []),
                                'time': article_dict.get('time', None).strftime("%Y-%m-%d %H:%M"),
                                'comment_counts': article_dict.get('comment_counts', 0),
                                'like_count': article_dict.get('like_count', 0),
                                'image_urls': article_dict.get('image_urls', []),
                            })
                        # writers.append(user)
                # 다음 페이지 가져오기
                page = page.get_next_page()
        else:
            # 쿼리 실행
            articles_stream = query.stream()  # 쿼리 실행

            for article in articles_stream:
                article_dict = article.to_dict()

                # 내용에서 모든 공백 제거 및 소문자로 변환
                content = re.sub(r'\s+', '', article_dict.get('contents', '')).lower()
                
                # 키워드에서 모든 공백 제거 및 소문자로 변환
                keywords = [
                    re.sub(r'\s+', '', keyword).lower() for keyword in article_dict.get('keywords', [])
                ]

                # 게시글 항목 생성
                article_item = {
                    'uid': article.id,
                    'contents': article_dict.get('contents', ''),
                    'cat1': article_dict.get('cat1', ''),
                    'cat2': article_dict.get('cat2', ''),
                    'keywords': article_dict.get('keywords', []),
                    'time': article_dict.get('time', None).strftime("%Y-%m-%d %H:%M"),
                    'comment_counts': article_dict.get('comment_counts', 0),
                    'like_count': article_dict.get('like_count', 0),
                    'image_urls': article_dict.get('image_urls', []),
                    # 'user_img': picture,
                    # 'writer': nickname,
                }
                
                # 검색 필터링
                if search_type == 'content' and q in content:
                    articles.append(article_item)
                elif search_type == 'keyword' and any(q in keyword for keyword in keywords):
                    articles.append(article_item)
    # else:
        # 검색어가 없을 경우 전체 쿼리 실행
        # articles = [article.to_dict() for article in query.stream()]

    # print({
    #     'success': True,
    #     'msg': '검색 목록 반환',
    #     'articles': articles
    # })

    articles.sort(key=lambda x: x['time'], reverse=True)

    return jsonify({
        'success': True,
        'msg': '검색 목록 반환',
        'articles': articles
    })
