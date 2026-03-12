from docx import Document
import os

os.makedirs('tests/fixtures', exist_ok=True)

# 标准样本
doc = Document()
doc.add_heading('1 项目概况', level=1)
doc.add_heading('1.1 项目背景', level=2)
doc.add_heading('1.1.1 政策背景', level=3)
doc.add_heading('1.1.1.1 详细政策', level=4)
doc.add_heading('2 需求分析', level=1)
doc.add_heading('2.1 业务需求', level=2)
doc.add_heading('2.1.1 用户需求', level=3)
doc.save('tests/fixtures/sample_standard.docx')
print('OK: sample_standard.docx')

# 非标准样本
doc2 = Document()
doc2.add_heading('1 项目概述', level=1)
doc2.add_heading('2 现状分析', level=1)
p = doc2.add_paragraph('2.1 建设背景', style='Normal')
p.runs[0].font.bold = True
p = doc2.add_paragraph('2.2 现有系统不足', style='Normal')
p.runs[0].font.bold = True
p = doc2.add_paragraph('2.2.1 操作复杂', style='Normal')
p.runs[0].font.bold = True
p = doc2.add_paragraph('2.2.2 功能单一', style='Normal')
p.runs[0].font.bold = True
p = doc2.add_paragraph('2.2.2.1 缺乏移动端', style='Normal')
p.runs[0].font.bold = True
p = doc2.add_paragraph('2.2.2.2 数据分析弱', style='Normal')
p.runs[0].font.bold = True
p = doc2.add_paragraph('2.2.2.2.1 无报表功能', style='Normal')
p.runs[0].font.bold = True
doc2.add_heading('3 建设目标', level=1)
doc2.save('tests/fixtures/sample_nonstandard.docx')
print('OK: sample_nonstandard.docx')
print('Done!')

# 创建测试文件
test_content = '''# -*- coding: utf-8 -*-
import pytest
from web_system.app import get_heading_level, scan_template_styles

def test_heading_1():
    assert get_heading_level('Heading 1') == 1

def test_heading_6():
    assert get_heading_level('Heading 6') == 6

def test_not_heading():
    assert get_heading_level('Normal') == 0

def test_scan_standard(sample_standard_doc):
    result = scan_template_styles(str(sample_standard_doc))
    assert result['success'] is True
    print('OK:', result['message'])

def test_scan_nonstandard(sample_nonstandard_doc):
    result = scan_template_styles(str(sample_nonstandard_doc))
    assert result['success'] is True
    print('OK:', result['message'])
'''

with open('tests/test_document_analyzer.py', 'w', encoding='utf-8') as f:
    f.write(test_content)
print('OK: tests/test_document_analyzer.py')
