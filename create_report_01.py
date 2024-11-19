import json
import os, sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import BaseDocTemplate,Flowable, Frame, PageTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics



# JSON 파일 읽기
def get_script_path():
    return os.path.dirname(os.path.realpath(sys.argv[0]))
path = get_script_path()
json_path = path+"/"+"metric-data.json"
cover_image_path = path+"/reportlab/"+"banner.png"
#json_path = '/mnt/data/metric-data.json'  # 업로드된 JSON 파일 경로
with open(json_path, 'r') as file:
    json_data = json.load(file)

# 한글 폰트 등록
pdfmetrics.registerFont(TTFont('Freesentation', path+'/reportlab/Freesentation-5Medium.ttf'))  # 시스템에 설치된 폰트 경로
pdfmetrics.registerFont(TTFont('Freesentation-Bold', path+'/reportlab/Freesentation-7Bold.ttf'))

# 스타일 설정
styles = getSampleStyleSheet()
styles['Title'].fontName = 'Freesentation-Bold'
styles['Normal'].fontName = 'Freesentation'
styles['Heading1'].fontName = 'Freesentation-Bold'
styles['Heading2'].fontName = 'Freesentation-Bold'
styles['Heading3'].fontName = 'Freesentation-Bold'
styles['Heading4'].fontName = 'Freesentation-Bold'


# PDF 설정
pdf_path = "metric_report.pdf"
doc = BaseDocTemplate(pdf_path, pagesize=letter, topMargin=0, bottomMargin=50)
elements = []
page_width, page_height = letter
frame_width = page_width - doc.leftMargin - doc.rightMargin
# 페이지마다 커버 이미지 추가 함수
def add_header_footer(canvas, doc):    
    if cover_image_path:
        header_image = Image(cover_image_path, width=page_width, height=50)
        header_image.drawOn(canvas, 0, page_height - 50)  # 페이지 상단에 이미지 위치 조정
    
    page_num = canvas.getPageNumber()
    page_number_text = f"Page {page_num}"
    canvas.setFont('Freesentation', 10)
    canvas.drawString(page_width / 2 - 20, 20, page_number_text)

# 페이지 템플릿 설정
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 80, id='normal')
template = PageTemplate(id='header_template', frames=frame, onPage=add_header_footer)
doc.addPageTemplates([template])


# 제목 추가
title = Paragraph("템플릿 - 정기점검 보고서", styles['Title'])
elements.append(title)
elements.append(Spacer(1, 20))

# Custom Flowable to draw a signature box
class SignatureBox(Flowable):
    def __init__(self, width=100, height=20, text=""):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.text = text

    def draw(self):
        # Draw rectangle for signature box
        self.canv.rect(page_width - self.width - doc.leftMargin - doc.rightMargin, 130, self.width, self.height)
        # Add text inside the rectangle
        self.canv.drawString(page_width - self.width - doc.leftMargin - doc.rightMargin + 10, 135, self.text)

# "기본 정보" 추가
title_pages = [
    f"고객사 : ",
    f"보고서 생성 시간 : {json_data[1]['timestamp']}",
    f"유지보수 계약 구분 : ",
    f"지원 엔지니어 : "
    ]

for title_page in title_pages:
  elements.append(Paragraph(title_page, styles['Heading4']))
  elements.append(Spacer(1,10))


# 서명란 추가
signature_box = SignatureBox(width=150, height=50, text="(담당자 서명)")
signature_box_reporter = SignatureBox(width=150, height=50, text="(점검자 서명)")
elements.append(signature_box)
elements.append(Spacer(1, 10))
elements.append(signature_box_reporter)

# 아래쪽 여백 추가
elements.append(Spacer(1, 20))

# 점검 항목 추가
elements.append(Paragraph("계약 대상 제품 구분 및 수량", styles['Heading2']))
list_data = [
    ["항목","수량","버전"],
    ["vCenter", f"{json_data[0]['allstats'][0]['stats']['summary|total_number_vcenters']:.0f}  (EA)","version"],
    ["vSphere ESXi","2","version"],
    ["Aria Suite","2","version"]
    ]


list_data_table = Table(list_data, colWidths=[frame_width/3, frame_width/3, frame_width/3], rowHeights=[ 20, 40, 40, 40])
list_data_table.setStyle(TableStyle({
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Freesentation-Bold'),
    ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ('GRID', (0, 0), (-1, -1), 1, colors.black),
}))
elements.append(list_data_table)
# 페이지 나누기
elements.append(PageBreak())

# 목차 생성
elements.append(Paragraph("점검 항목", styles['Heading1']))
elements.append(Spacer(1, 12))
list_data = [
    ["가상화 제품 - 기본 점검 항목", "확인"],
    ["클러스터 기능 설정 상태 확인", "□"],
    ["ESXi 서비스 및 설정 상태 확인", "□"],
    ["클러스터 리소스 사용률 상태 확인", "□"],
    ["데이터스토어 사용율 상태 확인", "□"],
    ["가상 시스템 스냅샷 보유 상태 확인", "□"],
    ["vCenter 서버 설정 및 상태 확인", "□"]
]
reco_data = [
    ["권장 가이드"],
    ["※ 클러스터 환경에 대한 리소스 사용율은  '2대 호스트 구성 기준'으로 'CPU 와 Memory'에 대해서 '50% 미만(45%)'으로 유지 하는 것을 권장 (호스트 1대 장애 발생 대비)"],
    ["※ 일반적으로 데이터스토어는 2개 이상을 사용하는 것을 권장(Datastore heartbeat or Migration)하며, 각 데이터스토어의 사용률은 전체 사이즈의 80% 수준을 권장"],
    ["※ 가상화 인프라를 구성하고 있는 모든 IO 디바이스에 대해서는 이중화(Redundancy) 구성을 권장"],
    ["※ 가상시스템에 생성되어 있는 스냅샷은 72시간 이내에 삭제하는 것을 권장 (스냅샷을 백업 용도로 장기간 보존하는 것을 권장하지 않음)"],
    ["※ 가상시스템 환경은 버전에 맞는 'VMware Tools'를 설치 및 사용하는 것을 권장 (VMware Tools 에는 가상화 환경에 필요한 여러가지 드라이버와 기능을 포함)"],
    ["※ 가상화 인프라를 구성하고 있는 주요 컴포넌트(vCenter) 및 구성 설정(vDS)에 대해서 주기적으로 백업(RVTools, Export, FTP 등)하는 것을 권장"]
]

list_data_table = Table(list_data, colWidths=[frame_width - frame_width/5, frame_width/5], rowHeights=30)
list_data_table.setStyle(TableStyle({
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
    ('ALIGN', (1, 1), (1, -1), 'CENTER'),
    ('LEFTPADDING', (0, 1), (0, -1), 20),
    ('FONTNAME', (0, 0), (-1, 0), 'Freesentation-Bold'),
    ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
    ('FONTNAME', (0, 1), (-1, -1), 'Freesentation'),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ('BOX', (0, 0), (-1, -1), 1, colors.black),
}))
reco_data_table = Table(reco_data, colWidths=frame_width, rowHeights=30)
reco_data_table.setStyle(TableStyle({
    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
    ('FONTSIZE', (0, 1), (0, -1), 7.5),
    ('FONTNAME', (0, 0), (-1, 0), 'Freesentation-Bold'),
    ('VALIGN', (0, 0), (0, -1), "MIDDLE"),
    ('FONTNAME', (0, 1), (0, -1), 'Freesentation'),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ('BOX', (0, 0), (-1, -1), 1, colors.black),
}))

elements.append(list_data_table)
elements.append(Spacer(1, 100))
elements.append(reco_data_table)
elements.append(PageBreak())

# PDF 작성
doc.build(elements)
print(f"PDF 생성 완료: {pdf_path}")