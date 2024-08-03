from app import db
from app.functions.clusterer import *
from app.utils.decorators import *
from config import googleapi
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime
import requests
import time

# 마커 블루프린트 작성
marker_routes = Blueprint('marker', __name__)

@marker_routes.route('/get_center_addr', methods=['GET'])
def get_center_addr():
    latlng = request.args.get('latlng')
    language = request.args.get('language')
    try:
        response = requests.get(f'https://maps.googleapis.com/maps/api/geocode/json?latlng={latlng}&language={language}&key={googleapi.GOOGLEMAPS_KEY}').json()
    except Exception as e:
        print("Exception:", e)
        return jsonify({
            'success': False,
            'msg': str(e)
        }), 400
    
    return jsonify(response), 200

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
                
                # 댓글 수 가져오기
                comment_count = article_data.get('comment_counts')
                
                # 좋아요 수 가져오기
                like_count = article_data.get('like_count')
                
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
    zoom_level = float(request.args.get('zoom_level'))
    
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
        clustered_markers = cluster_articles(articles, zoom_level)
        
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
