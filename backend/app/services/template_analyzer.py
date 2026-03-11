# -*- coding: utf-8 -*-
"""
模板分析服务 - SKILL-003
分析模板文档的章节结构、样式信息
"""

import os
import re
import zipfile
from typing import Dict, List, Any, Optional
from docx import Document
from docx.oxml.ns import qn


class TemplateAnalyzer:
    """模板分析器类"""

    def __init__(self, template_path: str):
        """初始化模板分析器

        Args:
            template_path: 模板文档路径
        """
        self.template_path = template_path
        self.doc = None
        self.styles = {}  # 样式定义
        self.chapter_tree = []  # 章节结构树

        self._load_document()
        self._extract_styles()
        self._extract_chapter_structure()

    def _load_document(self) -> None:
        """加载 Word 文档"""
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"模板文件不存在：{self.template_path}")

        try:
            self.doc = Document(self.template_path)
        except Exception as e:
            raise Exception(f"无法读取 Word 文档：{str(e)}")

    def _extract_styles(self) -> None:
        """提取文档样式定义"""
        if not self.doc:
            return

        # 提取所有样式的定义
        for style in self.doc.styles:
            style_name = style.name
            style_info = {
                'name': style_name,
                'font_name': None,
                'font_size': None,
                'bold': False,
                'italic': False,
                'alignment': 'left',
                'space_before': 0,
                'space_after': 0,
                'line_spacing': 1.0,
                'first_indent': 0
            }

            # 提取字体信息
            if hasattr(style, 'font') and style.font:
                font = style.font
                if font.name:
                    style_info['font_name'] = font.name
                if font.size:
                    style_info['font_size'] = font.size.pt
                style_info['bold'] = font.bold if font.bold is not None else False
                style_info['italic'] = font.italic if font.italic is not None else False

            # 提取段落格式
            if hasattr(style, 'paragraph_format') and style.paragraph_format:
                pf = style.paragraph_format
                if hasattr(pf, 'alignment') and pf.alignment:
                    style_info['alignment'] = str(pf.alignment)
                if hasattr(pf, 'space_before') and pf.space_before:
                    style_info['space_before'] = pf.space_before.pt if pf.space_before else 0
                if hasattr(pf, 'space_after') and pf.space_after:
                    style_info['space_after'] = pf.space_after.pt if pf.space_after else 0
                if hasattr(pf, 'line_spacing') and pf.line_spacing:
                    style_info['line_spacing'] = pf.line_spacing
                if hasattr(pf, 'first_line_indent') and pf.first_line_indent:
                    style_info['first_indent'] = pf.first_line_indent.cm if pf.first_line_indent else 0

            self.styles[style_name] = style_info

    def _extract_chapter_structure(self) -> None:
        """提取章节结构树"""
        if not self.doc:
            return

        self.chapter_tree = []
        heading_stack = []  # 用栈来管理层级关系

        for para in self.doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            style_name = para.style.name if para.style else 'Normal'

            # 检测章节层级
            level = self._detect_heading_level(text, style_name)

            if level == 0:  # 正文，跳过
                continue

            # 创建当前节点
            node = {
                'level': level,
                'number': self._extract_number(text),
                'title': text,
                'style': style_name,
                'children': []
            }

            # 找到父节点：弹出栈中所有层级大于等于当前层级的节点
            while heading_stack and heading_stack[-1]['level'] >= level:
                heading_stack.pop()

            if heading_stack:
                # 添加到父节点的 children
                heading_stack[-1]['children'].append(node)
            else:
                # 没有父节点，作为根节点
                self.chapter_tree.append(node)

            # 当前节点入栈
            heading_stack.append(node)

    def _detect_heading_level(self, text: str, style_name: str) -> int:
        """检测标题层级

        Returns:
            1=章，2=节，3=小节，4=小小节，5=第 5 级，6=第 6 级，0=正文
        """
        # 检测章标题：第一章、第 1 章
        if re.match(r'^第 [一二三四五六七八九十\d]+ 章', text):
            return 1

        # 检测节标题：1.1、2.1 等（两位数字编号）
        if re.match(r'^\d+\.\d+$', text) or re.match(r'^\d+\.\d+\s', text):
            return 2

        # 检测小节标题：1.1.1、2.1.1 等（三位数字编号）
        if re.match(r'^\d+\.\d+\.\d+$', text) or re.match(r'^\d+\.\d+\.\d+\s', text):
            return 3

        # 检测小小节标题：1.1.1.1（四位数字编号）
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', text) or re.match(r'^\d+\.\d+\.\d+\.\d+\s', text):
            return 4

        # 检测第 5 级标题：1.1.1.1.1（五位数字编号）
        if re.match(r'^\d+\.\d+\.\d+\.\d+\.\d+$', text) or re.match(r'^\d+\.\d+\.\d+\.\d+\.\d+\s', text):
            return 5

        # 检测第 6 级标题：1.1.1.1.1.1（六位数字编号）
        if re.match(r'^\d+\.\d+\.\d+\.\d+\.\d+\.\d+$', text) or re.match(r'^\d+\.\d+\.\d+\.\d+\.\d+\.\d+\s', text):
            return 6

        # 检查样式名
        style_lower = style_name.lower()
        if 'heading 1' in style_lower or '标题 1' in style_lower or '章' in style_lower:
            return 1
        elif 'heading 2' in style_lower or '标题 2' in style_lower or '节' in style_lower:
            return 2
        elif 'heading 3' in style_lower or '标题 3' in style_lower or '小节' in style_lower:
            return 3
        elif 'heading 4' in style_lower or '标题 4' in style_lower:
            return 4
        elif 'heading 5' in style_lower or '标题 5' in style_lower:
            return 5
        elif 'heading 6' in style_lower or '标题 6' in style_lower:
            return 6

        return 0

    def _extract_number(self, text: str) -> str:
        """从标题中提取编号"""
        # 匹配第 X 章格式
        match = re.match(r'^(第 [一二三四五六七八九十\d]+ 章)', text)
        if match:
            return match.group(1)

        # 匹配数字编号格式
        match = re.match(r'^(\d+(?:\.\d+)*)', text)
        if match:
            return match.group(1)

        return ''

    def get_chapter_tree(self) -> List[Dict[str, Any]]:
        """获取章节结构树

        Returns:
            章节结构树
        """
        return self.chapter_tree

    def get_styles(self) -> Dict[str, Dict[str, Any]]:
        """获取样式定义

        Returns:
            样式字典
        """
        return self.styles

    def get_style_for_level(self, level: int) -> Optional[Dict[str, Any]]:
        """根据层级获取推荐样式

        Args:
            level: 标题层级 (1-6)

        Returns:
            样式配置
        """
        style_mapping = {
            1: ['Heading 1', '标题 1', '章标题', '1'],
            2: ['Heading 2', '标题 2', '节标题', '2'],
            3: ['Heading 3', '标题 3', '小节标题', '3'],
            4: ['Heading 4', '标题 4', '小小节标题', '4'],
            5: ['Heading 5', '标题 5', '5'],
            6: ['Heading 6', '标题 6', '6']
        }

        style_names = style_mapping.get(level, [])
        for name in style_names:
            if name in self.styles:
                return self.styles[name]

        # 返回默认样式
        return self._get_default_style(level)

    def _get_default_style(self, level: int) -> Dict[str, Any]:
        """获取默认样式配置"""
        defaults = {
            1: {
                'font_name': '黑体',
                'font_size': 22,
                'bold': True,
                'alignment': 'center',
                'space_before': 0,
                'space_after': 0
            },
            2: {
                'font_name': '黑体',
                'font_size': 16,
                'bold': True,
                'alignment': 'left',
                'space_before': 0.5,
                'space_after': 0
            },
            3: {
                'font_name': '黑体',
                'font_size': 14,
                'bold': True,
                'alignment': 'left',
                'space_before': 0.5,
                'space_after': 0
            },
            4: {
                'font_name': '黑体',
                'font_size': 12,
                'bold': False,
                'alignment': 'left',
                'space_before': 0,
                'space_after': 0
            },
            5: {
                'font_name': '宋体',
                'font_size': 10.5,
                'bold': False,
                'alignment': 'left',
                'space_before': 0,
                'space_after': 0
            },
            6: {
                'font_name': '宋体',
                'font_size': 10.5,
                'bold': False,
                'alignment': 'left',
                'space_before': 0,
                'space_after': 0
            }
        }
        return defaults.get(level, defaults[1])


def create_template_analyzer(template_path: str) -> TemplateAnalyzer:
    """创建模板分析器实例"""
    return TemplateAnalyzer(template_path)


if __name__ == '__main__':
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        analyzer = TemplateAnalyzer(sys.argv[1])
        print("章节结构:")
        print(analyzer.get_chapter_tree())
