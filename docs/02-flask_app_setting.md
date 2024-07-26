# 02. 플라스크 앱 설정하기

플라스크 앱의 초기화 설정은 `app/__init__.py` 파일에 정의되어 있습니다. 이 파일은 플라스크 앱과 파이어베이스 서비스를 초기화하는 코드를 포함합니다.

```
# __init__.py
import firebase_admin
import firebase_admin.firestore
import firebase_admin.functions
from firebase_admin import credentials, firestore, storage
from google.cloud import firestore
from config import firebase, settings
from flask import Flask
import os

# Flask 생성
app = Flask(__name__)
app.config.from_object(settings)    # Flask 설정

# Firebase 초기화
cred = credentials.Certificate(firebase.CREDENTIAL_PATH)
firebase_app = firebase_admin.initialize_app(cred, {
    'storageBucket': firebase.STORAGE_BUCKET
})

# Google Cloud 프로젝트 ID 설정
project_id = firebase.PROJECT_ID
# 서비스 계정 인증 파일 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = firebase.GOOGLE_APPLICATION_CREDENTIALS

db = firestore.client(app=firebase_app)
bucket = storage.bucket(app=firebase_app)
```
위 코드에서는 플라스크 앱 초기화, 파이어베이스 크리덴셜 초기화, 파이어스토어 초기화가 진행됩니다.

## 플라스크 앱 구성

`app/` 디렉토리 내에는 `functions/`, `routes/`, `utils/` 디렉토리가 존재합니다. 각각의 디렉토리의 역할은 다음과 같습니다:

- `functions/`: 엔드포인트에서 사용되는 함수들을 정의합니다. 엔드포인트 코드 파일에 함께 작성할 수도 있지만, 기능별로 코드를 분리하기 위해 functions 디렉토리에 놓습니다.
- `routes/`: 엔드포인트를 정의합니다.
- `utils/`: 헤더에서 토큰을 받아오는 등, 엔드포인트마다 공통적으로 진행해야 하는 로직에 대한 데코레이터를 정의합니다.

## 중요 변수 설정 및 관리
중요 변수를 코드 내에 직접 저장하는 것은 바람직하지 않습니다. 이러한 변수는 별도의 설정 파일에 저장하여 관리하는 것이 좋습니다. 이는 코드 유지보수를 용이하게 하고 보안을 강화할 수 있습니다.

### config 디렉토리 구성
`config/` 디렉토리에는 `__init__.py`, `firebase.py`, `server.py`, `settings.py` 네 개의 파일이 있습니다. 각각의 파일은 다음과 같은 역할을 합니다.

1. `__init__.py` .env 파일을 불러오기 위한 설정을 포함합니다.
```
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

load_dotenv()
```

2. `firebase.py`: 파이어베이스 관련 설정을 포함합니다.
```
from config import *
import os

# Firebase Configurations
CREDENTIAL_PATH = os.getenv('CREDENTIAL_PATH', '/default/path')
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/default/path')
STORAGE_BUCKET = os.getenv('STORAGE_BUCKET', "default.bucket.com")
PROJECT_ID = os.getenv('PROJECT_ID', 'default-project-id')
```

3. `server.py`: 서버 관련 값을 설정합니다.
```
from config import *
import os

# Server Configurations
SERVER_DOMAIN = os.getenv('SERVER_DOMAIN', 'localhost')
SERVER_PORT = os.getenv('SERVER_PORT', 5000)
```

4. `settings.py`: 플라스크 앱 관련 설정을 포함합니다.
```
from config import *
import os

JSON_AS_ASCII = os.getenv('JSON_AS_ASCII', False)
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/default/path')
```

### .env 파일 내용
`.env` 파일은 중요한 변수를 저장하는 파일로, 다음과 같은 내용을 포함합니다.
```
CREDENTIAL_PATH=''
GOOGLE_APPLICATION_CREDENTIALS=''
JSON_AS_ASCII=False
PROJECT_ID=''
UPLOAD_PATH=''
SERVER_DOMAIN=domain.com
SERVER_PORT=5126
STORAGE_BUCKET='bucket.com'
```
이러한 설정을 통해 플라스크 앱이 필요한 변수들을 환경 변수 파일과 설정 파일에서 로드하여 사용할 수 있습니다. 이는 코드의 가독성을 높이고, 중요 변수를 안전하게 관리할 수 있게 합니다.
