# 라우트(엔드포인트) 설정하기
플라스크에서 파일 분리화를 하기 위해, 플라스크에서 제공하는 `blueprint` 기능을 사용합니다. 

`comment.py`를 생성하는 것을 예시로 들어 설명하겠습니다.

## 1) routes/ 폴더 안에 파이썬 파일 만들기
기본적으로 파이썬 코드는 같은 범주의 기능을 수행하는 함수끼리 묶어 저장합니다. 예를 들어, 게시글 작성, 불러오기, 삭제는 모두 게시글과 관련된 기능이기 때문에, `article.py`에 함께 작성합니다. 반면, 댓글 작성과 같이 게시글과 관련된 기능이 아닌 경우 새로 `comment.py`를 만들어 관리합니다.

`routes/` 폴더 안에 `comment.py` 파일을 새로 만들고, 기본적으로 아래와 같은 코드를 삽입합니다.

```
# comment.py
from app.utils.decorators import *
from flask import Blueprint, request, jsonify

# 댓글 블루프린트 작성
comment_routes = Blueprint('comment', __name__)
```
여기서 `flask`의 `Blueprint`, `request`, `jsonify`를 불러오고, `comment`라는 이름으로 블루프린트를 작성합니다. 이 프로젝트에서는 블루프린트의 변수명을 `<파일명>_routes`로 통일합니다. 예를 들어, `comment.py` 파일의 블루프린트 변수명은 `comment_routes`가 됩니다.
또한 블루프린트의 이름도 지정해주어야 합니다. 블루프린트 이름 또한 `<파일명>`으로 통일합니다. 만약 a라는 파일을 만들게 된다면, 아래와 같은 코드를 작성하게 됩니다.

```
a_routes = Blueprint('a', __name__)
```

## 2) 블루프린트에 엔드포인트 추가하기
이제, 블루프린트에 실제 엔드포인트를 추가합니다. 예를 들어, 댓글 작성 엔드포인트를 추가하려면 아래와 같이 코드를 작성합니다.

```
# comment.py
from app.utils.decorators import *
from flask import Blueprint, request, jsonify

# 댓글 블루프린트 작성
comment_routes = Blueprint('comment', __name__)

# 댓글 작성 엔드포인트
@comment_routes.route('/add_comment', methods=['POST'])
@validation_token()  # 토큰 검증 및 user_id를 받아와야 할 떄에만 사용               
def create_comment(uid, user_id):
    # 여기에 댓글 저장 로직을 작성
    return jsonify({
        'success': True, 
        'msg': '댓글 작성 완료'
    }), 200
```
이렇게 하면 `/add_comment` 경로로 POST 요청을 보내 댓글을 작성할 수 있습니다.

## 3) 블루프린트를 앱에 등록하기
`routes/comment.py` 파일에서 블루프린트를 작성한 후, 이를 Flask 애플리케이션에 등록해야 합니다. 이를 위해 `app/__init__.py`에서 다음과 같은 코드를 추가합니다.

```
import firebase_admin.firestore
import firebase_admin.functions
from firebase_admin import credentials, firestore, storage, auth
from google.cloud import firestore
from config import firebase, settings
from flask import Flask
import firebase_admin
from firebase_admin import credentials


# Flask 생성
app = Flask(__name__)
app.config.from_object(settings)    # Flask 설정

# Firebase 초기화
cred = credentials.Certificate(firebase.CREDENTIAL_PATH)
firebase_app = firebase_admin.initialize_app(cred, {
    'storageBucket': firebase.STORAGE_BUCKET
})

db = firestore.client(app=firebase_app)
bucket = storage.bucket(app=firebase_app)


# 블루프린트 등록
from app.routes.article import article_routes
from app.routes.comment import comment_routes

app.register_blueprint(article_routes)
app.register_blueprint(comment_routes)
# 다른 블루프린트도 필요에 따라 등록
```

이렇게 하면 `/add_comment` 경로로 POST 요청을 보내 댓글을 작성할 수 있습니다.
