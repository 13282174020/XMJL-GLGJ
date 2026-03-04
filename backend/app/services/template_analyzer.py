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
        current_chapter = None
        current_section = None
        current_subsection = None
        
        for para in self.doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            style_name = para.style.name if para.style else 'Normal'
            
            # 检测章节层级
            level = self._detect_heading_level(text, style_name)
            
            if level == 1:  # 章
                current_chapter = {
                    'level': 1,
                    'number': self._extract_number(text),
                    'title': text,
                    'style': style_name,
                    'subsections': []
                }
                self.chapter_tree.append(current_chapter)
                current_section = None
                current_subsection = None
                
            elif level == 2 and current_chapter:  # 节
                current_section = {
                    'level': 2,
                    'number': self._extract_number(text),
                    'title': text,
                    'style': style_name,
                    'children': []
                }
                current_chapter['subsections'].append(current_section)
                current_subsection = None
                
            elif level == 3 and current_section:  # 小节
                current_subsection = {
                    'level': 3,
                    'number': self._extract_number(text),
                    'title': text,
                    'style': style_name,
                    'children': []
                }
                current_section['children'].append(current_subsection)
                
            elif level == 4 and current_subsection:  # 小小节
                current_subsection['children'].append({
                    'level': 4,
                    'number': self._extract_number(text),
                    'title': text,
                    'style': style_name
                })
    
    def _detect_heading_level(self, text: str, style_name: str) -> int:
        """检测标题层级
        
        Returns:
            1=章，2=节，3=小节，4=小小节，0=正文
        """
        # 检测章标题：第一章、第 1 章
        if re.match(r'^第 [一二三四五六七八九十\d]+章', text):
            return 1
        
        # 检测节标题：1.1、2.1 等
        if re.match(r'^\d+\.\d+$', text) or re.match(r'^\d+\.\d+\s', text):
            match = re.match(r'^(\d+)\.(\d+)', text)
            if match:
                # 检查是否有第三级
                if re.match(r'^\d+\.\d+\.\d+', text):
                    return 3
                return 2
        
        # 检测小节标题：1.1.1、2.1.1 等
        if re.match(r'^\d+\.\d+\.\d+$', text) or re.match(r'^\d+\.\d+\.\d+\s', text):
            return 3
        
        # 检测小小节标题：1.1.1.1
        if re.match(r'^\d+\.\d+\.\d+\.\d+', text):
            return 4
        
        # 检查样式名
        style_lower = style_name.lower()
        if 'heading 1' in style_lower or '标题 1' in style_lower or '章' in style_lower:
            return 1
        elif 'heading 2' in style_lower or '标题 2' in style_lower or '节' in style_lower:
            return 2
        elif 'heading 3' in style_lower or '标题 3' in style_lower or '小节' in style_lower:
            return 3
        
        return 0
    
    def _extract_number(self, text: str) -> str:
        """从标题中提取编号"""
        # 匹配第 X 章格式
        match = re.match(r'^(第 [一二三四五六七八九十\d]+章)', text)
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
            level: 标题层级 (1-4)
            
        Returns:
            样式配置
        """
        style_mapping = {
            1: ['Heading 1', '标题 1', '章标题', '1'],
            2: ['Heading 2', '标题 2', '节标题', '2'],
            3: ['Heading 3', '标题 3', '小节标题', '3'],
            4: ['Heading 4', '标题 4', '小小节标题', '4']
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
                'space_before': 18,
                'space_after': 12
            },
            2: {
                'font_name': '黑体',
                'font_size': 16,
                'bold': True,
                'alignment': 'left',
                'space_before': 12,
                'space_after': 6
            },
            3: {
                'font_name': '黑体',
                'font_size': 14,
                'bold': True,
                'alignment': 'left',
                'space_before': 8,
                'space_after': 4
            },
            4: {
                'font_name': '仿宋',
                'font_size': 10.5,
                'bold': True,
                'alignment': 'left',
                'space_before': 0,
                'space_after': 0,
                'first_indent': 0.74
            }
        }
        return defaults.get(level, defaults[4])
    
    def get_full_structure(self) -> Dict[str, Any]:
        """获取完整的模板结构信息
        
        Returns:
            包含章节树和样式的完整结构
        """
        return {
            'chapter_tree': self.chapter_tree,
            'styles': self.styles,
            'total_chapters': len(self.chapter_tree),
            'total_sections': sum(len(ch.get('subsections', [])) for ch in self.chapter_tree)
        }
    
    def print_structure(self) -> None:
        """打印章节结构（用于调试）"""
        print(f"\n{'='*60}")
        print(f"模板：{self.template_path}")
        print(f"{'='*60}")
        print(f"章节数：{len(self.chapter_tree)}")
        
        for chapter in self.chapter_tree:
            print(f"\n{chapter['title']} [样式：{chapter['style']}]")
            for section in chapter.get('subsections', []):
                indent = "  "
                print(f"{indent}{section['title']} [样式：{section['style']}]")
                for child in section.get('children', []):
                    print(f"  {indent}{child['title']} [样式：{child['style']}]")


def analyze_template(template_path: str) -> Dict[str, Any]:
    """分析模板文档的便捷函数
    
    Args:
        template_path: 模板文件路径
        
    Returns:
        模板结构信息
    """
    analyzer = TemplateAnalyzer(template_path)
    return analyzer.get_full_structure()


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        analyzer = TemplateAnalyzer(sys.argv[1])
        analyzer.print_structure()
        
        print(f"\n样式列表:")
        for name, style in analyzer.get_styles().items():
            print(f"  {name}: 字体={style.get('font_name')}, 大小={style.get('font_size')}pt")
