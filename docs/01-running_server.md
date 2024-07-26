# 01. 서버 실행
## 서버 실행하기
백엔드 서버는 프로젝트 내에 있는 `run.py`를 실행시키면 됩니다.
```
$ python run.py
```

## 서버 실행 여부 확인하기
백엔드 서버의 실행 여부는 `netstat` 명령어를 사용해 확인 가능합니다.\
현재 LoopSNS 백엔드 서버는 `5126` 포트에서 실행되고 있기 때문에, `5126` 포트로 실행되고 있는 프로세스가 있는지 확인하면 됩니다.
```
$ netstat -tnlp | grep 5126
(Not all processes could be identified, non-owned process info
 will not be shown, you would have to be root to see it all.)
tcp        0      0 222.116.135.166:5126    0.0.0.0:*               LISTEN      295741/python 
```

## 서버 종료하기
만약 서버가 백그라운드(nohup)에서 실행되고 있다면, `netstat`으로 프로세스 PID를 확인해 직접 `kill` 해주어야 합니다.

```
$ netstat -tnlp | grep 5126
(Not all processes could be identified, non-owned process info
 will not be shown, you would have to be root to see it all.)
tcp        0      0 222.116.135.166:5126    0.0.0.0:*               LISTEN      295741/python 
```
위와 같이 뜬다면 LISTEN 옆에 있는 PID를 `kill` 해주면 됩니다.

```
$ kill -9 PID
```
위 과정을 한 번 더 해서, 해당 포트로 실행되고 있는 프로세스가 없는 것을 확인해줍니다.

```
$ netstat -tnlp | grep 5126
(Not all processes could be identified, non-owned process info
 will not be shown, you would have to be root to see it all.)
```
아무것도 뜨지 않는다면, 서버가 종료된 것 입니다.
