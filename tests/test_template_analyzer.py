# -*- coding: utf-8 -*-
"""模板分析器测试"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'web_system'))

from template_analyzer import DocumentAnalyzer

class TestDocumentAnalyzer:
    def test_analyze_standard(self, sample_standard_doc):
        analyzer = DocumentAnalyzer()
        report = analyzer.analyze(str(sample_standard_doc))
        assert report.total_paragraphs > 0
        assert len(report.heading_styles) > 0
        print(f"标准文档：{len(report.heading_styles)} 种样式")
    
    def test_analyze_nonstandard(self, sample_nonstandard_doc):
        analyzer = DocumentAnalyzer()
        report = analyzer.analyze(str(sample_nonstandard_doc))
        assert len(report.potential_heading_styles) > 0
        rules = report.generate_mapping_rules()
        assert len(rules) > 0
        print(f"非标准文档：{len(rules)} 条规则")
    
    def test_get_heading_level(self):
        analyzer = DocumentAnalyzer()
        assert analyzer._get_heading_level('Heading 1') == 1
        assert analyzer._get_heading_level('Normal') == 0

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
