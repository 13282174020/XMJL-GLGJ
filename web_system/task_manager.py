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
    index: int                              # 章节索引（扁平索引）
    title: str                              # 章节标题
    status: str = 'pending'                 # pending/generating/completed/failed
    content: Optional[str] = None           # 已生成的内容
    word_count: int = 0                     # 字数统计
    error_message: Optional[str] = None     # 失败时的错误信息
    generated_at: Optional[str] = None      # 生成完成时间
    regenerated_count: int = 0              # 重新生成次数
    last_user_instruction: Optional[str] = None  # 最后一次用户补充需求
    level: int = 1                          # 章节层级（1=一级章节，2=二级章节，以此类推）
    number: str = ''                        # 章节编号（如 1, 1.1, 1.1.1）

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ChapterStatus':
        # 兼容旧数据（没有 level 和 number 字段）
        if 'level' not in data:
            data['level'] = 1
        if 'number' not in data:
            data['number'] = str(data.get('index', 0) + 1)
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
    message: str = ''                       # 任务状态消息/错误信息
    current_chapter_index: Optional[int] = None  # 当前正在生成的章节索引
    total_chapters: int = 0                 # 总章节数
    completed_chapters: int = 0             # 已完成章节数
    failed_chapters: List[int] = field(default_factory=list)  # 失败章节索引
    created_at: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    requirement_filename: Optional[str] = None  # 需求文档文件名
    template_filename: Optional[str] = None     # 模板文档文件名
    output_filename: Optional[str] = None       # 输出文件名
    partial_filename: Optional[str] = None      # 部分输出文件名
    
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

        # 更新更新时间
        task_info.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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
        """初始化章节列表（扁平结构，兼容旧代码）"""
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

    def initialize_chapters_with_tree(self, task_id: str, chapter_tree: List[Dict]):
        """
        初始化章节列表（树形结构）
        
        Args:
            chapter_tree: 树形结构的章节列表，每个节点包含 number, title, level, children
        """
        chapters = []
        index = 0

        def flatten_chapters(nodes: List[Dict], parent_level: int = 0):
            nonlocal index
            for node in nodes:
                level = node.get('level', parent_level + 1)
                chapters.append(ChapterStatus(
                    index=index,
                    title=node.get('title', ''),
                    level=level,
                    number=node.get('number', '')
                ))
                index += 1
                # 递归处理子章节
                children = node.get('children', [])
                if children:
                    flatten_chapters(children, level)

        flatten_chapters(chapter_tree)
        self._save_chapters(task_id, chapters)

        # 更新任务信息
        task_info = self.load_task_info(task_id)
        if task_info:
            task_info.total_chapters = len(chapters)
            self._save_task_info(task_id, task_info)

        print(f'[TASK] 初始化章节列表（树形）：{len(chapters)} 章')
    
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

        # 获取当前章节（状态为 generating 的章节）
        current_chapter = None
        for ch in chapters:
            if ch.status == 'generating':
                current_chapter = ch.title
                break

        # 如果没有正在生成的章节，使用任务信息中的 current_chapter_index
        if current_chapter is None and task_info.current_chapter_index is not None and chapters:
            idx = task_info.current_chapter_index
            if 0 <= idx < len(chapters):
                current_chapter = chapters[idx].title

        # 检查临时文档是否存在
        partial_doc_exists = False
        if task_info.partial_filename:
            partial_doc_exists = True
        else:
            # 检查是否有 partial_{task_id}.docx 文件
            partial_path = os.path.join(self._get_task_directory(task_id), f'partial_{task_id}.docx')
            partial_doc_exists = os.path.exists(partial_path)

        # 将扁平章节转换为树形结构
        chapter_tree = self._build_chapter_tree(chapters)

        return {
            'task_id': task_info.task_id,
            'status': task_info.status,
            'progress': task_info.progress,
            'message': task_info.message,
            'current_chapter': current_chapter,
            'total_chapters': task_info.total_chapters,
            'completed_chapters': task_info.completed_chapters,  # 已完成章节数（数字）
            'failed_chapters': task_info.failed_chapters,
            'chapters': chapter_tree,  # 返回树形结构
            'partial_doc_url': f'/api/v2/task/{task_id}/download-partial' if partial_doc_exists else None,
            'output_filename': task_info.output_filename,
            'created_at': task_info.created_at,
            'updated_at': task_info.updated_at
        }

    def _build_chapter_tree(self, chapters: List[ChapterStatus]) -> List[Dict]:
        """将扁平章节列表转换为树形结构"""
        if not chapters:
            return []

        tree = []
        chapter_dicts = [ch.to_dict() for ch in chapters]

        for ch in chapter_dicts:
            level = ch.get('level', 1)
            ch['children'] = ch.get('children', [])

            if level == 1:
                tree.append(ch)
            else:
                # 查找父节点（最后一个 level-1 的节点）
                parent = self._find_parent_node(tree, level - 1)
                if parent:
                    if 'children' not in parent:
                        parent['children'] = []
                    parent['children'].append(ch)
                else:
                    # 没有找到父节点，作为一级章节
                    tree.append(ch)

        return tree

    def _find_parent_node(self, nodes: List[Dict], target_level: int) -> Optional[Dict]:
        """递归查找指定层级的最后一个节点"""
        for node in reversed(nodes):
            if node.get('level', 1) == target_level:
                return node
            children = node.get('children', [])
            if children:
                result = self._find_parent_node(children, target_level)
                if result:
                    return result
        return None
    
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

    def delete_task(self, task_id: str) -> bool:
        """
        删除任务及其所有相关文件
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否删除成功
        """
        task_dir = self._get_task_directory(task_id)
        
        if not os.path.exists(task_dir):
            print(f'[TASK] 任务目录不存在：{task_id}')
            return False
        
        try:
            # 删除整个任务目录
            shutil.rmtree(task_dir)
            print(f'[TASK] 任务已删除：{task_id}')
            return True
        except Exception as e:
            print(f'[ERROR] 删除任务失败：{e}')
            return False
    
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

    def update_task_progress(self, task_id: str, progress: int = None, message: str = None, status: str = None):
        """更新任务进度和消息"""
        task_info = self.load_task_info(task_id)
        if not task_info:
            return

        if progress is not None:
            task_info.progress = max(0, min(100, progress))
        if message is not None:
            task_info.message = message
        if status is not None:
            task_info.status = status

        task_info.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._save_task_info(task_id, task_info)

    def set_partial_filename(self, task_id: str, filename: str):
        """设置部分输出文件名"""
        task_info = self.load_task_info(task_id)
        if not task_info:
            return

        task_info.partial_filename = filename
        task_info.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._save_task_info(task_id, task_info)

    def set_task_started(self, task_id: str):
        """设置任务开始状态"""
        task_info = self.load_task_info(task_id)
        if not task_info:
            return

        task_info.status = 'generating'
        task_info.started_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task_info.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._save_task_info(task_id, task_info)

    def mark_task_completed(self, task_id: str, output_filename: str = None):
        """标记任务完成"""
        task_info = self.load_task_info(task_id)
        if not task_info:
            return

        task_info.status = 'completed'
        task_info.progress = 100
        task_info.message = '文档生成成功'
        task_info.completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task_info.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if output_filename:
            task_info.output_filename = output_filename

        self._save_task_info(task_id, task_info)

    def mark_task_failed(self, task_id: str, error_message: str):
        """标记任务失败"""
        task_info = self.load_task_info(task_id)
        if not task_info:
            return

        task_info.status = 'failed'
        task_info.message = f'生成失败：{error_message}'
        task_info.completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task_info.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self._save_task_info(task_id, task_info)

    def set_current_chapter(self, task_id: str, chapter_title: str):
        """设置当前章节标题（用于兼容旧代码）"""
        # 持久化版本使用 current_chapter_index，这个方法仅用于兼容
        pass

    def set_pending_confirmation(self, task_id: str, pending: bool):
        """设置等待确认状态（用于兼容旧代码）"""
        # 持久化版本不支持等待确认功能
        pass


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
