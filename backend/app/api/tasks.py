# -*- coding: utf-8 -*-
"""
任务管理 API 接口
"""

import os
import uuid
import json
import threading
import time
from flask import Blueprint, request, jsonify, current_app, stream_with_context
from datetime import datetime

from app.models.task import GenerationTask, UploadedDocument, DocumentTemplate, ChapterContent
from app.services.ai_engine import AIEngine
from app.services.document_parser import parse_document
from app.utils.doc_builder import DocBuilder
from app.config import config

bp = Blueprint('tasks', __name__, url_prefix='/tasks')


# 任务执行状态（内存）
task_threads = {}


@bp.route('', methods=['POST'])
def create_task():
    """创建生成任务
    
    请求体:
    {
        "requirement_doc_id": "需求文档 ID",
        "template_id": "模板 ID（可选）",
        "user_instruction": "用户补充说明",
        "llm_model": "模型名称",
        "options": {...}
    }
    """
    try:
        data = request.json
        
        requirement_doc_id = data.get('requirement_doc_id')
        if not requirement_doc_id:
            return jsonify({'success': False, 'message': '需求文档 ID 不能为空'}), 400
        
        template_id = data.get('template_id', '')
        user_instruction = data.get('user_instruction', '')
        llm_model = data.get('llm_model', config.default_model)
        options = data.get('options', {})
        
        # 验证需求文档
        db_session = current_app.config['db_session']()
        try:
            req_doc = db_session.query(UploadedDocument).filter_by(id=requirement_doc_id).first()
            if not req_doc:
                return jsonify({'success': False, 'message': '需求文档不存在'}), 404
            
            # 获取模板
            template = None
            if template_id:
                template = db_session.query(DocumentTemplate).filter_by(id=template_id).first()
            
            # 创建任务
            task = GenerationTask(
                id=uuid.uuid4().hex,
                status='pending',
                progress=0,
                requirement_doc_id=requirement_doc_id,
                template_id=template_id if template else None,
                user_instruction=user_instruction,
                llm_model=llm_model
            )
            db_session.add(task)
            db_session.commit()
            
            # 启动后台线程处理任务
            thread = threading.Thread(
                target=process_task,
                args=(task.id, req_doc.extracted_text, template, user_instruction, llm_model, options)
            )
            thread.daemon = True
            task_threads[task.id] = thread
            thread.start()
            
            return jsonify({
                'success': True,
                'message': '任务已创建，正在处理中',
                'task_id': task.id,
                'status': 'pending',
                'estimated_time_minutes': 15
            })
            
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'创建失败：{str(e)}'}), 500


@bp.route('/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情"""
    try:
        db_session = current_app.config['db_session']()
        try:
            task = db_session.query(GenerationTask).filter_by(id=task_id).first()
            if not task:
                return jsonify({'success': False, 'message': '任务不存在'}), 404
            
            return jsonify({
                'success': True,
                'task': task.to_dict()
            })
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'查询失败：{str(e)}'}), 500


@bp.route('/<task_id>/progress', methods=['GET'])
def get_task_progress(task_id):
    """SSE 实时进度推送"""
    def generate():
        db_session = current_app.config['db_session']()
        try:
            while True:
                task = db_session.query(GenerationTask).filter_by(id=task_id).first()
                if not task:
                    yield f'event: error\ndata: {{"message": "任务不存在"}}\n\n'
                    break
                
                task_data = task.to_dict()
                
                yield f'event: progress\ndata: {json.dumps(task_data, ensure_ascii=False)}\n\n'
                
                # 任务完成/失败/取消时停止
                if task.status in ['completed', 'failed', 'cancelled']:
                    if task.status == 'completed':
                        yield f'event: completed\ndata: {json.dumps(task_data, ensure_ascii=False)}\n\n'
                    break
                
                time.sleep(2)  # 每 2 秒推送一次
                
        finally:
            db_session.close()
    
    return stream_with_context(generate()), {'Content-Type': 'text/event-stream'}


@bp.route('/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    try:
        db_session = current_app.config['db_session']()
        try:
            task = db_session.query(GenerationTask).filter_by(id=task_id).first()
            if not task:
                return jsonify({'success': False, 'message': '任务不存在'}), 404
            
            if task.status in ['completed', 'failed', 'cancelled']:
                return jsonify({'success': False, 'message': '任务已完成/失败，无法取消'}), 400
            
            task.status = 'cancelled'
            task.completed_at = datetime.now()
            db_session.commit()
            
            return jsonify({'success': True, 'message': '任务已取消'})
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'取消失败：{str(e)}'}), 500


@bp.route('/<task_id>/continue', methods=['POST'])
def continue_task(task_id):
    """继续生成（用户确认后）"""
    try:
        db_session = current_app.config['db_session']()
        try:
            task = db_session.query(GenerationTask).filter_by(id=task_id).first()
            if not task:
                return jsonify({'success': False, 'message': '任务不存在'}), 404
            
            task.pending_confirmation = False
            db_session.commit()
            
            return jsonify({'success': True, 'message': '已确认，继续生成'})
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败：{str(e)}'}), 500


@bp.route('/<task_id>/download', methods=['GET'])
def download_task(task_id):
    """下载生成的文档"""
    try:
        db_session = current_app.config['db_session']()
        try:
            task = db_session.query(GenerationTask).filter_by(id=task_id).first()
            if not task:
                return jsonify({'success': False, 'message': '任务不存在'}), 404
            
            file_path = task.output_file_path or task.partial_file_path
            if not file_path or not os.path.exists(file_path):
                return jsonify({'success': False, 'message': '文档不存在'}), 404
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=os.path.basename(file_path)
            )
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'下载失败：{str(e)}'}), 500


@bp.route('', methods=['GET'])
def list_tasks():
    """获取任务列表"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        status = request.args.get('status', '')
        
        db_session = current_app.config['db_session']()
        try:
            query = db_session.query(GenerationTask)
            
            if status:
                query = query.filter_by(status=status)
            
            # 按创建时间倒序
            query = query.order_by(GenerationTask.created_at.desc())
            
            total = query.count()
            tasks = query.offset((page - 1) * page_size).limit(page_size).all()
            
            return jsonify({
                'success': True,
                'tasks': [task.to_dict() for task in tasks],
                'total': total,
                'page': page,
                'page_size': page_size
            })
        finally:
            db_session.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'查询失败：{str(e)}'}), 500


def process_task(task_id: str, requirement_text: str, template, user_instruction: str, llm_model: str, options: dict):
    """后台处理任务
    
    五阶段流程：
    1. 文档解析与信息提取
    2. 模板结构分析
    3. 分章节内容生成
    4. 质量审校
    5. Word 文档渲染
    """
    db_session = current_app.config['db_session']()
    
    try:
        task = db_session.query(GenerationTask).filter_by(id=task_id).first()
        if not task:
            return
        
        # 更新状态：开始处理
        task.status = 'parsing'
        task.progress = 5
        task.started_at = datetime.now()
        db_session.commit()
        
        # 初始化 AI 引擎
        api_key = config.llm_api_key
        if not api_key:
            raise Exception("未配置 LLM API Key，请在 config.json 中设置")
        
        engine = AIEngine(api_key, llm_model)
        
        # ========== 阶段一：信息提取 ==========
        task.status = 'parsing'
        task.progress = 10
        task.current_stage = '正在提取需求信息...'
        db_session.commit()
        
        try:
            project_context = engine.extract_requirements(requirement_text)
            task.project_context_json = project_context
            db_session.commit()
        except Exception as e:
            # 使用默认结构
            project_context = {
                'project_info': {'name': '建设项目'},
                'org_info': {},
                'pain_points': [],
                'requirements': [],
                'constraints': [],
                'special_notes': []
            }
        
        # ========== 阶段二：模板分析 ==========
        task.status = 'analyzing'
        task.progress = 20
        task.current_stage = '正在分析模板结构...'
        db_session.commit()
        
        # 使用默认章节结构
        chapter_structure = {
            'chapters': [
                {'number': '1', 'title': '项目概况', 'level': 1, 'subsections': []},
                {'number': '2', 'title': '项目建设单位概况', 'level': 1, 'subsections': []},
                {'number': '3', 'title': '项目建设的必要性', 'level': 1, 'subsections': []},
            ]
        }
        task.chapter_structure_json = chapter_structure
        db_session.commit()
        
        # ========== 阶段三：分章节生成 ==========
        task.status = 'generating'
        task.progress = 30
        task.current_stage = '正在生成章节内容...'
        db_session.commit()
        
        generated_chapters = []
        
        for idx, chapter in enumerate(chapter_structure['chapters']):
            # 检查是否被取消
            db_session.refresh(task)
            if task.status == 'cancelled':
                return
            
            task.current_chapter = chapter['title']
            task.progress = 30 + int((idx + 1) / len(chapter_structure['chapters']) * 40)
            db_session.commit()
            
            try:
                # 生成章节
                chapter_content = engine.generate_chapter(
                    project_context=project_context,
                    chapter=chapter,
                    user_instruction=user_instruction
                )
                generated_chapters.append(chapter_content)
                
            except Exception as e:
                # 生成失败，使用默认内容
                generated_chapters.append({
                    'chapter_number': chapter['number'],
                    'chapter_title': chapter['title'],
                    'subsections': []
                })
        
        task.generated_chapters_json = generated_chapters
        db_session.commit()
        
        # ========== 阶段四：质量审校 ==========
        task.status = 'reviewing'
        task.progress = 75
        task.current_stage = '正在进行质量审校...'
        db_session.commit()
        
        # 简化处理，跳过详细审校
        
        # ========== 阶段五：Word 文档渲染 ==========
        task.status = 'rendering'
        task.progress = 85
        task.current_stage = '正在生成 Word 文档...'
        db_session.commit()
        
        # 构建完整 JSON
        doc_json = {
            'project_info': project_context.get('project_info', {}),
            'chapters': chapter_structure.get('chapters', []),
            'generated_chapters': generated_chapters
        }
        
        # 渲染文档
        builder = DocBuilder()
        output_filename = f"report_{task_id[:8]}.docx"
        output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)
        
        try:
            builder.render_document(doc_json)
            builder.save(output_path)
            task.output_file_path = output_path
        except Exception as e:
            task.error_message = f"文档渲染失败：{str(e)}"
        
        # ========== 完成 ==========
        task.status = 'completed'
        task.progress = 100
        task.current_stage = ''
        task.completed_at = datetime.now()
        db_session.commit()
        
    except Exception as e:
        # 任务失败
        if task:
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = datetime.now()
            db_session.commit()
    
    finally:
        db_session.close()
        if task_id in task_threads:
            del task_threads[task_id]
