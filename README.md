# 목적
Aria Operations에서 수집한 메트릭을 기반으로 PDF형식의 보고서 생성을 목적으로 해당 프로젝트를 생성하였습니다.
기본적으로 vSphere환경에 대한 점검 보고서에 Aria Operations에서 제공하는 용량 및 비용에 대한 분석을 추가하여 작성하고자 합니다.

# 소개
파이썬 스크립트는 vROps 파이썬 클라이언트를 사용하여 vROps 서버에서 직접 정보를 쿼리하고 수집합니다. 그리고 수집한 메트릭을 기반으로 reportlab 라이브러리를 활용하여 보고서를 생성합니다.
백엔드에서 REST API를 사용하여 정보를 가져오기 때문에 스크립트를 실행하려면 vROps 서버에서 Python 클라이언트를 다운로드하여 설치해야 합니다.

## 시작하기
VMware에서 Aria Operations API를 쉽게 사용할 수 있도록 python Client Library를 제공하였습니다.
vcops-python.zip 다운로드 하여 압축 해제 후 setup.py을 실행하여 python client를 설치 합니다.



