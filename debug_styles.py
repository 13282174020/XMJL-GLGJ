# -*- coding: utf-8 -*-
"""调试样式加载"""
import sys
sys.path.insert(0, 'backend')

from app.utils.doc_builder import DocBuilder

template_path = r'e:\Qwen\xmjl\03-临平区数字慈善系统建设方案模板.docx'

print('创建 DocBuilder...')
builder = DocBuilder(template_path=template_path)

print(f'\ntemplate_styles 数量：{len(builder.template_styles)}')
print(f'\n检查关键样式是否存在:')
for style_name in ['Heading 1', 'Heading 2', 'Body Text First Indent 2', 'BZ_正文']:
    exists = style_name in builder.template_styles
    print(f'  {style_name}: {"存在" if exists else "不存在"}')

print(f'\n前 10 个样式:')
for i, name in enumerate(list(builder.template_styles.keys())[:10]):
    print(f'  {name}')
