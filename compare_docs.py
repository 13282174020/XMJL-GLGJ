# -*- coding: utf-8 -*-
"""对比两个文档的目录结构"""
from docx import Document
import re

def extract_headings(doc_path):
    """提取文档中的标题"""
    doc = Document(doc_path)
    headings = []
    
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue
        style_name = para.style.name if para.style else 'Normal'
        
        # 检查是否是标题样式
        style_lower = style_name.lower()
        is_heading = 'heading' in style_lower or '标题' in style_lower
        
        # 检查是否包含编号
        numbering_match = re.match(r'^(\d+(?:\.\d+)*)', text)
        
        if is_heading or numbering_match:
            headings.append({
                'index': i,
                'style': style_name,
                'text': text[:80],
                'is_heading': is_heading,
                'has_numbering': numbering_match is not None
            })
    
    return headings

print('=' * 80)
print('文档 1: 03-临平区数字慈善系统建设方案模板.docx')
print('=' * 80)

template_headings = extract_headings('03-临平区数字慈善系统建设方案模板.docx')
print(f'\n共找到 {len(template_headings)} 个标题/编号段落')
print('\n前 50 个标题:')
for h in template_headings[:50]:
    flag = ''
    if h['is_heading']:
        flag += '[H]'
    if h['has_numbering']:
        flag += '[N]'
    print(f"  {h['index']:4d}. {flag:4s} [{h['style']}] {h['text']}")

if len(template_headings) > 50:
    print(f'  ... 还有 {len(template_headings) - 50} 个标题')

# 统计样式分布
style_count = {}
for h in template_headings:
    style_count[h['style']] = style_count.get(h['style'], 0) + 1

print('\n标题样式分布:')
for style, count in sorted(style_count.items(), key=lambda x: -x[1]):
    print(f'  {style}: {count} 个')

print('\n' + '=' * 80)
print('文档 2: 新模板 2_1773646675212.docx')
print('=' * 80)

generated_headings = extract_headings('新模板 2_1773646675212.docx')
print(f'\n共找到 {len(generated_headings)} 个标题/编号段落')
print('\n前 50 个标题:')
for h in generated_headings[:50]:
    flag = ''
    if h['is_heading']:
        flag += '[H]'
    if h['has_numbering']:
        flag += '[N]'
    print(f"  {h['index']:4d}. {flag:4s} [{h['style']}] {h['text']}")

if len(generated_headings) > 50:
    print(f'  ... 还有 {len(generated_headings) - 50} 个标题')

# 统计样式分布
style_count2 = {}
for h in generated_headings:
    style_count2[h['style']] = style_count2.get(h['style'], 0) + 1

print('\n标题样式分布:')
for style, count in sorted(style_count2.items(), key=lambda x: -x[1]):
    print(f'  {style}: {count} 个')

print('\n' + '=' * 80)
print('对比分析')
print('=' * 80)
print(f'模板文档标题数：{len(template_headings)}')
print(f'生成文档标题数：{len(generated_headings)}')
print(f'差异：{len(template_headings) - len(generated_headings)}')

# 对比样式分布
print('\n样式分布对比:')
all_styles = set(style_count.keys()) | set(style_count2.keys())
for style in sorted(all_styles):
    c1 = style_count.get(style, 0)
    c2 = style_count2.get(style, 0)
    diff = c2 - c1
    if diff != 0:
        print(f'  {style}: 模板={c1}, 生成={c2}, 差异={diff:+d}')
    else:
        print(f'  {style}: {c1} (相同)')
