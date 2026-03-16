# -*- coding: utf-8 -*-
"""检查样式是否可链接到多级列表"""
from docx import Document

print('=' * 80)
print('检查 Heading 样式的 outlineLvl 属性（决定多级列表层级）')
print('=' * 80)

generated = Document(r'e:\Qwen\xmjl\web_system\outputs\test_cscswj2_processed.docx')

for style in generated.styles:
    if 'Heading' in style.name:
        # 检查样式是否定义了大纲级别
        outline_lvl = None
        try:
            # 尝试从 XML 中获取 outlineLvl
            pPr = style._element.pPr
            if pPr is not None:
                outlineLvl = pPr.outlineLvl
                if outlineLvl is not None:
                    outline_lvl = outlineLvl.val
        except:
            pass
        
        print(f'{style.name}: outlineLvl={outline_lvl}')
