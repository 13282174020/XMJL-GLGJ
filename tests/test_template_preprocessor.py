# -*- coding: utf-8 -*-
"""预处理引擎测试"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'web_system'))

from template_preprocessor import TemplatePreprocessor, preprocess_template


class TestTemplatePreprocessor:
    def test_preprocess_with_rules(self, sample_nonstandard_doc, output_dir):
        analyzer = __import__('template_analyzer', fromlist=['DocumentAnalyzer'])
        analyzer_instance = analyzer.DocumentAnalyzer()
        report = analyzer_instance.analyze(str(sample_nonstandard_doc))
        rules = report.generate_mapping_rules()
        
        preprocessor = TemplatePreprocessor()
        output_path = output_dir / 'processed.docx'
        result = preprocessor.preprocess(str(sample_nonstandard_doc), str(output_path), rules)
        
        assert result.success is True
        assert output_path.exists()
        print(f"预处理成功：{result.message}")
        print(f"统计：{result.stats}")
    
    def test_preprocess_with_analysis(self, sample_nonstandard_doc, output_dir):
        preprocessor = TemplatePreprocessor()
        output_path = output_dir / 'processed_auto.docx'
        result = preprocessor.preprocess_with_analysis(str(sample_nonstandard_doc), str(output_path))
        
        assert result.success is True
        assert output_path.exists()
        print(f"自动预处理成功：{result.message}")
    
    def test_preprocess_standard_doc(self, sample_standard_doc, output_dir):
        preprocessor = TemplatePreprocessor()
        output_path = output_dir / 'processed_standard.docx'
        
        analyzer = __import__('template_analyzer', fromlist=['DocumentAnalyzer'])
        report = analyzer.DocumentAnalyzer().analyze(str(sample_standard_doc))
        rules = report.generate_mapping_rules()
        
        result = preprocessor.preprocess(str(sample_standard_doc), str(output_path), rules)
        
        assert result.success is True
        print(f"标准文档预处理：{result.message}")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
