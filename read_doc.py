# -*- coding: utf-8 -*-
"""分析 Word 文档的样式和段落"""
from docx import Document
import re
import sys

# 重定向输出到文件
output_file = r'e:\Qwen\xmjl\analysis_output.txt'
f = open(output_file, 'w', encoding='utf-8')
sys.stdout = f

file_path = r'e:\Qwen\xmjl\03-临平区数字慈善系统建设方案模板.docx'
doc = Document(file_path)

# 1. 收集所有样式
all_styles = set()
paragraphs_info = []

for para in doc.paragraphs:
    style_name = para.style.name if para.style else '无样式'
    text = para.text.strip()
    all_styles.add(style_name)
    if text:
        paragraphs_info.append({'style': style_name, 'text': text})

print('=' * 80)
print('1. 文档中使用的所有样式名称')
print('=' * 80)
for style in sorted(all_styles):
    print(f'  - {style}')
print(f'\n共 {len(all_styles)} 种样式')

print('\n' + '=' * 80)
print('2. 前 50 个非空段落（样式名 + 文本内容前 30 字）')
print('=' * 80)
for i, para in enumerate(paragraphs_info[:50], 1):
    text_preview = para['text'][:30] + '...' if len(para['text']) > 30 else para['text']
    print(f'{i:3d}. [{para["style"]}] {text_preview}')

print('\n' + '=' * 80)
print('3. 包含数字编号的段落（如 1.、1.1、第一章等）')
print('=' * 80)

patterns = [
    r'^\d+\.',
    r'^\d+\.\d+',
    r'^\d+\.\d+\.\d+',
    r'^第 [一二三四五六七八九十百]+[章条节款]',
    r'^[一二三四五六七八九十]+[、.]',
    r'^\(\d+\)',
    r'^①',
]

numbered_paras = []
for para in paragraphs_info:
    for pattern in patterns:
        if re.match(pattern, para['text']):
            numbered_paras.append(para)
            break

if numbered_paras:
    for i, para in enumerate(numbered_paras, 1):
        text_preview = para['text'][:80] + '...' if len(para['text']) > 80 else para['text']
        print(f'{i:3d}. [{para["style"]}] {text_preview}')
    print(f'\n共 {len(numbered_paras)} 个包含数字编号的段落')
else:
    print('未找到包含数字编号的段落')

print('\n' + '=' * 80)
print('4. 样式使用统计（按使用次数排序）')
print('=' * 80)
style_count = {}
for para in paragraphs_info:
    style_count[para['style']] = style_count.get(para['style'], 0) + 1

for style, count in sorted(style_count.items(), key=lambda x: x[1], reverse=True):
    print(f'  {style}: {count} 次')
