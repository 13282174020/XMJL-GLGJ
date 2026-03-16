from docx import Document
import re

doc_path = '新模板_1773310314036 (1).docx'
doc = Document(doc_path)

print('=== Body Text First Indent 2 样式的段落 ===\n')

count = 0
for i, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    style_name = p.style.name if p.style else 'None'
    
    if style_name == 'Body Text First Indent 2':
        count += 1
        if count <= 20:
            patterns = [
                (r'^(\d+)\.(\d+)', '2 级'),
                (r'^(\d+)\.(\d+)\.(\d+)', '3 级'),
                (r'^(\d+)', '1 级'),
            ]
            matched = None
            for pattern, level_name in patterns:
                if re.match(pattern, text):
                    matched = level_name
                    break
            
            print(f'{count:3d}: [{matched or "无编号":8s}] | {text[:60]}')

print(f'\n总计：{count} 个段落')
