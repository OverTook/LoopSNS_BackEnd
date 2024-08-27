# 파이어베이스 연결, 파일 실행시키면 입력된 내용에 맞춰
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import firebase_admin.firestore
import firebase_admin
from firebase_admin import credentials, firestore
from config import googleapi
from datetime import datetime
import string
import random
import pytz



# Firebase 초기화
cred = credentials.Certificate(googleapi.CREDENTIAL_PATH)
firebase_app = firebase_admin.initialize_app(cred)


db = firestore.client(app=firebase_app)
db._database = 'loop-2'


# datetime을 활용한 하위 랜덤 문자열 출력
now = datetime.now()
timestamp = datetime.timestamp(now)

time = int(timestamp)
re_time = format(time, 'x')
str_time = str(re_time)
upp_time = str_time.upper()
str_len = len(upp_time)


# 하위 자릿수에 따라 상위 랜덤 문자열 생성 및 합체
string_upper = string.ascii_uppercase + string.digits
random_str = ''

for i in range(str_len):
    random_str += random.choice(string_upper)

all = random_str + upp_time
print(all)

count = 0
license_key = ''
for item in all:
    if count == 4:
        license_key = license_key + '-'
        license_key = license_key + item
        count = 0
    else:
        license_key = license_key + item

    count = count + 1

# 최대 라이센스 유저 수 입력
max_users = input('최대 라이센스 유저 수를 입력하세요 : ')
max_users = int(max_users)


# 라이센스 기간 입력
year = input('기간(년도)')
month = input('기간(월)')
day = input('기간(일)')

valid_until = datetime(int(year), int(month), int(day), 00, 00, 00, 000000, tzinfo=pytz.UTC)


license_data = {
    'license_key': license_key,
    'max_users': max_users,
    'valid_until': valid_until
}

collection_name = 'licenses'

db.collection(collection_name).document(license_key).set(license_data)

print("라이센스 추가를 완료했습니다.")
print(license_key)