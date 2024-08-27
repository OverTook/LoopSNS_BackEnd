from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import numpy as np
import pandas as pd

from sklearn.cluster import AgglomerativeClustering
from sklearn.cluster import MeanShift, estimate_bandwidth


def _calc_scale_k(lat_from, lng_from, lat_to, lng_to):
    lat_range = abs(lat_to - lat_from)
    lng_range = lng_to - lng_from
    k_avg = 0.65
    # k_avg가 0.8일때가 딱 마커끼리 안겹칠 정도로만 클러스터링 해줌
    if lat_range == 0 or lng_range == 0:
        k = k_avg  # 만약 범위가 0이면 기본 k_avg 값을 사용
    else:
        k = k_avg / lat_range
    return k

def cluster_articles(articles, lat_from, lng_from, lat_to, lng_to):
    datas = []

    # Firestore에서 가져온 각 게시글의 좌표와 ID를 리스트에 저장
    for article in articles:
        article_data = article.to_dict()
        latlng = article_data['latlng']
        datas.append([float(latlng.latitude), float(latlng.longitude), article.reference.id])

    df = pd.DataFrame(datas, columns=['lat', 'lng', 'article_id'])

    if len(df) == 0:
        return []

    if len(df) == 1:
        # 데이터가 1개일 경우, 클러스터링 진행이 안 됨.
        return [{
            'articles': df['article_id'].tolist(),
            'lat': df['lat'][0],
            'lng': df['lng'][0]
        }]
    
    print(df)
    
    # 위도와 경도 데이터만 추출
    coords = df[['lat', 'lng']]

    # 대역폭을 자동으로 추정
    # bandwidth = estimate_bandwidth(coords, quantile=0.2, n_samples=len(df))
    bandwidth = 0.05
    bandwidth = bandwidth / _calc_scale_k(lat_from, lng_from, lat_to, lng_to)
    # 최소 bandwidth 값을 0.001로 설정하여 0이 되는 것을 방지
    bandwidth = max(bandwidth, 0.001)

    # MeanShift 클러스터링 적용
    mean_shift = MeanShift(bandwidth=bandwidth, bin_seeding=True)
    df['cluster'] = mean_shift.fit_predict(coords)

    # 클러스터 중심 계산
    cluster_centers = pd.DataFrame(mean_shift.cluster_centers_, columns=['lat', 'lng'])

    # 클러스터링 된 데이터들의 중심좌표와 해당 클러스터 안의 게시글 ID를 저장할 리스트
    clustered_markers = []

    # 각 클러스터별로 그룹화하여 처리
    for cluster_id in df['cluster'].unique():
        cluster_data = df[df['cluster'] == cluster_id]
        
        # 클러스터 중심 좌표
        center_coords = cluster_centers.loc[cluster_id]
        
        # 클러스터에 속한 게시글들의 ID
        cluster_article_ids = cluster_data['article_id'].tolist()
        
        # 결과를 리스트에 추가
        clustered_markers.append({
            'articles': cluster_article_ids,
            'lat': center_coords['lat'],
            'lng': center_coords['lng']
        })
    return clustered_markers
