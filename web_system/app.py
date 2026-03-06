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


def scan_template_styles(file_path):
    """扫描 Word 模板文件，提取章节目录结构和样式信息（支持无限层级）"""
    try:
        doc = Document(file_path)
        chapters = []
        
        # 一级章节标题关键词（通常作为独立章节出现）
        level1_keywords = [
            '项目概况', '项目总论', '项目建设单位', '项目建设的必要性', '需求分析',
            '项目建设方案', '总体思路', '总体框架', '技术路线', '投资估算',
            '资金筹措', '效益分析', '风险分析', '结论', '建议', '结论和建议',
            '市场分析', '建设方案', '实施计划', '环保', '节能', '招标', '安全',
            '组织机构', '人员', '进度', '财务', '评价', '附录', '附件',
            '项目编审人员名单', '目录', '项目建设单位概况', '项目实施机构',
            '与数字化改革总体方案的关系', '应用系统设计', '国产化改造', '系统安全'
        ]
        
        # 二级章节标题关键词（通常作为子章节出现）
        level2_keywords = [
            '概况', '必要性', '分析', '方案', '思路', '框架', '路线', '目标',
            '内容', '规模', '周期', '估算', '筹措', '效益', '风险', '对策',
            '背景', '现状', '需求', '设计', '建设', '管理', '运维', '培训',
            '依据', '职能', '职责', '差距', '问题', '趋势', '评估'
        ]
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            # 跳过太短的文本（可能是页码）
            if len(text) < 2:
                continue
            
            # 跳过纯数字（可能是页码）
            if text.isdigit():
                continue
            
            # 跳过包含句号的文本（通常是正文）
            if '。' in text:
                continue
            
            # 跳过包含冒号的文本（通常是列表项或说明）
            if ':' in text:
                continue
            
            # 跳过以括号开头的文本（通常是列表项）
            if text.startswith('(') or text.startswith('（'):
                continue
            
            # 跳过以数字 + 顿号开头的文本（如"1、"）
            if re.match(r'^\d+[,、]', text):
                continue
            
            # 跳过包含"详见"的文本（通常是引用）
            if '详见' in text:
                continue
            
            # 跳过包含"预算"、"费用"、"表"的短文本（通常是表格标题）
            if len(text) < 15 and any(kw in text for kw in ['预算', '费用', '表', '清单']):
                continue
            
            # 尝试匹配带编号的章节标题（支持无限层级）
            numbered_match = re.match(r'^(\d+(?:\.\d+)*)\s+(.+)$', text)
            
            if numbered_match:
                number = numbered_match.group(1)
                title = numbered_match.group(2)
                level = number.count('.') + 1
                
                # 排除类似"1、"这样的列表项
                if title.startswith('、') or title.startswith('，') or title.startswith(';'):
                    continue
                
                # 排除过长的文本
                if len(title) > 80:
                    continue
                
                # 排除 GB/T 等标准编号
                if title.startswith('《') or 'GB/T' in title or 'DB33' in title:
                    continue
                
                style_info = extract_paragraph_style(para)
                
                chapter_node = {
                    'number': number,
                    'title': title,
                    'level': level,
                    'style': style_info,
                    'children': []
                }
                
                add_to_parent(chapters, chapter_node, number)
            else:
                # 尝试匹配没有编号的章节标题
                is_chapter = False
                level = 1
                
                # 检查是否包含一级章节关键词（且文本较短）
                if len(text) < 35:
                    for keyword in level1_keywords:
                        if text == keyword or text.startswith(keyword) or keyword in text:
                            is_chapter = True
                            level = 1
                            break
                
                # 如果不是章节，继续检查是否是二级章节
                if not is_chapter and len(text) < 25:
                    for keyword in level2_keywords:
                        if keyword in text and len(text) < 20:
                            is_chapter = True
                            level = 2
                            break
                
                if is_chapter:
                    style_info = extract_paragraph_style(para)
                    
                    chapter_node = {
                        'number': '',  # 编号由用户后续编辑
                        'title': text,
                        'level': level,
                        'style': style_info,
                        'children': []
                    }
                    
                    chapters.append(chapter_node)
        
        return {
            'success': True,
            'chapters': chapters,
            'message': f'成功扫描 {len(chapters)} 个章节',
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
    """递归查找指定编号的节点"""
    for chapter in chapters:
        if chapter['number'] == number:
            return chapter
        # 在子节点中递归查找
        if chapter.get('children'):
            result = find_node_by_number(chapter['children'], number)
            if result:
                return result
    return None


def count_all_nodes(chapters):
    """递归统计所有节点数量"""
    count = 0
    for chapter in chapters:
        count += 1
        if chapter.get('children'):
            count += count_all_nodes(chapter['children'])
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
    """使用 AI 生成指定小节的内容"""

    prompt = f"""你是一位专业的可行性研究报告撰写专家。请根据以下材料，为"{section_title}"这一小节撰写专业、详细的正文内容。

【需求文档内容】
{requirement_content[:3000] if requirement_content else '暂无需求文档'}

【模板格式参考】
{template_content[:2000] if template_content else '暂无模板'}

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

    for idx, chapter in enumerate(user_chapters):
        # 添加章节标题
        add_heading(doc, f"{chapter['number']} {chapter['title']}", level=1, styles=styles)

        # 递归生成子章节
        generate_chapter_content(doc, chapter, requirement_content, template_content, 
                                  user_prompt, api_key, model, styles)

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
    """递归渲染目录"""
    for chapter in chapters:
        para = doc.add_paragraph()
        para.paragraph_format.left_indent = Cm(0.74 * level)
        run = para.add_run(f"{chapter['number']} {chapter['title']}")
        run.font.name = '宋体'
        run.font.size = Pt(10.5)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        
        if chapter.get('children'):
            render_doc_toc(doc, chapter['children'], styles, level + 1)


def generate_chapter_content(doc, chapter_node, requirement_content, template_content, 
                              user_prompt, api_key, model, styles, depth=0):
    """递归生成章节内容"""
    
    # 生成子章节内容
    if chapter_node.get('children'):
        for child in chapter_node['children']:
            # 添加子章节标题
            level = min(child.get('level', 2), 4)  # 最多支持 4 级标题
            add_heading(doc, f"{child['number']} {child['title']}", level=level, styles=styles)
            
            # 如果有更深层级的子节点，递归处理
            if child.get('children'):
                generate_chapter_content(doc, child, requirement_content, template_content,
                                          user_prompt, api_key, model, styles, depth + 1)
            else:
                # 叶子节点，生成内容
                if api_key:
                    ai_content = generate_content_with_ai(
                        requirement_content,
                        template_content,
                        user_prompt,
                        child['title'],
                        api_key,
                        model
                    )
                    cleaned_paragraphs = clean_ai_content(ai_content, child['title'])
                    for para_text in cleaned_paragraphs:
                        if para_text.strip():
                            add_normal_paragraph(doc, para_text.strip(), styles=styles)
                else:
                    default_content = f"""{child['title']}的具体内容。本项目按照相关规范和要求进行编制，确保符合可行性研究报告的标准。

结合需求文档中的具体要求，本节内容应根据项目实际情况进行详细阐述。"""
                    for para_text in default_content.split('\n'):
                        if para_text.strip():
                            add_normal_paragraph(doc, para_text.strip(), styles=styles)


def generate_chapter(doc, chapter_title, sections, requirement_content, template_content,
                     user_prompt, api_key, model, section_title_prefix=''):
    """生成单个章节的内容"""
    add_heading(doc, chapter_title, level=1)
    
    for section_title in sections:
        add_heading(doc, section_title, level=2)
        
        if api_key:
            ai_content = generate_content_with_ai(
                requirement_content,
                template_content,
                user_prompt,
                section_title,
                api_key,
                model
            )
            cleaned_paragraphs = clean_ai_content(ai_content, section_title)
            for para_text in cleaned_paragraphs:
                if para_text.strip():
                    add_normal_paragraph(doc, para_text.strip())
        else:
            default_content = f"""{section_title}的具体内容。本项目按照相关规范和要求进行编制，确保符合可行性研究报告的标准。

结合需求文档中的具体要求，本节内容应根据项目实际情况进行详细阐述。包括但不限于项目背景、实施必要性、技术方案、投资估算等方面的内容。

在编制过程中，充分考虑了项目的特点、建设条件、技术要求等因素，确保报告内容的科学性、合理性和可操作性。"""
            for para_text in default_content.split('\n'):
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
        
        # 逐章生成
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
        task_manager.set_partial_filename(task_id, None)  # 清除部分文件标记
        task_manager.mark_task_completed(task_id, output_filename=os.path.basename(output_path))
        
    except Exception as e:
        import traceback
        task_manager.mark_task_failed(task_id, f'{str(e)}\n{traceback.format_exc()}')


# ==================== Flask 路由 ====================

@app.route('/')
def index():
    return render_template('index.html', template_types=TEMPLATE_TYPES)


@app.route('/task-center')
def task_center():
    """文件生成管理中心"""
    return render_template('task_center.html')


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

        # 启动异步线程处理任务
        thread = threading.Thread(
            target=process_document_async,
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
