from app import db
from app.functions.clusterer import *
from app.utils.decorators import *
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime
import time

# 마커 블루프린트 작성
marker_routes = Blueprint('marker', __name__)

# 마커를 눌렀을 때 게시글의 타임라인이 나오는 함수
@marker_routes.route('/get_marker_timeline', methods=['GET'])
def get_marker_timeline():
    try:
        start_time = time.time() #   
        # 앱으로부터 데이터 수신
        articles = request.args.getlist('articles')
        
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
        
        split_time = time.time() #
        print(f"Time to split articles: {split_time - start_time} seconds") #
                
        # Firestore에서 데이터 가져오기
        articles_list = []
        for count in articles_count:
            docs_start_time = time.time() #
            docs = db.collection('articles').where(FieldPath.document_id(), "in", count).stream()
            docs_end_time = time.time() # 
            print(f"Time to fetch docs for count {count}: {docs_end_time - docs_start_time} seconds") #
            
            for doc in docs:
                doc_start_time = time.time() #
                article_data = doc.to_dict()
                
                # 댓글 수 가져오기
                comments_start_time = time.time()
                '''
                comments_ref = doc.reference.collection('comments')
                count_query = comments_ref.count()
                query_result = count_query.get()
                comment_count = query_result[0][0].value
                '''
                comment_count = article_data.get('comment_counts')
                
                comments_end_time = time.time()
                print(f"Time to fetch comments count for doc {doc.id}: {comments_end_time - comments_start_time} seconds")
                
                

                # 좋아요 수 가져오기
                likes_start_time = time.time()
                '''
                liked_users_ref = doc.reference.collection('liked_users')
                count_query_liked = liked_users_ref.count()
                query_result_liked = count_query_liked.get()
                like_count = query_result_liked[0][0].value
                '''
                like_count = article_data.get('like_count')
                
                likes_end_time = time.time()
                print(f"Time to fetch likes count for doc {doc.id}: {likes_end_time - likes_start_time} seconds")

                
                doc_end_time = time.time()
                print(f"Time to process doc {doc.id}: {doc_end_time - doc_start_time} seconds")
                
                article_item = {
                    'uid': doc.id,
                    'writer': article_data.get('writer', ''),
                    'title': article_data.get('title', ''),
                    'contents': article_data.get('contents', ''),
                    'cat1': article_data.get('cat1', ''),
                    'cat2': article_data.get('cat2', ''),
                    'keywords': article_data.get('keywords', []),
                    'time': article_data.get('time', None).strftime("%Y-%m-%d %H:%M"),
                    'comment_count': comment_count,
                    'like_count': like_count,
                    'image_urls': article_data.get('image_urls', [])
                }
                articles_list.append(article_item)
        processing_time = time.time() # 
        print(f"Total time to process articles: {processing_time - split_time} seconds") #

        time_list = sorted(articles_list, key=lambda x: x['time'], reverse=True)
        return jsonify({
            'success': True,
            'msg': '',
            'articles': time_list
        }), 200
    
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({
            'success': False,
            'msg': str(e),
            'articles': []
        }), 500
    
# 마커 클러스터
@marker_routes.route('/get_marker_clusterer', methods=['GET'])
def get_marker_clusterer():
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
