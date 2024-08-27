import re
import base64
import vertexai
import os
from vertexai.generative_models import GenerativeModel, Part
from config import googleapi

def read_prompt(path):
    with open(path, 'r', encoding='utf-8') as file:
        return file.read()

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
        
    else:
        korean_count = 0
        english_count = 0
        
        for c in text_content:
            if '가' <= c <= '힣':
                korean_count += 1
            elif 'a' <= c.lower() <= 'z':
                english_count += 1
        
        if korean_count < english_count:
            print(text_content)
            print("영어입니다.")
            prompt = read_prompt(os.getenv('PROMPT_EN')) 
        else:
            print(text_content)
            print("한글입니다.")
            prompt = read_prompt(os.getenv('PROMPT_KO'))
    
    # 모델
    vertexai.init(project=googleapi.PROJECT_ID, location="us-central1")
    model = GenerativeModel('gemini-1.5-flash')
    
    '''
    max_output_tokens = 생성할 답변의 최대 토큰 수
    temperature = 생성된 텍스트의 다양성을 제어하는 매개변수, 높으면 다양성이 높음
    top_p = 누적 확률이 top_p 값보다 낮은 토큰들만 고려하여 텍스트를 생성
    top_k = 매 단계에서 가장 높은 확률을 가진 top_k 개의 토큰들 중에서 다음 토큰을 샘플링
    '''
    # 이미지와 텍스트를 모두 사용하는 경우
    if image_part and text_content:
        response = model.generate_content(
            [image_part, text_content, prompt],
            generation_config={"max_output_tokens": 200, "temperature": 0.7, "top_p": 0.2, "top_k": 1},
            stream=False
        )

    # 이미지만 사용하는 경우
    elif image_part:
        response = model.generate_content(
            [image_part, prompt],
            generation_config={"max_output_tokens": 200, "temperature": 0.7, "top_p": 0.2, "top_k": 1},
            stream=False  
        )

    # 텍스트만 사용하는 경우
    else:
        response = model.generate_content(
            [text_content, prompt],
            generation_config={"max_output_tokens": 200, "temperature": 0.7, "top_p": 0.2, "top_k": 1},
            stream=False  
        )
        
    return response.candidates[0].content.parts[0].text

# 출력 결과에 대해서 카테고리와 키워드를 분류하는 함수
def category_and_keyword(result):
    category_pattern = re.compile(r'\(([가-힣A-Za-z0-9\s]+)\)')
    keyword_pattern = re.compile(r'\[([가-힣A-Za-z0-9\s]+)\]')

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

    if len(keyword_match) >= 1:
        k1 = keyword_match[0]
    if len(keyword_match) >= 2:
        k2 = keyword_match[1]
    if len(keyword_match) >= 3:
        k3 = keyword_match[2]
    if len(keyword_match) >= 4:
        k4 = keyword_match[3]

    return c1, c2, k1, k2, k3, k4