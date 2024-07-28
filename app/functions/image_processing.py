from app import bucket
import cv2
import numpy as np
import uuid

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

