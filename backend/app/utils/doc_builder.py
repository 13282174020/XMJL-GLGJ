# -*- coding: utf-8 -*-
"""
文档渲染工具 - SKILL-007
DocBuilder 工具类，封装 Word 文档生成操作
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn


class DocBuilder:
    """文档构建器类"""
    
    # 默认样式配置
    DEFAULT_STYLES = {
        'page': {
            'width_cm': 21,
            'height_cm': 29.7,
            'top_margin_cm': 2.54,
            'bottom_margin_cm': 2.54,
            'left_margin_cm': 3.17,
            'right_margin_cm': 3.17
        },
        'styles': {
            'chapter_title': {
                'font': '黑体',
                'size_pt': 16,
                'bold': True,
                'alignment': 'center',
                'space_before_pt': 18,
                'space_after_pt': 12
            },
            'section_title': {
                'font': '黑体',
                'size_pt': 15,
                'bold': True,
                'alignment': 'left',
                'space_before_pt': 12,
                'space_after_pt': 6
            },
            'subsection_title': {
                'font': '黑体',
                'size_pt': 14,
                'bold': True,
                'alignment': 'left',
                'space_before_pt': 8,
                'space_after_pt': 4
            },
            'body_text': {
                'font': '仿宋',
                'size_pt': 12,
                'bold': False,
                'alignment': 'justify',
                'first_indent_chars': 2,
                'line_spacing': 1.5
            },
            'table_header': {
                'font': '黑体',
                'size_pt': 10.5,
                'bold': True,
                'alignment': 'center',
                'bg_color': 'D9E2F3'
            },
            'table_cell': {
                'font': '宋体',
                'size_pt': 10.5,
                'alignment': 'center'
            },
            'cover_title': {
                'font': '黑体',
                'size_pt': 36,
                'bold': True,
                'alignment': 'center'
            },
            'cover_subtitle': {
                'font': '黑体',
                'size_pt': 26,
                'bold': True,
                'alignment': 'center'
            }
        }
    }
    
    def __init__(self, template_path: Optional[str] = None, style_config: Optional[Dict] = None):
        """初始化文档构建器
        
        Args:
            template_path: Word 模板文件路径（可选）
            style_config: 样式配置字典（可选）
        """
        self.template_path = template_path
        self.style_config = style_config or self.DEFAULT_STYLES
        
        if template_path and os.path.exists(template_path):
            self.doc = Document(template_path)
        else:
            self.doc = Document()
        
        self._setup_styles()
    
    def _setup_styles(self) -> None:
        """设置文档样式"""
        style = self.doc.styles['Normal']
        body_style = self.style_config['styles']['body_text']
        
        style.font.name = body_style['font']
        style.font.size = Pt(body_style['size_pt'])
        style._element.rPr.rFonts.set(qn('w:eastAsia'), body_style['font'])
    
    def add_cover(self, project_info: Dict[str, Any]) -> None:
        """添加封面页
        
        Args:
            project_info: 项目信息字典
        """
        # 主标题
        project_name = project_info.get('name', '建设项目')
        title = self.doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.paragraph_format.space_before = Cm(5)
        title.paragraph_format.space_after = Cm(1)
        
        run = title.add_run(project_name)
        self._apply_style(run, self.style_config['styles']['cover_title'])
        
        # 副标题
        subtitle = self.doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.paragraph_format.space_before = Cm(1)
        subtitle.paragraph_format.space_after = Cm(3)
        
        run = subtitle.add_run('可行性研究报告')
        self._apply_style(run, self.style_config['styles']['cover_subtitle'])
        
        # 空白行
        for _ in range(5):
            self.doc.add_paragraph()
        
        # 建设单位
        builder = self.doc.add_paragraph()
        builder.alignment = WD_ALIGN_PARAGRAPH.CENTER
        builder.paragraph_format.space_before = Cm(0.5)
        builder.paragraph_format.space_after = Cm(0.5)
        run = builder.add_run(f"建设单位：{project_info.get('org_name', 'XX 单位')}")
        run.font.name = '楷体'
        run.font.size = Pt(16)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
        
        # 编制单位
        compiler = self.doc.add_paragraph()
        compiler.alignment = WD_ALIGN_PARAGRAPH.CENTER
        compiler.paragraph_format.space_before = Cm(0.5)
        compiler.paragraph_format.space_after = Cm(0.5)
        run = compiler.add_run("编制单位：XX 数字科技有限公司")
        run.font.name = '楷体'
        run.font.size = Pt(16)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
        
        # 日期
        date_para = self.doc.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        date_para.paragraph_format.space_before = Cm(0.5)
        date_para.paragraph_format.space_after = Cm(0.5)
        run = date_para.add_run(f'编制日期：{datetime.now().strftime("%Y 年 %m 月")}')
        run.font.name = '楷体'
        run.font.size = Pt(16)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
        
        self.add_page_break()
    
    def add_toc(self, chapters: List[Dict[str, Any]]) -> None:
        """添加目录页
        
        Args:
            chapters: 章节列表
        """
        self.add_chapter_title('目录')
        self.doc.add_paragraph()
        
        for chapter in chapters:
            # 章标题
            para = self.doc.add_paragraph()
            para.paragraph_format.left_indent = Cm(0)
            run = para.add_run(chapter.get('number', '') + ' ' + chapter.get('title', ''))
            run.font.name = '宋体'
            run.font.size = Pt(10.5)
            run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
            
            # 小节
            for subsection in chapter.get('subsections', []):
                para = self.doc.add_paragraph()
                para.paragraph_format.left_indent = Cm(0.74)
                run = para.add_run(subsection.get('number', '') + ' ' + subsection.get('title', ''))
                run.font.name = '宋体'
                run.font.size = Pt(10.5)
                run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        
        self.add_page_break()
    
    def add_chapter_title(self, title: str) -> None:
        """添加章标题
        
        Args:
            title: 章标题
        """
        heading = self.doc.add_heading(title, level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        for run in heading.runs:
            run.font.name = self.style_config['styles']['chapter_title']['font']
            run.font.size = Pt(self.style_config['styles']['chapter_title']['size_pt'])
            run.font.bold = self.style_config['styles']['chapter_title']['bold']
            run._element.rPr.rFonts.set(
                qn('w:eastAsia'),
                self.style_config['styles']['chapter_title']['font']
            )
        
        heading.paragraph_format.space_before = Cm(
            self.style_config['styles']['chapter_title']['space_before_pt'] / 72 * 2.54
        )
        heading.paragraph_format.space_after = Cm(
            self.style_config['styles']['chapter_title']['space_after_pt'] / 72 * 2.54
        )
    
    def add_section_title(self, title: str) -> None:
        """添加节标题
        
        Args:
            title: 节标题
        """
        heading = self.doc.add_heading(title, level=2)
        
        for run in heading.runs:
            run.font.name = self.style_config['styles']['section_title']['font']
            run.font.size = Pt(self.style_config['styles']['section_title']['size_pt'])
            run.font.bold = self.style_config['styles']['section_title']['bold']
            run._element.rPr.rFonts.set(
                qn('w:eastAsia'),
                self.style_config['styles']['section_title']['font']
            )
        
        heading.paragraph_format.space_before = Cm(
            self.style_config['styles']['section_title']['space_before_pt'] / 72 * 2.54
        )
        heading.paragraph_format.space_after = Cm(
            self.style_config['styles']['section_title']['space_after_pt'] / 72 * 2.54
        )
    
    def add_subsection_title(self, title: str) -> None:
        """添加小节标题
        
        Args:
            title: 小节标题
        """
        heading = self.doc.add_heading(title, level=3)
        
        for run in heading.runs:
            run.font.name = self.style_config['styles']['subsection_title']['font']
            run.font.size = Pt(self.style_config['styles']['subsection_title']['size_pt'])
            run.font.bold = self.style_config['styles']['subsection_title']['bold']
            run._element.rPr.rFonts.set(
                qn('w:eastAsia'),
                self.style_config['styles']['subsection_title']['font']
            )
    
    def add_body(self, text: str) -> None:
        """添加正文段落
        
        Args:
            text: 段落文本
        """
        if not text.strip():
            return
        
        para = self.doc.add_paragraph()
        run = para.add_run(text)
        
        body_style = self.style_config['styles']['body_text']
        run.font.name = body_style['font']
        run.font.size = Pt(body_style['size_pt'])
        run._element.rPr.rFonts.set(qn('w:eastAsia'), body_style['font'])
        
        # 首行缩进
        para.paragraph_format.first_line_indent = Cm(
            body_style.get('first_indent_chars', 2) * 0.37
        )
        # 行距
        para.paragraph_format.line_spacing = body_style.get('line_spacing', 1.5)
        para.paragraph_format.space_before = Cm(0)
        para.paragraph_format.space_after = Cm(0)
    
    def add_table(self, headers: List[str], rows: List[List[str]]) -> None:
        """添加表格
        
        Args:
            headers: 表头
            rows: 数据行
        """
        if not headers or not rows:
            return
        
        table = self.doc.add_table(rows=len(rows) + 1, cols=len(headers))
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        # 设置表头
        header_row = table.rows[0]
        for i, header in enumerate(headers):
            cell = header_row.cells[i]
            cell.text = header
            
            # 设置表头样式
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.name = self.style_config['styles']['table_header']['font']
                    run.font.size = Pt(self.style_config['styles']['table_header']['size_pt'])
                    run.font.bold = self.style_config['styles']['table_header']['bold']
                    run._element.rPr.rFonts.set(
                        qn('w:eastAsia'),
                        self.style_config['styles']['table_header']['font']
                    )
        
        # 设置数据行
        for i, row_data in enumerate(rows):
            row = table.rows[i + 1]
            for j, cell_text in enumerate(row_data):
                cell = row.cells[j]
                cell.text = cell_text
                
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in paragraph.runs:
                        run.font.name = self.style_config['styles']['table_cell']['font']
                        run.font.size = Pt(self.style_config['styles']['table_cell']['size_pt'])
                        run._element.rPr.rFonts.set(
                            qn('w:eastAsia'),
                            self.style_config['styles']['table_cell']['font']
                        )
    
    def add_page_break(self) -> None:
        """添加分页符"""
        self.doc.add_page_break()
    
    def _apply_style(self, run, style: Dict[str, Any]) -> None:
        """应用样式到 run
        
        Args:
            run: docx run 对象
            style: 样式配置
        """
        run.font.name = style['font']
        run.font.size = Pt(style['size_pt'])
        run.font.bold = style.get('bold', False)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), style['font'])
    
    def save(self, output_path: str) -> str:
        """保存文档
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            保存的文件路径
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        self.doc.save(output_path)
        return output_path
    
    def render_chapter(self, chapter_data: Dict[str, Any]) -> None:
        """渲染单个章节
        
        Args:
            chapter_data: 章节数据 JSON
        """
        chapter_number = chapter_data.get('chapter_number', '')
        chapter_title = chapter_data.get('chapter_title', '')
        
        # 添加章标题
        self.add_chapter_title(f"{chapter_number} {chapter_title}")
        
        # 渲染小节
        for subsection in chapter_data.get('subsections', []):
            self._render_subsection(subsection)
        
        self.add_page_break()
    
    def _render_subsection(self, subsection: Dict[str, Any]) -> None:
        """渲染小节
        
        Args:
            subsection: 小节数据
        """
        number = subsection.get('number', '')
        title = subsection.get('title', '')
        level = subsection.get('level', 2)
        
        # 添加标题
        if level == 2:
            self.add_section_title(f"{number} {title}")
        elif level == 3:
            self.add_subsection_title(f"{number} {title}")
        
        # 渲染内容
        content_type = subsection.get('type', 'text')
        
        if content_type in ('text', 'list', 'mixed'):
            for para in subsection.get('paragraphs', []):
                self.add_body(para)
        
        if content_type in ('table', 'mixed'):
            table_data = subsection.get('table_data')
            if table_data:
                headers = table_data.get('headers', [])
                rows = table_data.get('rows', [])
                self.add_table(headers, rows)
        
        # 递归渲染子节点
        for child in subsection.get('children', []):
            self._render_subsection(child)
    
    def render_document(self, json_data: Dict[str, Any]) -> None:
        """渲染完整文档
        
        Args:
            json_data: 完整文档 JSON 数据
        """
        # 封面
        project_info = json_data.get('project_info', {})
        self.add_cover(project_info)
        
        # 目录
        chapters = json_data.get('chapters', [])
        self.add_toc(chapters)
        
        # 正文
        for chapter in json_data.get('generated_chapters', []):
            self.render_chapter(chapter)


def create_doc_builder(template_path: Optional[str] = None, style_config: Optional[Dict] = None) -> DocBuilder:
    """创建 DocBuilder 实例的便捷函数"""
    return DocBuilder(template_path, style_config)


if __name__ == '__main__':
    # 测试代码
    builder = DocBuilder()
    
    # 测试封面
    builder.add_cover({
        'name': '测试项目',
        'org_name': '测试单位'
    })
    
    # 测试保存
    builder.save('test_output.docx')
    print("测试文档生成成功")
