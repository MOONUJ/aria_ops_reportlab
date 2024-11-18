import json
import os, sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics



# JSON 파일 읽기
def get_script_path():
    return os.path.dirname(os.path.realpath(sys.argv[0]))
path = get_script_path()
json_path = path+"/"+"metric-data.json"
cover_image_path = path+"/reportlab/"+"goodmit.png"
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


# PDF 설정
pdf_path = "metric_report.pdf"
doc = SimpleDocTemplate(pdf_path, pagesize=letter)
elements = []

# 커버 이미지 추가
if cover_image_path:
    cover_image = Image(cover_image_path, width=600, height=300)
    elements.append(cover_image)
    elements.append(Spacer(1, 40))
# 제목 추가
title = Paragraph("템플릿 - 정기점검 보고서", styles['Title'])
elements.append(title)
elements.append(Spacer(1, 20))

# 시간 정보 추가
report_timestamp = f"점검 일자 : {json_data[1]['timestamp']}"
elements.append(Paragraph(report_timestamp, styles['Normal']))
elements.append(Spacer(1, 12))

# 페이지 나누기
elements.append(PageBreak())

# 목차 생성
elements.append(Paragraph("Table of Contents", styles['Title']))
elements.append(Spacer(1, 12))

toc_data = [["Section", "Page"]]
sections = [
    "1. Overview of Metrics",
    "2. CPU Demand Analysis",
    "3. Disk Capacity and Usage"
]

for i, section in enumerate(sections, start=1):
    toc_data.append([section, str(i + 2)])  # 페이지 번호를 임의로 할당

# 목차 테이블
toc_table = Table(toc_data)
toc_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Freesentation-Bold'),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ('GRID', (0, 0), (-1, -1), 1, colors.black),
]))

elements.append(toc_table)
elements.append(Spacer(1, 200))
elements.append(PageBreak())

# 테이블 데이터 준비
table_data = [["Name", "CPU Demand (MHz)", "Disk Capacity (GB)", "Disk Usage (GB)"]]

for item in json_data[2]['allstats']:
    name = item['name']
    cpu_demand = sum(stat['value'] for stat in item['stats']['cpu|demandmhz']) / len(item['stats']['cpu|demandmhz'])
    disk_capacity = sum(stat['value'] for stat in item['stats'].get('guestfilesystem|capacity_total', [{'value': 0}]))
    disk_usage = sum(stat['value'] for stat in item['stats'].get('guestfilesystem|usage_total', [{'value': 0}]))
    table_data.append([name, f"{cpu_demand:.2f}", f"{disk_capacity:.2f}", f"{disk_usage:.2f}"])

# 테이블 생성
table = Table(table_data)
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Freesentation-Bold'),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ('GRID', (0, 0), (-1, -1), 1, colors.black),
]))

elements.append(table)
elements.append(PageBreak())

# PDF 작성
doc.build(elements)
print(f"PDF 생성 완료: {pdf_path}")
