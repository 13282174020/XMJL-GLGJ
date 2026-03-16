# -*- coding: utf-8 -*-
"""对比模板和生成文档的样式定义"""
from docx import Document

print('=' * 80)
print('原始模板的样式')
print('=' * 80)

template = Document(r'e:\Qwen\xmjl\web_system\cscswj2.docx')
template_styles = {}
for style in template.styles:
    if 'Heading' in style.name:
        template_styles[style.name] = {
            'base_style': style.base_style.name if style.base_style else None,
            'next_style': style.next_style.name if style.next_style else None,
        }
        print(f'{style.name}: base={style.base_style.name if style.base_style else "None"}, next={style.next_style.name if style.next_style else "None"}')

print()
print('=' * 80)
print('生成文档的样式')
print('=' * 80)

generated = Document(r'e:\Qwen\xmjl\web_system\outputs\test_cscswj2_processed.docx')
generated_styles = {}
for style in generated.styles:
    if 'Heading' in style.name:
        generated_styles[style.name] = {
            'base_style': style.base_style.name if style.base_style else None,
            'next_style': style.next_style.name if style.next_style else None,
        }
        print(f'{style.name}: base={style.base_style.name if style.base_style else "None"}, next={style.next_style.name if style.next_style else "None"}')

print()
print('=' * 80)
print('对比结果')
print('=' * 80)

all_styles = set(template_styles.keys()) | set(generated_styles.keys())
for style in sorted(all_styles):
    t = template_styles.get(style, {})
    g = generated_styles.get(style, {})
    if t == g:
        print(f'✓ {style}: 相同')
    else:
        print(f'✗ {style}: 模板={t}, 生成={g}')
