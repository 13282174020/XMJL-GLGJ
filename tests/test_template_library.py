# -*- coding: utf-8 -*-
"""模板库管理测试"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'web_system'))

from template_library import TemplateLibrary, TemplateInfo


class TestTemplateLibrary:
    @pytest.fixture
    def library(self, tmp_path):
        lib = TemplateLibrary(str(tmp_path / 'templates'))
        return lib
    
    def test_add_template(self, library, sample_standard_doc):
        info = library.add_template(
            name='测试模板',
            file_path=str(sample_standard_doc),
            template_type='test',
            chapter_structure={'chapters': []},
            style_config={}
        )
        
        assert info.id.startswith('template_')
        assert info.name == '测试模板'
        assert Path(info.file_path).exists()
        print(f"添加模板：{info.name}, ID: {info.id}")
    
    def test_get_all_templates(self, library, sample_standard_doc):
        library.add_template('模板 1', str(sample_standard_doc), 'test', {}, {})
        library.add_template('模板 2', str(sample_standard_doc), 'test', {}, {})
        
        templates = library.get_all_templates()
        assert len(templates) == 2
        print(f"模板库中有 {len(templates)} 个模板")
    
    def test_get_template(self, library, sample_standard_doc):
        info = library.add_template('测试', str(sample_standard_doc), 'test', {}, {})
        
        retrieved = library.get_template(info.id)
        assert retrieved is not None
        assert retrieved.name == '测试'
    
    def test_delete_template(self, library, sample_standard_doc):
        info = library.add_template('测试', str(sample_standard_doc), 'test', {}, {})
        
        assert library.delete_template(info.id) is True
        assert library.get_template(info.id) is None
    
    def test_download_template(self, library, sample_standard_doc, tmp_path):
        info = library.add_template('测试', str(sample_standard_doc), 'test', {}, {})
        
        output_path = tmp_path / 'downloaded.docx'
        assert library.download_template(info.id, str(output_path)) is True
        assert output_path.exists()
        print(f"下载模板到：{output_path}")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
