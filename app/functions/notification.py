from firebase_admin import messaging
import json

# 푸시 알림 전송 함수
# n_type 노티피케이션 종류
def send_push_notification(registration_token, n_type, body):
    # JSON 객체를 문자열로 변환
    if isinstance(body, dict):
        body = json.dumps(body)
    
    # 메시지 생성
    message = messaging.Message(
        #notification=messaging.Notification(
        #    title=title,
        #    body=body,
        #),
        data = {
            'type': n_type,
            'body': body
        },
        token=registration_token,
    )
    print(body)

    # 메시지 전송
    response = messaging.send(message)
    print('Successfully sent message:', response)
