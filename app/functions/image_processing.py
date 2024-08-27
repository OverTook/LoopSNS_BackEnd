import cv2
import cv2.data
import numpy as np

# 자동차 번호판 모자이크
def mosaic(image_bytes):
    try:
        # OpenCV에서 제공하는 사전 학습된 번호판 검출기 로드
        plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml')

        img_array = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is None:
            print("이미지를 로드할 수 없습니다.")
            return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 번호판 검출
        plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        print(f"=== 검출된 번호판 수: {len(plates)} ===")
        
        if len(plates) == 0:
            print("번호판을 찾을 수 없습니다.")
            return None

        for (x, y, w, h) in plates:
            print(f"번호판 위치: x={x}, y={y}, w={w}, h={h}")

            # 번호판 영역 추출 및 모자이크 효과 적용
            plate_region = img[y:y+h, x:x+w]
            mosaic_strength = 15  # 모자이크 강도 조절

            small_plate = cv2.resize(plate_region, (w//mosaic_strength, h//mosaic_strength))
            plate_region = cv2.resize(small_plate, (w, h), interpolation=cv2.INTER_NEAREST)
            
            # 원본 이미지의 번호판 영역을 모자이크 처리된 영역으로 교체
            img[y:y+h, x:x+w] = plate_region

        # 디버깅용으로 모자이크 처리된 이미지 저장
        # debug_filename = f"{BASE_DIR}/data/mosaic_debug_{uuid.uuid4()}.jpg"
        # cv2.imwrite(debug_filename, img)
        # print(f"모자이크 처리된 이미지를 디버깅용으로 저장했습니다: {debug_filename}")

        # 이미지 파일을 임시로 저장할 UUID 생성
        _, output_img = cv2.imencode('.jpg', img)

        return output_img.tobytes()

    except Exception as e:
        print(f"에러가 발생했습니다: {str(e)}")
        return None
    