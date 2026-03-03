# -*- coding: utf-8 -*-
"""
数据库模型 - 生成任务
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class GenerationTask(Base):
    """生成任务表"""
    
    __tablename__ = 'generation_tasks'
    
    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    status = Column(String(20), default='pending', index=True)  # pending/parsing/analyzing/generating/reviewing/rendering/completed/failed/cancelled
    progress = Column(Integer, default=0)  # 0-100
    current_stage = Column(String(50), default='')  # 当前阶段描述
    current_chapter = Column(String(200), default='')  # 当前章节
    
    # 关联的文档
    requirement_doc_id = Column(String(36), ForeignKey('uploaded_documents.id'), nullable=True)
    template_id = Column(String(36), ForeignKey('document_templates.id'), nullable=True)
    
    # 用户输入
    user_instruction = Column(Text, default='')  # 用户补充指令
    
    # 中间数据（JSON 格式）
    project_context_json = Column(JSON, default=dict)  # 提取的项目上下文信息
    chapter_structure_json = Column(JSON, default=dict)  # 解析的章节结构树
    data_points_json = Column(JSON, default=dict)  # 数据点字典快照
    generated_chapters_json = Column(JSON, default=list)  # 已生成的章节内容
    
    # 输出
    output_file_path = Column(String(500), default='')  # 生成的 Word 文件路径
    partial_file_path = Column(String(500), default='')  # 部分生成的文件路径
    
    # LLM 信息
    llm_model = Column(String(50), default='qwen-max')  # 使用的 LLM 模型名称
    total_tokens = Column(Integer, default=0)  # 消耗的总 Token 数
    total_cost = Column(Float, default=0.0)  # 消耗的总费用
    
    # 错误信息
    error_message = Column(Text, default='')  # 错误信息（失败时）
    
    # 审校结果
    review_result_json = Column(JSON, default=dict)  # 审校结果
    pending_confirmation = Column(Boolean, default=False)  # 是否等待用户确认
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 关联关系
    requirement_doc = relationship('UploadedDocument', foreign_keys=[requirement_doc_id])
    template = relationship('DocumentTemplate', foreign_keys=[template_id])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.id,
            'status': self.status,
            'progress': self.progress,
            'current_stage': self.current_stage,
            'current_chapter': self.current_chapter,
            'requirement_doc_id': self.requirement_doc_id,
            'template_id': self.template_id,
            'user_instruction': self.user_instruction,
            'project_context_json': self.project_context_json,
            'chapter_structure_json': self.chapter_structure_json,
            'data_points_json': self.data_points_json,
            'generated_chapters_json': self.generated_chapters_json,
            'output_file_path': self.output_file_path,
            'partial_file_path': self.partial_file_path,
            'llm_model': self.llm_model,
            'total_tokens': self.total_tokens,
            'total_cost': self.total_cost,
            'error_message': self.error_message,
            'review_result_json': self.review_result_json,
            'pending_confirmation': self.pending_confirmation,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'started_at': self.started_at.strftime('%Y-%m-%d %H:%M:%S') if self.started_at else None,
            'completed_at': self.completed_at.strftime('%Y-%m-%d %H:%M:%S') if self.completed_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<GenerationTask(id={self.id}, status={self.status})>"


class UploadedDocument(Base):
    """上传的文档表"""
    
    __tablename__ = 'uploaded_documents'
    
    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    file_name = Column(String(255), nullable=False)  # 原始文件名
    file_path = Column(String(500), nullable=False)  # 存储路径
    file_type = Column(String(20), nullable=False)  # requirement/template
    file_size = Column(Integer, default=0)  # 文件大小（字节）
    
    # 提取的内容
    extracted_text = Column(Text, default='')  # 提取的文本内容
    extracted_json = Column(JSON, default=dict)  # 提取的结构化数据
    
    # 元数据
    metadata_json = Column(JSON, default=dict)  # 文档元数据
    
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联关系
    tasks = relationship('GenerationTask', foreign_keys='GenerationTask.requirement_doc_id', back_populates='requirement_doc')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'file_path': self.file_path,
            'extracted_text': self.extracted_text,
            'extracted_json': self.extracted_json,
            'metadata_json': self.metadata_json,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<UploadedDocument(id={self.id}, file_name={self.file_name})>"


class DocumentTemplate(Base):
    """格式模板表"""
    
    __tablename__ = 'document_templates'
    
    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(200), nullable=False)  # 模板名称
    description = Column(Text, default='')  # 模板描述
    
    # 文件
    template_file_path = Column(String(500), nullable=False)  # 模板 Word 文件路径
    
    # 配置
    style_config_json = Column(JSON, default=dict)  # 样式配置
    chapter_structure_json = Column(JSON, default=dict)  # 预解析的章节结构
    
    # 标记
    is_default = Column(Boolean, default=False)  # 是否为默认模板
    is_active = Column(Boolean, default=True)  # 是否启用
    
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联关系
    tasks = relationship('GenerationTask', foreign_keys='GenerationTask.template_id', back_populates='template')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'template_file_path': self.template_file_path,
            'style_config_json': self.style_config_json,
            'chapter_structure_json': self.chapter_structure_json,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<DocumentTemplate(id={self.id}, name={self.name})>"


class ChapterContent(Base):
    """章节内容表"""
    
    __tablename__ = 'chapter_contents'
    
    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    task_id = Column(String(36), ForeignKey('generation_tasks.id'), nullable=False)
    chapter_number = Column(String(50), nullable=False)  # 章节编号
    chapter_title = Column(String(200), nullable=False)  # 章节标题
    
    # 内容
    json_content = Column(JSON, default=dict)  # JSON 格式的章节内容
    status = Column(String(20), default='pending')  # pending/generating/completed/failed
    
    # 审校
    review_status = Column(String(20), default='pending')  # pending/passed/needs_revision
    review_comments = Column(Text, default='')  # 审校意见
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'chapter_number': self.chapter_number,
            'chapter_title': self.chapter_title,
            'json_content': self.json_content,
            'status': self.status,
            'review_status': self.review_status,
            'review_comments': self.review_comments,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ChapterContent(id={self.id}, chapter={self.chapter_number})>"


class FewShotExample(Base):
    """Few-shot 示例表"""
    
    __tablename__ = 'few_shot_examples'
    
    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    chapter_type = Column(String(50), nullable=False)  # 章节类型
    title = Column(String(200), default='')  # 示例标题
    content = Column(Text, nullable=False)  # 示例内容
    source = Column(String(200), default='')  # 来源
    tags = Column(JSON, default=list)  # 标签
    
    # 状态
    is_active = Column(Boolean, default=True)  # 是否启用
    usage_count = Column(Integer, default=0)  # 使用次数
    
    created_at = Column(DateTime, default=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'chapter_type': self.chapter_type,
            'title': self.title,
            'content': self.content,
            'source': self.source,
            'tags': self.tags,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<FewShotExample(id={self.id}, type={self.chapter_type})>"
