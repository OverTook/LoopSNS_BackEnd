import re
import base64
from vertexai.preview.generative_models import GenerativeModel, Part

#카테고리 파트    
def process_image_and_text(image_bytes, text_content=""):
    if image_bytes:
        encode_image = base64.b64encode(image_bytes).decode('utf-8')
        image_part = Part.from_data(data=base64.b64decode(encode_image), mime_type="image/jpeg")
        print("good")
    else:
        image_part = None

    if not text_content:
        text_content = ""

    prompt = """
    Your job will be to analyze the images and text you're sent and classify them into categories and keywords.
    Even if you don't have either the image or the text, you still need to categorize it.
    You should output two categories and four keywords.

    For each input, you should do the following
    1. determine a primary and secondary category based on the content.
    2. extract the four relevant keywords that best describe the content.

    The categories should be chosen from the examples given, and the keywords should be relevant to the image, text, or both.

    Output format:
    - Primary categories should be enclosed in parentheses ().
    - Secondary categories should be enclosed in parentheses ().
    - Keywords should be enclosed in square brackets [].
    
    The example below shows a primary category and secondary categories that fall under the primary category.
    When analyzing images and text, be sure to pick the primary and secondary categories from the example below so that you can categorize them.
    
    카테고리 예시:
    (일상): [취미, 생활정보, 설득, 공감, 소통, 감정, 예술성, 창의성, 칭찬, 사과, 불만, 교류, 고민, 상담, 가족, 여행, 음식, 운동, 양치질, 식사]
    (동물): [고양이, 강아지, 호랑이, 사슴, 사자, 기린, 판다, 오리, 비둘기, 사람, 하마, 코뿔소]
    (전자제품): [키보드, 노트북, 컴퓨터, 마우스, 오디오, TV, 세탁기, 냉장고, 조명]
    (정보공유): [뉴스, 팁/노하우, 교육, 기술, 건강, 경제, 문화, 정치, 과학]
    (질문): [정보요청, 의견수렴, 고민, 소통, 상담, 교육, 추천, 도움 요청]
    (일정): [모임, 기념일, 이벤트, 회의, 약속, 일정 관리]
    (광고): [프로모션, 구인/구직, 음식점, 의류, 아르바이트, 서비스, 제품 출시, 할인 행사]
    (제보): [분실물, 발견물, 사건사고, 재난사고, 불법 행위, 신고, 교통사고]
    (제안): [아이디어 제안, 피드백 요청, 협동, 타협, 정책 제안, 개선안, 프로젝트 제안]
    (폭력적): [출혈, 사망, 살인, 칼, 흉기, 사고, 시신, 폭행, 협박]
    (성인물): [성폭행, 성폭력, 성기, 성기 노출, 노상방뇨, 섹스, 음란물, 성매매]
    (기타): [상품, 공지사항, 일반, 이벤트, 제안, 도움말]
    (건강): [운동, 영양, 정신건강, 질병, 의학정보, 건강관리, 심리, 피트니스]
    (여행): [여행지 추천, 여행 팁, 숙소 정보, 맛집, 교통, 여행기, 여행사진, 여행 계획]
    (음식): [레시피, 요리법, 음식 리뷰, 맛집 추천, 식품 정보, 건강 식품, 요리 사진, 음식 문화]
    (기술): [IT, 소프트웨어, 하드웨어, 프로그래밍, 모바일, 가젯, 인터넷, 혁신 기술]
    (문화): [영화, 음악, 책, 전시, 공연, 역사, 예술, 축제, 문화 행사]
    (경제): [주식, 투자, 부동산, 재테크, 금융, 경제뉴스, 소비자 정보, 경제 동향]
    (정치): [정치뉴스, 선거, 정책, 국제정치, 정치인, 정치 토론, 사회 이슈]
    (과학): [물리학, 화학, 생물학, 천문학, 지구과학, 과학뉴스, 연구, 발명]
    (기타): [상품, 생활, 잡화]
    
    Be sure to follow the example below to output 
    
    결과물 출력 예시:
    1차 카테고리: (전자제품)
    2차 카테고리: (키보드)
    키워드: [리뷰], [기능], [신제품], [품질]
    
    1차 카테고리: (일상)
    2차 카테고리: (불만)
    키워드: [쓰레기], [분리수거 불이행], [환경오염], [청소]
    
    1차 카테고리: (정보공유)
    2차 카테고리: (교육)
    키워드: [문제집], [수학], [풀이], [공부]
    
    1차 카테고리: (음식)
    2차 카테고리: (레시피)
    키워드: [김치], [계란볶음밥], [간편한], [추천메뉴]
    
    1차 카테고리: (문화)
    2차 카테고리: (영화)
    키워드: [어벤져스], [유행], [박스오피스], [아이언맨]
    
    1차 카테고리: (일상)
    2차 카테고리: (취미)
    키워드: [피아노], [연주], [취미생활], [악기]

    1차 카테고리: (정보공유)
    2차 카테고리: (팁/노하우)
    키워드: [컴퓨터], [키보드], [단축키], [사용법]

    1차 카테고리: (질문)
    2차 카테고리: (정보요청)
    키워드: [여행지], [추천], [유럽], [여행 팁]

    1차 카테고리: (기술)
    2차 카테고리: (IT)
    키워드: [키보드], [리뷰], [기능], [신제품]
    
    1차 카테고리: (일정)
    2차 카테고리: (모임)
    키워드: [친구], [만남], [저녁식사], [약속]

    1차 카테고리: (광고)
    2차 카테고리: (구인/구직)
    키워드: [알바], [채용], [일자리], [근무조건]

    1차 카테고리: (제안)
    2차 카테고리: (아이디어 제안)
    키워드: [프로젝트], [혁신], [창의적], [개선]

    1차 카테고리: (여행)
    2차 카테고리: (여행지 추천)
    키워드: [휴양지], [추천], [바다], [리조트]
    
    The primary and secondary categories must be chosen from the provided examples.
    Ensure to output both the primary and secondary categories.
    The four keywords should be derived based on the context of the image and text, and must align with the selected categories.
    """

    # 모델
    model = GenerativeModel("gemini-pro-vision")
    
    # 이미지와 텍스트를 모두 사용하는 경우
    if image_part and text_content:
        response = model.generate_content(
            [image_part, text_content, prompt],
            generation_config={"max_output_tokens": 1000, "temperature": 0.5, "top_p": 1, "top_k": 32},
            stream=False
        )

    # 이미지만 사용하는 경우
    elif image_part:
        response = model.generate_content(
            [image_part, prompt],
            generation_config={"max_output_tokens": 1000, "temperature": 0.5, "top_p": 1, "top_k": 32},
            stream=False  
        )

    # 텍스트만 사용하는 경우
    else:
        response = model.generate_content(
            [text_content, prompt],
            generation_config={"max_output_tokens": 1000, "temperature": 0.5, "top_p": 1, "top_k": 32},
            stream=False  
        )
        
    return response.candidates[0].content.parts[0].text

# 출력 결과에 대해서 카테고리와 키워드를 분류하는 함수
def category_and_keyword(result):
    category_pattern = re.compile(r'\(([가-힣A-Za-z]+)\)')
    keyword_pattern = re.compile(r'\[([가-힣A-Za-z]+)\]')

    category_match = category_pattern.findall(result)
    keyword_match = keyword_pattern.findall(result)
    
    # 공백 제거
    category_match = [c.strip() for c in category_match]
    keyword_match = [k.strip() for k in keyword_match]

    # 각각의 변수에 값 저장
    c1 = c2 = k1 = k2 = k3 = k4 = ""

    if len(category_match) >= 2:
        c1 = category_match[0]
        c2 = category_match[1]

    if len(keyword_match) >= 4:
        k1 = keyword_match[0]
        k2 = keyword_match[1]
        k3 = keyword_match[2]
        k4 = keyword_match[3]

    return c1, c2, k1, k2, k3, k4
