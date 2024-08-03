import numpy as np
from sklearn.cluster import MeanShift, estimate_bandwidth
from sklearn.preprocessing import StandardScaler

# 클러스터링 함수
def cluster_articles(articles, zoom_level, cluster_zoom_threshold=2):
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
        
        if zoom_level <= cluster_zoom_threshold:
            clustered_markers = [{'articles': [article_ids[i]], 'lat': coordinates[i][0], 'lng': coordinates[i][1]} for i in range(len(coordinates))]
            return clustered_markers


        # 데이터 스케일링
        scaler = StandardScaler()
        coordinates = scaler.fit_transform(coordinates)

        # zoom_level에 따른 bandwidth 설정
        min_zoom = 2.0
        max_zoom = 21.0
        min_bandwidth = 0.1
        max_bandwidth = 2.0

        zoom = (max_zoom - zoom_level) / (max_zoom - min_zoom)
        bandwidth_m = max(min_bandwidth, min_bandwidth + (max_bandwidth - min_bandwidth) * zoom)

        # bandwidth 값 설정
        bandwidth_b = estimate_bandwidth(coordinates, quantile=0.2, n_samples=len(coordinates))
        if bandwidth_b <= 0:
            bandwidth_b = 1.0  # 기본 bandwidth 값 설정

        bandwidth = max(bandwidth_b * bandwidth_m, min_bandwidth, bandwidth_b)

        # MeanShift 클러스터링 부분
        mean_shift = MeanShift(bandwidth=bandwidth, bin_seeding=True)
        mean_shift.fit(coordinates)

        # 클러스터 중심점과 레이블 가져옴
        cluster_centers = mean_shift.cluster_centers_
        labels = mean_shift.labels_

        clustered_markers = []

        # 클러스터링된 결과를 딕셔너리에 추가
        for i, center in enumerate(cluster_centers):
            cluster_article_ids = [article_ids[j] for j in range(len(labels)) if labels[j] == i]
            center_orig = scaler.inverse_transform([center])[0]
            clustered_markers.append({
                'articles': cluster_article_ids,
                'lat': center_orig[0],
                'lng': center_orig[1]
            })

        return clustered_markers
    
    except Exception as e:
        raise RuntimeError(f"Error in clustering process: {str(e)}")
