from app import db
from app.functions.category_extraction import *
from app.functions.image_processing import *
from app.utils.decorators import *
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore_v1.base_query import FieldFilter
import datetime
import re

# 카테고리 블루프린트 작성
category_routes = Blueprint('category', __name__)

@category_routes.route('/get_category', methods=['POST'])
def get_category():
    try:
        images = request.files.getlist('images')
        contents = request.form.get('contents')
        
        if len(contents.strip()) < 16:  # 내용이 15자 이하인지 판단
            return jsonify({"success": False, "msg": "get category", "categories": [], "keywords": []})
            
        
        print(images)
        print(contents)
        
        
        image_urls = []
        if images:  # 이미지가 있는 경우에만 처리
            for image in images:
                image_bytes = image.read()
                mosaic_image_bytes = mosaic(image_bytes)

                image_url = mosaic_image_bytes
                image_urls.append(image_url)
        else:
            image_bytes = None
        result_text = process_image_and_text(image_bytes, contents if contents else " ")
        
        
        print(result_text)
        
        msg = contains_bad_content(result_text)
        print(msg)
        if msg == "bad":
            return jsonify({"success": False, "msg": "bad words in contents", "categories": [], "keywords": []}), 422
        else:
            # 카테고리와 키워드 추출
            c1, c2, k1, k2, k3, k4 = category_and_keyword(result_text)

            # 지금 카테고리가 제대로 분류되지 않았을 경우엔 무조건 기타, 잡화로 선정되도록 함.
            if not c1:
                c1 = "기타"

            if not c2:
                c2 = "잡화"

            print(c1)
            print(c2)
            print(k1)
            print(k2)
            print(k3)
            print(k4)

            return jsonify({"success": True, "msg": "get category", "categories": [c1, c2], "keywords": [k1, k2, k3, k4]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    

def contains_bad_content(text):
    bad_words = ["폭력", "폭행", "폭력적", "살인", "자살", "성적", "성폭력", "성희롱", "욕설", "비속어", "부적절", "공격적", "죄송합니다."]
    bad_word_patterns = [re.compile(r'\b' + re.escape(word) + r'\b|\b' + word + r'\w*', re.IGNORECASE) for word in bad_words]

    for pattern in bad_word_patterns:
        if pattern.search(text):
            return "bad"
    return "good"