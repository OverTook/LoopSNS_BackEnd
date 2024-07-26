import numpy as np
from sklearn.cluster import MeanShift, estimate_bandwidth

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
