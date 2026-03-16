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
    """上传新模板 - 分析文档并提取目录结构"""
    import logging
    import os
    import io
    from docx import Document
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '未选择文件'}), 400

        logging.info('=' * 80)
        logging.info('[API] 开始上传模板')
        logging.info(f'[API] 文件名：{file.filename}')

        # 保存到临时文件
        base_dir = os.path.dirname(os.path.abspath(__file__))
        temp_dir = os.path.join(base_dir, 'uploads', 'templates', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_filename = f'{uuid.uuid4().hex}.docx'
        temp_path = os.path.join(temp_dir, temp_filename)
        
        # 读取文件内容
        file_content = file.read()
        logging.info(f'[API] 读取文件内容：{len(file_content)} 字节')
        
        # 使用二进制写入
        with open(temp_path, 'wb') as f:
            f.write(file_content)
        logging.info(f'[API] 文件已写入磁盘')
        
        # 验证写入的文件
        file_size = os.path.getsize(temp_path)
        logging.info(f'[API] 临时文件已保存：{temp_path} ({file_size} 字节)')
        
        # 读取文件头检查格式
        with open(temp_path, 'rb') as f:
            header = f.read(4)
            logging.info(f'[API] 文件头：{header.hex()} (应为 504B0304 表示 ZIP 格式)')
        
        if file_size < 1000:
            logging.error(f'[API] 文件大小异常：{file_size} 字节')
            return jsonify({'success': False, 'message': '文件已损坏'}), 500
        
        # 验证文件是否为有效的 zip/docx
        import zipfile
        try:
            with zipfile.ZipFile(temp_path, 'r') as z:
                # 检查是否包含 docx 必需的文件
                if '[Content_Types].xml' not in z.namelist():
                    logging.error('[API] 文件不是有效的 DOCX 格式')
                    return jsonify({'success': False, 'message': '文件格式不正确'}), 400
                logging.info(f'[API] 文件验证通过，包含 {len(z.namelist())} 个文件')
        except zipfile.BadZipFile as e:
            logging.error(f'[API] 文件不是有效的 ZIP 文件：{e}')
            return jsonify({'success': False, 'message': '文件已损坏'}), 400
        
        # 分析文档（使用文件路径）
        logging.info('[API] 开始分析文档...')
        analyzer = get_analyzer()
        report = analyzer.analyze(file_path=temp_path)
        
        logging.info(f'[API] 分析完成：{len(report.heading_styles)} 种样式，{len(report.potential_heading_styles)} 种潜在标题样式')
        
        # 生成映射规则
        rules = report.generate_mapping_rules()
        logging.info(f'[API] 生成 {len(rules)} 条映射规则')
        for rule in rules:
            logging.info(f'[API]   规则：{rule["source_style"]} -> {rule["target_style"]}')

        # 生成目录结构
        chapter_structure = report.to_dict()
        logging.info(f'[API] 目录结构：{len(chapter_structure.get("heading_styles", {}))} 种样式')
        
        logging.info('=' * 80)

        return jsonify({
            'success': True,
            'message': f'上传成功，检测到 {len(report.heading_styles)} 种样式',
            'analysis': chapter_structure,
            'rules': rules,
            'temp_path': str(temp_path)
        })
    except Exception as e:
        import traceback
        logging.error(f'[API] 异常：{e}')
        logging.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500


@template_bp.route('/preprocess', methods=['POST'])
def preprocess_template():
    """预处理模板 - 根据目录结构生成新文档"""
    import logging
    import os
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    try:
        data = request.json
        temp_path = data.get('temp_path')
        rules = data.get('rules', [])
        chapter_structure = data.get('chapter_structure', {})

        logging.info('=' * 80)
        logging.info('[API] 开始预处理模板')
        logging.info(f'[API] 临时文件：{temp_path}')
        logging.info(f'[API] 规则数：{len(rules)}')
        logging.info(f'[API] 目录结构：{bool(chapter_structure)}')

        if not temp_path:
            return jsonify({'success': False, 'message': '请指定临时文件路径'}), 400

        # 预处理（使用绝对路径）
        preprocessor = get_preprocessor()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, 'uploads', 'templates', 'processed')
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f'{uuid.uuid4().hex}.docx'
        output_path = os.path.join(output_dir, output_filename)

        logging.info(f'[API] 输出文件：{output_path}')

        # 使用 preprocess_with_analysis 方法，它会自动分析并预处理
        result = preprocessor.preprocess_with_analysis(temp_path, output_path)

        if result.success:
            logging.info(f'[API] 预处理成功：{result.message}')
            logging.info(f'[API] 统计：{result.stats}')
            logging.info('=' * 80)

            return jsonify({
                'success': True,
                'message': result.message,
                'stats': result.stats,
                'output_path': result.output_path
            })
        else:
            logging.error(f'[API] 预处理失败：{result.message}')
            logging.error('=' * 80)
            return jsonify({'success': False, 'message': result.message}), 400
    except Exception as e:
        import traceback
        logging.error(f'[API] 异常：{e}')
        logging.error(traceback.format_exc())
        logging.error('=' * 80)
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
