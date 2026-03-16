# -*- coding: utf-8 -*-
"""检查章标题使用的样式"""
from docx import Document

output_path = r'e:\Qwen\xmjl\outputs\test_with_logs.docx'
doc = Document(output_path)

print('检查前 15 个非空段落的样式:')
count = 0
for i, para in enumerate(doc.paragraphs):
    text = para.text.strip()
    if not text:
        continue
    style_name = para.style.name if para.style else 'Normal'
    print(f'  段落 {i}: [{style_name}] {text[:50]}')
    count += 1
    if count >= 15:
        break

# 检查文档中可用的样式
print(f'\n文档中可用的样式:')
for style in doc.styles:
    print(f'  {style.name}')
