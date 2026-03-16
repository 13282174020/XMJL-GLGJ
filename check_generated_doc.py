# -*- coding: utf-8 -*-
"""检查生成文档的标题层级问题"""
from docx import Document

def check_heading_levels(doc_path):
    """检查标题层级"""
    doc = Document(doc_path)
    
    print(f'检查文档：{doc_path}')
    print('=' * 80)
    
    issues = []
    
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue
        style_name = para.style.name if para.style else 'Normal'
        
        # 检查 2 级和 3 级标题
        import re
        is_l2 = re.match(r'^\d+\.\d+$', text) or re.match(r'^\d+\.\d+\s', text)
        is_l3 = re.match(r'^\d+\.\d+\.\d+$', text) or re.match(r'^\d+\.\d+\.\d+\s', text)
        
        if is_l2 or is_l3:
            expected_level = 2 if is_l2 else 3
            expected_style = 'Body Text First Indent 2'  # 模板中的样式
            
            # 检查样式是否正确
            if style_name != expected_style:
                issues.append({
                    'index': i,
                    'text': text[:50],
                    'expected_style': expected_style,
                    'actual_style': style_name,
                    'expected_level': expected_level
                })
                print(f'段落 {i}: [{style_name}] 应该是 [{expected_style}] - {text[:50]}')
    
    print(f'\n共发现 {len(issues)} 个样式不正确的标题')
    return issues

# 检查生成的文档
issues = check_heading_levels(r'e:\Qwen\xmjl\新模板 2_1773646675212.docx')

# 统计问题类型
style_issues = {}
for issue in issues:
    style = issue['actual_style']
    style_issues[style] = style_issues.get(style, 0) + 1

print('\n样式问题统计:')
for style, count in sorted(style_issues.items(), key=lambda x: -x[1]):
    print(f'  {style}: {count} 个')
