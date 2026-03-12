# -*- coding: utf-8 -*-
"""模板预处理引擎模块"""
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict
from docx import Document


@dataclass
class PreprocessResult:
    success: bool
    output_path: Optional[str]
    message: str
    stats: Dict[str, int]
    
    def to_dict(self):
        return {'success': self.success, 'output_path': self.output_path, 
                'message': self.message, 'stats': self.stats}


class TemplatePreprocessor:
    def __init__(self):
        self.standard_styles = ['Heading 1', 'Heading 2', 'Heading 3', 
                                'Heading 4', 'Heading 5', 'Heading 6', 'Normal']
    
    def preprocess(self, input_path: str, output_path: str, 
                   rules: List[dict]) -> PreprocessResult:
        try:
            doc = Document(input_path)
            stats = {}
            
            compiled_rules = []
            for rule in rules:
                compiled_rule = rule.copy()
                if rule.get('pattern'):
                    try:
                        compiled_rule['compiled_pattern'] = re.compile(rule['pattern'])
                    except re.error as e:
                        return PreprocessResult(False, None, f'正则错误：{e}', {})
                compiled_rules.append(compiled_rule)
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                current_style = para.style.name if para.style else 'Normal'
                new_style = self._apply_rules(current_style, text, compiled_rules)
                
                if new_style and new_style != current_style:
                    para.style = new_style
                    key = f'{current_style}->{new_style}'
                    stats[key] = stats.get(key, 0) + 1
                else:
                    stats['unchanged'] = stats.get('unchanged', 0) + 1
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path))
            
            total = sum(v for k, v in stats.items() if k != 'unchanged')
            return PreprocessResult(True, str(output_path), 
                                   f'处理完成，{total} 个段落已转换', stats)
        except Exception as e:
            return PreprocessResult(False, None, f'处理失败：{e}', {})
    
    def _apply_rules(self, style_name: str, text: str, rules: List[dict]) -> Optional[str]:
        for rule in rules:
            if rule['source_style'] != style_name:
                continue
            if rule.get('compiled_pattern'):
                if rule['compiled_pattern'].match(text):
                    return rule['target_style']
            elif rule.get('pattern') is None:
                return rule['target_style']
        return None
    
    def preprocess_with_analysis(self, input_path: str, output_path: str) -> PreprocessResult:
        from template_analyzer import DocumentAnalyzer
        analyzer = DocumentAnalyzer()
        report = analyzer.analyze(input_path)
        rules = report.generate_mapping_rules()
        return self.preprocess(input_path, output_path, rules)


def preprocess_template(input_path: str, output_path: str, 
                       rules: List[dict]) -> PreprocessResult:
    preprocessor = TemplatePreprocessor()
    return preprocessor.preprocess(input_path, output_path, rules)
