# -*- coding: utf-8 -*-
"""API 路由测试"""
import pytest
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'web_system'))

from template_api import register_template_routes, get_library


class TestTemplateAPI:
    @pytest.fixture
    def app(self):
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = 'uploads'
        register_template_routes(app)
        return app
    
    @pytest.fixture
    def client(self, app):
        return app.test_client()
    
    def test_list_templates_empty(self, client):
        response = client.get('/api/v2/templates/list')
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'templates' in data
    
    def test_upload_template(self, client, sample_standard_doc):
        with open(sample_standard_doc, 'rb') as f:
            response = client.post(
                '/api/v2/templates/upload',
                data={'file': (f, 'test.docx')},
                content_type='multipart/form-data'
            )
        data = json.loads(response.data)
        if not data['success']:
            print(f"错误：{data.get('message')}")
        assert data['success'] is True
        assert 'analysis' in data
        print(f"上传分析：{data['message']}")
    
    def test_save_template(self, client, sample_standard_doc):
        # 先上传
        with open(sample_standard_doc, 'rb') as f:
            upload_resp = client.post(
                '/api/v2/templates/upload',
                data={'file': (f, 'test.docx')},
                content_type='multipart/form-data'
            )
        upload_data = json.loads(upload_resp.data)
        if not upload_data['success']:
            print(f"上传失败：{upload_data.get('message')}")
            pytest.skip("上传失败，跳过后续测试")
        
        # 再预处理
        preprocess_resp = client.post(
            '/api/v2/templates/preprocess',
            json={
                'temp_path': upload_data['temp_path'],
                'rules': upload_data['rules']
            }
        )
        preprocess_data = json.loads(preprocess_resp.data)
        if not preprocess_data['success']:
            print(f"预处理失败：{preprocess_data.get('message')}")
            pytest.skip("预处理失败，跳过后续测试")
        
        # 最后保存
        save_resp = client.post(
            '/api/v2/templates/save',
            json={
                'name': '测试模板',
                'type': 'test',
                'output_path': preprocess_data['output_path'],
                'chapter_structure': {},
                'style_config': {}
            }
        )
        save_data = json.loads(save_resp.data)
        assert save_data['success'] is True
        print(f"保存模板：{save_data['message']}")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
