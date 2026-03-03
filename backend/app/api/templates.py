# -*- coding: utf-8 -*-
"""
模板管理 API 接口
"""

import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from datetime import datetime

from app.models.task import DocumentTemplate
from app.services.document_parser import parse_document

bp = Blueprint('templates', __name__, url_prefix='/templates')


@bp.route('', methods=['GET'])
def list_templates():
    """获取模板列表"""
    try:
        db_session = current_app.config['db_session']()
        try:
            templates = db_session.query(DocumentTemplate).filter_by(is_active=True).all()
            
            return jsonify({
                'success': True,
                'templates': [t.to_dict() for t in templates]
            })
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'查询失败：{str(e)}'}), 500


@bp.route('', methods=['POST'])
def upload_template():
    """上传模板"""
    try:
        # 检查文件
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '未找到上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '文件名为空'}), 400
        
        name = request.form.get('name', file.filename)
        description = request.form.get('description', '')
        
        # 保存文件
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'docx'
        filename = f"template_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 解析模板
        try:
            parse_result = parse_document(filepath, 'template')
            chapter_structure = {
                'chapters': parse_result.get('chapters', [])
            }
        except:
            chapter_structure = {'chapters': []}
        
        # 保存到数据库
        db_session = current_app.config['db_session']()
        try:
            template = DocumentTemplate(
                id=uuid.uuid4().hex,
                name=name,
                description=description,
                template_file_path=filepath,
                chapter_structure_json=chapter_structure
            )
            db_session.add(template)
            db_session.commit()
            
            return jsonify({
                'success': True,
                'message': '模板上传成功',
                'template': template.to_dict()
            })
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败：{str(e)}'}), 500


@bp.route('/<template_id>', methods=['GET'])
def get_template(template_id):
    """获取模板详情"""
    try:
        db_session = current_app.config['db_session']()
        try:
            template = db_session.query(DocumentTemplate).filter_by(id=template_id).first()
            if not template:
                return jsonify({'success': False, 'message': '模板不存在'}), 404
            
            return jsonify({
                'success': True,
                'template': template.to_dict()
            })
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'查询失败：{str(e)}'}), 500


@bp.route('/<template_id>', methods=['PUT'])
def update_template(template_id):
    """更新模板"""
    try:
        data = request.json
        
        db_session = current_app.config['db_session']()
        try:
            template = db_session.query(DocumentTemplate).filter_by(id=template_id).first()
            if not template:
                return jsonify({'success': False, 'message': '模板不存在'}), 404
            
            if 'name' in data:
                template.name = data['name']
            if 'description' in data:
                template.description = data['description']
            if 'style_config_json' in data:
                template.style_config_json = data['style_config_json']
            if 'is_default' in data:
                # 取消其他模板的默认状态
                db_session.query(DocumentTemplate).filter_by(is_default=True).update({'is_default': False})
                template.is_default = data['is_default']
            
            db_session.commit()
            
            return jsonify({
                'success': True,
                'message': '更新成功',
                'template': template.to_dict()
            })
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500


@bp.route('/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    """删除模板"""
    try:
        db_session = current_app.config['db_session']()
        try:
            template = db_session.query(DocumentTemplate).filter_by(id=template_id).first()
            if not template:
                return jsonify({'success': False, 'message': '模板不存在'}), 404
            
            # 删除文件
            if os.path.exists(template.template_file_path):
                os.remove(template.template_file_path)
            
            # 删除数据库记录
            db_session.delete(template)
            db_session.commit()
            
            return jsonify({'success': True, 'message': '删除成功'})
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'}), 500


@bp.route('/<template_id>/toggle', methods=['POST'])
def toggle_template(template_id):
    """切换模板启用状态"""
    try:
        db_session = current_app.config['db_session']()
        try:
            template = db_session.query(DocumentTemplate).filter_by(id=template_id).first()
            if not template:
                return jsonify({'success': False, 'message': '模板不存在'}), 404
            
            template.is_active = not template.is_active
            db_session.commit()
            
            return jsonify({
                'success': True,
                'message': f'模板已{"启用" if template.is_active else "禁用"}',
                'template': template.to_dict()
            })
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败：{str(e)}'}), 500
