# -*- coding: utf-8 -*-
"""模板文档分析器模块"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set
from collections import defaultdict


@dataclass
class NumberingPattern:
    pattern: str
    suggested_level: int
    count: int = 0
    example_texts: List[str] = field(default_factory=list)


@dataclass
class StyleAnalysis:
    style_name: str
    total_count: int = 0
    is_heading: bool = False
    heading_level: int = 0
    numbering_patterns: Dict[str, NumberingPattern] = field(default_factory=dict)


@dataclass
class AnalysisReport:
    file_path: str
    total_paragraphs: int = 0
    styles_usage: Dict[str, int] = field(default_factory=dict)
    heading_styles: Dict[str, StyleAnalysis] = field(default_factory=dict)
    potential_heading_styles: List[str] = field(default_factory=list)
    
    def generate_mapping_rules(self) -> List[dict]:
        rules = []
        for style_name, analysis in self.heading_styles.items():
            if analysis.is_heading and analysis.heading_level > 0:
                rules.append({
                    'source_style': style_name,
                    'pattern': None,
                    'target_style': f'Heading {analysis.heading_level}',
                    'rule_type': 'heading'
                })
        for style_name in self.potential_heading_styles:
            if style_name in self.heading_styles:
                continue
            analysis = self.heading_styles.get(style_name)
            if analysis and analysis.numbering_patterns:
                for pattern_str, pattern_info in analysis.numbering_patterns.items():
                    rules.append({
                        'source_style': style_name,
                        'pattern': pattern_str,
                        'target_style': f'Heading {pattern_info.suggested_level}',
                        'rule_type': 'numbering'
                    })
        return rules


class DocumentAnalyzer:
    def __init__(self):
        self.numbering_regex_patterns = [
            (r'^(\d+)\.(\d+)\.(\d+)\.(\d+)', 4),
            (r'^(\d+)\.(\d+)\.(\d+)', 3),
            (r'^(\d+)\.(\d+)', 2),
            (r'^(\d+)', 1),
        ]
    
    def analyze(self, file_path: str) -> AnalysisReport:
        from docx import Document
        doc = Document(file_path)
        styles_usage = defaultdict(int)
        heading_styles = {}
        potential_heading_styles = set()
        style_numbering = defaultdict(dict)
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style_name = para.style.name if para.style else 'Normal'
            styles_usage[style_name] += 1
            level = self._get_heading_level(style_name, text)
            
            if level > 0:
                if style_name not in heading_styles:
                    heading_styles[style_name] = StyleAnalysis(
                        style_name=style_name, is_heading=True, heading_level=level)
                heading_styles[style_name].total_count += 1
            else:
                for pattern, suggested_level in self.numbering_regex_patterns:
                    if re.match(pattern, text):
                        potential_heading_styles.add(style_name)
                        if pattern not in style_numbering[style_name]:
                            style_numbering[style_name][pattern] = NumberingPattern(
                                pattern=pattern, suggested_level=suggested_level)
                        pattern_info = style_numbering[style_name][pattern]
                        pattern_info.count += 1
                        if len(pattern_info.example_texts) < 3:
                            pattern_info.example_texts.append(text[:50])
                        break
        
        for style_name in potential_heading_styles:
            if style_name not in heading_styles:
                heading_styles[style_name] = StyleAnalysis(
                    style_name=style_name, is_heading=False, heading_level=0,
                    total_count=styles_usage.get(style_name, 0))
            heading_styles[style_name].numbering_patterns = style_numbering.get(style_name, {})
        
        return AnalysisReport(
            file_path=file_path, total_paragraphs=len(doc.paragraphs),
            styles_usage=dict(styles_usage), heading_styles=heading_styles,
            potential_heading_styles=list(potential_heading_styles))
    
    def _get_heading_level(self, style_name: str, text: str = '') -> int:
        if not style_name:
            return 0
        style_lower = style_name.lower()
        if 'heading' in style_lower:
            try:
                num_str = ''.join(filter(str.isdigit, style_lower.replace('heading', '')))
                if num_str:
                    level = int(num_str)
                    if 1 <= level <= 6:
                        return level
            except:
                pass
        if '标题' in style_lower:
            try:
                num_str = ''.join(filter(str.isdigit, style_lower.replace('标题', '')))
                if num_str:
                    level = int(num_str)
                    if 1 <= level <= 6:
                        return level
            except:
                pass
        return 0
