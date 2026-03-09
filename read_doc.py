# -*- coding: utf-8 -*-
from docx import Document

doc = Document('partial_617cd6d4.docx')

print(f'段落数量: {len(doc.paragraphs)}')
print()

# 查找有实际内容的段落（不是标题）
content_paras = []
for i, para in enumerate(doc.paragraphs):
    text = para.text.strip()
    if text and len(text) > 20 and not text.startswith(('第', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '(', '（')):
        content_paras.append((i+1, text))

print(f'=== 实际内容段落（共{len(content_paras)}段）===')
for idx, (i, text) in enumerate(content_paras[:20]):
    print(f'{idx+1}. [第{i}段] {text[:100]}...')
    print()
