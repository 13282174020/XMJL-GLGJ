# Word Document AI Generation Module
# Word 文档 AI 生成模块

"""
快速开始：
    from word_doc_module import TemplateScanner, StyleManager, AIChapterGenerator

    # 1. 扫描模板
    scanner = TemplateScanner()
    result = scanner.scan('template.docx')
    chapters = result['chapters']

    # 2. 生成章节内容
    generator = AIChapterGenerator(model_config)
    content = generator.generate(
        section_title='项目概况',
        requirement_text='...',
        template_text='...'
    )

    # 3. 生成 Word 文档
    manager = StyleManager()
    doc = manager.create_document()
    manager.add_heading(doc, '项目概况', level=1)
    manager.add_normal_paragraph(doc, content)
    doc.save('output.docx')
"""

from .template_scanner import TemplateScanner, scan_template_styles
from .style_manager import StyleManager
from .ai_engine import AIChapterGenerator, build_desc_field_prompt, build_info_field_prompt

__all__ = [
    'TemplateScanner',
    'StyleManager',
    'AIChapterGenerator',
    'scan_template_styles',
    'build_desc_field_prompt',
    'build_info_field_prompt',
]
