# -*- coding: utf-8 -*-
"""检查生成文档的样式问题 - 详细版"""
from docx import Document
import re

doc = Document('outputs/test_cscswj2_processed.docx')

print('=' * 80)
print('检查生成文档中所有非 Heading 且非 Normal 的样式段落')
print('=' * 80)

for i, para in enumerate(doc.paragraphs):
    text = para.text.strip()
    if not text:
        continue
    style = para.style.name if para.style else 'Normal'
    
    # 检查是否是非 Heading 且非 Normal 的样式
    if style not in ['Normal', 'Heading 1', 'Heading 2', 'Heading 3', 'Heading 4', 'Heading 5', 'Heading 6']:
        # 检查是否有编号
        has_numbering = (
            re.match(r'^\d+\.\d+', text) or
            re.match(r'^[一二三四五六七八九十]+[、.]', text) or
            re.match(r'^（[一二三四五六七八九十\d]+）', text)
        )
        
        marker = '***' if has_numbering else '   '
        print(f'{marker} 段落 {i:4d}: [{style:35s}] {text[:70]}')
