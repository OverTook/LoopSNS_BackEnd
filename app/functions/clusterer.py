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
        datas.append([float(article_data['lat']), float(article_data['lng']), article.reference.id])

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
    
    # 위도와 경도 데이터만 추출
    coords = df[['lat', 'lng']]

    # 대역폭을 자동으로 추정
    #bandwidth = estimate_bandwidth(coords, quantile=0.2, n_samples=len(df))
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

'''
def cluster_articles(articles, zoom_level):
    coordinates = [] 
    article_ids = [] 

    # Firestore에서 가져온 각 게시글의 좌표와 ID를 리스트에 저장
    for article in articles:
        article_data = article.to_dict()
        coordinates.append([float(article_data['lat']), float(article_data['lng'])])
        article_ids.append(article.reference.id)

    coordinates = np.array(coordinates)

    try:
        if len(coordinates) == 0:
            return []

        if len(coordinates) == 1:
            # 데이터가 1개일 경우, 클러스터링 진행이 안 됨.
            return [{
                'articles': article_ids,
                'lat': coordinates[0][0],
                'lng': coordinates[0][1]
            }]

        # 줌 레벨에 따른 클러스터 수 설정
        min_zoom = 6.0
        max_zoom = 17.0
        min_clusters = 1  # 최소 클러스터 수
        max_clusters = min(len(coordinates), 10)  # 데이터 수와 최대 클러스터 수를 제한, 제한을 두면 조금 더 클러스터링이 진행되는 것을 확인할 수 있음.

        # 줌 레벨에 따른 클러스터 수 계산
        zoom_ratio = (zoom_level - min_zoom) / (max_zoom - min_zoom)
        zoom_ratio = max(0, min(1, zoom_ratio))  # zoom_ratio는 0과 1 사이로 제한

        # 줌 레벨에 따라 클러스터링이 바뀌도록 설정.
        if zoom_ratio < 0.3:
            # 줌 레벨이 절반 이하일 때는 클러스터 수가 높게 설정 원래는 0.5였는데 지금은 0.3으로 수정함
            n_clusters = int(min_clusters + (max_clusters - min_clusters) * (1 - zoom_ratio))
        else:
            # 줌 레벨이 절반 이상일 때는 클러스터 수가 낮게 설정
            n_clusters = int(min_clusters + (max_clusters - min_clusters) * (zoom_ratio - 0.5) * 2)

        n_clusters = max(n_clusters, min_clusters)  # 클러스터 수가 최소 클러스터 수 이하로 가지 않도록 함
        n_clusters = min(n_clusters, len(coordinates))  # 클러스터 수가 데이터 수를 초과하지 않도록 함

        

        scaler = StandardScaler()
        coordinates = scaler.fit_transform(coordinates)

        # Agglomerative Clustering 적용
        clustering = AgglomerativeClustering(n_clusters=n_clusters)
        labels = clustering.fit_predict(coordinates)
        

        # 클러스터링 된 중심점 계산
        cluster_centers = np.array([coordinates[labels == i].mean(axis=0) for i in range(n_clusters)])

        clustered_markers = []

        # 클러스터링 결과를 딕셔너리 형식으로 저장
        for i in range(n_clusters):
            cluster_article_ids = [article_ids[j] for j in range(len(labels)) if labels[j] == i]
            center = cluster_centers[i]
            center_orig = scaler.inverse_transform([center])[0]
            clustered_markers.append({
                'articles': cluster_article_ids,
                'lat': center_orig[0],
                'lng': center_orig[1]
            })

        return clustered_markers
    
    except Exception as e:
        raise RuntimeError(f"Error in clustering process: {str(e)}")
'''


'''
def cluster_articles(articles, zoom_level):
    coordinates = [] 
    article_ids = [] 

    # Firestore에서 가져온 각 게시글의 좌표와 ID를 리스트에 저장
    for article in articles:
        article_data = article.to_dict()
        coordinates.append([float(article_data['lat']), float(article_data['lng'])])
        article_ids.append(article.reference.id)

    coordinates = np.array(coordinates)
    #print(coordinates)

    try:
        if len(coordinates) == 0:
            return []

        if len(coordinates) == 1:
            # 데이터가 1개일 경우, 클러스터링 진행 x 이거 추가 안 하면 오류 남 
            return [{
                'articles': article_ids,
                'lat': coordinates[0][0],
                'lng': coordinates[0][1]
            }]

        # 줌 레벨에 따라 DBSCAN의 eps 값 설정
        # 일단 줌 레벨 최소는 6 최대는 17 고정
        min_zoom = 6.0
        max_zoom = 17.0

        # 줌 레벨에 따른 eps 값 계산
        zoom_ratio = (zoom_level - min_zoom) / (max_zoom - min_zoom)
        zoom_ratio = max(0, min(1, zoom_ratio))  # zoom_ratio는 0과 1 사이로 제한
        
        
        eps_min = 0.5  # eps의 최소값 설정
        eps_max = 1.0  # eps의 최대값 설정 이 값을 키우면 클러스터링이 증가
        eps = eps_min + (eps_max - eps_min) * zoom_ratio  # eps 값 조정


        # 데이터 스케일링
        scaler = StandardScaler()
        coordinates = scaler.fit_transform(coordinates)

        # DBSCAN 적용 진행
        clustering = DBSCAN(eps=eps, min_samples=1)
        labels = clustering.fit_predict(coordinates)

        # 클러스터의 중심점 계산
        unique_labels = set(labels)
        if -1 in unique_labels:
            unique_labels.remove(-1)  # noise 제외

        clustered_markers = []
        for label in unique_labels:
            cluster_points = coordinates[labels == label]
            cluster_article_ids = [article_ids[j] for j in range(len(labels)) if labels[j] == label]
            if len(cluster_article_ids) == 0:
                continue
            center = cluster_points.mean(axis=0)
            center_orig = scaler.inverse_transform([center])[0]
            clustered_markers.append({
                'articles': cluster_article_ids,
                'lat': center_orig[0],
                'lng': center_orig[1]
            })

        return clustered_markers
    
    except Exception as e:
        raise RuntimeError(f"Error in clustering process: {str(e)}")
'''        
        
        
'''
# 클러스터링 함수
def cluster_articles(articles, zoom_level, cluster_zoom_threshold=6):
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
        
        # 줌 레벨에 따른 클러스터 수 설정
        # min = 1, max 17
        min_zoom = 2.0
        max_zoom = 21.0
        min_clusters = 1
        max_clusters = len(coordinates)  

        if zoom_level <= cluster_zoom_threshold:
            n_clusters = min_clusters  
        else:
            zoom_ratio = (zoom_level - cluster_zoom_threshold) / (max_zoom - cluster_zoom_threshold)
            n_clusters = int(min_clusters + (max_clusters - min_clusters) * zoom_ratio)
            n_clusters = min(n_clusters, len(coordinates))  

        # 데이터 스케일링
        scaler = StandardScaler()
        coordinates = scaler.fit_transform(coordinates)

        # K-Means 클러스터링 사용
        kmeans = KMeans(n_clusters=n_clusters, random_state=0)
        kmeans.fit(coordinates)

        cluster_centers = kmeans.cluster_centers_
        labels = kmeans.labels_

        clustered_markers = []

        # 클러스터링된 결과를 딕셔너리에 추가
        for i in range(n_clusters):
            cluster_article_ids = [article_ids[j] for j in range(len(labels)) if labels[j] == i]
            if len(cluster_article_ids) == 0:
                continue
            center = cluster_centers[i]
            center_orig = scaler.inverse_transform([center])[0]
            clustered_markers.append({
                'articles': cluster_article_ids,
                'lat': center_orig[0],
                'lng': center_orig[1]
            })

        return clustered_markers
    
    except Exception as e:
        raise RuntimeError(f"Error in clustering process: {str(e)}")
'''