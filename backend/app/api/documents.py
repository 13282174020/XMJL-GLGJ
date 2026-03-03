# -*- coding: utf-8 -*-
"""
文档上传 API 接口
"""

import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from datetime import datetime

from app.services.document_parser import parse_document
from app.models.task import UploadedDocument
from app.config import config

bp = Blueprint('documents', __name__, url_prefix='/documents')


ALLOWED_EXTENSIONS = {'docx', 'doc', 'txt'}


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/upload', methods=['POST'])
def upload_document():
    """上传文档
    
    请求参数:
    - file: 文件
    - file_type: 文件类型 (requirement/template)
    """
    try:
        # 检查文件
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '未找到上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '文件名为空'}), 400
        
        # 检查文件类型
        file_type = request.form.get('file_type', 'requirement')
        if file_type not in ['requirement', 'template']:
            return jsonify({'success': False, 'message': '文件类型必须是 requirement 或 template'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': '不支持的文件格式，仅支持 .docx, .doc, .txt'}), 400
        
        # 生成唯一文件名
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # 保存文件
        file.save(filepath)
        file_size = os.path.getsize(filepath)
        
        # 解析文档
        try:
            parse_result = parse_document(filepath, file_type)
        except Exception as e:
            os.remove(filepath)
            return jsonify({'success': False, 'message': f'文档解析失败：{str(e)}'}), 500
        
        # 保存到数据库
        db_session = current_app.config['db_session']()
        try:
            doc = UploadedDocument(
                id=uuid.uuid4().hex,
                file_name=secure_filename(file.filename),
                file_path=filepath,
                file_type=file_type,
                file_size=file_size,
                extracted_text=parse_result['full_text'],
                extracted_json={
                    'paragraphs': parse_result['paragraphs'],
                    'tables': parse_result['tables'],
                    'chapters': parse_result['chapters']
                },
                metadata_json={
                    'character_count': parse_result['character_count'],
                    'paragraph_count': parse_result['paragraph_count'],
                    'table_count': parse_result['table_count'],
                    'is_too_long': parse_result['is_too_long']
                }
            )
            db_session.add(doc)
            db_session.commit()
            
            return jsonify({
                'success': True,
                'message': '上传成功',
                'document': doc.to_dict()
            })
            
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败：{str(e)}'}), 500


@bp.route('/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """获取文档详情"""
    try:
        db_session = current_app.config['db_session']()
        try:
            doc = db_session.query(UploadedDocument).filter_by(id=doc_id).first()
            if not doc:
                return jsonify({'success': False, 'message': '文档不存在'}), 404
            
            return jsonify({
                'success': True,
                'document': doc.to_dict()
            })
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'查询失败：{str(e)}'}), 500


@bp.route('/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """删除文档"""
    try:
        db_session = current_app.config['db_session']()
        try:
            doc = db_session.query(UploadedDocument).filter_by(id=doc_id).first()
            if not doc:
                return jsonify({'success': False, 'message': '文档不存在'}), 404
            
            # 删除文件
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
            
            # 删除数据库记录
            db_session.delete(doc)
            db_session.commit()
            
            return jsonify({'success': True, 'message': '删除成功'})
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'}), 500


@bp.route('/<doc_id>/content', methods=['GET'])
def get_document_content(doc_id):
    """获取文档提取的内容"""
    try:
        db_session = current_app.config['db_session']()
        try:
            doc = db_session.query(UploadedDocument).filter_by(id=doc_id).first()
            if not doc:
                return jsonify({'success': False, 'message': '文档不存在'}), 404
            
            return jsonify({
                'success': True,
                'content': {
                    'full_text': doc.extracted_text,
                    'paragraphs': doc.extracted_json.get('paragraphs', []),
                    'tables': doc.extracted_json.get('tables', []),
                    'chapters': doc.extracted_json.get('chapters', [])
                }
            })
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'查询失败：{str(e)}'}), 500
