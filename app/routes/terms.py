from app import db, bucket
from app.utils.decorators import *
from config import BASE_DIR
from flask import Blueprint, request, jsonify
import os

# 사용자 블루프린트 작성
terms_routes = Blueprint('terms', __name__)

@terms_routes.route('/terms_of_use', methods=['GET'])
def get_terms_of_use():
    language = str(request.args.get('language', 'ko'))
    
    if language == 'ko':
        html_path = os.path.join(BASE_DIR, 'data', 'terms', 'terms_of_use.html')
    else:
        html_path = os.path.join(BASE_DIR, 'data', 'terms', 'terms_of_use_eng.html')
        
    with open(html_path, 'r') as f:
        data = f.read()
    
    return jsonify({
        'success': True, 
        'msg': '이용약관을 받아왔습니다.', 
        'data': data
    }), 200 


@terms_routes.route('/terms_of_information', methods=['GET'])
def get_terms_of_information():
    language = str(request.args.get('language', 'ko'))
    
    if language == 'ko':
        html_path = os.path.join(BASE_DIR, 'data', 'terms', 'terms_of_information.html')
    else:
        html_path = os.path.join(BASE_DIR, 'data', 'terms', 'terms_of_information_eng.html')    

    with open(html_path, 'r') as f:
        data = f.read()
    
    return jsonify({
        'success': True,
        'msg': '개인정보 처리방침을 받아왔습니다.',
        'data': data
    }), 200

@terms_routes.route('/terms_of_faq', methods=['GET'])
def get_terms_of_faq():
    language = str(request.args.get('language', 'ko'))
    
    if language == 'ko':
        html_path = os.path.join(BASE_DIR, 'data', 'terms', 'FAQ.html')
    else:
        html_path = os.path.join(BASE_DIR, 'data', 'terms', 'FAQ_eng.html')    

    with open(html_path, 'r') as f:
        data = f.read()
    
    return jsonify({
        'success': True,
        'msg': '개인정보 처리방침을 받아왔습니다.',
        'data': data,
        'mail': '2023khci@gmail.com'
    }), 200



@terms_routes.route('/report', methods=['POST'])
def report():   
    return jsonify({
        'success': True,
        'msg': '신고 성공',
    }), 200