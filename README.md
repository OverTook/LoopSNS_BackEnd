# 🐮 LoopSNS (BackEnd)

<br/>

## **Team & Project Details:**
- **Team Name:** HCI
- **Team Members:** *(This is not FrontEnd Team)*
    - 🧑‍⚖️ 고건호 **(팀장)**
    - 🧑‍💻 김도환
    - 🧑‍💻 송주훈
    - 👩‍💻 김채리
- **Project Duration:** 2024.06.22 ~ 2024.08.12

<br/>

## **Overview:**
위치 기반 SNS.. 

<br/>

## **Key Features:**
- **카테고리 자동 분석:** 
- **KMeans 알고리즘을 이용한 클러스터링:** 

<br/>

## **Project Organization:**
```
├── app/
│   ├── functions/
│   │   ├── __init__.py
│   │   ├── category_extraction.py
│   │   ├── clusterer.py
│   │   ├── image_processing.py
│   │   └── user_auth.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── article.py
│   │   ├── auth.py
│   │   ├── category.py
│   │   ├── comment.py
│   │   ├── like.py
│   │   └── marker.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── decorators.py
│   └── __init__.py
├── config/
│   ├── __init__.py
│   ├── firebase.py
│   ├── server.py
│   └── settings.py
├── data/
│   ├── auth/
│   │   ├── hci-service-account.json
│   │   └── kdb-firebase-adminsdk.json
│   └── upload/
├── docs/
│   ├── 01-running_server.md
│   ├── 02-flask_app_setting.md
│   └── 03-route_setting.md
├── .env
├── README.md
├── requirements.txt
└── run.py
```
