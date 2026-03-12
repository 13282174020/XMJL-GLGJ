# -*- coding: utf-8 -*-
"""集成测试"""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'web_system'))

from template_analyzer import DocumentAnalyzer
from template_preprocessor import TemplatePreprocessor
from template_library import TemplateLibrary

class TestIntegration:
    def test_full_workflow(self, sample_nonstandard_doc, tmp_path):
        # 1. 分析
        analyzer = DocumentAnalyzer()
        report = analyzer.analyze(str(sample_nonstandard_doc))
        assert report.total_paragraphs > 0
        print(f"分析：{report.total_paragraphs}段落")
        
        # 2. 规则
        rules = report.generate_mapping_rules()
        assert len(rules) > 0
        print(f"规则：{len(rules)}条")
        
        # 3. 预处理
        preprocessor = TemplatePreprocessor()
        output_path = tmp_path / 'processed.docx'
        result = preprocessor.preprocess(str(sample_nonstandard_doc), str(output_path), rules)
        assert result.success
        print(f"预处理：{result.message}")
        
        # 4. 保存
        library = TemplateLibrary(str(tmp_path / 'templates'))
        info = library.add_template('测试', str(output_path), 'test', {}, {})
        assert info.id.startswith('template_')
        print(f"保存：{info.name}")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
