# -*- coding: utf-8 -*-
"""
任务管理器 - 支持持久化和实时预览
功能：
1. 任务状态持久化到文件
2. 章节内容保存和加载
3. 临时文档管理
4. 轮询状态查询
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import uuid


# 任务存储根目录
TASKS_ROOT = os.path.join(os.path.dirname(__file__), 'tasks')

# 最大重新生成次数
MAX_REGENERATE_COUNT = 2


@dataclass
class ChapterStatus:
    """章节状态"""
    index: int                              # 章节索引
    title: str                              # 章节标题
    status: str = 'pending'                 # pending/generating/completed/failed
    content: Optional[str] = None           # 已生成的内容
    word_count: int = 0                     # 字数统计
    error_message: Optional[str] = None     # 失败时的错误信息
    generated_at: Optional[str] = None      # 生成完成时间
    regenerated_count: int = 0              # 重新生成次数
    last_user_instruction: Optional[str] = None  # 最后一次用户补充需求
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChapterStatus':
        return cls(**data)


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str                            # 任务 ID
    template_type: str                      # 模板类型
    user_prompt: str = ''                   # 用户补充要求
    model: str = 'qwen-max'                 # 模型名称
    status: str = 'pending'                 # pending/generating/paused/completed/failed/partially_completed
    progress: int = 0                       # 总体进度 0-100
    current_chapter_index: int = 0          # 当前正在生成的章节索引
    total_chapters: int = 0                 # 总章节数
    completed_chapters: int = 0             # 已完成章节数
    failed_chapters: List[int] = field(default_factory=list)  # 失败章节索引
    created_at: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    requirement_filename: Optional[str] = None  # 需求文档文件名
    template_filename: Optional[str] = None     # 模板文档文件名
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TaskInfo':
        return cls(**data)


class TaskManager:
    """任务管理器 - 单例模式"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._ensure_tasks_directory()
    
    def _ensure_tasks_directory(self):
        """确保任务存储目录存在"""
        os.makedirs(TASKS_ROOT, exist_ok=True)
    
    def _get_task_directory(self, task_id: str) -> str:
        """获取任务目录路径"""
        return os.path.join(TASKS_ROOT, task_id)
    
    def create_task(self, template_type: str, user_prompt: str = '', 
                    model: str = 'qwen-max',
                    requirement_filename: str = None,
                    template_filename: str = None) -> str:
        """创建新任务"""
        task_id = uuid.uuid4().hex
        task_dir = self._get_task_directory(task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        # 创建任务信息
        task_info = TaskInfo(
            task_id=task_id,
            template_type=template_type,
            user_prompt=user_prompt,
            model=model,
            requirement_filename=requirement_filename,
            template_filename=template_filename
        )
        
        # 保存任务信息
        self._save_task_info(task_id, task_info)
        
        # 初始化章节列表（空，后续设置）
        self._save_chapters(task_id, [])
        
        print(f'[TASK] 创建任务：{task_id}')
        print(f'[TASK]   模板类型：{template_type}')
        print(f'[TASK]   模型：{model}')
        print(f'[TASK]   任务目录：{task_dir}')
        
        return task_id
    
    def _save_task_info(self, task_id: str, task_info: TaskInfo):
        """保存任务信息"""
        task_info.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task_dir = self._get_task_directory(task_id)
        filepath = os.path.join(task_dir, 'task_info.json')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(task_info.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """加载任务信息"""
        task_dir = self._get_task_directory(task_id)
        filepath = os.path.join(task_dir, 'task_info.json')
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return TaskInfo.from_dict(data)
    
    def update_task_status(self, task_id: str, **kwargs):
        """更新任务状态"""
        task_info = self.load_task_info(task_id)
        if not task_info:
            return
        
        for key, value in kwargs.items():
            if hasattr(task_info, key):
                setattr(task_info, key, value)
        
        self._save_task_info(task_id, task_info)
    
    def _save_chapters(self, task_id: str, chapters: List[ChapterStatus]):
        """保存章节列表"""
        task_dir = self._get_task_directory(task_id)
        filepath = os.path.join(task_dir, 'chapters.json')
        
        data = {
            'chapters': [chapter.to_dict() for chapter in chapters]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_chapters(self, task_id: str) -> List[ChapterStatus]:
        """加载章节列表"""
        task_dir = self._get_task_directory(task_id)
        filepath = os.path.join(task_dir, 'chapters.json')
        
        if not os.path.exists(filepath):
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return [ChapterStatus.from_dict(ch) for ch in data.get('chapters', [])]
    
    def initialize_chapters(self, task_id: str, chapter_titles: List[str]):
        """初始化章节列表"""
        chapters = [
            ChapterStatus(index=i, title=title)
            for i, title in enumerate(chapter_titles)
        ]
        
        self._save_chapters(task_id, chapters)
        
        # 更新任务信息
        task_info = self.load_task_info(task_id)
        if task_info:
            task_info.total_chapters = len(chapters)
            self._save_task_info(task_id, task_info)
        
        print(f'[TASK] 初始化章节列表：{len(chapters)} 章')
    
    def update_chapter_status(self, task_id: str, chapter_index: int, **kwargs):
        """更新章节状态"""
        chapters = self.load_chapters(task_id)
        
        if chapter_index >= len(chapters):
            print(f'[WARN] 章节索引超出范围：{chapter_index}')
            return
        
        chapter = chapters[chapter_index]
        
        for key, value in kwargs.items():
            if hasattr(chapter, key):
                setattr(chapter, key, value)
        
        # 特殊处理：如果状态变为 completed，设置完成时间
        if kwargs.get('status') == 'completed':
            chapter.generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 特殊处理：如果重新生成，增加计数
        if 'content' in kwargs and chapter.status == 'completed':
            chapter.regenerated_count += 1
        
        chapters[chapter_index] = chapter
        self._save_chapters(task_id, chapters)
        
        # 更新任务进度
        self._update_task_progress(task_id)
    
    def _update_task_progress(self, task_id: str):
        """更新任务进度"""
        task_info = self.load_task_info(task_id)
        chapters = self.load_chapters(task_id)
        
        if not task_info or not chapters:
            return
        
        # 计算进度
        completed = sum(1 for ch in chapters if ch.status == 'completed')
        failed = sum(1 for ch in chapters if ch.status == 'failed')
        
        task_info.completed_chapters = completed
        task_info.failed_chapters = [ch.index for ch in chapters if ch.status == 'failed']
        
        if chapters:
            task_info.progress = int((completed / len(chapters)) * 100)
        
        # 检查是否完成
        if completed + failed == len(chapters):
            if failed == 0:
                task_info.status = 'completed'
                task_info.completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                task_info.status = 'partially_completed'
                task_info.completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self._save_task_info(task_id, task_info)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态（用于轮询 API）"""
        task_info = self.load_task_info(task_id)
        if not task_info:
            return None
        
        chapters = self.load_chapters(task_id)
        
        # 获取当前章节
        current_chapter = None
        for ch in chapters:
            if ch.status == 'generating':
                current_chapter = ch.title
                break
        
        return {
            'task_id': task_info.task_id,
            'status': task_info.status,
            'progress': task_info.progress,
            'current_chapter': current_chapter,
            'total_chapters': task_info.total_chapters,
            'completed_chapters': task_info.completed_chapters,
            'failed_chapters': task_info.failed_chapters,
            'chapters': [ch.to_dict() for ch in chapters],
            'partial_doc_url': f'/api/task/{task_id}/download-partial' if os.path.exists(
                os.path.join(self._get_task_directory(task_id), f'partial_{task_id}.docx')
            ) else None,
            'created_at': task_info.created_at,
            'updated_at': task_info.updated_at
        }
    
    def save_file(self, task_id: str, filename: str, content: bytes):
        """保存上传的文件"""
        task_dir = self._get_task_directory(task_id)
        filepath = os.path.join(task_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(content)
        
        print(f'[TASK] 保存文件：{filename}')
    
    def get_file_path(self, task_id: str, filename: str) -> Optional[str]:
        """获取文件路径"""
        task_dir = self._get_task_directory(task_id)
        filepath = os.path.join(task_dir, filename)
        
        if os.path.exists(filepath):
            return filepath
        return None
    
    def save_partial_document(self, task_id: str, doc):
        """保存临时文档"""
        task_dir = self._get_task_directory(task_id)
        filepath = os.path.join(task_dir, f'partial_{task_id}.docx')
        
        doc.save(filepath)
        print(f'[PERSIST] 临时文档已更新：{filepath}')
    
    def get_partial_document_path(self, task_id: str) -> Optional[str]:
        """获取临时文档路径"""
        task_dir = self._get_task_directory(task_id)
        filepath = os.path.join(task_dir, f'partial_{task_id}.docx')
        
        if os.path.exists(filepath):
            return filepath
        return None
    
    def save_final_document(self, task_id: str, output_path: str):
        """保存最终文档"""
        task_dir = self._get_task_directory(task_id)
        final_path = os.path.join(task_dir, f'final_{task_id}.docx')
        
        # 复制最终文档到任务目录
        shutil.copy2(output_path, final_path)
        print(f'[PERSIST] 最终文档已保存：{final_path}')
        
        # 清理临时文件
        self._cleanup_temporary_files(task_id)
    
    def _cleanup_temporary_files(self, task_id: str):
        """清理临时文件"""
        task_dir = self._get_task_directory(task_id)
        partial_file = os.path.join(task_dir, f'partial_{task_id}.docx')
        
        if os.path.exists(partial_file):
            os.remove(partial_file)
            print(f'[CLEANUP] 已清理临时文件：{partial_file}')
    
    def pause_task(self, task_id: str):
        """暂停任务"""
        self.update_task_status(task_id, status='paused')
        print(f'[TASK] 任务已暂停：{task_id}')
    
    def continue_task(self, task_id: str):
        """继续任务"""
        self.update_task_status(task_id, status='generating')
        print(f'[TASK] 任务已继续：{task_id}')
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        self.update_task_status(task_id, status='cancelled')
        print(f'[TASK] 任务已取消：{task_id}')
    
    def is_paused(self, task_id: str) -> bool:
        """检查任务是否暂停"""
        task_info = self.load_task_info(task_id)
        return task_info and task_info.status == 'paused'
    
    def is_cancelled(self, task_id: str) -> bool:
        """检查任务是否取消"""
        task_info = self.load_task_info(task_id)
        return task_info and task_info.status == 'cancelled'
    
    def can_regenerate(self, task_id: str, chapter_index: int) -> bool:
        """检查章节是否可以重新生成"""
        chapters = self.load_chapters(task_id)
        
        if chapter_index >= len(chapters):
            return False
        
        chapter = chapters[chapter_index]
        return chapter.regenerated_count < MAX_REGENERATE_COUNT
    
    def get_failed_chapters(self, task_id: str) -> List[ChapterStatus]:
        """获取失败的章节列表"""
        chapters = self.load_chapters(task_id)
        return [ch for ch in chapters if ch.status == 'failed']


# 全局任务管理器实例
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


# 测试代码
if __name__ == '__main__':
    manager = get_task_manager()
    
    # 创建测试任务
    task_id = manager.create_task(
        template_type='future_community',
        user_prompt='测试任务',
        model='glm-4'
    )
    
    # 初始化章节
    manager.initialize_chapters(task_id, [
        '第一章 项目概况',
        '第二章 建设背景',
        '第三章 建设必要性'
    ])
    
    # 获取状态
    status = manager.get_task_status(task_id)
    print(f'\n任务状态：{json.dumps(status, ensure_ascii=False, indent=2)}')
