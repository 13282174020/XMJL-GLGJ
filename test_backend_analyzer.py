# -*- coding: utf-8 -*-
"""测试 backend 的模板分析器"""
import sys
sys.path.insert(0, 'backend')

from app.services.template_analyzer import TemplateAnalyzer

# 分析模板
analyzer = TemplateAnalyzer(r'e:\Qwen\xmjl\03-临平区数字慈善系统建设方案模板.docx')

print(f'章节树节点数：{len(analyzer.chapter_tree)}')
print(f'\n章节结构:')
for chapter in analyzer.chapter_tree:
    print(f'  L{chapter["level"]} [{chapter["style"]}] {chapter["title"]}')
    for section in chapter.get('children', []):
        print(f'    L{section["level"]} [{section["style"]}] {section["title"]}')
        for subsection in section.get('children', []):
            print(f'      L{subsection["level"]} [{subsection["style"]}] {subsection["title"]}')

print(f'\n样式定义数：{len(analyzer.styles)}')
print(f'\n部分样式:')
for style_name in ['Heading 1', 'Heading 2', 'Body Text First Indent 2', 'Normal'][:4]:
    if style_name in analyzer.styles:
        print(f'  {style_name}: {analyzer.styles[style_name]}')
