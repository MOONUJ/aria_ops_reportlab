# 목적
Aria Operations에서 수집한 메트릭을 기반으로 PDF형식의 보고서 생성을 목적으로 해당 프로젝트를 생성하였습니다.
기본적으로 vSphere환경에 대한 점검 보고서에 Aria Operations에서 제공하는 용량 및 비용에 대한 분석을 추가하여 작성하고자 합니다.

# 소개
파이썬 스크립트는 vROps 파이썬 클라이언트를 사용하여 vROps 서버에서 직접 정보를 쿼리하고 수집합니다. 그리고 수집한 메트릭을 기반으로 reportlab 라이브러리를 활용하여 보고서를 생성합니다.
백엔드에서 REST API를 사용하여 정보를 가져오기 때문에 스크립트를 실행하려면 vROps 서버에서 Python 클라이언트를 다운로드하여 설치해야 합니다.

# 실행
VMware에서 Aria Operations API를 쉽게 사용할 수 있도록 python Client Library를 제공하였습니다.
먼저, 해당 repository를 다운로드 하여 vcops-python 디렉토리에 있는 setup.py을 실행하여 python client를 설치 합니다.

이 후 실행 할 스크립트는 3가지 입니다. 'set-config.py', 'metric-collection.py', 'create_report_01.py'
set-config.py 스크립트를 실행하여 수집하고자 하는 Aria Operations의 정보, 어댑터 정보, 리소스 Kind, metric 또는 property 값을 지정합니다.
그럼 다음 'metric-collection.py'을 실행하여 메트릭 값을 수집하고 'create_report_01.py'을 실행하여 pdf 형식의 보고서를 출력합니다.

참조할 만한 추가 리소스 문서들을 공유합니다.
- Aria Operatioins API Guide Document
https://docs.vmware.com/en/VMware-Aria-Operations/SaaS/API-Programming-Operations/GUID-6744E93C-DED3-4530-B86E-BEC09BF56EC2.html

- ReportLAb User Guide Document
https://docs.reportlab.com/reportlab/userguide/ch1_intro/






