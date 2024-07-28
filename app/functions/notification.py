from firebase_admin import messaging

# 푸시 알림 전송 함수
def send_push_notification(registration_token, title, body):
    # 메시지 생성
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=registration_token,
    )

    # 메시지 전송
    response = messaging.send(message)
    print('Successfully sent message:', response)
