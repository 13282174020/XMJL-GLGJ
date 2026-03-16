# -*- coding: utf-8 -*-
"""检查生成文档的样式名称"""
from docx import Document

doc = Document(r'e:\Qwen\xmjl\web_system\outputs\test_cscswj2_processed.docx')

print('检查 Heading 样式的段落:')
print('=' * 80)

heading_styles = {}
for i, para in enumerate(doc.paragraphs):
    text = para.text.strip()
    if not text:
        continue
    style = para.style.name if para.style else 'Normal'
    
    if 'Heading' in style:
        if style not in heading_styles:
            heading_styles[style] = 0
        heading_styles[style] += 1
        
        # 打印前 20 个
        if heading_styles[style] <= 5:
            print(f'[{style}] {text[:60]}')

print(f'\n样式统计:')
for style, count in sorted(heading_styles.items()):
    print(f'  {style}: {count}')
