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

class VSphereMetricsHandler:
    RESOURCE_TYPES = {
        'VSPHERE_WORLD': 0,
        'VCENTER': 1,
        'VIRTUAL_MACHINE': 5,
        'HOST_SYSTEM': 3,
        'CLUSTER': 2,
        'DATASTORE': 4
    }

    def __init__(self, json_data):
        self.data = json_data
        self._validate_data()
        self.available_metrics = self._get_available_metrics()
        self.available_properties = self._get_available_properties()

    def _validate_data(self):
        """데이터 구조 검증"""
        if not isinstance(self.data, list):
            raise ValueError("Invalid data format: Expected a list")
        
    def _get_available_metrics(self):
        """각 리소스 타입별 사용 가능한 메트릭 키 수집"""
        metrics = {}
        for resource_type, index in self.RESOURCE_TYPES.items():
            if index < len(self.data):
                metrics[resource_type] = self.data[index].get('metricKeys', [])
        return metrics

    def _get_available_properties(self):
        """각 리소스 타입별 사용 가능한 프로퍼티 키 수집"""
        properties = {}
        for resource_type, index in self.RESOURCE_TYPES.items():
            if index < len(self.data):
                properties[resource_type] = self.data[index].get('propertyKeys', [])
        return properties

    def get_timestamp(self):
        """타임스탬프 반환"""
        return self.data[self.RESOURCE_TYPES['VCENTER']]['timestamp']

    def get_metrics(self, resource_type, metric_key=None, filters=None):
        """특정 리소스 타입의 메트릭 데이터 반환
        
        Args:
            resource_type (str): RESOURCE_TYPES에 정의된 리소스 타입
            metric_key (str, optional): 특정 메트릭 키. None이면 모든 메트릭 반환
            filters (dict, optional): 필터링 조건 (예: {'name': 'vm-01', 'cpu|usage_average': '>50'})
        
        Returns:
            dict: 필터링된 메트릭 데이터
        """
        if resource_type not in self.RESOURCE_TYPES:
            raise ValueError(f"Invalid resource type: {resource_type}")
        
        resource_index = self.RESOURCE_TYPES[resource_type]
        if resource_index >= len(self.data):
            return {}

        resource_data = self.data[resource_index]
        result = []

        for item in resource_data.get('allstats', []):
            # 필터 조건 검사
            if filters and not self._check_filters(item, filters):
                continue

            stats = item.get('stats', {})
            if metric_key:
                # 특정 메트릭 키만 반환
                if metric_key in stats:
                    result.append(stats[metric_key]) 
            else:
                # 모든 메트릭 반환
                result = stats

        return result

    def get_properties(self, resource_type, property_key=None, filters=None):
        """특정 리소스 타입의 프로퍼티 데이터 반환
        
        Args:
            resource_type (str): RESOURCE_TYPES에 정의된 리소스 타입
            property_key (str, optional): 특정 프로퍼티 키. None이면 모든 프로퍼티 반환
            filters (dict, optional): 필터링 조건 (예: {'name': 'vm-01'})
        
        Returns:
            dict: 필터링된 프로퍼티 데이터
        """
        if resource_type not in self.RESOURCE_TYPES:
            raise ValueError(f"Invalid resource type: {resource_type}")
        
        resource_index = self.RESOURCE_TYPES[resource_type]
        if resource_index >= len(self.data):
            return {}

        resource_data = self.data[resource_index]
        result = []

        for item in resource_data.get('allstats', []):
            # 필터 조건 검사
            if filters and not self._check_filters(item, filters):
                continue

            properties = item.get('properties', {})
            if property_key:
                # 특정 프로퍼티 키만 반환
                if property_key in properties:
                    result.append(properties[property_key]) 
            else:
                # 모든 프로퍼티 반환
                result = properties

        return result

    def _check_filters(self, item, filters):
        """필터 조건 검사
        
        Args:
            item (dict): 검사할 아이템
            filters (dict): 필터 조건
        
        Returns:
            bool: 필터 조건 만족 여부
        """
        for key, value in filters.items():
            # 이름으로 필터링
            if key == 'name' and item.get('name') != value:
                return False
            
            # 메트릭 값으로 필터링
            if key in item.get('stats', {}):
                stat_value = item['stats'][key]
                if isinstance(value, str):
                    # 비교 연산자 처리 (예: '>50', '<=30' 등)
                    operator = ''.join(c for c in value if not c.isdigit() and c != '.')
                    threshold = float(''.join(c for c in value if c.isdigit() or c == '.'))
                    
                    if operator == '>':
                        if not stat_value > threshold:
                            return False
                    elif operator == '>=':
                        if not stat_value >= threshold:
                            return False
                    elif operator == '<':
                        if not stat_value < threshold:
                            return False
                    elif operator == '<=':
                        if not stat_value <= threshold:
                            return False
                    elif operator == '==':
                        if not stat_value == threshold:
                            return False
                else:
                    if stat_value != value:
                        return False
            
            # 프로퍼티 값으로 필터링
            if key in item.get('properties', {}) and item['properties'][key] != value:
                return False
                
        return True

    def list_available_metrics(self, resource_type):
        """특정 리소스 타입에서 사용 가능한 메트릭 키 목록 반환"""
        return self.available_metrics.get(resource_type, [])

    def list_available_properties(self, resource_type):
        """특정 리소스 타입에서 사용 가능한 프로퍼티 키 목록 반환"""
        return self.available_properties.get(resource_type, [])

# 사용 예시
"""
# 핸들러 초기화
metrics_handler = VSphereMetricsHandler(json_data)

# 특정 VM의 CPU 사용량 조회
vm_cpu = metrics_handler.get_metrics(
    'VIRTUAL_MACHINE', 
    'cpu|usage_average',
    filters={'name': 'Web-Dev-01'}
)

# CPU 사용량이 50% 이상인 VM들 조회
high_cpu_vms = metrics_handler.get_metrics(
    'VIRTUAL_MACHINE', 
    'cpu|usage_average',
    filters={'cpu|usage_average': '>50'}
)

# 특정 프로퍼티를 가진 호스트 조회
hosts = metrics_handler.get_properties(
    'HOST_SYSTEM',
    'config|network|dnsConfig|hostName',
    filters={'config|network|dnsConfig|hostName': 'host-01'}
)

# 사용 가능한 메트릭/프로퍼티 키 확인
vm_metrics = metrics_handler.list_available_metrics('VIRTUAL_MACHINE')
host_properties = metrics_handler.list_available_properties('HOST_SYSTEM')
"""
class CustomFlowables:
    class SignatureBox(Flowable):
        """
        Custom Flowable for creating signature boxes that can be positioned anywhere on the page
        """
        def __init__(self, width=100, height=20, text="", x_offset=0, y_offset=0):
            Flowable.__init__(self)
            self.width = width
            self.height = height
            self.text = text
            self.x_offset = x_offset  # From left margin
            self.y_offset = y_offset  # From bottom margin

        def draw(self):
            # Save canvas state
            self.canv.saveState()
            
            # Move to desired position
            self.canv.translate(self.x_offset, self.y_offset)
            
            # Draw rectangle for signature box
            self.canv.rect(0, 0, self.width, self.height)
            
            # Add text inside the rectangle
            self.canv.setFont('Freesentation', 10)
            self.canv.drawString(10, 5, self.text)
            
            # Restore canvas state
            self.canv.restoreState()

class TableGenerator:
    """
    Factory class for creating custom tables with various styles and configurations
    """
    def __init__(self, page_width, margins):
        self.page_width = page_width
        self.margins = margins
        self.frame_width = page_width - margins['left'] - margins['right']

    def create_table(self, data, style_config):
        """
        Creates a table with custom styling
        
        Args:
            data (list): List of lists containing table data
            style_config (dict): Configuration for table styling containing:
                - col_widths (list): List of column widths
                - row_heights (list/int): List of row heights or single height for all rows
                - styles (dict): Dictionary of style commands
                - header_color (str/tuple): Color for header row
                - cell_color (str/tuple): Color for cells
                - align (str): Text alignment
                - padding (dict): Padding configuration
                - fonts (dict): Font configuration
        """
        # Process column widths
        col_widths = style_config.get('col_widths', [self.frame_width / len(data[0])] * len(data[0]))
        if isinstance(col_widths, dict):
            processed_widths = []
            for width in col_widths.values():
                if isinstance(width, float) and 0 <= width <= 1:
                    processed_widths.append(self.frame_width * width)
                else:
                    processed_widths.append(width)
            col_widths = processed_widths

        # Process row heights
        row_heights = style_config.get('row_heights', 30)
        if isinstance(row_heights, (int, float)):
            row_heights = [row_heights] * len(data)

        # Create table
        table = Table(data, colWidths=col_widths, rowHeights=row_heights)

        # Build style commands
        style_list = []
        
        # Default styles
        defaults = {
            'header_color': colors.grey,
            'header_text_color': colors.whitesmoke,
            'cell_color': colors.white,
            'grid_color': colors.black,
            'align': 'CENTER',
            'valign': 'MIDDLE',
            'padding': {'left': 5, 'right': 5, 'top': 5, 'bottom': 5},
            'fonts': {'header': 'Freesentation-Bold', 'cells': 'Freesentation'}
        }

        # Merge defaults with provided styles
        style_config = {**defaults, **style_config}

        # Apply basic styles
        style_list.extend([
            ('BACKGROUND', (0, 0), (-1, 0), style_config['header_color']),
            ('TEXTCOLOR', (0, 0), (-1, 0), style_config['header_text_color']),
            ('BACKGROUND', (0, 1), (-1, -1), style_config['cell_color']),
            ('ALIGN', (0, 0), (-1, -1), style_config['align']),
            ('VALIGN', (0, 0), (-1, -1), style_config['valign']),
            ('FONTNAME', (0, 0), (-1, 0), style_config['fonts']['header']),
            ('FONTNAME', (0, 1), (-1, -1), style_config['fonts']['cells']),
        ])

        # Add custom styles if provided
        if 'styles' in style_config:
            style_list.extend(style_config['styles'])

        # Apply all styles
        table.setStyle(TableStyle(style_list))
        
        return table


def generate_pdf():
    # 핸들러 초기화
    metrics_handler = VSphereMetricsHandler(json_data)


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
    page_width, page_height = letter
    frame_width = page_width - doc.leftMargin - doc.rightMargin
    frame_height = page_height - doc.bottomMargin - 50
    # 마진 설정
    margins = {
        'left': doc.leftMargin,
        'right': doc.rightMargin,
        'top': doc.topMargin,
        'bottom': doc.bottomMargin
    }

    # TableGenerator 인스턴스 생성
    table_gen = TableGenerator(page_width, margins)
    elements = []

    #수정 추후 삭제
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
    
    signature_boxes = [
        CustomFlowables.SignatureBox(width=150, height=50, text="(담당자 서명)", x_offset=frame_width-150, y_offset=140),
        CustomFlowables.SignatureBox(width=150, height=50, text="(점검자 서명)", x_offset=frame_width-150, y_offset=130)
    ]

    for box in signature_boxes:
        elements.append(box)
        

    # 점검 항목 추가
    elements.append(Paragraph("점검 항목", styles['Heading2']))

    # 점검 항목 테이블 생성
    check_items_data = [
        ["가상화 제품 - 기본 점검 항목", "확인"],
        ["관리 서버 및 호스트 환경에 대한 이벤트(Alram) 상태 확인", "□"],
        ["관리 서버(vCenter) 설정 및 상태 확인", "□"],
        ["클러스터 기능 설정 상태 확인", "□"],
        ["ESXi 서비스 및 설정 상태 확인", "□"],
        ["가상 시스템 스냅샷 보유 상태 확인", "□"],
        ["가상 시스템 VM Tools 실행 상태 확인", "□"],
        ["클러스터 리소스 사용률 상태 확인", "□"],
        ["데이터스토어 사용율 상태 확인", "□"]
    ]

    check_items_style = {
        'col_widths': {
            'col1': 0.8,  # 80% of frame width
            'col2': 0.2   # 20% of frame width
        },
        'row_heights': 30,
        'header_color': colors.grey,
        'cell_color': colors.white,
        'styles': [
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 1), (0, -1), 20),        
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ]
    }

    check_items_table = table_gen.create_table(check_items_data, check_items_style)
    elements.append(check_items_table)

    # 페이지 나누기
    elements.append(PageBreak())

    # 2 페이지 생성
    elements.append(Paragraph("계약 대상 제품 구분 및 수량", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    product_count_data = [
    ["항목", "수량"],
    ["vCenter", f"{metrics_handler.get_metrics(resource_type='VSPHERE_WORLD',metric_key='summary|total_number_vcenters')[0]:.0f} (EA)"],
    ["Datacenter", f"{metrics_handler.get_metrics(resource_type='VSPHERE_WORLD',metric_key='summary|total_number_datacenters')[0]:.0f} (EA)"],
    ["Cluster", f"{metrics_handler.get_metrics(resource_type='VSPHERE_WORLD',metric_key='summary|total_number_clusters')[0]:.0f} (EA)"],
    ["Host(ESXi)", f"{metrics_handler.get_metrics(resource_type='VSPHERE_WORLD',metric_key='summary|total_number_hosts')[0]:.0f} (EA)"],
    ["Virtual Machine", f"{metrics_handler.get_metrics(resource_type='VSPHERE_WORLD',metric_key='summary|total_number_vms')[0]:.0f} (EA)"]
    ]
    product_count_style = {
        'col_widths': {
        'col1': 0.5,  # 50% of frame width
        'col2': 0.5   # 50% of frame width
        },
        'row_heights': [20, 40, 40, 40, 40, 40],
        'header_color': colors.grey,
        'cell_color': colors.white,
        'align': 'CENTER',
        'styles': [
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]
    }

    product_count_table = table_gen.create_table(product_count_data, product_count_style)
    elements.append(product_count_table)
    elements.append(Spacer(1, 100))


    guide_data = [
        ["권장 가이드"],
        ["※ 클러스터 환경에 대한 리소스 사용율은  '2대 호스트 구성 기준'으로 'CPU 와 Memory'에 대해서 '50% 미만(45%)'으로 유지 하는 것을 권장 (호스트 1대 장애 발생 대비)"],
        ["※ 일반적으로 데이터스토어는 2개 이상을 사용하는 것을 권장(Datastore heartbeat or Migration)하며, 각 데이터스토어의 사용률은 전체 사이즈의 80% 수준을 권장"],
        ["※ 가상화 인프라를 구성하고 있는 모든 IO 디바이스에 대해서는 이중화(Redundancy) 구성을 권장"],
        ["※ 가상시스템에 생성되어 있는 스냅샷은 72시간 이내에 삭제하는 것을 권장 (스냅샷을 백업 용도로 장기간 보존하는 것을 권장하지 않음)"],
        ["※ 가상시스템 환경은 버전에 맞는 'VMware Tools'를 설치 및 사용하는 것을 권장 (VMware Tools 에는 가상화 환경에 필요한 여러가지 드라이버와 기능을 포함)"],
        ["※ 가상화 인프라를 구성하고 있는 주요 컴포넌트(vCenter) 및 구성 설정(vDS)에 대해서 주기적으로 백업(RVTools, Export, FTP 등)하는 것을 권장"]
    ]
    guide_style = {
        'col_widths': [frame_width],
        'row_heights': 30,
        'header_color': colors.lightgrey,
        'cell_color': colors.white,
        'styles': [
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTSIZE', (0, 1), (0, -1), 7.5),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ]
    }   

    guide_table = table_gen.create_table(guide_data, guide_style)
    elements.append(guide_table)

    elements.append(PageBreak())

    # 3 페이지 생성
    elements.append(Paragraph("vSphere 환경 이벤트 상태 확인",styles['Title']))
    elements.append(Spacer(1,12))
    elements.append(Paragraph("심각도 수준(Severity Level) 별 이벤트 발생 수",styles['Heading2']))
    list_data = [
        ["위험(Critical Level)","즉시(High Level)","경고(Medium Level)","정보(Low Level)"],
        [f"{metrics_handler.get_metrics(resource_type="VSPHERE_WORLD",metric_key="System Attributes|alert_count_critical")[0]:.0f}",
        f"{metrics_handler.get_metrics(resource_type="VSPHERE_WORLD",metric_key="System Attributes|alert_count_immediate")[0]:.0f}",
        f"{metrics_handler.get_metrics(resource_type="VSPHERE_WORLD",metric_key="System Attributes|alert_count_warning")[0]:.0f}",
        f"{metrics_handler.get_metrics(resource_type="VSPHERE_WORLD",metric_key="System Attributes|alert_count_info")[0]:.0f}"
        ]
    ]
    list_data_table = Table(list_data, colWidths=frame_width/4, rowHeights=[30,40])
    list_data_table.setStyle(TableStyle({
        ('BACKGROUND', (0, 0), (0, 0), (0.9,0.25,0.2)),
        ('BACKGROUND', (1, 0), (1, 0), colors.orange),
        ('BACKGROUND', (2, 0), (2, 0), (0.95,0.9,0.1)),
        ('BACKGROUND', (3, 0), (3, 0), (0.25,0.6,0.3)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Freesentation-Bold'),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    }))

    add_data = [
        ["비고"],
        [""]
    ]
    add_data_table = Table(add_data, colWidths=frame_width, rowHeights=[20,400])
    add_data_table.setStyle(TableStyle({
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Freesentation-Bold'),
        ('VALIGN', (0, 0), (0, -1), "MIDDLE"),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (0, 0), 1, colors.black),
    }))
    elements.append(list_data_table)
    elements.append(Spacer(1,30))
    elements.append(add_data_table)
    elements.append(PageBreak())

    # 4 페이지 생성
    elements.append(Paragraph("관리서버(vCenter) 설정 및 상태 확인",styles['Title']))
    elements.append(PageBreak())

    # 5 페이지 생성
    elements.append(Paragraph("클러스터 기능 설정 상태 확인",styles['Title']))
    elements.append(Spacer(1,12))
    cluster_drs_data = [
        ['클러스터 이름','DRS 사용', 'DRS 기본 동작', '마이그레이션 임계값','DRS로 수행된 vMotion 수']
    ]

    tt = metrics_handler.get_properties(resource_type='CLUSTER',property_key='config|name')
    for i in range(len(tt)):
        li = [
            metrics_handler.get_properties(resource_type='CLUSTER',property_key='config|name')[i],
            metrics_handler.get_properties(resource_type='CLUSTER',property_key='configuration|drsConfig|enabled')[i],
            metrics_handler.get_properties(resource_type='CLUSTER',property_key='configuration|drsConfig|defaultVmBehavior')[i],  
            metrics_handler.get_properties(resource_type='CLUSTER',property_key='configuration|drsConfig|vmotionRate')[i],
            metrics_handler.get_metrics(resource_type='CLUSTER', metric_key='summary|number_drs_vmotion')[i]
              ]
        cluster_drs_data.append(li)

    cluster_drs_style = {
        'col_widths': {
            'col1': 0.2,  
            'col2': 0.1,
            'col3': 0.2,   
            'col4': 0.2,
            'col5': 0.3,
        },
        #'row_heights': 30,
        #'header_color': colors.lightgrey,
        'cell_color': colors.white,
        'styles': [
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTSIZE', (0, 1), (0, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]
    }   

    cluster_drs_table = table_gen.create_table(cluster_drs_data, cluster_drs_style)
    elements.append(Paragraph("클러스터 DRS 설정",styles['Heading2']))
    elements.append(cluster_drs_table)
    elements.append(Spacer(1,30))

    cluster_ha_data = [
        ['클러스터 이름','HA 사용','승인제어 사용', 'HA CPU 페일로버 비율', 'HA 메모리 페일오버 비율']
    ]

    for i in range(len(tt)):
        li = [
            metrics_handler.get_properties(resource_type='CLUSTER',property_key='config|name')[i],
            metrics_handler.get_properties(resource_type='CLUSTER',property_key='configuration|dasConfig|enabled')[i],
            metrics_handler.get_properties(resource_type='CLUSTER',property_key='configuration|dasConfig|admissionControlEnabled')[i],  
            metrics_handler.get_properties(resource_type='CLUSTER',property_key='configuration|dasConfig|cpuFailoverPercent')[i],
            metrics_handler.get_properties(resource_type='CLUSTER', property_key='configuration|dasConfig|memFailoverPercent')[i]
            ]
        cluster_ha_data.append(li)

    cluster_ha_style = {
        'col_widths': {
            'col1': 0.2,  
            'col2': 0.15,
            'col3': 0.15,   
            'col4': 0.25,
            'col5': 0.25,
        },
        #'row_heights': 30,
        #'header_color': colors.lightgrey,
        'cell_color': colors.white,
        'styles': [
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTSIZE', (0, 1), (0, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]
    }   

    cluster_ha_table = table_gen.create_table(cluster_ha_data, cluster_ha_style)
    elements.append(Paragraph("클러스터 HA 설정",styles['Heading2']))
    elements.append(cluster_ha_table)
    elements.append(PageBreak())

    # 6 페이지 생성
    elements.append(Paragraph("ESXi 서비스 및 설정 상태 확인",styles['Title']))
    esxi_data = [
        ['이름', 'IP']
    ]
    elements.append(PageBreak())

    # 7 페이지 생성
    elements.append(Paragraph("가상 시스템 스냅샷 보유 상태 및 VM Tools 상태 확인",styles['Title']))
    elements.append(PageBreak())

    # 7 페이지 생성
    elements.append(Paragraph("클러스터 및 호스트 리소스 사용률 상태 확인",styles['Title']))
    elements.append(PageBreak())

    # 7 페이지 생성
    elements.append(Paragraph("데이터스토어 사용율 상태 확인",styles['Title']))
    elements.append(PageBreak())
    # PDF 작성
    doc.build(elements)
    print(f"PDF 생성 완료: {pdf_path}")

generate_pdf()