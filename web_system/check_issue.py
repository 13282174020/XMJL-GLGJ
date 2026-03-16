# -*- coding: utf-8 -*-
"""检查生成文档的样式问题"""
from docx import Document
import re

doc = Document('outputs/test_cscswj2_processed.docx')

print('=' * 80)
print('检查生成文档中所有带编号但不是 Heading 样式的段落')
print('=' * 80)

styles_found = set()
count = 0

for i, para in enumerate(doc.paragraphs):
    text = para.text.strip()
    if not text:
        continue
    style = para.style.name if para.style else 'Normal'
    styles_found.add(style)
    
    # 检查是否有编号格式但不是 Heading 样式
    has_numbering = (
        re.match(r'^\d+\.\d+', text) or
        re.match(r'^[一二三四五六七八九十]+[、.]', text) or
        re.match(r'^（[一二三四五六七八九十\d]+）', text) or
        re.match(r'^\d+\.\d+\.\d+', text)
    )
    
    if has_numbering and 'Heading' not in style and 'toc' not in style.lower():
        print(f'段落 {i:4d}: [{style:35s}] {text[:70]}')
        count += 1
        if count >= 50:
            break

print(f'\n共找到 {count} 个有编号但不是 Heading 样式的段落')
print(f'\n文档中所有样式：{sorted(styles_found)}')
