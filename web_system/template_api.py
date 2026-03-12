# -*- coding: utf-8 -*-
"""模板管理 API 路由模块"""
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import os
import uuid
from datetime import datetime

# 创建蓝图
template_bp = Blueprint('template_api', __name__, url_prefix='/api/v2/templates')

# 模板库实例（单例）
_library = None
_analyzer = None
_preprocessor = None


def get_library():
    global _library
    if _library is None:
        from template_library import TemplateLibrary
        _library = TemplateLibrary('templates')
    return _library


def get_analyzer():
    global _analyzer
    if _analyzer is None:
        from template_analyzer import DocumentAnalyzer
        _analyzer = DocumentAnalyzer()
    return _analyzer


def get_preprocessor():
    global _preprocessor
    if _preprocessor is None:
        from template_preprocessor import TemplatePreprocessor
        _preprocessor = TemplatePreprocessor()
    return _preprocessor


@template_bp.route('/list', methods=['GET'])
def list_templates():
    """获取模板列表"""
    try:
        library = get_library()
        templates = library.get_all_templates()
        
        return jsonify({
            'success': True,
            'templates': [
                {
                    'id': t.id,
                    'name': t.name,
                    'type': t.type,
                    'created_at': t.created_at,
                    'is_default': t.is_default
                } for t in templates
            ]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@template_bp.route('/<template_id>', methods=['GET'])
def get_template(template_id):
    """获取模板详情"""
    try:
        library = get_library()
        template = library.get_template(template_id)
        
        if not template:
            return jsonify({'success': False, 'message': '模板不存在'}), 404
        
        return jsonify({
            'success': True,
            'template': template.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@template_bp.route('/upload', methods=['POST'])
def upload_template():
    """上传新模板"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '未选择文件'}), 400
        
        # 保存临时文件
        temp_dir = Path('uploads') / 'templates' / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f'{uuid.uuid4().hex}.docx'
        file.save(str(temp_path))
        
        # 分析文档
        analyzer = get_analyzer()
        report = analyzer.analyze(str(temp_path))
        
        # 生成映射规则
        rules = report.generate_mapping_rules()
        
        return jsonify({
            'success': True,
            'message': f'上传成功，检测到 {len(report.heading_styles)} 种样式',
            'analysis': report.to_dict(),
            'rules': rules,
            'temp_path': str(temp_path)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@template_bp.route('/preprocess', methods=['POST'])
def preprocess_template():
    """预处理模板"""
    try:
        data = request.json
        temp_path = data.get('temp_path')
        rules = data.get('rules', [])
        
        if not temp_path:
            return jsonify({'success': False, 'message': '请指定临时文件路径'}), 400
        
        # 预处理
        preprocessor = get_preprocessor()
        output_dir = Path('uploads') / 'templates' / 'processed'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{uuid.uuid4().hex}.docx'
        
        result = preprocessor.preprocess(temp_path, str(output_path), rules)
        
        if result.success:
            return jsonify({
                'success': True,
                'message': result.message,
                'stats': result.stats,
                'output_path': result.output_path
            })
        else:
            return jsonify({'success': False, 'message': result.message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@template_bp.route('/save', methods=['POST'])
def save_template():
    """保存模板到库"""
    try:
        data = request.json
        name = data.get('name', '未命名模板')
        template_type = data.get('type', 'custom')
        output_path = data.get('output_path')
        chapter_structure = data.get('chapter_structure', {})
        style_config = data.get('style_config', {})
        
        if not output_path:
            return jsonify({'success': False, 'message': '请指定文件路径'}), 400
        
        # 添加到模板库
        library = get_library()
        info = library.add_template(
            name=name,
            file_path=output_path,
            template_type=template_type,
            chapter_structure=chapter_structure,
            style_config=style_config
        )
        
        return jsonify({
            'success': True,
            'message': '模板已保存到模板库',
            'template': info.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@template_bp.route('/<template_id>/download', methods=['GET'])
def download_template(template_id):
    """下载模板"""
    try:
        library = get_library()
        template = library.get_template(template_id)
        
        if not template:
            return jsonify({'success': False, 'message': '模板不存在'}), 404
        
        file_path = Path(template.file_path)
        if not file_path.exists():
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=f'{template.name}.docx'
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@template_bp.route('/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    """删除模板"""
    try:
        library = get_library()
        
        if library.delete_template(template_id):
            return jsonify({'success': True, 'message': '模板已删除'})
        else:
            return jsonify({'success': False, 'message': '模板不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


def register_template_routes(app):
    """注册模板路由到 Flask 应用"""
    app.register_blueprint(template_bp)
