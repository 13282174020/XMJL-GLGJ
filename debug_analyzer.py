# -*- coding: utf-8 -*-
"""调试分析器逻辑"""
from docx import Document
import re
from collections import defaultdict

file_path = r'e:\Qwen\xmjl\03-临平区数字慈善系统建设方案模板.docx'
doc = Document(file_path)

# 编号正则（与 template_analyzer.py 一致）
numbering_regex_patterns = [
    (r'^(\d+)\.(\d+)\.(\d+)\.(\d+)', 4),
    (r'^(\d+)\.(\d+)\.(\d+)', 3),
    (r'^(\d+)\.(\d+)', 2),
]

def _get_heading_level(style_name, text=''):
    if not style_name:
        return 0
    style_lower = style_name.lower()
    if 'heading' in style_lower:
        try:
            num_str = ''.join(filter(str.isdigit, style_lower.replace('heading', '')))
            if num_str:
                level = int(num_str)
                if 1 <= level <= 6:
                    return level
        except:
            pass
    if '标题' in style_lower:
        try:
            num_str = ''.join(filter(str.isdigit, style_lower.replace('标题', '')))
            if num_str:
                level = int(num_str)
                if 1 <= level <= 6:
                    return level
        except:
            pass
    return 0

# 模拟 analyze 方法逻辑
styles_usage = defaultdict(int)
heading_styles = {}
potential_heading_styles = set()
style_numbering = defaultdict(dict)

for para in doc.paragraphs:
    text = para.text.strip()
    if not text:
        continue
    style_name = para.style.name if para.style else 'Normal'
    styles_usage[style_name] += 1
    level = _get_heading_level(style_name, text)
    
    print(f'段落：{text[:30]} | 样式：{style_name} | 层级：{level}')
    
    if level > 0:
        print(f'  -> 已识别为标题 L{level}')
        if style_name not in heading_styles:
            heading_styles[style_name] = {'is_heading': True, 'heading_level': level}
        continue
    
    # 检查编号模式
    for pattern, suggested_level in numbering_regex_patterns:
        if re.match(pattern, text):
            print(f'  -> 匹配编号模式 L{suggested_level}')
            potential_heading_styles.add(style_name)
            break

print(f'\n潜在标题样式：{potential_heading_styles}')
print(f'标题样式：{list(heading_styles.keys())}')

# 写入文件
with open('debug_output.txt', 'w', encoding='utf-8') as f:
    f.write(f'潜在标题样式：{potential_heading_styles}\n')
    f.write(f'标题样式：{list(heading_styles.keys())}\n')
