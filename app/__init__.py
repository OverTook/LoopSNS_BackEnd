import firebase_admin.firestore
from config import googleapi, settings
import firebase_admin
from firebase_admin import credentials, firestore, storage
from flask import Flask
import os

# Flask 생성
app = Flask(__name__)
app.config.from_object(settings)    # Flask 설정

# Firebase 초기화
cred = credentials.Certificate(googleapi.CREDENTIAL_PATH)
firebase_app = firebase_admin.initialize_app(cred, {
    'storageBucket': googleapi.STORAGE_BUCKET,
})

# Google Cloud 프로젝트 ID 설정
project_id = googleapi.PROJECT_ID
# 서비스 계정 인증 파일 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = googleapi.GOOGLE_APPLICATION_CREDENTIALS

db = firestore.client(app=firebase_app)
db._database = 'loop-2'
bucket = storage.bucket(app=firebase_app)

# 블루프린트 등록
from app.routes.article import article_routes
from app.routes.auth import auth_routes
from app.routes.category import category_routes
from app.routes.comment import comment_routes
from app.routes.fcm_token import fcm_token_routes
from app.routes.geo import geo_routes
from app.routes.like import like_routes
from app.routes.marker import marker_routes
from app.routes.report import report_routes
from app.routes.search import search_routes
from app.routes.terms import terms_routes
from app.routes.user import user_routes

app.register_blueprint(article_routes)
app.register_blueprint(auth_routes)
app.register_blueprint(category_routes)
app.register_blueprint(comment_routes)
app.register_blueprint(fcm_token_routes)
app.register_blueprint(geo_routes)
app.register_blueprint(like_routes)
app.register_blueprint(marker_routes)
app.register_blueprint(report_routes)
app.register_blueprint(search_routes)
app.register_blueprint(terms_routes)
app.register_blueprint(user_routes)
