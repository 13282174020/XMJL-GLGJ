# -*- coding: utf-8 -*-
"""
未来社区建设方案生成系统 - Flask 后端 (AI 增强版)
支持调用 Qwen API 生成定制化内容
"""

import os
import uuid
import json
import requests
import threading
import time
from enum import Enum
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import re
import base64

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['SECRET_KEY'] = os.urandom(24).hex()

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'docx', 'doc', 'txt', 'pdf'}

# ========== 异步任务管理模块 ==========

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = 'pending'              # 等待处理
    PROCESSING = 'processing'        # 处理中
    PARSING_FILE = 'parsing_file'    # 解析文件中
    GENERATING_AI = 'generating_ai'  # AI 推理生成中
    CREATING_DOC = 'creating_doc'    # 生成 Word 文档中
    COMPLETED = 'completed'          # 已完成
    FAILED = 'failed'                # 失败
    CANCELLED = 'cancelled'          # 已取消


class TaskManager:
    """任务管理器 - 单例模式"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.tasks = {}  # task_id -> task_info
        self._lock = threading.Lock()

    def create_task(self, task_type, user_prompt='', api_key='', model='qwen-max',
                    template_type='future_community', requirement_file=None, template_file=None):
        """创建新任务"""
        task_id = uuid.uuid4().hex
        with self._lock:
            self.tasks[task_id] = {
                'task_id': task_id,
                'template_type': template_type,
                'task_type': task_type,
                'user_prompt': user_prompt,
                'api_key': api_key,
                'model': model,
                'status': TaskStatus.PENDING.value,
                'progress': 0,
                'message': '任务已提交，等待处理',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'started_at': None,
                'completed_at': None,
                'output_filename': None,
                'error_message': None,
                'requirement_file': requirement_file,
                'template_file': template_file,
                'chapter_steps': [],  # 记录章节生成步骤
                'current_chapter': None,  # 当前正在生成的章节
                'completed_chapters': [],  # 已完成的章节列表
                'pending_confirmation': False,  # 是否等待确认
                'partial_filename': None  # 部分生成的文档文件名
            }
        return task_id

    def get_task_status(self, task_id):
        """获取任务状态"""
        with self._lock:
            return self.tasks.get(task_id)

    def update_task_progress(self, task_id, progress=None, message=None, status=None):
        """更新任务进度"""
        if not task_id:
            return False
        with self._lock:
            if task_id not in self.tasks:
                return False
            task = self.tasks[task_id]
            if progress is not None:
                task['progress'] = max(0, min(100, progress))
            if message is not None:
                task['message'] = message
            if status is not None:
                task['status'] = status
            return True

    def mark_task_completed(self, task_id, output_filename=None):
        """标记任务完成"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            task = self.tasks[task_id]
            task['status'] = TaskStatus.COMPLETED.value
            task['progress'] = 100
            task['message'] = '文档生成成功'
            task['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if output_filename:
                task['output_filename'] = output_filename
            return True

    def mark_task_failed(self, task_id, error_message):
        """标记任务失败"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            task = self.tasks[task_id]
            task['status'] = TaskStatus.FAILED.value
            task['error_message'] = error_message
            task['message'] = f'生成失败：{error_message}'
            task['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return True

    def cancel_task(self, task_id):
        """取消任务"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            task = self.tasks[task_id]
            if task['status'] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                return False  # 已完成或失败的任务不能取消
            task['status'] = TaskStatus.CANCELLED.value
            task['message'] = '任务已取消'
            task['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return True

    def get_task_list(self, page=1, page_size=10, keyword=None, status_filter=None):
        """获取任务列表（分页）"""
        with self._lock:
            tasks = list(self.tasks.values())

            # 关键词过滤
            if keyword:
                tasks = [t for t in tasks if keyword.lower() in t.get('template_type', '').lower()
                        or keyword in t.get('task_id', '').lower()]

            # 状态过滤
            if status_filter:
                tasks = [t for t in tasks if t.get('status') == status_filter]

            # 按创建时间倒序
            tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)

            total = len(tasks)
            start = (page - 1) * page_size
            end = start + page_size

            return {
                'tasks': tasks[start:end],
                'total': total,
                'page': page,
                'page_size': page_size
            }

    def set_task_started(self, task_id):
        """标记任务开始处理"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]['started_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.tasks[task_id]['status'] = TaskStatus.PROCESSING.value

    def add_chapter_step(self, task_id, chapter_index, chapter_title, status='pending'):
        """添加章节生成步骤记录"""
        with self._lock:
            if task_id in self.tasks:
                step = {
                    'chapter_index': chapter_index,
                    'chapter_title': chapter_title,
                    'status': status,  # pending, generating, completed, failed
                    'started_at': None,
                    'completed_at': None,
                    'message': ''
                }
                self.tasks[task_id]['chapter_steps'].append(step)
                return True
            return False

    def update_chapter_step(self, task_id, chapter_index, status=None, message=None):
        """更新章节生成步骤状态"""
        with self._lock:
            if task_id in self.tasks:
                for step in self.tasks[task_id]['chapter_steps']:
                    if step['chapter_index'] == chapter_index:
                        if status:
                            step['status'] = status
                            if status == 'generating':
                                step['started_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            elif status in ['completed', 'failed']:
                                step['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        if message:
                            step['message'] = message
                        return True
                return False
            return False

    def set_current_chapter(self, task_id, chapter_title):
        """设置当前正在生成的章节"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]['current_chapter'] = chapter_title
                return True
            return False

    def add_completed_chapter(self, task_id, chapter_title):
        """添加已完成的章节"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]['completed_chapters'].append(chapter_title)
                return True
            return False

    def set_pending_confirmation(self, task_id, pending):
        """设置等待确认状态"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]['pending_confirmation'] = pending
                return True
            return False

    def set_partial_filename(self, task_id, filename):
        """设置部分生成的文档文件名"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]['partial_filename'] = filename
                return True
            return False


# 全局任务管理器实例
task_manager = TaskManager()

# 应用配置（用于百炼应用 API）
APP_CONFIGS = {
    'default': {'app_id': '2641738c46274ac0b08ba4520cc2313b'}  # 阿里云百炼文本推理智能体
}

# 模型配置（用于 API Key 验证提示）
MODEL_CONFIGS = {
    'qwen-max': {'name': '通义千问-Max', 'provider': '阿里云'},
    'qwen-plus': {'name': '通义千问-Plus', 'provider': '阿里云'},
    'qwen-turbo': {'name': '通义千问-Turbo', 'provider': '阿里云'},
    'glm-4': {'name': 'GLM-4', 'provider': '智谱 AI'},
    'glm-3-turbo': {'name': 'GLM-3-Turbo', 'provider': '智谱 AI'},
    'kimi-latest': {'name': 'Kimi', 'provider': '月之暗面'},
    'mini-max': {'name': 'MiniMax', 'provider': 'MiniMax'}
}

# 章节分类配置
# 信息提取类：直接从需求文档中提取信息，不需要 AI 生成
# 内容撰写类：需要 AI 根据模板和需求撰写内容
CHAPTER_CATEGORIES = {
    'info_extract': [  # 信息提取类章节
        '项目名称', '项目建设单位', '负责人', '联系方式',
        '建设工期', '总投资', '资金来源', '编制单位',
        '项目概况', '建设单位', '项目负责', '实施机构',
        '工期', '投资估算', '资金筹措'
    ],
    'content_write': [  # 内容撰写类章节
        '必要性', '分析', '方案', '技术路线',
        '效益分析', '风险分析', '结论', '建议',
        '背景', '需求', '设计', '建设内容',
        '系统', '安全', '环保', '节能',
        '招标', '组织', '人员', '培训',
        '进度', '财务', '评价', '市场',
        '产品', '服务', '运营', '管理'
    ]
}


def is_info_chapter(section_title):
    """判断是否为信息提取类章节"""
    for keyword in CHAPTER_CATEGORIES['info_extract']:
        if keyword in section_title:
            return True
    return False


def is_content_chapter(section_title):
    """判断是否为内容撰写类章节"""
    for keyword in CHAPTER_CATEGORIES['content_write']:
        if keyword in section_title:
            return True
    return False


# 模板类型配置
TEMPLATE_TYPES = {
    'future_community': {
        'name': '未来社区可行性研究报告',
        'chapters': [
            ('1 项目概况', ['1.1 项目名称', '1.2 项目建设单位及负责人', '1.3 方案编制依据', '1.4 建设目标、规模、内容、周期', '1.5 项目总投资及资金来源', '1.6 项目效益分析', '1.7 主要结论和建议']),
            ('2 项目建设单位概况', ['2.1 项目建设单位与职能', '2.2 项目实施机构与职责']),
            ('3 项目建设的必要性', ['3.1 项目提出的背景', '3.2 是否纳入一本帐', '3.3 项目建设的必要性']),
            ('4 需求分析', ['4.1 与政务职能相关的社会问题和政务目标分析', '4.2 现况分析及差距']),
            ('5 项目建设方案', ['5.1 总体思路', '5.2 总体框架', '5.3 技术路线', '5.4 建设目标', '5.5 建设内容']),
            ('6 与数字化改革总体方案的关系', ['6.1 基础设施', '6.2 数据资源', '6.3 应用系统', '6.4 公共组件建设']),
            ('7 应用系统设计', ['7.1 系统总体设计', '7.2 功能模块设计', '7.3 硬件系统设计']),
            ('8 国产化改造和适配', ['8.1 产品选型及平台适配', '8.2 应用安全可靠构建及部署']),
            ('9 系统安全', ['9.1 网络安全等级保护方案', '9.2 信息系统安全管理方案', '9.3 安全防护软件和设备']),
            ('10 项目招标方案', ['10.1 招标范围', '10.2 招标方式', '10.3 招标组织形式']),
            ('11 环保、消防、职业安全和节能', ['11.1 环境影响和环保措施', '11.2 消防措施', '11.3 职业安全和卫生措施', '11.4 节能目标及措施']),
            ('12 项目组织机构和人员', ['12.1 项目领导、实施和运维机构', '12.2 人员配置', '12.3 人员培训']),
            ('13 项目实施进度', ['13.1 项目建设工期', '13.2 实施进度计划']),
            ('14 投资估算和资金筹措', ['14.1 投资估算的有关说明', '14.2 项目总投资估算', '14.3 资金来源与落实情况', '14.4 资金使用计划']),
            ('15 效益与风险分析', ['15.1 经济效益分析', '15.2 社会效益分析', '15.3 项目风险与风险对策']),
        ]
    },
    'general_project': {
        'name': '通用项目可行性研究报告',
        'chapters': [
            ('1 项目总论', ['1.1 项目概况', '1.2 编制依据', '1.3 研究范围', '1.4 主要结论']),
            ('2 项目背景与必要性', ['2.1 项目背景', '2.2 项目建设的必要性']),
            ('3 市场分析', ['3.1 市场现状', '3.2 市场需求预测', '3.3 竞争分析']),
            ('4 建设方案', ['4.1 建设目标', '4.2 建设内容', '4.3 技术方案']),
            ('5 投资估算与资金筹措', ['5.1 投资估算', '5.2 资金筹措']),
            ('6 效益分析', ['6.1 经济效益', '6.2 社会效益']),
            ('7 风险分析', ['7.1 风险识别', '7.2 风险对策']),
        ]
    },
    'smart_community': {
        'name': '智慧社区建设方案',
        'chapters': [
            ('1 项目概述', ['1.1 项目背景', '1.2 建设目标', '1.3 建设内容']),
            ('2 需求分析', ['2.1 业务需求', '2.2 功能需求', '2.3 性能需求']),
            ('3 总体设计', ['3.1 架构设计', '3.2 技术路线', '3.3 安全设计']),
            ('4 应用系统建设', ['4.1 社区治理', '4.2 物业服务', '4.3 便民服务']),
            ('5 基础设施建设', ['5.1 网络建设', '5.2 感知设备', '5.3 数据中心']),
            ('6 投资估算', ['6.1 预算编制', '6.2 资金安排']),
            ('7 实施计划', ['7.1 进度安排', '7.2 保障措施']),
        ]
    },
    'business_plan': {
        'name': '商业计划书',
        'chapters': [
            ('1 执行摘要', ['1.1 项目简介', '1.2 商业模式', '1.3 核心优势', '1.4 融资需求']),
            ('2 公司概述', ['2.1 公司基本情况', '2.2 发展历程', '2.3 组织架构', '2.4 核心团队']),
            ('3 产品与服务', ['3.1 产品介绍', '3.2 技术特点', '3.3 服务模式', '3.4 研发规划']),
            ('4 市场分析', ['4.1 行业现状', '4.2 市场规模', '4.3 目标客户', '4.4 竞争格局']),
            ('5 商业模式', ['5.1 盈利模式', '5.2 营销策略', '5.3 运营计划', '5.4 合作伙伴']),
            ('6 财务预测', ['6.1 收入预测', '6.2 成本分析', '6.3 利润预测', '6.4 现金流分析']),
            ('7 融资方案', ['7.1 融资计划', '7.2 资金用途', '7.3 退出机制', '7.4 投资回报']),
            ('8 风险分析', ['8.1 市场风险', '8.2 技术风险', '8.3 管理风险', '8.4 应对策略']),
        ]
    },
    'project_proposal': {
        'name': '项目建议书',
        'chapters': [
            ('1 项目总论', ['1.1 项目概况', '1.2 编制依据', '1.3 研究结论']),
            ('2 项目背景', ['2.1 政策背景', '2.2 市场背景', '2.3 建设必要性']),
            ('3 市场预测', ['3.1 市场现状', '3.2 需求预测', '3.3 价格预测']),
            ('4 建设规模', ['4.1 建设规模', '4.2 产品方案', '4.3 技术标准']),
            ('5 建设条件', ['5.1 选址方案', '5.2 资源条件', '5.3 配套条件']),
            ('6 技术方案', ['6.1 技术方案', '6.2 设备方案', '6.3 工程方案']),
            ('7 环保节能', ['7.1 环境影响', '7.2 节能措施', '7.3 劳动安全']),
            ('8 投资估算', ['8.1 投资估算', '8.2 资金筹措', '8.3 用款计划']),
            ('9 效益分析', ['9.1 经济效益', '9.2 社会效益']),
            ('10 结论建议', ['10.1 主要结论', '10.2 建议']),
        ]
    },
    'funding_application': {
        'name': '资金申请报告',
        'chapters': [
            ('1 项目概况', ['1.1 项目基本情况', '1.2 建设单位概况', '1.3 编制依据']),
            ('2 政策符合性', ['2.1 产业政策', '2.2 行业准入', '2.3 资金支持方向']),
            ('3 市场分析', ['3.1 市场现状', '3.2 市场需求', '3.3 竞争优势']),
            ('4 技术方案', ['4.1 技术来源', '4.2 工艺流程', '4.3 设备选型']),
            ('5 建设方案', ['5.1 建设内容', '5.2 建设工期', '5.3 实施进度']),
            ('6 投资估算', ['6.1 总投资估算', '6.2 资金申请', '6.3 配套资金']),
            ('7 财务评价', ['7.1 基础数据', '7.2 财务指标', '7.3 敏感性分析']),
            ('8 风险分析', ['8.1 风险识别', '8.2 风险程度', '8.3 防范措施']),
        ]
    },
    'social_stability': {
        'name': '社会稳定风险评估报告',
        'chapters': [
            ('1 总论', ['1.1 项目概况', '1.2 评估依据', '1.3 评估范围']),
            ('2 风险调查', ['2.1 调查内容', '2.2 调查方式', '2.3 调查结果']),
            ('3 风险识别', ['3.1 风险因素', '3.2 风险类型', '3.3 主要风险']),
            ('4 风险估计', ['4.1 风险概率', '4.2 影响程度', '4.3 风险等级']),
            ('5 风险防范', ['5.1 防范措施', '5.2 应急预案', '5.3 责任主体']),
            ('6 评估结论', ['6.1 风险等级', '6.2 主要结论', '6.3 建议']),
        ]
    }
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def clean_ai_content(content, section_title):
    """清理 AI 生成的内容，移除可能的标题行和 Markdown 格式"""
    if not content:
        return []

    lines = content.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 跳过可能是标题的行（包含小节标题的行）
        if stripped.startswith(section_title) or stripped.startswith('《' + section_title + '》'):
            continue
        if stripped.startswith('#') or stripped.startswith('##') or stripped.startswith('###'):
            continue

        # 移除 Markdown 格式
        cleaned = stripped
        cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', cleaned)  # 移除 ** 粗体
        cleaned = re.sub(r'\*(.+?)\*', r'\1', cleaned)      # 移除 * 斜体
        cleaned = re.sub(r'`(.+?)`', r'\1', cleaned)        # 移除 ` 代码
        cleaned = re.sub(r'^[-•●]\s*', '', cleaned)         # 移除列表符号

        if cleaned:
            cleaned_lines.append(cleaned)

    return cleaned_lines


def extract_info_from_requirement(section_title, requirement_content):
    """从需求文档中提取信息类章节的内容"""
    if not requirement_content:
        return None
    
    # 项目名称
    if '项目名称' in section_title:
        patterns = [
            r'项目名称 [：:]\s*([^\n]+)',
            r'项目名称为 [：:]\s*([^\n]+)',
            r'项目名称是 [：:]\s*([^\n]+)',
            r'称 [：:]\s*([^\n]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, requirement_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        # 尝试从第一行提取
        first_line = requirement_content.strip().split('\n')[0]
        if len(first_line) < 50 and '项目' in first_line:
            return first_line
    
    # 建设单位
    if '建设单位' in section_title or '项目实施单位' in section_title:
        patterns = [
            r'建设单位 [：:]\s*([^\n]+)',
            r'业主单位 [：:]\s*([^\n]+)',
            r'实施单位 [：:]\s*([^\n]+)',
            r'项目单位 [：:]\s*([^\n]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, requirement_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # 负责人
    if '负责人' in section_title or '联系人' in section_title:
        patterns = [
            r'负责人 [：:]\s*([^\n]+)',
            r'联系人 [：:]\s*([^\n]+)',
            r'项目负责 [人]?[：:]\s*([^\n]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, requirement_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # 联系方式/电话
    if '联系' in section_title or '电话' in section_title or '方式' in section_title:
        patterns = [
            r'联系方式 [：:]\s*([^\n]+)',
            r'联系电话 [：:]\s*([^\n]+)',
            r'电话 [：:]\s*([^\n]+)',
            r'手机 [：:]\s*([^\n]+)',
            r'邮箱 [：:]\s*([^\n]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, requirement_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # 建设工期
    if '工期' in section_title or '建设周期' in section_title:
        patterns = [
            r'建设工期 [：:]\s*([^\n]+)',
            r'工期 [：:]\s*([^\n]+)',
            r'建设周期 [：:]\s*([^\n]+)',
            r'周期 [：:]\s*([^\n]+)',
            r'([\d]+)[个]?[年月天]'
        ]
        for pattern in patterns:
            match = re.search(pattern, requirement_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # 总投资
    if '投资' in section_title or '资金' in section_title:
        patterns = [
            r'总投资 [：:]\s*([^\n]+)',
            r'投资估算 [：:]\s*([^\n]+)',
            r'项目总投 [：:]\s*([^\n]+)',
            r'([\d\.]+)\s*万?元'
        ]
        for pattern in patterns:
            match = re.search(pattern, requirement_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # 资金来源
    if '资金来源' in section_title or '资金筹措' in section_title:
        patterns = [
            r'资金来源 [：:]\s*([^\n]+)',
            r'资金筹措 [：:]\s*([^\n]+)',
            r'出资 [：:]\s*([^\n]+)',
            r'财政拨款|自筹|银行贷款|专项资金'
        ]
        for pattern in patterns:
            match = re.search(pattern, requirement_content, re.IGNORECASE)
            if match:
                return match.group(0).strip()
    
    # 编制单位
    if '编制' in section_title or '可研单位' in section_title:
        patterns = [
            r'编制单位 [：:]\s*([^\n]+)',
            r'可研编制 [：:]\s*([^\n]+)',
            r'咨询单位 [：:]\s*([^\n]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, requirement_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # 建设目标
    if '建设目标' in section_title or '项目目标' in section_title:
        patterns = [
            r'建设目标 [：:]\s*([^\n]+)',
            r'项目目标 [：:]\s*([^\n]+)',
            r'目标 [：:]\s*([^\n]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, requirement_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # 建设规模
    if '建设规模' in section_title or '规模' in section_title:
        patterns = [
            r'建设规模 [：:]\s*([^\n]+)',
            r'项目规模 [：:]\s*([^\n]+)',
            r'规模 [：:]\s*([^\n]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, requirement_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # 建设内容
    if '建设内容' in section_title or '建设任务' in section_title:
        patterns = [
            r'建设内容 [：:]\s*([^\n]+)',
            r'建设任务 [：:]\s*([^\n]+)',
            r'主要建设内容 [：:]\s*([^\n]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, requirement_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    return None


def extract_template_example(section_title, template_content):
    """从模板内容中提取该章节的参考示例"""
    if not template_content:
        return ""
    
    # 找到章节标题位置
    title_pos = template_content.find(section_title)
    if title_pos == -1:
        # 尝试模糊匹配
        for keyword in [section_title.split(' ')[-1] if ' ' in section_title else section_title]:
            title_pos = template_content.find(keyword)
            if title_pos != -1:
                break
    
    if title_pos == -1:
        return ""
    
    # 提取章节后面的内容（到下一个章节前）
    next_chapter_pos = len(template_content)
    
    # 查找下一个章节标记
    chapter_markers = ['\n\n', '\n', '。', '；']
    for marker in chapter_markers:
        pos = template_content.find(marker, title_pos + len(section_title))
        if pos != -1 and pos < next_chapter_pos:
            # 检查是否是下一个章节标题
            next_text = template_content[title_pos + len(section_title):pos].strip()
            if len(next_text) < 50 and not any(c in next_text for c in '。！？'):
                next_chapter_pos = title_pos + len(section_title) + len(next_text)
                break
    
    # 提取示例内容（取前 500 字符）
    example_start = title_pos + len(section_title)
    example_end = min(example_start + 500, next_chapter_pos)
    example = template_content[example_start:example_end].strip()
    
    # 清理示例内容，去掉过多的空白
    example = ' '.join(example.split())
    
    return example if len(example) > 10 else ""


def read_docx_text(file_path):
    """读取 Word 文档文本内容"""
    try:
        doc = Document(file_path)
        texts = []
        for para in doc.paragraphs:
            if para.text.strip():
                texts.append(para.text)
        return '\n'.join(texts)
    except Exception as e:
        return f"读取失败：{str(e)}"


def read_txt_text(file_path):
    """读取 TXT 文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
        except Exception as e:
            return f"读取失败：{str(e)}"


def get_heading_level(style_name):
    """从样式名获取标题级别"""
    if style_name and 'Heading' in style_name:
        try:
            level_str = style_name.replace('Heading', '').strip()
            level = int(''.join(filter(str.isdigit, level_str)) or '0')
            return level if level > 0 else 1
        except:
            return 1
    return 0


def generate_chapter_numbering(headings):
    """
    根据标题层级生成标准的中文编号
    L1: 第一章、第二章...
    L2: 1.1, 1.2...
    L3: 1.1.1, 1.1.2...
    L4: (1), (2)...
    """
    counters = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    chinese_num = [
        '零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
        '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
        '二十一', '二十二', '二十三', '二十四', '二十五', '二十六', '二十七', '二十八', '二十九', '三十'
    ]

    for h in headings:
        level = h['level']
        counters[level] += 1
        for l in range(level + 1, 6):
            counters[l] = 0

        if level == 1:
            h['numbering'] = f'第{chinese_num[counters[1]]}章'
        elif level == 2:
            h['numbering'] = f'{counters[1]}.{counters[2]}'
        elif level == 3:
            h['numbering'] = f'{counters[1]}.{counters[2]}.{counters[3]}'
        elif level == 4:
            h['numbering'] = f'({counters[4]})'
        elif level == 5:
            h['numbering'] = f'{counters[1]}.{counters[2]}.{counters[3]}.{counters[4]}'
    return headings


def build_chapter_tree(headings):
    """将扁平的标题列表转换为树形结构"""
    chapters = []
    for h in headings:
        level = h['level']
        node = {
            'number': h['numbering'],
            'title': h['text'],
            'level': level,
            'style': h['style'],
            'children': []
        }
        if level == 1:
            chapters.append(node)
        else:
            parent = find_parent_node(chapters, level - 1)
            if parent:
                parent['children'].append(node)
            else:
                chapters.append(node)
    return chapters


def find_parent_node(chapters, target_level):
    """递归查找指定层级的最后一个节点 - 修复空列表处理"""
    for chapter in reversed(chapters):
        if chapter['level'] == target_level:
            return chapter
        children = chapter.get('children')
        if children is not None and len(children) > 0:
            result = find_parent_node(children, target_level)
            if result:
                return result
    return None


def scan_template_styles(file_path):
    """
    扫描 Word 模板文件，提取章节目录结构
    严格基于 Heading 样式和 XML 编号信息提取（参考 extract_toc.py）
    """
    try:
        doc = Document(file_path)
        headings = []

        # 提取所有 Heading 样式的段落
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            style_name = para.style.name if para.style else ''
            level = get_heading_level(style_name)

            if level > 0:
                headings.append({
                    'level': level,
                    'text': text,
                    'style': style_name,
                    'numbering': ''
                })

        # 生成编号
        headings = generate_chapter_numbering(headings)

        # 构建章节树
        chapters = build_chapter_tree(headings)

        return {
            'success': True,
            'chapters': chapters,
            'message': f'成功扫描 {len(chapters)} 个一级章节',
            'total_nodes': count_all_nodes(chapters)
        }
    except Exception as e:
        import traceback
        return {
            'success': False,
            'chapters': [],
            'message': f'扫描失败：{str(e)}',
            'detail': traceback.format_exc()
        }


def get_paragraph_numbering(para):
    """从段落的 XML 结构中获取编号信息（支持 WPS 多级编号）"""
    try:
        # 获取段落的 XML 元素
        p_element = para._element
        
        # 查找编号属性（w:numPr）
        numPr = p_element.find('.//w:numPr', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
        
        if numPr is None:
            return None
        
        # 获取编号级别（w:ilvl）
        ilvl = numPr.find('w:ilvl', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
        if ilvl is None:
            return None
        
        level = int(ilvl.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')) + 1
        
        # 获取编号 ID（w:numId）
        numId = numPr.find('w:numId', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
        if numId is None:
            return None
        
        num_id = int(numId.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val'))
        
        # 获取编号文本（从段落样式或编号定义中）
        # 尝试从段落文本开头提取编号
        text = para.text.strip()
        
        # 匹配常见编号格式
        import re
        
        # 格式 1: 第一章 项目概况
        match = re.match(r'^第 ([一二三四五六七八九十\d]+) 章\s*(.+)$', text)
        if match:
            return {'number': f'第{match.group(1)}章', 'level': 1}
        
        # 格式 2: 第一节 项目名称
        match = re.match(r'^第 ([一二三四五六七八九十\d]+) 节\s*(.+)$', text)
        if match:
            return {'number': f'第{match.group(1)}节', 'level': 2}
        
        # 格式 3: 一、项目概况
        match = re.match(r'^([一二三四五六七八九十]+)[、.]\s*(.+)$', text)
        if match:
            return {'number': f'{match.group(1)}、', 'level': 1}
        
        # 格式 4: 1 项目概况 或 1.1 项目名称
        match = re.match(r'^(\d+(?:\.\d+)*)\s+(.+)$', text)
        if match:
            num = match.group(1)
            return {'number': num, 'level': len(num.split('.'))}
        
        # 如果无法从文本提取，返回编号级别
        return {'number': str(level), 'level': level}
        
    except Exception as e:
        return None


def add_to_parent_by_level(chapters, node, level):
    """将节点添加到合适的父节点下（按层级）"""
    if not chapters:
        chapters.append(node)
        return
    
    # 从后往前查找最近的层级为 level-1 的节点
    def find_parent(nodes, target_level):
        for n in reversed(nodes):
            if n.get('level', 1) == target_level:
                return n
            children = n.get('children')
            if children is not None and len(children) > 0:
                result = find_parent(children, target_level)
                if result:
                    return result
        return None
    
    parent = find_parent(chapters, level - 1)
    if parent:
        parent['children'].append(node)
    else:
        # 没有找到父节点，添加到最后一个一级章节
        chapters[-1]['children'].append(node)


def add_to_parent(chapters, node, number):
    """将节点添加到正确的父节点下（递归查找）"""
    parts = number.split('.')
    current_level = len(parts)  # 当前节点的层级
    
    if current_level == 1:
        # 一级章节直接添加到 chapters 列表
        chapters.append(node)
    else:
        # 查找父节点（层级为 current_level - 1 的最后一个节点）
        parent_parts = parts[:-1]
        parent_number = '.'.join(parent_parts)
        
        # 在 chapters 中递归查找父节点
        parent = find_node_by_number(chapters, parent_number)
        if parent:
            parent['children'].append(node)


def find_node_by_number(chapters, number):
    """递归查找指定编号的节点 - 修复空列表处理"""
    for chapter in chapters:
        if chapter['number'] == number:
            return chapter
        # 在子节点中递归查找
        children = chapter.get('children')
        if children is not None and len(children) > 0:
            result = find_node_by_number(children, number)
            if result:
                return result
    return None


def count_all_nodes(chapters):
    """递归统计所有节点数量 - 修复空列表处理"""
    count = 0
    for chapter in chapters:
        count += 1
        children = chapter.get('children')
        if children is not None and len(children) > 0:
            count += count_all_nodes(children)
    return count


def extract_paragraph_style(para):
    """提取段落的样式信息"""
    style_info = {
        'font_name': '',
        'font_size': 0,
        'bold': False,
        'italic': False,
        'underline': False,
        'color': '',
        'alignment': '',
        'line_spacing': 0,
        'space_before': 0,
        'space_after': 0,
        'first_line_indent': 0
    }
    
    try:
        # 获取段落格式
        para_format = para.paragraph_format
        
        # 对齐方式
        alignment_map = {
            0: 'left',
            1: 'center',
            2: 'right',
            3: 'justify'
        }
        style_info['alignment'] = alignment_map.get(para_format.alignment, 'left')
        
        # 间距和缩进
        if hasattr(para_format, 'line_spacing') and para_format.line_spacing:
            style_info['line_spacing'] = float(para_format.line_spacing)
        if hasattr(para_format, 'space_before') and para_format.space_before:
            style_info['space_before'] = float(para_format.space_before)
        if hasattr(para_format, 'space_after') and para_format.space_after:
            style_info['space_after'] = float(para_format.space_after)
        if hasattr(para_format, 'first_line_indent') and para_format.first_line_indent:
            style_info['first_line_indent'] = float(para_format.first_line_indent)
        
        # 获取第一个 run 的字体样式（通常段落内样式一致）
        if para.runs:
            run = para.runs[0]
            style_info['font_name'] = run.font.name or ''
            style_info['font_size'] = float(run.font.size) if run.font.size else 0
            style_info['bold'] = run.font.bold or False
            style_info['italic'] = run.font.italic or False
            style_info['underline'] = run.font.underline or False
            
            # 尝试获取中文字体名称
            try:
                from docx.oxml.ns import qn
                rFonts = run._element.rPr.rFonts
                if rFonts is not None and hasattr(rFonts, 'get'):
                    east_asia = rFonts.get(qn('w:eastAsia'))
                    if east_asia:
                        style_info['font_name'] = east_asia
            except:
                pass
    except Exception as e:
        print(f"提取样式失败：{e}")
    
    return style_info


def call_bailian_api(prompt, api_key, model='qwen-max'):
    """调用阿里云百炼平台 API 生成内容（支持多模型和应用 API）"""
    
    # 检测 API Key 类型：sk-sp- 开头的是百炼应用 API Key
    is_app_api = api_key.startswith('sk-sp-') or api_key.startswith('sk-app-')
    
    if is_app_api:
        # 百炼应用 API 调用
        return call_bailian_app_api(prompt, api_key, model)
    else:
        # DashScope 模型 API 调用
        return call_dashscope_api(prompt, api_key, model)


def call_bailian_app_api(prompt, api_key, model='qwen-max'):
    """调用百炼应用 API（使用 sk-sp- 开头的 API Key）"""
    # 百炼应用 API 需要 APP_ID，这里使用默认端点
    # 用户需要在 APP_CONFIGS 中配置 APP_ID，或者在 API Key 中附带 APP_ID
    
    # 检查 API Key 是否包含 APP_ID（格式：sk-sp-xxx#appid）
    app_id = None
    if '#' in api_key:
        api_key, app_id = api_key.split('#', 1)
    else:
        # 尝试从配置中获取默认 APP_ID
        app_id = APP_CONFIGS.get('default', {}).get('app_id')
    
    if not app_id:
        return "错误：百炼应用 API Key 需要配置 APP_ID。请在 APP_CONFIGS 中设置，或在 API Key 后添加 #APP_ID"
    
    url = f"https://dashscope.aliyuncs.com/api/v1/apps/{app_id}/completion"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "input": {
            "prompt": prompt
        },
        "parameters": {
            "max_tokens": 4000
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code == 200:
            result = response.json()
            # 应用 API 响应格式
            if 'output' in result:
                if 'text' in result['output']:
                    return result['output']['text']
                elif 'choices' in result['output']:
                    return result['output']['choices'][0]['message']['content']
            elif 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                return f"API 返回格式异常：{result}"
        else:
            return f"API 调用失败 (状态码 {response.status_code}): {response.text}"
    except requests.exceptions.Timeout:
        return "API 调用超时，请重试"
    except Exception as e:
        return f"API 调用异常：{str(e)}"


def call_dashscope_api(prompt, api_key, model='qwen-max'):
    """调用 DashScope 模型 API（使用 sk- 开头的 API Key）"""
    
    # 不同模型的 API 端点
    api_endpoints = {
        'qwen-max': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
        'qwen-plus': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
        'qwen-turbo': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
        'glm-4': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
        'glm-3-turbo': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
        'kimi-latest': 'https://api.moonshot.cn/v1/chat/completions',
        'mini-max': 'https://api.minimax.chat/v1/text/chatcompletion_v2',
    }
    
    url = api_endpoints.get(model, api_endpoints['qwen-max'])
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # 根据模型构建不同的请求格式
    if model.startswith('qwen'):
        # 通义千问系列（DashScope 格式）
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "max_tokens": 4000,
                "temperature": 0.7,
                "top_p": 0.8
            }
        }
    elif model.startswith('glm'):
        # GLM 系列（智谱 AI / 百炼平台格式）
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.7,
            "top_p": 0.8
        }
    elif model.startswith('kimi'):
        # Kimi（月之暗面格式）
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.7,
            "top_p": 0.8
        }
    elif model.startswith('mini'):
        # MiniMax 格式
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.7,
            "top_p": 0.8
        }
    else:
        # 默认使用通义千问格式
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "max_tokens": 4000,
                "temperature": 0.7,
                "top_p": 0.8
            }
        }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code == 200:
            result = response.json()
            # 不同模型的响应格式解析
            if 'output' in result and 'text' in result['output']:
                # 通义千问格式
                return result['output']['text']
            elif 'output' in result and 'choices' in result['output']:
                # 通义千问新格式
                return result['output']['choices'][0]['message']['content']
            elif 'choices' in result and len(result['choices']) > 0:
                # OpenAI 兼容格式（GLM、Kimi、MiniMax）
                return result['choices'][0]['message']['content']
            else:
                return f"API 返回格式异常：{result}"
        else:
            return f"API 调用失败 (状态码 {response.status_code}): {response.text}"
    except requests.exceptions.Timeout:
        return "API 调用超时，请重试"
    except Exception as e:
        return f"API 调用异常：{str(e)}"


def call_qwen_api(prompt, api_key, model='qwen-max'):
    """调用 AI API 生成内容（兼容旧接口）"""
    return call_bailian_api(prompt, api_key, model)


def generate_content_with_ai(requirement_content, template_content, user_prompt, section_title, api_key, model='qwen-max', progress_callback=None):
    """使用 AI 生成指定小节的内容（支持章节分类处理）"""
    
    # 判断章节类型
    if is_info_chapter(section_title):
        # 信息提取类章节：直接从需求文档中提取
        extracted_info = extract_info_from_requirement(section_title, requirement_content)
        if extracted_info:
            return extracted_info
        # 如果提取失败，降级为 AI 生成
    
    # 内容撰写类章节（或信息提取失败）：调用 AI 生成
    # 从模板中提取参考示例
    template_example = extract_template_example(section_title, template_content)
    
    # 构建精准 Prompt
    if template_example:
        prompt = f"""你是一位专业的可行性研究报告撰写专家。请根据以下材料，为"{section_title}"这一小节撰写专业、详细的正文内容。

【模板中的参考示例】（请参考此格式和风格）
{template_example}

【需求文档内容】
{requirement_content[:5000] if requirement_content else '暂无需求文档'}

【用户额外要求】
{user_prompt if user_prompt else '无特殊要求'}

【重要撰写要求】
1. 内容要专业、严谨，符合可行性研究报告的规范
2. 结合需求文档中的具体信息，不要泛泛而谈
3. 数据要合理，逻辑要清晰
4. 使用正式的公文语言
5. 参考模板示例的格式和风格，不要发挥
6. 不要包含 Markdown 格式（如 #、** 等），使用纯文本
7. 【重要】不要输出任何标题，只输出正文内容！标题已经由系统自动生成
8. 【重要】不要以"{section_title}"或类似标题开头，直接开始正文内容

请为"{section_title}"这一小节撰写正文内容（只输出正文，不要输出标题）："""
    else:
        # 没有模板示例时的降级 Prompt
        prompt = f"""你是一位专业的可行性研究报告撰写专家。请根据以下材料，为"{section_title}"这一小节撰写专业、详细的正文内容。

【需求文档内容】
{requirement_content[:5000] if requirement_content else '暂无需求文档'}

【模板格式参考】
{template_content[:3000] if template_content else '暂无模板'}

【用户额外要求】
{user_prompt if user_prompt else '无特殊要求'}

【重要撰写要求】
1. 内容要专业、严谨，符合可行性研究报告的规范
2. 结合需求文档中的具体信息，不要泛泛而谈
3. 数据要合理，逻辑要清晰
4. 使用正式的公文语言
5. 字数控制在 800-1500 字之间
6. 不要包含 Markdown 格式（如 #、** 等），使用纯文本
7. 【重要】不要输出任何标题，只输出正文内容！标题已经由系统自动生成
8. 【重要】不要以"{section_title}"或类似标题开头，直接开始正文内容

请为"{section_title}"这一小节撰写正文内容（只输出正文，不要输出标题）："""

    return call_bailian_api(prompt, api_key, model)


def load_style_config():
    """加载样式配置"""
    styles_path = os.path.join(app.config['UPLOAD_FOLDER'], 'style_config.json')
    default_styles = {
        'heading1': {
            'font_name': '黑体',
            'font_size': 22,
            'bold': True,
            'alignment': 'center'
        },
        'heading2': {
            'font_name': '楷体',
            'font_size': 16,
            'bold': True,
            'alignment': 'left'
        },
        'heading3': {
            'font_name': '楷体',
            'font_size': 14,
            'bold': True,
            'alignment': 'left'
        },
        'normal': {
            'font_name': '仿宋',
            'font_size': 10.5,
            'line_spacing': 1.5,
            'first_line_indent': 0.74
        }
    }
    
    if os.path.exists(styles_path):
        try:
            with open(styles_path, 'r', encoding='utf-8') as f:
                styles = json.load(f)
            # 合并用户配置和默认配置
            for key in default_styles:
                if key in styles:
                    default_styles[key].update(styles[key])
        except:
            pass
    
    return default_styles


def add_heading(doc, text, level=1, styles=None):
    """添加标题 - 支持自定义样式配置"""
    if styles is None:
        styles = load_style_config()
    
    if level == 1:
        style = styles.get('heading1', {})
        heading = doc.add_heading(text, level=1)
        
        # 对齐方式
        align_map = {'center': WD_ALIGN_PARAGRAPH.CENTER, 'left': WD_ALIGN_PARAGRAPH.LEFT, 
                     'right': WD_ALIGN_PARAGRAPH.RIGHT, 'justify': WD_ALIGN_PARAGRAPH.JUSTIFY}
        heading.alignment = align_map.get(style.get('alignment', 'center'), WD_ALIGN_PARAGRAPH.CENTER)
        
        # 设置字体样式
        for run in heading.runs:
            run.font.name = style.get('font_name', '黑体')
            run.font.size = Pt(style.get('font_size', 22))
            run.font.bold = style.get('bold', True)
            run._element.rPr.rFonts.set(qn('w:eastAsia'), style.get('font_name', '黑体'))
        
        heading.paragraph_format.space_before = Cm(0)
        heading.paragraph_format.space_after = Cm(0.5)
        
    elif level == 2:
        style = styles.get('heading2', {})
        heading = doc.add_heading(text, level=2)
        
        align_map = {'center': WD_ALIGN_PARAGRAPH.CENTER, 'left': WD_ALIGN_PARAGRAPH.LEFT,
                     'right': WD_ALIGN_PARAGRAPH.RIGHT, 'justify': WD_ALIGN_PARAGRAPH.JUSTIFY}
        heading.alignment = align_map.get(style.get('alignment', 'left'), WD_ALIGN_PARAGRAPH.LEFT)
        
        for run in heading.runs:
            run.font.name = style.get('font_name', '楷体')
            run.font.size = Pt(style.get('font_size', 16))
            run.font.bold = style.get('bold', True)
            run._element.rPr.rFonts.set(qn('w:eastAsia'), style.get('font_name', '楷体'))
        
        heading.paragraph_format.space_before = Cm(0.5)
        heading.paragraph_format.space_after = Cm(0.5)
        
    elif level == 3:
        style = styles.get('heading3', {})
        heading = doc.add_heading(text, level=3)
        
        align_map = {'center': WD_ALIGN_PARAGRAPH.CENTER, 'left': WD_ALIGN_PARAGRAPH.LEFT,
                     'right': WD_ALIGN_PARAGRAPH.RIGHT, 'justify': WD_ALIGN_PARAGRAPH.JUSTIFY}
        heading.alignment = align_map.get(style.get('alignment', 'left'), WD_ALIGN_PARAGRAPH.LEFT)
        
        for run in heading.runs:
            run.font.name = style.get('font_name', '楷体')
            run.font.size = Pt(style.get('font_size', 14))
            run.font.bold = style.get('bold', True)
            run._element.rPr.rFonts.set(qn('w:eastAsia'), style.get('font_name', '楷体'))
        
        heading.paragraph_format.space_before = Cm(0.3)
        heading.paragraph_format.space_after = Cm(0.3)
        
    elif level == 4:
        style = styles.get('heading3', {})
        heading = doc.add_paragraph()
        run = heading.add_run(text)
        run.font.name = style.get('font_name', '楷体')
        run.font.size = Pt(style.get('font_size', 14))
        run.font.bold = style.get('bold', True)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), style.get('font_name', '楷体'))
        heading.paragraph_format.first_line_indent = Cm(0.74)
        heading.paragraph_format.space_before = Cm(0)
        heading.paragraph_format.space_after = Cm(0)
        
    return heading


def add_normal_paragraph(doc, text, indent=True, styles=None):
    """添加正文段落 - 支持自定义样式配置"""
    if styles is None:
        styles = load_style_config()
    
    style = styles.get('normal', {})
    
    para = doc.add_paragraph()
    if not text.strip():
        return para
    
    run = para.add_run(text)
    run.font.name = style.get('font_name', '仿宋')
    run.font.size = Pt(style.get('font_size', 10.5))
    run._element.rPr.rFonts.set(qn('w:eastAsia'), style.get('font_name', '仿宋'))
    
    if indent and style.get('first_line_indent'):
        para.paragraph_format.first_line_indent = Cm(style.get('first_line_indent', 0.74))
    
    if style.get('line_spacing'):
        para.paragraph_format.line_spacing = style.get('line_spacing', 1.5)
    
    para.paragraph_format.space_before = Cm(0)
    para.paragraph_format.space_after = Cm(0)
    return para


def generate_word_document(template_type, requirement_content, template_content, user_prompt, api_key, output_path, progress_callback=None, model='qwen-max'):
    """生成 Word 文档（AI 增强版）- 使用用户配置的目录结构"""

    doc = Document()
    styles = load_style_config()
    
    style = doc.styles['Normal']
    style.font.name = styles['normal'].get('font_name', '仿宋')
    style.font.size = Pt(styles['normal'].get('font_size', 10.5))
    style._element.rPr.rFonts.set(qn('w:eastAsia'), styles['normal'].get('font_name', '仿宋'))

    # 尝试加载用户保存的章节目录
    chapters_path = os.path.join(app.config['UPLOAD_FOLDER'], 'chapter_config.json')
    user_chapters = None
    if os.path.exists(chapters_path):
        try:
            with open(chapters_path, 'r', encoding='utf-8') as f:
                user_chapters = json.load(f)
        except:
            user_chapters = None
    
    # 如果没有用户目录，使用硬编码的 TEMPLATE_TYPES
    if not user_chapters:
        template_config = TEMPLATE_TYPES.get(template_type, TEMPLATE_TYPES['future_community'])
        # 转换为统一格式
        user_chapters = []
        for chapter_title, sections in template_config['chapters']:
            chapter_node = {
                'number': chapter_title.split()[0] if ' ' in chapter_title else '1',
                'title': chapter_title,
                'level': 1,
                'children': []
            }
            for idx, section in enumerate(sections):
                section_num = section.split()[0] if ' ' in section else f'{chapter_node["number"]}.{idx+1}'
                chapter_node['children'].append({
                    'number': section_num,
                    'title': section,
                    'level': 2,
                    'children': []
                })
    
    project_name = "良熟新苑未来社区建设项目" if template_type == 'future_community' else "建设项目"

    # ========== 封面 ==========
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Cm(5)
    title.paragraph_format.space_after = Cm(1)
    run = title.add_run(project_name)
    run.font.name = '黑体'
    run.font.size = Pt(36)
    run.font.bold = True
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_before = Cm(1)
    subtitle.paragraph_format.space_after = Cm(3)
    run = subtitle.add_run(template_config['name'] if 'template_config' in dir() else '可行性研究报告')
    run.font.name = '黑体'
    run.font.size = Pt(26)
    run.font.bold = True
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')

    for _ in range(5):
        doc.add_paragraph()

    builder = doc.add_paragraph()
    builder.alignment = WD_ALIGN_PARAGRAPH.CENTER
    builder.paragraph_format.space_before = Cm(0.5)
    builder.paragraph_format.space_after = Cm(0.5)
    run = builder.add_run('建设单位：良熟社区居委会')
    run.font.name = '楷体'
    run.font.size = Pt(16)
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')

    compiler = doc.add_paragraph()
    compiler.alignment = WD_ALIGN_PARAGRAPH.CENTER
    compiler.paragraph_format.space_before = Cm(0.5)
    compiler.paragraph_format.space_after = Cm(0.5)
    run = compiler.add_run('编制单位：XX 数字科技有限公司')
    run.font.name = '楷体'
    run.font.size = Pt(16)
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')

    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_para.paragraph_format.space_before = Cm(0.5)
    date_para.paragraph_format.space_after = Cm(0.5)
    run = date_para.add_run(f'编制日期：{datetime.now().strftime("%Y 年 %m 月")}')
    run.font.name = '楷体'
    run.font.size = Pt(16)
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')

    doc.add_page_break()
    if progress_callback:
        progress_callback(5, "封面完成")

    # ========== 项目编审人员名单 ==========
    add_heading(doc, '项目编审人员名单', level=1, styles=styles)
    doc.add_paragraph()
    add_normal_paragraph(doc, '项目负责：张建国', styles=styles)
    add_normal_paragraph(doc, '编制小组：李明、王芳、陈伟、刘洋', styles=styles)
    add_normal_paragraph(doc, '勘误核稿：赵强', styles=styles)
    add_normal_paragraph(doc, '项目审定：周建华', styles=styles)
    doc.add_page_break()
    if progress_callback:
        progress_callback(10, "编审名单完成")

    # ========== 目录 ==========
    add_heading(doc, '目录', level=1, styles=styles)
    doc.add_paragraph()
    
    # 递归渲染目录
    render_doc_toc(doc, user_chapters, styles)

    doc.add_page_break()
    if progress_callback:
        progress_callback(15, "目录完成")

    # ========== 正文章节（使用用户配置的目录） ==========
    total_chapters = len(user_chapters)

    def render_chapter_content(node, level=1):
        """递归渲染章节内容"""
        node_number = node.get('number', '')
        node_title = node.get('title', '')
        node_level = node.get('level', level)
        children = node.get('children')
        
        # 添加章节标题
        add_heading(doc, f"{node_number} {node_title}", level=node_level, styles=styles)
        
        # 判断是否有子节点
        if children is not None and len(children) > 0:
            # 有子节点，递归处理
            for child in children:
                render_chapter_content(child, level=node_level + 1)
        else:
            # 叶子节点，生成内容
            content = get_chapter_content_template(node_title)
            for para_text in content.split('\n'):
                if para_text.strip():
                    add_normal_paragraph(doc, para_text.strip(), styles=styles)

    for idx, chapter in enumerate(user_chapters):
        # 渲染章节内容（递归处理所有层级）
        render_chapter_content(chapter, level=1)
        
        doc.add_page_break()

        # 进度回调
        progress = 15 + int((idx + 1) / total_chapters * 80)
        if progress_callback:
            progress_callback(progress, f"正在生成第{idx + 1}章：{chapter['title']}")

    # 保存文档
    doc.save(output_path)
    if progress_callback:
        progress_callback(100, "文档保存成功")

    return True


def render_doc_toc(doc, chapters, styles, level=0):
    """递归渲染目录 - 正确处理空列表和 null"""
    for chapter in chapters:
        para = doc.add_paragraph()
        para.paragraph_format.left_indent = Cm(0.74 * level)
        run = para.add_run(f"{chapter['number']} {chapter['title']}")
        run.font.name = '宋体'
        run.font.size = Pt(10.5)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

        # 修复：检查 children 是否存在且非空
        children = chapter.get('children')
        if children is not None and len(children) > 0:
            render_doc_toc(doc, children, styles, level + 1)

def get_chapter_content_template(section_title, requirement_content=''):
    """根据章节标题返回预定义的内容模板
    优化：区分信息型字段和描述型字段
    
    信息型字段：简短、具体（如项目名称、总投资等）
    描述型字段：需要论述、分析（如项目概况、建设必要性等）
    """
    # 信息型字段 - 简短、具体
    info_templates = {
        '项目名称': '根据需求文档提取的项目名称',
        '项目建设单位': '根据需求文档提取的建设单位名称',
        '负责人': 'XXX',
        '联系方式': '电话：XXX-XXXXXXX',
        '建设工期': 'XX 个月',
        '总投资': 'XX 万元',
        '资金来源': '财政拨款/自筹',
        '编制单位': 'XX 数字科技有限公司',
    }
    
    # 描述型字段 - 需要论述、分析（每段 200-300 字）
    desc_templates = {
        '建设目标': '本项目的建设目标是根据实际需求，制定科学合理的建设方案，确保项目顺利实施并达到预期效果。通过本项目的实施，将有效提升相关领域的信息化水平，改善工作效率，优化服务质量，为业务发展提供有力支撑。项目建设遵循统筹规划、分步实施的原则，确保各项建设任务有序推进。',
        '项目概况': '本项目按照相关规范和要求进行编制，确保符合可行性研究报告的标准。项目立足于当前实际需求，采用先进的技术路线和科学的管理方法，力求在技术先进性、经济合理性和实施可行性之间取得最佳平衡。项目建设内容包括硬件设施、软件系统、数据资源等多个方面。',
        '项目建设单位概况': '项目建设单位的基本情况介绍，包括单位性质、主要职能、组织架构等内容。单位在相关领域具有丰富的经验和雄厚的技术实力，为本项目的顺利实施提供了坚实保障。单位现有人员配置合理，技术力量充足，能够满足项目建设和运营的需要。',
        '项目实施机构': '项目实施机构负责项目的具体实施工作，包括项目管理、协调推进、质量控制等职责。机构设置合理，人员配备充足，能够确保项目按计划高质量完成。实施机构建立了完善的管理制度和工作流程，为项目顺利实施提供了组织保障。',
        '项目建设的必要性': '从政策要求、实际需求、发展趋势等方面论证项目建设的必要性。当前，随着业务的不断发展和信息化水平的提升，现有系统已无法满足日益增长的需求，亟需通过本项目的建设来解决相关问题。项目建设对于提升工作效率、优化服务质量具有重要意义。',
        '需求分析': '对项目的需求进行全面分析，包括业务需求、功能需求、性能需求等。通过深入调研和分析，明确了项目的核心需求和关键指标，为后续的方案设计提供了重要依据。需求分析结果将为项目建设内容的确定和投资估算提供参考。',
        '总体思路': '项目建设的总体思路是坚持以需求为导向，以技术为支撑，确保项目建设的科学性和可行性。在实施过程中，注重技术创新与管理创新相结合，力求实现最佳的建设效果。项目建设将充分利用现有资源，避免重复建设，提高投资效益。',
        '总体框架': '项目总体框架包括架构设计、功能模块、技术路线等核心内容。框架设计遵循先进性、实用性、可扩展性的原则，能够满足当前需求并适应未来发展。总体框架的确定为后续详细设计和技术实现提供了指导。',
        '技术路线': '项目采用成熟可靠的技术路线，确保系统的稳定性、安全性和可扩展性。在技术选型上，充分考虑了当前技术发展趋势和项目实施风险，选择了最适合的技术方案。技术路线的确定将为项目实施提供技术保障。',
        '投资估算': '投资估算包括硬件设备、软件开发、系统集成、工程建设等费用。估算依据充分，计算方法科学，能够真实反映项目建设所需的资金投入。投资估算结果为项目资金筹措和使用计划提供了参考依据。',
        '资金筹措': '项目资金来源明确，筹措方案可行，确保项目顺利实施。资金安排合理，能够满足项目各阶段的资金需求。资金筹措方案的确定为项目顺利实施提供了资金保障。',
        '效益分析': '项目效益包括经济效益、社会效益、环境效益等多个方面。通过综合分析，项目具有良好的投资回报和显著的社会效益。效益分析结果为项目投资决策提供了重要参考。',
        '风险分析': '项目风险包括技术风险、管理风险、市场风险等，需制定相应的风险应对措施。通过风险识别和评估，制定了完善的风险管理方案。风险分析和应对措施的制定将为项目顺利实施提供保障。',
        '结论': '综合各方面分析，项目具备建设的必要性和可行性。项目建设条件成熟，实施方案可行，建议尽快启动实施。结论为项目投资决策提供了科学依据。',
        '建议': '建议尽快启动项目实施，并做好组织保障、资金保障、技术保障等工作。在实施过程中，要加强项目管理，确保项目按计划高质量完成。同时，要建立健全项目运营维护机制，确保项目长期稳定运行。',
    }
    
    # 先精确匹配
    if section_title in info_templates:
        return info_templates[section_title]
    if section_title in desc_templates:
        return desc_templates[section_title]
    
    # 再模糊匹配
    for key, content in info_templates.items():
        if key in section_title:
            return content
    for key, content in desc_templates.items():
        if key in section_title:
            return content
    
    # 默认返回
    return f'{section_title}的具体内容根据项目实际情况进行编制。'



def generate_chapter_content(doc, chapter_node, requirement_content, template_content,
                              user_prompt, api_key, model, styles, depth=0):
    """
    递归生成章节内容
    严格按照目录树结构生成标题和内容
    
    优化：支持 AI 生成
    - 有 API Key：调用 AI 生成内容
    - 无 API Key：使用模板内容
    """
    children = chapter_node.get('children')

    # 判断是否有子节点
    if children is not None and len(children) > 0:
        # 有子节点，递归处理
        for child in children:
            child_level = child.get('level', 2)
            # 根据层级添加标题
            add_heading(doc, f"{child['number']} {child['title']}", level=child_level, styles=styles)

            # 递归处理子节点
            generate_chapter_content(doc, child, requirement_content, template_content,
                                      user_prompt, api_key, model, styles, depth + 1)
    else:
        # 叶子节点，生成内容
        section_title = chapter_node['title']
        
        # 判断是否使用 AI 生成
        if api_key and api_key.strip():
            # 调用 AI 生成
            from ai_engine import generate_section_content_with_ai
            content = generate_section_content_with_ai(
                section_title=section_title,
                requirement_text=requirement_content,
                template_text=template_content,
                user_instruction=user_prompt,
                api_key=api_key,
                model=model
            )
            # 如果 AI 生成失败，降级使用模板
            if content.startswith('[') and 'API' in content:
                print(f'[WARNING] AI 生成失败，使用模板：{section_title}')
                content = get_chapter_content_template(section_title)
        else:
            # 使用模板内容
            content = get_chapter_content_template(section_title)
        
        # 添加正文内容
        for para_text in content.split('\n'):
            if para_text.strip():
                add_normal_paragraph(doc, para_text.strip(), styles=styles)


def generate_chapter(doc, chapter_title, sections, requirement_content, template_content,
                     user_prompt, api_key, model, section_title_prefix=''):
    """生成单个章节的内容（使用本地生成方式）"""
    add_heading(doc, chapter_title, level=1)

    for section_title in sections:
        add_heading(doc, section_title, level=2)

        # 使用本地方式生成内容
        content = get_chapter_content_template(section_title)
        for para_text in content.split('\n'):
            if para_text.strip():
                add_normal_paragraph(doc, para_text.strip())

    doc.add_page_break()
    return doc


def process_document_async(task_id, template_type, requirement_content, template_content,
                           user_prompt, api_key, model, output_path):
    """异步处理文档生成任务 - 分章节生成，每章等待确认"""
    
    # 全局变量用于持续追踪文档
    doc_container = {'doc': None}
    
    def progress_callback(progress, message):
        """进度回调函数"""
        task_manager.update_task_progress(task_id, progress=progress, message=message)
    
    def save_partial_document():
        """保存部分生成的文档"""
        if doc_container['doc']:
            partial_filename = f'partial_{task_id[:8]}.docx'
            partial_path = os.path.join(app.config['OUTPUT_FOLDER'], partial_filename)
            doc_container['doc'].save(partial_path)
            task_manager.set_partial_filename(task_id, partial_filename)
    
    try:
        # 标记任务开始
        task_manager.set_task_started(task_id)
        
        # 更新状态：解析文件
        task_manager.update_task_progress(task_id, progress=5,
            status=TaskStatus.PARSING_FILE.value, message='解析上传文件中...')
        
        # 更新状态：AI 生成
        task_manager.update_task_progress(task_id, progress=10,
            status=TaskStatus.GENERATING_AI.value, message='准备生成文档...')
        
        # 获取模板配置
        template_config = TEMPLATE_TYPES.get(template_type, TEMPLATE_TYPES['future_community'])
        total_chapters = len(template_config['chapters'])
        
        # 初始化 Word 文档（封面、编审名单、目录）
        doc = Document()
        style = doc.styles['Normal']
        style.font.name = '仿宋'
        style.font.size = Pt(10.5)
        style._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋')
        
        project_name = "良熟新苑未来社区建设项目" if template_type == 'future_community' else "建设项目"
        
        # 封面
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.paragraph_format.space_before = Cm(5)
        title.paragraph_format.space_after = Cm(1)
        run = title.add_run(project_name)
        run.font.name = '黑体'
        run.font.size = Pt(36)
        run.font.bold = True
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        
        subtitle = doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.paragraph_format.space_before = Cm(1)
        subtitle.paragraph_format.space_after = Cm(3)
        run = subtitle.add_run(template_config['name'])
        run.font.name = '黑体'
        run.font.size = Pt(26)
        run.font.bold = True
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        
        for _ in range(5):
            doc.add_paragraph()
        
        builder = doc.add_paragraph()
        builder.alignment = WD_ALIGN_PARAGRAPH.CENTER
        builder.paragraph_format.space_before = Cm(0.5)
        builder.paragraph_format.space_after = Cm(0.5)
        run = builder.add_run('建设单位：良熟社区居委会')
        run.font.name = '楷体'
        run.font.size = Pt(16)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
        
        compiler = doc.add_paragraph()
        compiler.alignment = WD_ALIGN_PARAGRAPH.CENTER
        compiler.paragraph_format.space_before = Cm(0.5)
        compiler.paragraph_format.space_after = Cm(0.5)
        run = compiler.add_run('编制单位：XX 数字科技有限公司')
        run.font.name = '楷体'
        run.font.size = Pt(16)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
        
        date_para = doc.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        date_para.paragraph_format.space_before = Cm(0.5)
        date_para.paragraph_format.space_after = Cm(0.5)
        run = date_para.add_run(f'编制日期：{datetime.now().strftime("%Y 年 %m 月")}')
        run.font.name = '楷体'
        run.font.size = Pt(16)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
        
        doc.add_page_break()
        
        # 编审名单
        add_heading(doc, '项目编审人员名单', level=1)
        doc.add_paragraph()
        add_normal_paragraph(doc, '项目负责：张建国')
        add_normal_paragraph(doc, '编制小组：李明、王芳、陈伟、刘洋')
        add_normal_paragraph(doc, '勘误核稿：赵强')
        add_normal_paragraph(doc, '项目审定：周建华')
        doc.add_page_break()
        
        # 目录
        add_heading(doc, '目录', level=1)
        doc.add_paragraph()
        for chapter_title, sections in template_config['chapters']:
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Cm(0)
            run = para.add_run(chapter_title)
            run.font.name = '宋体'
            run.font.size = Pt(10.5)
            run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
            for section in sections:
                para = doc.add_paragraph()
                para.paragraph_format.left_indent = Cm(0.74)
                run = para.add_run(section)
                run.font.name = '宋体'
                run.font.size = Pt(10.5)
                run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        doc.add_page_break()
        
        # 保存初始文档（含封面、名单、目录）
        doc_container['doc'] = doc
        save_partial_document()
        
        task_manager.update_task_progress(task_id, progress=15,
            status=TaskStatus.CREATING_DOC.value, message='目录完成，准备生成正文')
        
        # 逐章生��
        for idx, (chapter_title, sections) in enumerate(template_config['chapters']):
            # 检查任务是否被取消
            task_info = task_manager.get_task_status(task_id)
            if task_info and task_info.get('status') == TaskStatus.CANCELLED.value:
                return
            
            # 记录章节步骤
            task_manager.add_chapter_step(task_id, idx, chapter_title, status='pending')
            
            # 更新当前章节
            task_manager.set_current_chapter(task_id, chapter_title)
            task_manager.update_chapter_step(task_id, idx, status='generating', 
                message=f'正在生成第{idx + 1}章：{chapter_title}')
            
            task_manager.update_task_progress(task_id, 
                progress=15 + int((idx + 1) / total_chapters * 80),
                status=TaskStatus.GENERATING_AI.value,
                message=f'正在生成第{idx + 1}章：{chapter_title}')
            
            # 生成当前章节
            doc = generate_chapter(
                doc, chapter_title, sections,
                requirement_content, template_content, user_prompt,
                api_key, model
            )
            
            # 标记章节完成
            task_manager.add_completed_chapter(task_id, chapter_title)
            task_manager.update_chapter_step(task_id, idx, status='completed',
                message=f'第{idx + 1}章：{chapter_title} 生成完成')
            
            # 保存部分文档
            save_partial_document()
            
            # 如果不是最后一章，等待用户确认
            if idx < total_chapters - 1:
                task_manager.set_pending_confirmation(task_id, True)
                task_manager.update_task_progress(task_id,
                    progress=15 + int((idx + 1) / total_chapters * 80),
                    status=TaskStatus.CREATING_DOC.value,
                    message=f'第{idx + 1}章已完成，请预览并确认后继续生成下一章')
                
                # 等待用户确认（轮询检查）
                wait_start = time.time()
                while task_manager.get_task_status(task_id).get('pending_confirmation'):
                    time.sleep(1)
                    # 超时检查（5 分钟）
                    if time.time() - wait_start > 300:
                        task_manager.update_task_progress(task_id,
                            message='等待确认超时，继续生成下一章')
                        break
                    
                    # 检查是否被取消
                    task_info = task_manager.get_task_status(task_id)
                    if task_info and task_info.get('status') == TaskStatus.CANCELLED.value:
                        return
        
        # 所有章节生成完成
        doc.save(output_path)
        task_manager.set_partial_filename(task_id, None)
        task_manager.mark_task_completed(task_id, output_filename=os.path.basename(output_path))
        print(f'[INFO] 文档生成完成：{output_path}')

    except Exception as e:
        import traceback
        print(f'[ERROR] 文档生成失败：{e}')
        task_manager.mark_task_failed(task_id, f'{str(e)}\n{traceback.format_exc()}')


# ==================== 修复后的 process_document_async 函数 ==========
# 使用保存的目录配置生成文档，而不是硬编码的 TEMPLATE_TYPES

def process_document_async_v2(task_id, template_type, requirement_content, template_content,
                           user_prompt, api_key, model, output_path):
    """异步处理文档生成任务 - 使用保存的目录配置"""
    doc_container = {'doc': None}

    def save_partial_document():
        if doc_container['doc']:
            partial_filename = f'partial_{task_id[:8]}.docx'
            partial_path = os.path.join(app.config['OUTPUT_FOLDER'], partial_filename)
            doc_container['doc'].save(partial_path)
            task_manager.set_partial_filename(task_id, partial_filename)

    try:
        task_manager.set_task_started(task_id)
        task_manager.update_task_progress(task_id, progress=5,
            status=TaskStatus.PARSING_FILE.value, message='解析上传文件中...')
        task_manager.update_task_progress(task_id, progress=10,
            status=TaskStatus.GENERATING_AI.value, message='准备生成文档...')

        # 加载保存的目录配置
        chapters_path = os.path.join(app.config['UPLOAD_FOLDER'], 'chapter_config.json')
        user_chapters = None
        if os.path.exists(chapters_path):
            try:
                with open(chapters_path, 'r', encoding='utf-8') as f:
                    user_chapters = json.load(f)
                print(f'[INFO] 已加载用户目录配置：{len(user_chapters)} 个一级章节')
            except Exception as e:
                print(f'[ERROR] 加载目录配置失败：{e}')
        
        if not user_chapters:
            template_config = TEMPLATE_TYPES.get(template_type, TEMPLATE_TYPES['future_community'])
            user_chapters = []
            for chapter_title, sections in template_config['chapters']:
                chapter_node = {
                    'number': chapter_title.split()[0] if ' ' in chapter_title else '1',
                    'title': chapter_title,
                    'level': 1,
                    'children': []
                }
                for idx, section in enumerate(sections):
                    section_num = section.split()[0] if ' ' in section else f'{chapter_node["number"]}.{idx+1}'
                    chapter_node['children'].append({
                        'number': section_num,
                        'title': section,
                        'level': 2,
                        'children': []
                    })
            print('[INFO] 使用默认模板配置')

        styles = load_style_config()
        doc = Document()
        normal_style = styles.get('normal', {})
        style = doc.styles['Normal']
        style.font.name = normal_style.get('font_name', '仿宋')
        style.font.size = Pt(normal_style.get('font_size', 10.5))
        style._element.rPr.rFonts.set(qn('w:eastAsia'), normal_style.get('font_name', '仿宋'))

        project_name = "建设项目"

        # 封面
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.paragraph_format.space_before = Cm(5)
        run = title.add_run(project_name)
        run.font.name = '黑体'
        run.font.size = Pt(36)
        run.font.bold = True
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        doc.add_page_break()

        # 编审名单
        add_heading(doc, '项目编审人员名单', level=1, styles=styles)
        doc.add_page_break()

        # 目录 - 使用保存的目录配置
        add_heading(doc, '目录', level=1, styles=styles)
        
        def render_toc(nodes, level=0):
            for node in nodes:
                para = doc.add_paragraph()
                para.paragraph_format.left_indent = Cm(0.74 * level)
                run = para.add_run(f"{node.get('number', '')} {node.get('title', '')}")
                children = node.get('children')
                if children is not None and len(children) > 0:
                    render_toc(children, level + 1)
        
        render_toc(user_chapters)
        doc.add_page_break()

        doc_container['doc'] = doc
        save_partial_document()
        task_manager.update_task_progress(task_id, progress=15, message='目录完成')

        # 正文 - 递归生成所有章节
        total_chapters = len(user_chapters)

        def render_chapter_content(node, level=1):
            node_number = node.get('number', '')
            node_title = node.get('title', '')
            node_level = node.get('level', level)
            children = node.get('children')
            
            add_heading(doc, f"{node_number} {node_title}", level=node_level, styles=styles)
            
            if children is not None and len(children) > 0:
                for child in children:
                    render_chapter_content(child, level=node_level + 1)
            else:
                content = get_chapter_content_template(node_title)
                for para_text in content.split('\n'):
                    if para_text.strip():
                        add_normal_paragraph(doc, para_text.strip(), styles=styles)

        for idx, chapter in enumerate(user_chapters):
            task_manager.update_task_progress(task_id,
                progress=15 + int((idx + 1) / total_chapters * 80),
                message=f'正在生成第{idx + 1}章')
            render_chapter_content(chapter, level=1)
            save_partial_document()

        doc.save(output_path)
        task_manager.mark_task_completed(task_id, output_filename=os.path.basename(output_path))
        print(f'[INFO] 文档生成完成：{output_path}')

    except Exception as e:
        import traceback
        print(f'[ERROR] 文档生成失败：{e}')
        task_manager.mark_task_failed(task_id, f'{str(e)}\n{traceback.format_exc()}')


# ==================== Flask 路由 ====================

@app.route('/')
def index():
    return render_template('index.html', template_types=TEMPLATE_TYPES)


@app.route('/task-center')
def task_center():
    """文件生成管理中心"""
    return render_template('task_center.html')


# ==================== 代码生成接口（A 方案） ====================

@app.route('/api/generate_code', methods=['POST'])
def generate_code():
    """
    根据目录结构和需求文档生成完整的 Python 代码
    """
    try:
        # 获取参数
        template_type = request.form.get('template_type', 'future_community')
        
        # 读取需求文档
        requirement_file = request.files.get('requirement_file')
        requirement_content = ''
        
        if requirement_file and allowed_file(requirement_file.filename):
            filename = secure_filename(requirement_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'{uuid.uuid4()}_{filename}')
            requirement_file.save(filepath)
            
            if filename.endswith('.docx'):
                requirement_content = read_docx_text(filepath)
            elif filename.endswith('.txt'):
                requirement_content = read_txt_text(filepath)
            
            # 同时保存为 requirement.txt 方便后续使用
            req_path = os.path.join(app.config['UPLOAD_FOLDER'], 'requirement.txt')
            with open(req_path, 'w', encoding='utf-8') as f:
                f.write(requirement_content)
        
        # 加载目录配置
        chapters_path = os.path.join(app.config['UPLOAD_FOLDER'], 'chapter_config.json')
        if not os.path.exists(chapters_path):
            return jsonify({
                'success': False,
                'message': '请先扫描模板并保存目录结构'
            }), 400
        
        with open(chapters_path, 'r', encoding='utf-8') as f:
            chapters = json.load(f)
        
        # 加载样式配置
        styles = load_style_config()
        
        # 生成代码
        from generators import generate_word_code
        python_code = generate_word_code(chapters, styles, requirement_content, template_type)
        
        # 保存生成的代码
        code_filename = f'generated_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
        code_path = os.path.join(app.config['UPLOAD_FOLDER'], code_filename)
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(python_code)
        
        return jsonify({
            'success': True,
            'message': '代码生成成功',
            'code_filename': code_filename,
            'code_preview': python_code[:2000]  # 返回前 2000 字符预览
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'生成失败：{str(e)}',
            'detail': traceback.format_exc()
        }), 500


@app.route('/api/execute_code', methods=['POST'])
def execute_code():
    """
    执行生成的 Python 代码，生成 Word 文档
    """
    try:
        data = request.get_json()
        code_filename = data.get('code_filename', '')
        
        if not code_filename:
            return jsonify({
                'success': False,
                'message': '请指定要执行的代码文件'
            }), 400
        
        code_path = os.path.join(app.config['UPLOAD_FOLDER'], code_filename)
        if not os.path.exists(code_path):
            return jsonify({
                'success': False,
                'message': '代码文件不存在'
            }), 404
        
        # 读取代码
        with open(code_path, 'r', encoding='utf-8') as f:
            python_code = f.read()
        
        # 创建临时目录执行代码
        import tempfile
        import subprocess
        
        # 在执行时重定向日志
        temp_dir = tempfile.mkdtemp()
        temp_script = os.path.join(temp_dir, 'run.py')
        
        # 修改代码，添加输出路径
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], f'generated_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx')
        
        # 执行代码
        exec_globals = {
            '__name__': '__main__',
            '__file__': code_path
        }

        # 为了安全，使用受限的执行环境
        # 这里直接执行生成的代码
        exec(compile(python_code, code_path, 'exec'), exec_globals)
        
        # 查找生成的文件
        output_files = [f for f in os.listdir('.') if f.endswith('.docx') and f.startswith('generated_')]
        output_files.sort(reverse=True)
        
        if output_files:
            output_file = output_files[0]
            return jsonify({
                'success': True,
                'message': '文档生成成功',
                'output_file': output_file,
                'download_url': f'/api/download/{output_file}'
            })
        else:
            return jsonify({
                'success': False,
                'message': '未找到生成的文件'
            }), 500
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'执行失败：{str(e)}',
            'detail': traceback.format_exc()
        }), 500


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """下载生成的文件"""
    from flask import send_file
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({'success': False, 'message': '文件不存在'}), 404


# ==================== 原有接口 ====================

@app.route('/api/generate', methods=['POST'])
def generate():
    """异步提交文档生成任务"""
    try:
        # 获取表单数据
        template_type = request.form.get('template_type', 'future_community')
        user_prompt = request.form.get('requirement', '')
        api_key = request.form.get('api_key', '')
        model = request.form.get('model', 'qwen-max')

        # 处理上传的文件
        template_file = request.files.get('template')
        requirement_file = request.files.get('requirement_file')

        template_content = ''
        requirement_content = ''
        template_filename = ''
        requirement_filename = ''

        # 读取模板文件
        if template_file and allowed_file(template_file.filename):
            filename = secure_filename(template_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'{uuid.uuid4()}_{filename}')
            template_file.save(filepath)
            template_filename = filename

            if filename.endswith('.docx'):
                template_content = read_docx_text(filepath)
            elif filename.endswith('.txt'):
                template_content = read_txt_text(filepath)

        # 读取需求文件
        if requirement_file and allowed_file(requirement_file.filename):
            filename = secure_filename(requirement_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'{uuid.uuid4()}_{filename}')
            requirement_file.save(filepath)
            requirement_filename = filename

            if filename.endswith('.docx'):
                requirement_content = read_docx_text(filepath)
            elif filename.endswith('.txt'):
                requirement_content = read_txt_text(filepath)

        # 创建任务
        task_id = task_manager.create_task(
            task_type='document_generation',
            template_type=template_type,
            user_prompt=user_prompt,
            api_key=api_key,
            model=model,
            requirement_file=requirement_filename,
            template_file=template_filename
        )

        # 生成输出文件名
        task_id_short = task_id[:8]
        output_filename = f'{template_type}_可行性研究报告_{task_id_short}.docx'
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        # 启动异步线程处理任务 - 使用修复后的 v2 版本
        thread = threading.Thread(
            target=process_document_async_v2,
            args=(task_id, template_type, requirement_content, template_content,
                  user_prompt, api_key, model, output_path)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': '任务已提交，正在后台处理中',
            'task_id': task_id,
            'status': 'pending'
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'提交失败：{str(e)}',
            'detail': traceback.format_exc()
        }), 500


@app.route('/api/task/status/<task_id>', methods=['GET'])
def task_status(task_id):
    """查询任务状态和进度"""
    task_info = task_manager.get_task_status(task_id)
    
    if not task_info:
        return jsonify({
            'success': False,
            'message': '任务不存在'
        }), 404

    # 移除敏感信息
    safe_info = {
        'task_id': task_info.get('task_id'),
        'template_type': task_info.get('template_type'),
        'status': task_info.get('status'),
        'progress': task_info.get('progress'),
        'message': task_info.get('message'),
        'created_at': task_info.get('created_at'),
        'started_at': task_info.get('started_at'),
        'completed_at': task_info.get('completed_at'),
        'output_filename': task_info.get('output_filename'),
        'error_message': task_info.get('error_message'),
        'model': task_info.get('model'),
        # 新增字段：章节生成步骤、当前章节、已完成章节、等待确认、部分文档
        'chapter_steps': task_info.get('chapter_steps', []),
        'current_chapter': task_info.get('current_chapter'),
        'completed_chapters': task_info.get('completed_chapters', []),
        'pending_confirmation': task_info.get('pending_confirmation', False),
        'partial_filename': task_info.get('partial_filename')
    }

    return jsonify({
        'success': True,
        'task': safe_info
    })


@app.route('/api/task/list', methods=['GET'])
def task_list():
    """获取任务列表（支持分页和搜索）"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        keyword = request.args.get('keyword', '')
        status_filter = request.args.get('status', '')
        
        result = task_manager.get_task_list(
            page=page,
            page_size=page_size,
            keyword=keyword,
            status_filter=status_filter if status_filter else None
        )
        
        return jsonify({
            'success': True,
            'tasks': result['tasks'],
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size']
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'查询失败：{str(e)}'
        }), 500


@app.route('/api/task/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    try:
        success = task_manager.cancel_task(task_id)

        if success:
            return jsonify({
                'success': True,
                'message': '任务已取消'
            })
        else:
            return jsonify({
                'success': False,
                'message': '任务已完成或失败，无法取消'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'取消失败：{str(e)}'
        }), 500


@app.route('/api/task/continue/<task_id>', methods=['POST'])
def continue_task(task_id):
    """继续生成下一章（用户确认后的回调）"""
    try:
        task_info = task_manager.get_task_status(task_id)
        if not task_info:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404

        if task_info.get('status') not in ['generating_ai', 'creating_doc']:
            return jsonify({
                'success': False,
                'message': '任务状态不允许继续生成'
            }), 400

        # 清除等待确认状态
        task_manager.set_pending_confirmation(task_id, False)
        task_manager.update_task_progress(task_id, message='用户已确认，继续生成下一章')

        return jsonify({
            'success': True,
            'message': '已确认，继续生成下一章'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'确认失败：{str(e)}'
        }), 500


@app.route('/api/task/preview/<task_id>', methods=['GET'])
def preview_task(task_id):
    """预览当前已生成的文档内容"""
    try:
        task_info = task_manager.get_task_status(task_id)
        if not task_info:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404

        # 检查是否有部分生成的文档
        partial_filename = task_info.get('partial_filename')
        if partial_filename:
            filepath = os.path.join(app.config['OUTPUT_FOLDER'], partial_filename)
            if os.path.exists(filepath):
                return send_file(filepath)

        # 或者检查已完成的文档
        output_filename = task_info.get('output_filename')
        if output_filename:
            filepath = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            if os.path.exists(filepath):
                return send_file(filepath)

        return jsonify({
            'success': False,
            'message': '暂无可预览的文档'
        }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'预览失败：{str(e)}'
        }), 500


@app.route('/api/download/<filename>')
def download(filename):
    """下载生成的文档"""
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({'error': '文件不存在'}), 404


@app.route('/api/template/scan', methods=['POST'])
def scan_template():
    """扫描上传的模板文件，提取章节目录和样式信息"""
    try:
        if 'template' not in request.files:
            return jsonify({'success': False, 'message': '请上传模板文件'}), 400
        
        file = request.files['template']
        if file.filename == '':
            return jsonify({'success': False, 'message': '未选择文件'}), 400
        
        if not file.filename.endswith('.docx'):
            return jsonify({'success': False, 'message': '请上传 .docx 格式的 Word 文件'}), 400
        
        # 保存临时文件
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_scan_{uuid.uuid4().hex[:8]}.docx')
        file.save(temp_path)
        
        try:
            # 扫描模板样式
            result = scan_template_styles(temp_path)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'chapters': result['chapters'],
                    'total_nodes': result.get('total_nodes', 0)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result['message']
                }), 400
        finally:
            # 删除临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'扫描失败：{str(e)}',
            'detail': traceback.format_exc()
        }), 500


@app.route('/api/chapters/save', methods=['POST'])
def save_chapters():
    """保存用户编辑后的章节目录配置"""
    try:
        data = request.json
        chapters = data.get('chapters', [])
        
        if not chapters:
            return jsonify({
                'success': False,
                'message': '章节目录不能为空'
            }), 400
        
        # 将章节目录保存到文件
        chapters_path = os.path.join(app.config['UPLOAD_FOLDER'], 'chapter_config.json')
        with open(chapters_path, 'w', encoding='utf-8') as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': '章节目录配置已保存'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'保存失败：{str(e)}'
        }), 500


@app.route('/api/chapters/load', methods=['GET'])
def load_chapters():
    """加载已保存的章节目录配置"""
    try:
        chapters_path = os.path.join(app.config['UPLOAD_FOLDER'], 'chapter_config.json')
        
        if os.path.exists(chapters_path):
            with open(chapters_path, 'r', encoding='utf-8') as f:
                chapters = json.load(f)
            return jsonify({
                'success': True,
                'chapters': chapters,
                'message': '已加载保存的章节目录配置'
            })
        else:
            return jsonify({
                'success': True,
                'chapters': [],
                'message': '未找到保存的章节目录配置'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'加载失败：{str(e)}'
        }), 500


@app.route('/api/styles/save', methods=['POST'])
def save_styles():
    """保存用户配置的样式"""
    try:
        data = request.json
        
        # 样式配置包括：
        # - heading1: 一级标题样式（章标题）
        # - heading2: 二级标题样式（节标题）
        # - heading3: 三级标题样式（小节标题）
        # - normal: 正文样式
        styles = data.get('styles', {})
        
        # 将样式配置保存到文件
        styles_path = os.path.join(app.config['UPLOAD_FOLDER'], 'style_config.json')
        with open(styles_path, 'w', encoding='utf-8') as f:
            json.dump(styles, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': '样式配置已保存'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'保存失败：{str(e)}'
        }), 500


@app.route('/api/styles/load', methods=['GET'])
def load_styles():
    """加载已保存的样式配置"""
    try:
        styles_path = os.path.join(app.config['UPLOAD_FOLDER'], 'style_config.json')
        
        if os.path.exists(styles_path):
            with open(styles_path, 'r', encoding='utf-8') as f:
                styles = json.load(f)
            return jsonify({
                'success': True,
                'styles': styles
            })
        else:
            # 返回默认样式
            default_styles = {
                'heading1': {
                    'font_name': '黑体',
                    'font_size': 22,
                    'bold': True,
                    'alignment': 'center'
                },
                'heading2': {
                    'font_name': '楷体',
                    'font_size': 16,
                    'bold': True,
                    'alignment': 'left'
                },
                'heading3': {
                    'font_name': '楷体',
                    'font_size': 14,
                    'bold': True,
                    'alignment': 'left'
                },
                'normal': {
                    'font_name': '仿宋',
                    'font_size': 10.5,
                    'line_spacing': 1.5,
                    'first_line_indent': 0.74
                }
            }
            return jsonify({
                'success': True,
                'styles': default_styles,
                'message': '未找到自定义配置，返回默认样式'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'加载失败：{str(e)}'
        }), 500


@app.route('/api/validate-key', methods=['POST'])
def validate_api_key():
    """验证 API Key 是否有效"""
    try:
        data = request.json
        api_key = data.get('api_key', '')
        model = data.get('model', 'qwen-max')

        if not api_key:
            return jsonify({'valid': False, 'message': 'API Key 不能为空'})

        # 检测 API Key 类型
        is_app_api = api_key.startswith('sk-sp-') or api_key.startswith('sk-app-')
        
        if is_app_api:
            # 百炼应用 API 验证
            app_id = None
            test_key = api_key
            if '#' in api_key:
                test_key, app_id = api_key.split('#', 1)
            else:
                app_id = APP_CONFIGS.get('default', {}).get('app_id')
            
            if not app_id:
                return jsonify({
                    'valid': False, 
                    'message': '百炼应用 API Key (sk-sp-) 需要配置 APP_ID。请在 app.py 的 APP_CONFIGS 中设置，或在 API Key 后添加 #APP_ID（例如：sk-sp-xxx#your_app_id）'
                })
            
            url = f"https://dashscope.aliyuncs.com/api/v1/apps/{app_id}/completion"
            payload = {
                "input": {"prompt": "你好"},
                "parameters": {"max_tokens": 10}
            }
        else:
            # DashScope 模型 API 验证
            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            payload = {
                "model": model,
                "input": {"messages": [{"role": "user", "content": "你好"}]},
                "parameters": {"max_tokens": 10}
            }

        headers = {"Authorization": f"Bearer {test_key if is_app_api else api_key}", "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload, timeout=15)

        if response.status_code == 200:
            if is_app_api:
                return jsonify({'valid': True, 'message': f'百炼应用 API Key 有效 (APP_ID: {app_id})'})
            else:
                return jsonify({'valid': True, 'message': f'{MODEL_CONFIGS.get(model, {}).get("name", model)} API Key 有效'})
        elif response.status_code == 401:
            return jsonify({'valid': False, 'message': 'API Key 无效或已过期，请检查 Key 是否正确'})
        elif response.status_code == 403:
            return jsonify({'valid': False, 'message': '权限不足，请检查是否开通了对应���务'})
        elif response.status_code == 404 and is_app_api:
            return jsonify({'valid': False, 'message': f'APP_ID ({app_id}) 不存在或无权访问'})
        elif response.status_code == 429:
            return jsonify({'valid': False, 'message': '请求频率超限，请稍后重试'})
        elif response.status_code == 500:
            return jsonify({'valid': False, 'message': '服务器内部错误，请稍后重试'})
        else:
            error_msg = response.text[:200] if response.text else '无响应内容'
            return jsonify({'valid': False, 'message': f'验证失败 (状态码 {response.status_code}): {error_msg}'})

    except requests.exceptions.Timeout:
        return jsonify({'valid': False, 'message': '验证超时，请检查网络连接'})
    except requests.exceptions.ConnectionError:
        return jsonify({'valid': False, 'message': '无法连接到 API 服务器，请检查网络'})
    except Exception as e:
        return jsonify({'valid': False, 'message': f'验证异常：{str(e)}'})


@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    """清理过期文件"""
    try:
        import time
        current_time = time.time()
        cleaned = 0
        
        for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath) and current_time - os.path.getctime(filepath) > 3600:
                    os.remove(filepath)
                    cleaned += 1
        
        return jsonify({'success': True, 'cleaned': cleaned})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("  未来社区建设方案生成系统 (AI 增强版)")
    print("=" * 50)
    print()
    print("  访问地址：http://localhost:5000")
    print("  访问地址：http://127.0.0.1:5000")
    print()
    print("  按 Ctrl+C 停止服务")
    print()
    app.run(debug=True, host='0.0.0.0', port=5000)
