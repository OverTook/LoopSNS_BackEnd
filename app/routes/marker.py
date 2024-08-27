from app import db
from app.functions.clusterer import *
from app.utils.decorators import *
from flask import Blueprint, request, jsonify
from google.cloud.firestore import GeoPoint
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta
import time
import pytz

# 마커 블루프린트 작성
marker_routes = Blueprint('marker', __name__)

# 마커를 눌렀을 때 게시글의 타임라인이 나오는 함수
@marker_routes.route('/get_marker_timeline', methods=['GET'])
def get_marker_timeline():
    try:
        # 앱으로부터 데이터 수신
        articles = request.args.getlist('articles')
        
        if len(articles) == 0:
            return jsonify({
                'success': False,
                'msg': 'No article IDs provided',
                'articles': []
            }), 400
        
        start = time.time()  # 시작 시간 저장
        
        # 최대 문서 ID 개수 30개로 고정시킴
        max = 30
        
        # 쿼리 분할을 통해 일단은 30개를 최대로 정하고
        articles_count = [articles[i:i + max] for i in range(0, len(articles), max)]
        
        # Firestore에서 데이터 가져오기
        articles_list = []
        hot_articles = []
        
        for count in articles_count:
        #def fetch_articles(count):
            docs = db.collection('articles').where(FieldPath.document_id(), "in", count).stream()
            
            for doc in docs:
                article_data = doc.to_dict()
                article_item = {
                    'uid': doc.id,
                    'writer': article_data.get('writer', ''),
                    'title': article_data.get('title', ''),
                    'contents': article_data.get('contents', ''),
                    'intention': article_data.get('intention', ''),
                    'subject': article_data.get('subject', ''),
                    'keywords': article_data.get('keywords', []),
                    'time': article_data.get('time', None).strftime("%Y-%m-%d %H:%M"),
                    'comment_counts': article_data.get('comment_counts', 0),
                    'like_count': article_data.get('like_count', 0),
                    'image_urls': article_data.get('image_urls', [])
                }
                articles_list.append(article_item)
                if len(hot_articles) == 0:
                    hot_articles.append(article_item)
                elif len(hot_articles) == 1:
                    if hot_articles[0]['like_count'] < article_item['like_count']:
                        hot_articles.append(hot_articles[0])
                        hot_articles[0] = article_item
                    else:
                        hot_articles.append(article_item)
                else:
                    if hot_articles[0]['like_count'] < article_item['like_count']:
                        hot_articles[1] = hot_articles[0]
                        hot_articles[0] = article_item
                    elif hot_articles[1]['like_count'] < article_item['like_count']:
                        hot_articles[1] = article_item
        
        time_list = sorted(articles_list, key=lambda x: x['time'], reverse=True)
        return jsonify({
            'success': True,
            'msg': '',
            'articles': time_list,
            'hot_articles': hot_articles
        }), 200
    
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({
            'success': False,
            'msg': str(e),
            'articles': [],
            'hot_articles': []
        }), 500
    
# 마커 클러스터
@marker_routes.route('/get_marker_clusterer', methods=['GET'])
def get_marker_clusterer():
    lat_from = float(request.args.get('lat_from'))
    lng_from = float(request.args.get('lng_from'))
    lat_to = float(request.args.get('lat_to'))
    lng_to = float(request.args.get('lng_to'))
    
    print(lat_from, lng_from, lat_to, lng_to)
    
    # 현재 UTC 시간 얻기
    day = datetime.now(pytz.timezone('UTC'))
    
    # 현재 UTC에서 빼고 싶은 날짜 빼기 현재는 하루만 뺌. 이후 30일로 수정.
    days = 36500
    day_utc = day - timedelta(days=days)

    # 뺀 날짜에서 시간과 분을 00:00으로 설정
    day_ago = day_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if None in (lat_from, lng_from, lat_to, lng_to):
        return jsonify({'success': False, 'msg': '좌표가 없거나 누락되었습니다.', 'markers': []}), 400

    try:
        # 좌표 범위 계산
        nw_coord = (min(lat_from, lat_to), min(lng_from, lng_to))
        se_coord = (max(lat_from, lat_to), max(lng_from, lng_to))
        
        print(nw_coord)
        print(se_coord)
        
        # Firestore에서 좌표 범위 내의 articles 가져오기
        articles_ref = db.collection('articles')
        
        # GeoPoint를 사용한 범위 쿼리
        query = articles_ref.where('latlng', '>=', GeoPoint(nw_coord[0], nw_coord[1])) \
                            .where('latlng', '<=', GeoPoint(se_coord[0], se_coord[1])) \
                            .where('time', '>=', day_ago)
        articles = query.stream()

        # 클러스터링 함수 호출
        clustered_markers = cluster_articles(articles, lat_from, lng_from, lat_to, lng_to)
        
        # 성공 시 클러스터링된 좌표와 문서 ID 반환
        return jsonify({
            'success': True,
            'msg': 'success',
            'markers': clustered_markers,
        }), 200
    
    except Exception as e:
        error_msg = f"Error occurred: {str(e)}"
        print(error_msg)
        return jsonify({
            'success': False, 
            'msg': error_msg, 
            'markers': []
        }), 500
    